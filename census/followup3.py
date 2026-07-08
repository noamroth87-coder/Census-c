"""Follow-up 3: OFA-refund detection & true bid for the >$1k tier. Census close.
Bounded fetch: 297 eth_getBlockReceipts (one call/block = every tx's index/from/to/logs)
+ traces of (arb, successor) for BACKRUN arbs only (native-ETH refunds). Hard cap 3000."""
import json, os
from collections import defaultdict, Counter
from census.report import UF, pct, med
from census.rpc import call, map_fn
from census.price import token_to_eth
from census.trace import trace_tx, h2i
from census.config import SWAP_TOPICS, TRANSFER

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CALLS = {"receipts": 0, "receipt_fail": 0, "traces": 0}

def ta(t): return "0x" + t[-40:]
def bucket(g): return "<$10" if g < 10 else "$10-100" if g < 100 else "$100-1k" if g < 1000 else ">$1k"
def f2(x, d=2): return f"{x:,.{d}f}" if x is not None else "n/a"

def tx_pools(logs):
    out = set()
    for l in logs:
        tp = l.get("topics") or []
        if tp and tp[0] and tp[0].lower() in SWAP_TOPICS:
            out.add(l["address"].lower())
    return out

def transfers_to(logs, victim):
    """ERC20 Transfer events crediting victim -> {token: total_raw}."""
    out = defaultdict(int)
    for l in logs:
        tp = l.get("topics") or []
        if tp and tp[0].lower() == TRANSFER and len(tp) == 3 and ta(tp[2]).lower() == victim:
            try: out[l["address"].lower()] += h2i(l["data"][:66])
            except Exception: pass
    return out

def main():
    arbs = [x for x in (json.loads(l) for l in open(os.path.join(OUT, "arbs.jsonl"))) if x["verdict"] == "arb"]
    uf = UF()
    for r in arbs:
        uf.union(("b", r["beneficiary"]), ("f", r["tx_from"]) if r.get("tx_from") else ("b", r["beneficiary"]))
    cid = {r["txhash"]: uf.find(("b", r["beneficiary"])) for r in arbs}
    # cluster -> set of controlled addresses (beneficiary + tx_from)
    cl_addrs = defaultdict(set)
    for r in arbs:
        c = cid[r["txhash"]]
        cl_addrs[c].add(r["beneficiary"]);
        if r.get("tx_from"): cl_addrs[c].add(r["tx_from"])
    # CONCENTRATED clusters from Follow-up 2 (by lead address)
    conc_leads = {"0x01fdc48ba090", "0x45e9b0494217", "0xad17043228"}
    def is_conc(c):
        return any(any(a.startswith(p) for a in cl_addrs[c]) for p in conc_leads)

    big = [r for r in arbs if bucket(r["gross_usd"]) == ">$1k"]
    by_block = defaultdict(list)
    for r in big: by_block[r["block"]].append(r)
    blocks = sorted(by_block)
    print(f"estimate: {len(blocks)} getBlockReceipts + up to {2*len(big)} traces = <= {len(blocks)+2*len(big)} calls (cap 3000)")

    # ---- fetch block receipts (one call/block) ----
    def fetch(bn):
        r = call("eth_getBlockReceipts", [hex(bn)])
        return (bn, r if isinstance(r, list) else None)
    res = map_fn(fetch, blocks, workers=16)
    blockdata = {}
    for bn, r in res:
        CALLS["receipts"] += 1
        if r is None: CALLS["receipt_fail"] += 1; continue
        idx_map = {}
        for rc in r:
            idx_map[h2i(rc.get("transactionIndex"))] = rc
        blockdata[bn] = idx_map
    fail_pct = 100*CALLS["receipt_fail"]/max(CALLS["receipts"], 1)
    print(f"receipts fetched: {CALLS['receipts']-CALLS['receipt_fail']}/{CALLS['receipts']} (fail {fail_pct:.1f}%)")
    if fail_pct > 15:
        print("ABORT: >15% receipt fetch failure"); return

    # ---- Task 1: classify predecessor ----
    recs = []  # per-arb enriched record
    for r in big:
        bn = r["block"]; idx = r["tx_index"]; c = cid[r["txhash"]]
        idx_map = blockdata.get(bn, {})
        arb_rc = idx_map.get(idx)
        arb_pools = tx_pools(arb_rc["logs"]) if arb_rc else set()
        pred = idx_map.get(idx-1)
        succ = idx_map.get(idx+1)
        label = "STANDALONE"; victim = None
        if pred is None:
            label = "STANDALONE"  # no predecessor (index 0)
        else:
            pfrom = (pred.get("from") or "").lower(); pto = (pred.get("to") or "").lower()
            ppools = tx_pools(pred["logs"])
            if pfrom in cl_addrs[c] or pto in cl_addrs[c]:
                label = "SELF-SEQUENCED"
            elif ppools & arb_pools and (pred["logs"]):
                label = "BACKRUN"; victim = pfrom
            else:
                label = "STANDALONE"
        recs.append(dict(r=r, c=c, idx=idx, label=label, victim=victim,
                         arb_rc=arb_rc, succ=succ, arb_pools=arb_pools))

    # ---- Task 2: refund detection on BACKRUN (traces for native ETH) ----
    backrun = [x for x in recs if x["label"] == "BACKRUN"]
    print(f"BACKRUN arbs: {len(backrun)} -> tracing arb+successor for native ETH refunds")
    hdr_cache = {}
    def miner_of(bn):
        if bn not in hdr_cache:
            h = call("eth_getBlockByNumber", [hex(bn), False])
            hdr_cache[bn] = (h.get("miner") or "").lower() if isinstance(h, dict) else ""
        return hdr_cache[bn]
    def refund_for(x):
        r = x["r"]; victim = x["victim"]; bn = r["block"]; blk = bn
        refund_eth = 0.0
        # (1) token transfers to victim in arb tx logs
        for tok, raw in transfers_to(x["arb_rc"]["logs"], victim).items():
            ve, _ = token_to_eth(tok, raw, blk); refund_eth += ve or 0
        # (2) token transfers to victim in successor tx (same block), if not victim's own tx
        succ = x["succ"]
        if succ and (succ.get("from") or "").lower() != victim:
            for tok, raw in transfers_to(succ["logs"], victim).items():
                ve, _ = token_to_eth(tok, raw, blk); refund_eth += ve or 0
        # (3) native ETH to victim via traces of arb tx + successor
        m = ""  # miner not needed for victim-directed transfers
        tr = trace_tx(r["txhash"], m); CALLS["traces"] += 1
        refund_eth += max(tr.get("eth_delta", {}).get(victim, 0), 0)/1e18
        if succ and (succ.get("from") or "").lower() != victim:
            tr2 = trace_tx(succ.get("transactionHash") or succ.get("hash"), m); CALLS["traces"] += 1
            refund_eth += max(tr2.get("eth_delta", {}).get(victim, 0), 0)/1e18
        return refund_eth
    ref = map_fn(refund_for, backrun, workers=12)
    for x, rf in zip(backrun, ref):
        x["refund_eth"] = rf
        x["refund_pct"] = 100*rf/x["r"]["gross_eth"] if x["r"]["gross_eth"] > 0 else 0
        x["refunded"] = x["refund_pct"] >= 1.0
    print(f"traces used: {CALLS['traces']}; total calls: {CALLS['receipts']+CALLS['traces']+len(hdr_cache)}")

    render(recs, backrun, big, arbs, cid, cl_addrs, is_conc, conc_leads)

def render(recs, backrun, big, arbs, cid, cl_addrs, is_conc, conc_leads):
    L = []; A = L.append
    A(""); A("---"); A("")
    A("## Follow-up 3: refund detection and true bid — census close")
    A("")
    tot_calls = CALLS["receipts"] + CALLS["traces"]
    A(f"*Final bounded fetch: {CALLS['receipts']} `eth_getBlockReceipts` (one call/block ⇒ every tx's "
      f"index, from/to, logs) + {CALLS['traces']} traces (arb + successor of BACKRUN arbs, for native-ETH "
      f"refunds) = **{tot_calls} RPC calls**, under the 3,000 cap. Receipt-fetch failures: "
      f"{100*CALLS['receipt_fail']/max(CALLS['receipts'],1):.1f}% (<15% ⇒ proceeded). Scope: the "
      f"{len(set(r['block'] for r in big))} blocks holding the {len(big)} >$1k measured arbs. All [M].*")
    A("")

    # -------- Task 1 --------
    A("### Task 1 — Backrun-adjacency of >$1k arbs [M]")
    A("")
    A("Predecessor = the tx immediately before the arb in-block. **BACKRUN** = predecessor is a swap "
      "touching ≥1 of the arb's own pools, by a different party (the victim). **SELF-SEQUENCED** = "
      "predecessor sent/received by the arb's own cluster. **STANDALONE** = unrelated predecessor (or "
      "arb is first in block).")
    A("")
    ov = Counter(x["label"] for x in recs)
    A("| Class | Count | Share |")
    A("|---|--:|--:|")
    for k in ("BACKRUN", "SELF-SEQUENCED", "STANDALONE"):
        A(f"| {k} | {ov[k]} | {100*ov[k]/len(recs):.1f}% |")
    A(f"| **total** | {len(recs)} | 100% |")
    A("")
    # per top cluster (by >$1k arb count)
    bycl = defaultdict(list)
    for x in recs: bycl[x["c"]].append(x)
    top = sorted(bycl.items(), key=lambda kv: -len(kv[1]))[:8]
    A("Per top cluster (by >$1k arb count):")
    A("")
    A("| Lead address | Arbs | BACKRUN | SELF-SEQ | STANDALONE |")
    A("|---|--:|--:|--:|--:|")
    for c, xs in top:
        lead = Counter(x["r"]["beneficiary"] for x in xs).most_common(1)[0][0]
        cc = Counter(x["label"] for x in xs)
        tag = " *(CONC)*" if is_conc(c) else ""
        A(f"| `{lead[:12]}…`{tag} | {len(xs)} | {cc['BACKRUN']} | {cc['SELF-SEQUENCED']} | {cc['STANDALONE']} |")
    A("")

    # -------- Task 2 --------
    A("### Task 2 — Refund detection on BACKRUN arbs [M]")
    A("")
    nb = len(backrun); refd = [x for x in backrun if x.get("refunded")]
    A(f"Victim = predecessor's originating address. A transfer to the victim (token/WETH in logs, or "
      f"native ETH via trace) inside the arb tx or its in-block successor, **≥1% of the arb's gross**, "
      f"= REFUNDED. That refund is the real competitive bid returned to order flow.")
    A("")
    A("| Metric | Value |")
    A("|---|--:|")
    A(f"| BACKRUN arbs | {nb} |")
    A(f"| REFUNDED (≥1% gross to victim) | {len(refd)} ({100*len(refd)/nb if nb else 0:.1f}%) |")
    if refd:
        rp = [x["refund_pct"] for x in refd]
        A(f"| Refund %gross — median | {f2(med(rp))}% |")
        A(f"| Refund %gross — p25 / p75 | {f2(pct(rp,.25))}% / {f2(pct(rp,.75))}% |")
    A("")
    if not refd:
        A("> **No BACKRUN arb refunds ≥1% of gross were detected on-chain.** Either these winners run no "
          "OFA/refund program, or refunds settle by a path invisible to receipts+traces (see closing "
          "unmeasurables). The real competitive bid in this tier is not visible on-chain.")
        A("")

    # -------- Task 3 --------
    A("### Task 3 — True winner take, >$1k tier [M/derived]")
    A("")
    A("True net = gross − gas − builder payment − refund. (Priority fee is already inside *gas* = "
      "gas_used × effective gas price, so it is not subtracted twice; the OFA refund is the extra bid "
      "on top.) True net margin = true net ÷ gross.")
    A("")
    refmap = {id(x): x.get("refund_eth", 0) for x in backrun}
    def truenet(x):
        r = x["r"]; rf = x.get("refund_eth", 0) if x["label"] == "BACKRUN" else 0
        return r["net_eth"] - rf
    def cat(x):
        if x["label"] == "BACKRUN": return "REFUNDED" if x.get("refunded") else "BACKRUN-unrefunded"
        if x["label"] == "SELF-SEQUENCED": return "SELF-SEQUENCED"
        return "STANDALONE"
    catg = defaultdict(list)
    for x in recs: catg[cat(x)].append(x)
    A("| Category | Count | Median true-net margin % | p75 true-net margin % |")
    A("|---|--:|--:|--:|")
    for k in ("REFUNDED", "BACKRUN-unrefunded", "STANDALONE", "SELF-SEQUENCED"):
        xs = catg.get(k, [])
        if not xs:
            A(f"| {k} | 0 | — | — |"); continue
        m = [100*truenet(x)/x["r"]["gross_eth"] for x in xs if x["r"]["gross_eth"] > 0]
        A(f"| {k} | {len(xs)} | {f2(med(m))}% | {f2(pct(m,.75))}% |")
    A("")
    # per top cluster dominant category
    A("Per top cluster — dominant category (and CONCENTRATED clusters explicitly):")
    A("")
    A("| Lead address | Arbs | Dominant category | Median true-net margin % | CONC? |")
    A("|---|--:|---|--:|:--:|")
    shown = set()
    def emit_cluster(c, xs):
        lead = Counter(x["r"]["beneficiary"] for x in xs).most_common(1)[0][0]
        dom = Counter(cat(x) for x in xs).most_common(1)[0][0]
        m = [100*truenet(x)/x["r"]["gross_eth"] for x in xs if x["r"]["gross_eth"] > 0]
        A(f"| `{lead[:12]}…` | {len(xs)} | {dom} | {f2(med(m))}% | {'yes' if is_conc(c) else ''} |")
    for c, xs in top:
        emit_cluster(c, xs); shown.add(c)
    # ensure the 3 CONCENTRATED clusters appear
    for c, xs in bycl.items():
        if c not in shown and is_conc(c):
            emit_cluster(c, xs)
    A("")

    # -------- Closing summary --------
    A("### Census closing summary [M]")
    A("")
    span = json.load(open(os.path.join(OUT, "window.json")))["span_days"]
    conc_cids = set(c for c in cl_addrs if is_conc(c))
    A("Per size bucket: **addressable** arbs/day (excluding the 3 CONCENTRATED clusters' volume), and "
      "median true-net margin. Refund/OFA is measured only in the >$1k tier (this fetch); for smaller "
      "tiers 'true net' = gross − gas − builder (refund unmeasured — stated, not assumed zero).")
    A("")
    A("| Bucket | Arbs | Addressable arbs/day | Median true-net margin % | Refund measured? |")
    A("|---|--:|--:|--:|:--:|")
    tn_big = {id(x): truenet(x) for x in recs}
    for b in ("<$10", "$10-100", "$100-1k", ">$1k"):
        rows = [r for r in arbs if bucket(r["gross_usd"]) == b]
        addr = [r for r in rows if cid[r["txhash"]] not in conc_cids]
        if b == ">$1k":
            m = [100*tn_big[id(x)]/x["r"]["gross_eth"] for x in recs if x["r"]["gross_eth"] > 0]
            refm = "yes"
        else:
            m = [100*r["net_eth"]/r["gross_eth"] for r in rows if r["gross_eth"] > 0]
            refm = "no (unmeasured)"
        A(f"| {b} | {len(rows):,} | {len(addr)/span:,.0f} | {f2(med(m))}% | {refm} |")
    A("")
    A("**Known-unmeasurables that still apply (stated, not estimated):** off-chain / out-of-band "
      "builder payments; searcher–builder profit-sharing and periodic netting; exclusive order-flow "
      "agreements; same-entity searcher+builder on unlinked addresses (self-building reads as a low "
      "bid); priority-fee-only private bundles (private flow is a lower bound); bundle-level payments "
      "in a separate tx not attributed here; OFA refunds settled off-chain or via the builder rather "
      "than an on-chain transfer to the victim; and the census's own coverage bound — 71.3% of detected "
      "arbs measured, the rest unpriceable or failed-to-measure. **The census is the measured map "
      "within these bounds; it is not a claim about what happens outside them.**")
    A("")
    A("*Census complete.*")

    with open(os.path.join(OUT, "CENSUS_REPORT.md"), "a") as f:
        f.write("\n".join(L))
    print("appended Follow-up 3:", len(L), "lines")

if __name__ == "__main__":
    main()

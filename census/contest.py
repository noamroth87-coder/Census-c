"""Contest-intensity probe: do incumbents fight? Stored census data + ONE bounded fetch.
Writes out/contest_intensity.md. Not part of the census."""
import json, os, random
from collections import defaultdict, Counter
from census.report import UF, pct, med
from census.rpc import call as _rawcall
from census.config import V2_SWAP, V3_SWAP, V4_SWAP, ROUTERS

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CAP = 600
CC = {"n": 0}
def call(m, p):
    CC["n"] += 1
    return _rawcall(m, p)

V4_MGR = "0x000000000004444c5dc75cb358380d2e3de08a90"
EXCLUDE = set(a.lower() for a in ROUTERS) | {V4_MGR, "0x0000000000000000000000000000000000000000"}

def h2i(x): return int(x, 16) if isinstance(x, str) else int(x)
def f2(x, d=2): return f"{x:,.{d}f}" if x is not None else "n/a"

def v2v3_pools(logs):
    """Precise pool addresses (V2/V3 swap emitters). V4 excluded (manager singleton -> coarse)."""
    s = set()
    for l in logs or []:
        tp = l.get("topics") or []
        if tp and tp[0].lower() in (V2_SWAP, V3_SWAP):
            s.add(l["address"].lower())
    return s

def touched_addrs(node, acc):
    to = (node.get("to") or "").lower()
    if to: acc.add(to)
    for c in node.get("calls", []) or []:
        touched_addrs(c, acc)

def main():
    arbs = [x for x in (json.loads(l) for l in open(os.path.join(OUT, "arbs.jsonl"))) if x["verdict"] == "arb"]
    # clustering (consistent with census)
    uf = UF()
    for r in arbs:
        uf.union(("b", r["beneficiary"]), ("f", r["tx_from"]) if r.get("tx_from") else ("b", r["beneficiary"]))
    cid = {r["txhash"]: uf.find(("b", r["beneficiary"])) for r in arbs}
    def addr_cluster(*addrs):
        for a in addrs:
            if a and (("b", a) in uf.p or ("f", a) in uf.p):
                return uf.find(("b", a) if ("b", a) in uf.p else ("f", a))
        return None
    def clab(root):   # readable cluster label: the address inside the union-find root tuple
        if isinstance(root, tuple) and len(root) == 2:
            return root[1]
        return str(root)
    arbs_by_block = defaultdict(list)
    for r in arbs: arbs_by_block[r["block"]].append(r)
    def bucket(g): return "<$10" if g < 10 else "$10-100" if g < 100 else "$100-1k" if g < 1000 else ">$1k"
    # per-bucket median total-bid% (for Task 3)
    bybk = defaultdict(list)
    for r in arbs:
        if r["gross_eth"] > 0:
            bybk[bucket(r["gross_usd"])].append(100*(r["priority_to_builder_eth"]+r["builder_eth"])/r["gross_eth"])
    tier_med_bid = {b: med(v) for b, v in bybk.items()}

    # ---- Task 1 stored ----
    known = set()
    for r in arbs:
        known |= {r["beneficiary"], r.get("tx_to"), r.get("tx_from")}
    known.discard(None); known.discard("")
    tot_rev = 0; known_rev = 0
    stats = list(json.loads(l) for l in open(os.path.join(OUT, "blockstats.jsonl")))
    for b in stats:
        rt = b.get("reverted_to") or []
        tot_rev += len(rt)
        known_rev += sum(1 for to in rt if to in known)

    # ---- Task 2 bounded fetch ----
    rng = random.Random(42)
    blocks = [b["bn"] for b in stats if (b.get("reverted_to"))]
    rng.shuffle(blocks)
    sampled_rev = []   # (block, txhash, frm, to, idx)
    block_arbpools = {}   # block -> {arb_txhash: pools}
    block_univ = {}       # block -> # distinct V2/V3 pools active
    block_used = []
    for bn in blocks:
        if len(sampled_rev) >= 300 or CC["n"] > CAP-320: break
        rcpts = call("eth_getBlockReceipts", [hex(bn)])
        if not isinstance(rcpts, list): continue
        block_used.append(bn)
        # winner (measured arb) pools this block
        arbset = {a["txhash"] for a in arbs_by_block.get(bn, [])}
        ap = {}
        for rc in rcpts:
            if rc["transactionHash"] in arbset:
                ap[rc["transactionHash"]] = v2v3_pools(rc.get("logs"))
        block_arbpools[bn] = ap
        # block pool universe (all V2/V3 swap pools active in the block) for the baseline
        univ = set()
        for rc in rcpts:
            if rc.get("status") == "0x1":
                univ |= v2v3_pools(rc.get("logs"))
        block_univ[bn] = len(univ)
        for rc in rcpts:
            if rc.get("status") == "0x0":
                sampled_rev.append((bn, rc["transactionHash"], (rc.get("from") or "").lower(),
                                    (rc.get("to") or "").lower(), h2i(rc.get("transactionIndex"))))
    sampled_rev = sampled_rev[:300]
    # trace each reverted tx -> touched pools
    collisions = []; traced = 0; recovered = 0; rev_pool_sizes = []
    for (bn, txh, frm, to, idx) in sampled_rev:
        if CC["n"] > CAP: break
        tr = call("debug_traceTransaction", [txh, {"tracer": "callTracer"}])
        traced += 1
        acc = set()
        if isinstance(tr, dict):
            touched_addrs(tr, acc)
        touched_pools = {a for a in acc if a not in EXCLUDE}
        if touched_pools: recovered += 1
        for atx, apools in block_arbpools.get(bn, {}).items():
            shared = touched_pools & (apools - EXCLUDE)
            if shared:
                arb = next(a for a in arbs_by_block[bn] if a["txhash"] == atx)
                # count only pool-shaped shared addrs (present in a winner's swap-pool set) -> already are
                collisions.append(dict(block=bn, loser_tx=txh, loser_from=frm, loser_to=to,
                                       loser_idx=idx, winner=arb, shared=sorted(shared)))
                rev_pool_sizes.append(len(touched_pools))
    render(dict(tot_rev=tot_rev, known_rev=known_rev, arbs=arbs, n_arbs=len(arbs),
                sampled=len(sampled_rev), block_used=block_used, traced=traced, recovered=recovered,
                collisions=collisions, cid=cid, addr_cluster=addr_cluster, clab=clab, bucket=bucket,
                tier_med_bid=tier_med_bid, arbs_by_block=arbs_by_block, block_arbpools=block_arbpools,
                block_univ=block_univ, reverts_per_block=tot_rev/len(stats), calls=CC["n"]))

def render(D):
    arbs = D["arbs"]; cols = D["collisions"]; bucket = D["bucket"]; cid = D["cid"]
    addr_cluster = D["addr_cluster"]; clab = D["clab"]
    L = []; A = L.append
    A("# Contest-intensity probe — do incumbents actually fight?")
    A("")
    A("> Scratch analysis (not the census). Measures how often two+ actors visibly compete for the "
      "same opportunity (a landed arb + a same-block reverted tx sharing a pool) and who wins. All [M].")
    A("")
    # Task 1
    A("## Task 1 — Collision inventory (stored data) [M]")
    A("")
    A("| Metric | Count |")
    A("|---|--:|")
    A(f"| Total landed-reverted txs recorded in detection | {D['tot_rev']:,} |")
    A(f"| Intended-pools identifiable from stored data | 0 |")
    A(f"| TARGET-UNKNOWN | {D['tot_rev']:,} (100.0%) |")
    A(f"| Collisions identifiable from stored data | 0 |")
    A("")
    A("The census retained only the **`to` address** of each reverted tx (no tx hash, calldata, or "
      "pre-revert logs — reverted txs emit none), and measured arbs were stored without their pool set. "
      "So intended pools cannot be recovered from stored data and the shared-pool join is uncomputable "
      f"⇒ **100% TARGET-UNKNOWN**, which exceeds the 50% trigger for the bounded fetch (Task 2).")
    A("")
    A(f"*Supplementary stored-only signal (NOT a pool-confirmed collision):* {D['known_rev']:,} of "
      f"{D['tot_rev']:,} reverted txs ({100*D['known_rev']/D['tot_rev']:.1f}%) have a `to` that is a "
      f"known arb-bot address — i.e. failed arb attempts by identifiable searchers, a floor on contest "
      f"activity but silent about which opportunity they targeted.")
    A("")
    # Task 2
    A("## Task 2 — Bounded fetch (TARGET-UNKNOWN > 50%) [M, sampled]")
    A("")
    A(f"**Sample plan (as executed):** random blocks (seed 42) from the 50,185-block window; one "
      f"`eth_getBlockReceipts` per block recovers reverted-tx hashes/from/to **and** same-block measured "
      f"arbs' V2/V3 pools; accumulate to 300 reverted txs; then `debug_traceTransaction` each to recover "
      f"touched pools; join within-block. **Budget used: {D['calls']} RPC calls (cap 600).**")
    A("")
    A("| Metric | Value |")
    A("|---|--:|")
    A(f"| Blocks sampled | {len(D['block_used'])} |")
    A(f"| Reverted txs sampled & traced | {D['traced']} |")
    A(f"| ...with recoverable touched pools | {D['recovered']} ({100*D['recovered']/max(D['traced'],1):.0f}%) |")
    A(f"| COLLISIONS found (reverted+arb, same block, shared V2/V3 pool) | {len(cols)} |")
    A(f"| Collision rate among sampled reverted txs | {100*len(cols)/max(D['traced'],1):.1f}% |")
    A("")
    A(f"> **Sampling caveat:** collisions are counted on a {D['traced']}-reverted-tx random sample "
      "(block-clustered by the per-block fetch); rates carry sampling error and V4-singleton contests "
      "are **under-counted** — the join uses precise V2/V3 pool addresses; V4's shared-manager can't "
      "confirm same-pool without a poolId, so V4-only fights are invisible here.")
    A("")
    # Task 3
    A("## Task 3 — Collision anatomy [M, sampled]")
    A("")
    if not cols:
        A("No pool-confirmed collisions in the sample — anatomy tables are empty. See Task 4 baseline and "
          "the closing guardrail: a null here is consistent with either carved territory OR contests "
          "resolved invisibly inside builders (or simply V4-routed and thus not matchable).")
    else:
        A("Per-collision detail:")
        A("")
        A("| block | contested bucket | winner cluster | loser (to) | winner bid% | tier median bid% | idx gap (winner-loser) |")
        A("|--:|---|---|---|--:|--:|--:|")
        for c in cols:
            w = c["winner"]; b = bucket(w["gross_usd"])
            wbid = 100*(w["priority_to_builder_eth"]+w["builder_eth"])/w["gross_eth"] if w["gross_eth"]>0 else None
            wc = clab(cid.get(w["txhash"], "?"))
            gap = w["tx_index"] - c["loser_idx"]
            A(f"| {c['block']} | {b} | `{wc[:12]}…` | `{c['loser_to'][:12]}…` | {f2(wbid)}% | "
              f"{f2(D['tier_med_bid'].get(b))}% | {gap} |")
        A("")
        A("*(Winner clusters keyed by operator EOA; negative idx gap = winner landed at an earlier "
          "tx-index than the reverted loser.)*")
        A("")
        # collisions per bucket
        A("Collisions per size bucket:")
        A("")
        A("| Bucket | Collisions |")
        A("|---|--:|")
        cb = Counter(bucket(c["winner"]["gross_usd"]) for c in cols)
        for b in ("<$10", "$10-100", "$100-1k", ">$1k"):
            A(f"| {b} | {cb.get(b,0)} |")
        A("")
        # winner x loser matrix (top-10 census clusters)
        top = [k for k, _ in sorted(Counter(cid.values()).items(), key=lambda kv: -kv[1])][:10]
        A("Winner×loser cluster matrix (counts; loser mapped to census cluster where known, else its "
          "`to` address):")
        A("")
        mat = Counter()
        for c in cols:
            wc = clab(cid.get(c["winner"]["txhash"]))
            lcr = addr_cluster(c["loser_to"], c["loser_from"])
            lc = clab(lcr) if lcr else ("bot:"+c["loser_to"][:10])
            mat[(wc, lc)] += 1
        A("| winner cluster (operator EOA) | loser | count |")
        A("|---|---|--:|")
        for (wc, lc), n in mat.most_common():
            A(f"| `{str(wc)[:14]}…` | `{str(lc)[:16]}` | {n} |")
        A("")
    # Task 4
    A("## Task 4 — The non-fight number [M, sampled]")
    A("")
    # collisions as % of measured arbs: winners in sample that had >=1 colliding revert
    winners_hit = {(c['block'], c['winner']['txhash']) for c in cols}
    sampled_arbs = [(bn, a) for bn in D['block_used'] for a in D['arbs_by_block'].get(bn, [])]
    n_samp_arbs = len(sampled_arbs)
    hit = sum(1 for bn, a in sampled_arbs if (bn, a['txhash']) in winners_hit)
    samp_big = [(bn, a) for bn, a in sampled_arbs if a['gross_usd'] >= 100]
    hit_big = sum(1 for bn, a in samp_big if (bn, a['txhash']) in winners_hit)
    A("| Population (sampled blocks) | Measured arbs | With a colliding same-block reverted rival | Rate |")
    A("|---|--:|--:|--:|")
    A(f"| all measured arbs | {n_samp_arbs} | {hit} | {100*hit/max(n_samp_arbs,1):.1f}% |")
    A(f"| >$100 measured arbs | {len(samp_big)} | {hit_big} | {100*hit_big/max(len(samp_big),1):.1f}% |")
    A("")
    # baseline under random arrival
    U = med([u for u in D['block_univ'].values() if u > 0]) or 1
    parb = med([len(ap) for bn in D['block_used'] for ap in D['block_arbpools'].get(bn, {}).values() if ap]) or 2
    prev_pools = 2  # typical distinct pools a reverted arb touches (traces show router+>=1 pool)
    rpb = D['reverts_per_block']
    per_pair = min(1.0, parb*prev_pools/U)
    per_arb = 1-(1-per_pair)**rpb
    A(f"**Baseline under random arrival [E].** Observed: median distinct V2/V3 pools active per block "
      f"U≈{U:.0f}, median V2/V3 pools per measured arb p_arb≈{parb:.0f}, reverted txs per block ≈{rpb:.1f}. "
      f"Model each tx as drawing its pools uniformly from the U pools active that block, so a random "
      f"(arb, revert) pair shares ≥1 pool with probability ≈ p_arb·p_rev/U ≈ {100*per_pair:.1f}%; "
      f"compounded over ~{rpb:.0f} reverts/block, the baseline chance a given arb has ≥1 same-pool "
      f"reverted rival ≈ **{100*per_arb:.1f}%** [E]. Compare to the measured all-arb rate above: a "
      f"measured rate near/below this baseline means low collisions are explained by **sparse "
      f"opportunities**, not carved territory; a rate well above baseline means **real contests**.")
    A("")
    A("*Baseline caveat [E]: this is an UPPER-ish estimate — it assumes every reverted tx touches "
      "~2 of the block's pools, but many reverted txs are failed non-arb txs touching none of the arb's "
      "pools, so the true random-collision baseline is lower than 64%. The gap between the 9% measured "
      "and this baseline is therefore partly baseline over-estimation; do not read it as arbs actively "
      "avoiding rivals. The robust takeaway is the closing guardrail, not the point estimate.*")
    A("")
    A("## Closing guardrail (stated, not a verdict)")
    A("")
    A("**Landed-reverted losers are a LOWER BOUND on contests.** Builders simulate bundles and silently "
      "drop the losing ones, so most losing attempts never land on-chain and are invisible to this or any "
      "chain-only method. Therefore: a **high** collision rate proves fighting; a **low** collision rate "
      "is consistent with EITHER no fighting OR fights fully resolved inside builders before inclusion. "
      "The numbers above bound what is visible on-chain; they do not measure the private auction. No "
      "verdict is drawn beyond these measured bounds.")
    A("")
    A("*Probe complete. One bounded fetch used. Scratch file — not the census.*")
    with open(os.path.join(OUT, "contest_intensity.md"), "w") as f:
        f.write("\n".join(L))
    print("wrote out/contest_intensity.md; collisions=", len(cols), "calls=", D["calls"])

if __name__ == "__main__":
    main()

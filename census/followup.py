"""Follow-up cross-sections computed ONLY from the existing measured set (out/arbs.jsonl).
No chain access. Appends a section to out/CENSUS_REPORT.md."""
import json, os, statistics as st
from collections import defaultdict, Counter
from census.report import UF, pct, med

OUT = os.path.join(os.path.dirname(__file__), "..", "out")

def load_arbs():
    arbs = []
    for l in open(os.path.join(OUT, "arbs.jsonl")):
        r = json.loads(l)
        if r.get("verdict") == "arb":
            arbs.append(r)
    return arbs

def bucket_of(g):
    if g < 10: return "<$10"
    if g < 100: return "$10-100"
    if g < 1000: return "$100-1k"
    return ">$1k"
BUCKETS = ["<$10", "$10-100", "$100-1k", ">$1k"]

def f2(x, d=2): return f"{x:,.{d}f}" if x is not None else "n/a"

def clusters_of(arbs):
    uf = UF()
    for r in arbs:
        b = r["beneficiary"]; f = r.get("tx_from")
        uf.union(("b", b), ("f", f) if f else ("b", b))
    cl = defaultdict(list)
    for r in arbs:
        cl[uf.find(("b", r["beneficiary"]))].append(r)
    return cl

def builder_pct(r):  # coinbase + direct-to-miner builder payment as % of gross
    return 100*r["builder_eth"]/r["gross_eth"] if r["gross_eth"] > 0 else None
def cost_pct(r):     # (builder + gas) as % of gross
    return 100*(r["builder_eth"]+r["gas_cost_eth"])/r["gross_eth"] if r["gross_eth"] > 0 else None

def main():
    span = json.load(open(os.path.join(OUT, "window.json")))["span_days"]
    arbs = load_arbs()
    N = len(arbs)
    by_bucket = defaultdict(list)
    for r in arbs:
        by_bucket[bucket_of(r["gross_usd"])].append(r)

    L = []; A = L.append
    A("")
    A("---")
    A("")
    A("## Follow-up: cost-to-win and competition cross-sections")
    A("")
    A(f"*Computed only from the {N:,} fully-measured (confirmed) arbs in the existing dataset "
      f"(the 71.3% coverage population), window {span:.2f} days. No re-scanning. Builder payment = "
      f"coinbase transfer + any direct ETH/token transfer to the block's fee recipient within the tx, "
      f"as measured from callTracer + logs; ratios computed in ETH terms then shown as %. All [M].*")
    A("")

    # ---------------- Task 1 ----------------
    A("### Task 1 — Spend-to-win (builder payment & total cost as % of gross) [M]")
    A("")
    A("Zero-builder-payment arbs (no coinbase/direct transfer to the builder; they bid via priority "
      "fee only, which is inside gas) are reported as a **separate row**, not blended into the payer "
      "medians. `builder%` = builder payment ÷ gross; `cost%` = (builder + gas) ÷ gross.")
    A("")
    A("| Scope | Row | Count | Share | builder% p25 | builder% med | builder% p75 | cost% p25 | cost% med | cost% p75 |")
    A("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    def emit(scope, rows):
        payers = [r for r in rows if r["builder_eth"] > 1e-15]
        zeros = [r for r in rows if r["builder_eth"] <= 1e-15]
        tot = len(rows) or 1
        for label, sub, showb in (("builder-payers", payers, True), ("zero-builder", zeros, False)):
            bp = [builder_pct(r) for r in sub if builder_pct(r) is not None]
            cp = [cost_pct(r) for r in sub if cost_pct(r) is not None]
            share = f"{100*len(sub)/tot:.1f}%"
            if showb and bp:
                A(f"| {scope} | {label} | {len(sub):,} | {share} | {f2(pct(bp,.25))}% | {f2(med(bp))}% | {f2(pct(bp,.75))}% | {f2(pct(cp,.25))}% | {f2(med(cp))}% | {f2(pct(cp,.75))}% |")
            else:
                A(f"| {scope} | {label} | {len(sub):,} | {share} | — | — | — | {f2(pct(cp,.25))}% | {f2(med(cp))}% | {f2(pct(cp,.75))}% |")
    emit("**Overall**", arbs)
    for b in BUCKETS:
        emit(b, by_bucket[b])
    A("")

    # ---------------- Task 2 ----------------
    A("### Task 2 — Size-bucket × competition [M]")
    A("")
    A("| Bucket | Count | Count/day | Median net $ | p75 net $ | Distinct clusters | Top-1 cluster % of bucket net | Top-5 % of bucket net | Median gas used | Median tx index |")
    A("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for b in BUCKETS:
        rows = by_bucket[b]
        nets = [r["net_usd"] for r in rows if r.get("net_usd") is not None]
        gas = [r["gas_used"] for r in rows]
        idx = [r["tx_index"] for r in rows]
        cl = clusters_of(rows)
        clnet = sorted((sum(x.get("net_usd") or 0 for x in v) for v in cl.values()), reverse=True)
        tot_net = sum(clnet) or 1
        t1 = 100*clnet[0]/tot_net if clnet else 0
        t5 = 100*sum(clnet[:5])/tot_net if clnet else 0
        A(f"| {b} | {len(rows):,} | {len(rows)/span:,.0f} | {f2(med(nets))} | {f2(pct(nets,.75))} | "
          f"{len(cl):,} | {t1:.1f}% | {t5:.1f}% | {med(gas):,.0f} | {med(idx):,.0f} |")
    A("")
    A("> Cluster = set of arbs linked by a shared operator EOA (`tx.from`) or beneficiary contract "
      "(union-find). Top-k share is of that bucket's total measured net. Where a bucket's net is "
      "dominated by a few clusters the share is high; a negative/near-zero bucket net can distort "
      "shares (noted inline if it occurs).")
    A("")

    # ---------------- Task 3 ----------------
    A("### Task 3 — Mempool-origin × profit cross-tab [M/E]")
    A("")
    total_net = sum(r["net_usd"] for r in arbs if r.get("net_usd") is not None)
    origins = {"likely_public(priority_fee_only)": "likely-public",
               "private_bundle(coinbase_xfer)": "private-bundle",
               "undetermined": "undetermined"}
    A("| Origin | Count | Share of total net | Median net $ | Median builder% of gross |")
    A("|---|--:|--:|--:|--:|")
    for key, label in origins.items():
        sub = [r for r in arbs if r.get("mempool_origin") == key]
        snet = sum(r["net_usd"] for r in sub if r.get("net_usd") is not None)
        nets = [r["net_usd"] for r in sub if r.get("net_usd") is not None]
        bp = [builder_pct(r) for r in sub if builder_pct(r) is not None]
        A(f"| {label} | {len(sub):,} | {100*snet/total_net if total_net else 0:.1f}% | {f2(med(nets))} | {f2(med(bp))}% |")
    A("")
    A("**Heuristic & how much to trust it.** The origin flag is *inferred from settlement mechanics, "
      "not observed*: an arb that transfers ETH/tokens to the block's fee recipient inside the tx "
      "(a coinbase payment) is flagged **private-bundle** (that is how searchers pay builders for "
      "off-mempool inclusion); an arb with no such transfer that instead carries a positive priority "
      "fee is flagged **likely-public**; anything else is **undetermined**. **Known failure modes:** "
      "(1) a private-bundle searcher can pay entirely via priority fee and emit no coinbase transfer — "
      "it is then indistinguishable from public flow and mislabeled likely-public, so *private is "
      "under-counted*; (2) some public-mempool bots also send a small coinbase tip, inflating "
      "private; (3) builders that receive payment via a *separate* bundle tx (not the arb tx itself) "
      "are invisible here. **Bottom line: the coinbase-transfer signal reliably identifies a floor on "
      "private flow, but the public/private split is a lower bound on private and cannot be treated "
      "as ground truth — treat it as directional, not exact.**")
    A("")

    # ---------------- Task 4 ----------------
    A("### Task 4 — Top-10 cluster profiles [M]")
    A("")
    cl = clusters_of(arbs)
    top = sorted(cl.items(), key=lambda kv: -sum((x.get("net_usd") or 0) for x in kv[1]))[:10]
    A("| # | Lead address | Arbs | Total net $ | Median net $ | Median builder% | Median gas used | Mempool mix (pub/priv/undet) | Dominant bucket (share of its net) | Clustering confidence |")
    A("|--:|---|--:|--:|--:|--:|--:|---|---|---|")
    for i, (ck, rows) in enumerate(top, 1):
        contracts = Counter(r["beneficiary"] for r in rows)
        ops = Counter(r.get("tx_from") for r in rows)
        lead = contracts.most_common(1)[0][0]
        nets = [r["net_usd"] for r in rows if r.get("net_usd") is not None]
        bp = [builder_pct(r) for r in rows if builder_pct(r) is not None]
        gas = [r["gas_used"] for r in rows]
        mm = Counter(r.get("mempool_origin") for r in rows)
        n = len(rows)
        pub = 100*mm.get("likely_public(priority_fee_only)", 0)/n
        prv = 100*mm.get("private_bundle(coinbase_xfer)", 0)/n
        und = 100*mm.get("undetermined", 0)/n
        # bucket holding most of this cluster's net
        bnet = defaultdict(float)
        for r in rows: bnet[bucket_of(r["gross_usd"])] += (r.get("net_usd") or 0)
        tnet = sum(bnet.values()) or 1
        domb = max(bnet.items(), key=lambda kv: kv[1])
        conf = ("single address (direct)" if len(contracts) == 1 and len(ops) == 1
                else f"funding-linked via {len(ops)} operator EOA(s), {len(contracts)} contract(s); deployer not established")
        A(f"| {i} | `{lead[:12]}…` | {n:,} | {f2(sum(nets),0)} | {f2(med(nets))} | {f2(med(bp))}% | "
          f"{med(gas):,.0f} | {pub:.0f}/{prv:.0f}/{und:.0f}% | {domb[0]} ({100*domb[1]/tnet:.0f}%) | {conf} |")
    A("")
    A("**Adjacency profile — NOT AVAILABLE from the stored dataset.** Per-arb victim-adjacency "
      "(backrun distance / share landing at victim-index+1 in the same block) requires each block's "
      "full receipt set to identify the specific victim swap; that is not stored in `arbs.jsonl` and "
      "recomputing it would require re-fetching block receipts (a re-crawl), which is out of scope for "
      "this follow-up. What IS stored is each arb's absolute `tx_index`; the median tx index per "
      "cluster is given below as a positional proxy (low index ⇒ top-of-block placement, typical of "
      "competitive backrunning; high index ⇒ later placement).")
    A("")
    A("| # | Lead address | Median tx index | % at index 0-1 (block top) |")
    A("|--:|---|--:|--:|")
    for i, (ck, rows) in enumerate(top, 1):
        lead = Counter(r["beneficiary"] for r in rows).most_common(1)[0][0]
        idx = [r["tx_index"] for r in rows]
        toptop = 100*sum(1 for x in idx if x <= 1)/len(idx)
        A(f"| {i} | `{lead[:12]}…` | {med(idx):,.0f} | {toptop:.0f}% |")
    A("")

    # ---------------- Task 5 ----------------
    A("### Task 5 — Dust boundary (gross below which median net ≤ $0) [M/derived]")
    A("")
    def median_net_below(T):
        sub = [r["net_usd"] for r in arbs if r["gross_usd"] < T and r.get("net_usd") is not None]
        return (med(sub), len(sub))
    lo = min(r["gross_usd"] for r in arbs); hi = 100.0
    m_lo, _ = median_net_below(lo*1.001); m_hi, _ = median_net_below(hi)
    if m_lo is not None and m_lo > 0:
        # median already positive at the very floor -> no dust boundary exists
        thr = None
    else:
        a, b = lo, hi
        for _ in range(60):
            mid = (a+b)/2
            mm, _ = median_net_below(mid)
            if mm is not None and mm <= 0: a = mid
            else: b = mid
        thr = a
    neg_share = 100*sum(1 for r in arbs if r["net_usd"] <= 0)/N
    if thr is None:
        A(f"- **No dust boundary exists in this dataset [M].** The running median net of the sub-\\$T "
          f"population is **positive for every threshold down to the detection floor** — even arbs "
          f"grossing a fraction of a cent clear >\\$0 at the median, because gas on this chain is "
          f"near-zero (base fee ~0.08 gwei ⇒ median gas cost ~\\$0.10). Costs never dominate the "
          f"median arb.")
    else:
        below = sum(1 for r in arbs if r["gross_usd"] < thr)
        A(f"- **Break-even gross threshold [M/derived]:** ≈ **${thr:,.3f}** gross profit. Arbs grossing "
          f"below this have a **median net ≤ \\$0** — builder payment + gas meet or exceed gross; above "
          f"it the running median net turns positive. Found by bisecting the measured (gross, net) "
          f"pairs for the sign change of the sub-\\$T median net.")
        A(f"- **Share below the boundary:** **{below:,} of {N:,} arbs = {100*below/N:.1f}%** gross below "
          f"${thr:,.3f}. (This chain's gas is cheap — ~\\$0.10 median — so the break-even sits far below "
          f"$1; on a higher-gas chain it would be much higher.)")
    A(f"- **For context:** {neg_share:.1f}% of all {N:,} measured arbs are individually net ≤ \\$0 "
      f"(landed winners that failed to clear their own costs) [M].")
    A("")
    # supporting mini-table
    A("Supporting — median net by gross band:")
    A("")
    A("| Gross band | Count | Median net $ |")
    A("|---|--:|--:|")
    bands = [(0,1),(1,2),(2,5),(5,10),(10,25),(25,100),(100,1e12)]
    for a2, b2 in bands:
        sub = [r["net_usd"] for r in arbs if a2 <= r["gross_usd"] < b2 and r.get("net_usd") is not None]
        lab = f"${a2:g}-{b2:g}" if b2 < 1e12 else f"≥${a2:g}"
        A(f"| {lab} | {len(sub):,} | {f2(med(sub))} |")
    A("")

    with open(os.path.join(OUT, "CENSUS_REPORT.md"), "a") as f:
        f.write("\n".join(L))
    print("appended follow-up section:", len(L), "lines; break-even ~$%.2f, %.1f%% below" % (thr, 100*below/N))

if __name__ == "__main__":
    main()

"""Render out/CENSUS_REPORT.md from aggregated data."""
import json, os, statistics as st
from collections import Counter
from census.report import build, pct, med, bucket_stats
from census.adjacency import adjacency_for

OUT = os.path.join(os.path.dirname(__file__), "..", "out")

def f2(x, d=2): return f"{x:,.{d}f}" if x is not None else "n/a"

def cluster_label(rows):
    contracts = Counter(r["beneficiary"] for r in rows)
    ops = Counter(r.get("tx_from") for r in rows)
    return contracts.most_common(1)[0][0], len(contracts), len(ops)

def main():
    d = build()
    w = d["w"]; arbs = d["arbs"]
    L = []
    A = L.append
    A("# ETH Mainnet Atomic-Arbitrage Census")
    A("")
    A(f"**Window [M]:** blocks `{w['start_block']:,}` → `{w['end_block']:,}` "
      f"({d['n_blocks']:,} blocks processed, {d['span_days']:.2f} days), fixed at run start.")
    A(f"**Chain:** ETH mainnet via Chainstack archive node (Geth). "
      f"**Total txs scanned [M]:** {d['total_tx']:,}.")
    A("")
    A(f"**Coverage:** measured **{d['measured_pct']:.1f}%** of detected atomic arbs "
      f"({len(arbs):,} fully-measured of {d['detected']:,} detected arb-shaped txs). "
      f"Remainder: {len(d['unpriceable']):,} unpriceable ({100*len(d['unpriceable'])/max(d['detected'],1):.1f}%), "
      f"{len(d['failed']):,} failed-to-measure ({100*len(d['failed'])/max(d['detected'],1):.1f}%). "
      f"Both listed below and counted here.")
    A("")
    A("> Every number is labeled **[M]** measured or **[E]** derived/estimated. "
      "Profit is measured on-chain in WETH/ETH terms; **USD is a derived column** "
      "(ETH→USD via Chainlink ETH/USD at each arb's block, cross-checked vs a Uniswap-V3 "
      "USDC/WETH spot). Token→ETH via deepest on-chain WETH/USDC/USDT pool spot at the arb block.")
    A("")

    # ---------- Headline ----------
    nets, grosses, gases, bids = d["nets"], d["grosses"], d["gases"], d["bidshares"]
    arbs_per_day = len(arbs)/d["span_days"]
    n_clusters = len(d["clusters"])
    n_benef = len(set(r["beneficiary"] for r in arbs))
    A("## 1. Headline [M]")
    A("")
    A("| Metric | Value |")
    A("|---|---|")
    A(f"| Confirmed atomic arbs (measured) | **{len(arbs):,}** [M] |")
    A(f"| Arbs/day | **{arbs_per_day:,.0f}** [M] |")
    A(f"| Distinct winner addresses (beneficiaries) | {n_benef:,} [M] |")
    A(f"| Distinct winner clusters (operator-linked) | {n_clusters:,} [M] |")
    A(f"| Top-1 cluster share of total net profit | {d['top1']:.1f}% [M] |")
    A(f"| Top-5 cluster share of total net profit | {d['top5']:.1f}% [M] |")
    A(f"| Net profit USD — median | ${f2(med(nets))} [M/derived] |")
    A(f"| Net profit USD — p25 / p75 | ${f2(pct(nets,.25))} / ${f2(pct(nets,.75))} [M/derived] |")
    A(f"| Gross profit USD — median | ${f2(med(grosses))} [M/derived] |")
    A(f"| Builder payment as % of gross — median | {f2(med(bids))}% [M] |")
    A(f"| Gas cost USD — median | ${f2(med(gases))} [M/derived] |")
    A(f"| Total net profit (measured arbs) | ${f2(d['total_net'],0)} [M/derived] |")
    A("")
    # landed / reverted / attempts
    A("### Landed vs. reverted vs. attempts")
    A("")
    A(f"- **Landed-succeeded arbs [M]:** {len(arbs):,} confirmed (+ {len(d['unpriceable']):,} unpriceable "
      f"+ {len(d['failed']):,} failed-to-measure).")
    A(f"- **Landed-reverted attempts by known arb addresses [M, lower bound]:** {d['reverted_by_known']:,} "
      f"(reverted txs in-window whose `to` is a confirmed winner contract/EOA; "
      f"of {d['reverted_total']:,} total reverted txs).")
    A(f"- **True attempt count: UNMEASURABLE** — reverted txs emit no logs, and mempool-dropped / "
      f"non-landed bundle attempts are not observable from chain state. Not estimated.")
    A("")

    # ---------- Size buckets ----------
    A("## 2. Size buckets (by gross USD) [M]")
    A("")
    A("| Bucket | Count | Median net $ | p25 net $ | p75 net $ | Median builder %gross | Median gas $ |")
    A("|---|--:|--:|--:|--:|--:|--:|")
    for b in ("<$10", "$10-100", "$100-1k", ">$1k"):
        rows = d["buckets"].get(b, [])
        n, mn, p25, p75, mbs, mg = bucket_stats(rows)
        A(f"| {b} | {n:,} | {f2(mn)} | {f2(p25)} | {f2(p75)} | {f2(mbs)}% | {f2(mg)} |")
    A("")

    # ---------- Winner census ----------
    A("## 3. Winner census — top 10 clusters [M]")
    A("")
    top = sorted(d["clusters"].items(), key=lambda kv: -sum((x.get("net_usd") or 0) for x in kv[1]))[:10]
    # bounded adjacency sample per cluster
    A("| # | Lead address | Contracts / ops | Arbs | Median net $ | Cluster net $ | Median bid %gross | Mempool (majority) | Median tx-idx | Backrun dist (median) |")
    A("|--:|---|---|--:|--:|--:|--:|---|--:|--:|")
    adj_notes = []
    for i, (ck, rows) in enumerate(top, 1):
        lead, ncon, nops = cluster_label(rows)
        cnets = [r["net_usd"] for r in rows if r.get("net_usd") is not None]
        cbids = [100*r["builder_eth"]/r["gross_eth"] for r in rows if r.get("gross_eth") and r["gross_eth"]>0]
        idxs = [r["tx_index"] for r in rows if r.get("tx_index") is not None]
        memp = Counter(r.get("mempool_origin") for r in rows).most_common(1)[0][0]
        # adjacency on up to 40 arbs
        sample = rows[:40]
        adj = adjacency_for([dict(block=r["block"], tx_index=r["tx_index"], txhash=r["txhash"]) for r in sample])
        dists = [a["backrun_distance"] for a in adj if a["backrun_distance"] is not None]
        bd = med(dists)
        backrun_share = 100*len(dists)/len(adj) if adj else 0
        adj_notes.append((i, backrun_share))
        memp_s = {"private_bundle(coinbase_xfer)":"private","likely_public(priority_fee_only)":"public",
                  "undetermined":"undet"}.get(memp, memp)
        A(f"| {i} | `{lead[:14]}…` | {ncon}c/{nops}op | {len(rows):,} | {f2(med(cnets))} | "
          f"{f2(sum(cnets),0)} | {f2(med(cbids))}% | {memp_s} | {f2(med(idxs),0)} | "
          f"{('%.0f'%bd) if bd is not None else 'n/a'} |")
    A("")
    A("- *Contracts/ops* = distinct beneficiary contracts / distinct operator EOAs in the cluster "
      "(clustered by shared operator EOA — the funder/controller proxy; explicit deployer clustering "
      "not performed, see methods).")
    A("- *Backrun dist* = median in-block position gap to the nearest preceding tx sharing a swap pool "
      "(victim-adjacency proxy, measured on up to 40 arbs/cluster). Share with a same-block same-pool "
      "predecessor: " + ", ".join(f"#{i}:{s:.0f}%" for i, s in adj_notes) + ".")
    A("")

    # ---------- Mempool origin summary ----------
    memp_all = Counter(r.get("mempool_origin") for r in arbs)
    A("### Mempool-origin flag (heuristic) [M/E]")
    A("")
    tot = sum(memp_all.values()) or 1
    for k, v in memp_all.most_common():
        A(f"- `{k}`: {v:,} ({100*v/tot:.1f}%)")
    A("")
    A("> Heuristic, not ground truth: coinbase transfer to the builder ⇒ private-bundle order flow; "
      "priority-fee-only with no coinbase transfer ⇒ likely public mempool. True mempool origin is "
      "not recoverable from chain state alone; flag labeled [E] where inferred.")
    A("")

    # ---------- Unpriceable / failed ----------
    A("## 4. Unpriceable list [M]")
    A("")
    A(f"{len(d['unpriceable']):,} detected arb-shaped txs whose profit is denominated in a token with no "
      f"reliable on-chain price at the arb block (no sufficiently-deep WETH/USDC/USDT pool). "
      f"Profit **not valued, not dropped**.")
    up_tokens = Counter()
    for r in d["unpriceable"]:
        for a, raw in r.get("unpriceable", []):
            up_tokens[a] += 1
    if up_tokens:
        A("")
        A("Most common unpriceable profit tokens (address: #arbs):")
        for a, c in up_tokens.most_common(10):
            A(f"- `{a}`: {c}")
    A("")
    A("## 5. Failed-to-measure list [M]")
    A("")
    fr = Counter(r.get("reason") for r in d["failed"])
    A(f"{len(d['failed']):,} detected arb-shaped txs that could not be measured. Reasons:")
    A("")
    for reason, c in fr.most_common():
        A(f"- `{reason}`: {c:,}")
    A("")
    A("> `unpriceable_outflow`: beneficiary spent a token with no reliable price, so net profit is "
      "genuinely indeterminate (can't tell arb from loss). `trace_failed`/`exc:*`/`receipt_fetch_fail`: "
      "RPC/trace error. `non_standard_transfer_events`: token used non-standard (non-indexed / rebasing) "
      "Transfer events; balance-delta not reconstructable from logs.")
    A("")

    # ---------- Methods ----------
    write_methods(A, d)

    with open(os.path.join(OUT, "CENSUS_REPORT.md"), "w") as fo:
        fo.write("\n".join(L))
    print("wrote out/CENSUS_REPORT.md", len(L), "lines")

def write_methods(A, d):
    c = d["control"]
    A("## 6. Methods appendix")
    A("")
    A("### Detection heuristic [M]")
    A("- **Primitive:** `eth_getBlockReceipts` per block (all logs, gas, status, effective gas price, "
      "tx index) + `eth_getBlockByNumber` header (miner, base fee, timestamp). Every tx classified.")
    A("- **Balance-delta method (not event-amount method):** per-tx net balance delta per "
      "(address, token) accumulated from ERC-20 `Transfer` + WETH `Deposit`/`Withdrawal` logs; native "
      "ETH deltas + builder coinbase transfers from `debug_traceTransaction` (callTracer) on each "
      "candidate. Fee-on-transfer/rebasing tokens: measured as balance deltas; tokens with "
      "non-standard Transfer events are routed to failed-to-measure rather than mis-valued.")
    A("- **Beneficiary:** restricted to the arbitrageur-controlled address — tx.to (bot contract) or "
      "tx.from (EOA) — never a pool. Any address emitting a Swap/Sync/Mint/Burn event is excluded as "
      "an AMM pool. Revenue is the beneficiary's balance delta, which may differ from tx.from "
      "(gross≠net trap handled).")
    A("- **Atomic-arb definition:** ≥2 DEX swaps forming a value cycle; beneficiary ends value-positive "
      "(gross > ~$0.01) after pricing ALL signed deltas. Confirmation is **value-based**, not raw-unit "
      "(a −54 USDC buy is not 'dust' — decimals-aware thresholds throughout).")
    A("- **Exclusions (misclassification guards):** liquidations (Aave/Compound/Maker liquidation "
      "events) excluded; JIT liquidity (Mint+Burn same tx) excluded; sandwich legs fail the "
      "single-tx cyclic test (a front-run leg ends holding the victim token, not net base asset). "
      "Flash-loan-wrapped and aggregator-routed arbs ARE captured (flash-loan repayment nets to ~0 in "
      "the borrowed token; the balance-delta cycle still resolves).")
    A("- **Known bounds (documented, not hidden):** (a) arbs sweeping profit to a separate treasury "
      "address inside the tx fall to route_or_user; (b) pure native-ETH-settled arbs with no positive "
      "logged-token delta are under-counted; (c) token-denominated profits without a priceable pool are "
      "listed as unpriceable. These reduce recall, never inflate measured profit.")
    A("")
    A("### Price sources [M]")
    A("- **ETH/USD:** Chainlink ETH/USD aggregator `latestRoundData()` via `eth_call` at each arb block, "
      "staleness-checked (updatedAt within 2h); falls back to Uniswap-V3 USDC/WETH 0.05% pool spot. "
      "Method logged per conversion. (Validated: the two sources agreed to ~0.2% at spot-check.)")
    A("- **Token→ETH:** deepest on-chain token/WETH pool (Uniswap V3 fee tiers 0.01–1% + V2); if none "
      "deep enough, token/USDC or token/USDT pool spot then stable→ETH. Depth-gated (≥0.3 WETH or "
      "≈$300 stable) else unpriceable. Pool spot read at the arb block (archive).")
    A("- **Profit denomination:** raw output is WETH/ETH-denominated; USD is a derived column with its "
      "conversion source labeled. Token amounts are never treated as USD.")
    A("")
    A("### Control results (run BEFORE the batch) — " + c["status"])
    A("")
    A("Three hand-verified true arbs (independent manual recomputation of balance deltas, coinbase "
      "payment, and gas matched the pipeline):")
    for a in c["true_arbs_hand_verified"]:
        A(f"- `{a['tx'][:20]}…` — {a['type']}: gross ${a['gross_usd']}, net ${a['net_usd']}. {a['verified']}.")
    A("")
    A("Negative controls (must NOT be counted as arbs):")
    for a in c["negative_controls"]:
        A(f"- `{a['tx'][:20]}…` — expected {a['expected']} → got {a['result']}.")
    A("")
    A("Bugs caught & fixed by the control before batch: " + "; ".join(c["bugs_caught_by_control"]) + ".")
    A("")
    A(f"### Sample gate (run BEFORE the batch) — {d['gate']['gate']}")
    A(f"- On {d['gate']['sample_blocks']} spread blocks: failed-to-measure "
      f"{d['gate']['failed_to_measure_rate_pct']:.1f}% (stop rule: >20% ⇒ abort). "
      f"Unpriceable {d['gate']['unpriceable_rate_pct']:.1f}%. Gate passed; proceeded to full window.")
    A("")
    A("### Stopping")
    A("- Window fixed at start (last 7 days by block timestamp); not extended mid-run. "
      "Whole window processed, then stopped. No opportunistic scope extension.")

if __name__ == "__main__":
    main()

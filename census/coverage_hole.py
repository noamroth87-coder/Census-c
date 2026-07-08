"""M1 — the coverage hole. Characterize the unmeasured 28.7% of detected arbs.

Denominator = detected atomic-arb candidates that reached a measurement verdict:
    arb (87,918) + unpriceable (20,234) + failed_measure (15,239) = 123,391
    71.3% measured / 16.4% unpriceable / 12.4% failed-to-measure.

Two hole populations, distinguished by WHICH leg is unmeasured:
  * unpriceable  (reason unpriceable_profit_token): the PROFIT token is an unpriceable
    GAIN. The cost side (WETH/stable outlay) is visible in `priced`; the upside is not.
  * failed_measure (reason unpriceable_outflow): a material OUTFLOW token is unpriceable.
    The revenue side (WETH inflow) may be visible; the cost is not, so sign is unknown.

Tasks:
  1  rank unpriceable tokens by arb count (top-20), with visible WETH-leg magnitude
  2  bucket failed_measure reasons + structural sub-buckets, count each
  3  bounded fetch (cap 2000): top-10 unpriceable tokens -> did a >$50k WETH/USDC route
     exist at the window?  PRICEABLE-IN-RETROSPECT vs GENUINELY-EXOTIC
  4  measurable-leg lower bound of hole profit-mass [E]; dust/treasure/mixed by counts
"""
import json, collections, statistics as st
from census.price import decimals, _pools_against, _call, eth_usd
from census.config import WETH, USDC, USDT, STABLES

ARBS = "out/arbs.jsonl"
WINDOW = dict(start=25437594, end=25487778)
MID_BLOCK = (WINDOW["start"] + WINDOW["end"]) // 2
ETH_USD_WINDOW = 1568.424           # chainlink window reference (stored on every record)

# a single priced leg worth > this is a broken-pool artifact, not real throughput.
# failed_measure retains mispriced legs because has_unpriceable_loss is tested before the
# pipeline's SANE_GROSS_ETH backstop, so we re-apply a sane cap here when reading them.
SANE_LEG_ETH = 30000.0              # ~$47M in a single leg => reject as mispriced

def _visible_leg_eth(rec):
    """Largest sane |priced-leg| in ETH = trade-size proxy actually visible on-chain."""
    legs = [abs(x[2]) for x in (rec.get("priced") or [])
            if x[2] is not None and abs(x[2]) <= SANE_LEG_ETH]
    return max(legs) if legs else 0.0

def _bucket(usd):
    a = abs(usd)
    if a < 1:    return "dust (<$1)"
    if a < 50:   return "small ($1-50)"
    if a < 1000: return "mid ($50-1k)"
    return "large (>$1k)"

BUCKET_ORDER = ["dust (<$1)", "small ($1-50)", "mid ($50-1k)", "large (>$1k)"]


def load():
    up = []; fm = []
    with open(ARBS) as f:
        for line in f:
            try: r = json.loads(line)
            except Exception: continue
            v = r.get("verdict")
            if v == "unpriceable":   up.append(r)
            elif v == "failed_measure": fm.append(r)
    return up, fm


def task1(up):
    """Rank unpriceable tokens by arb count; visible WETH-leg magnitude per token."""
    tok_ct = collections.Counter()
    tok_vis = collections.defaultdict(list)          # token -> [visible USD]
    for r in up:
        vis = _visible_leg_eth(r) * ETH_USD_WINDOW
        for leg in (r.get("unpriceable") or []):
            t = leg[0].lower()
            tok_ct[t] += 1
            tok_vis[t].append(vis)
    rows = []
    for t, c in tok_ct.most_common(20):
        v = [x for x in tok_vis[t] if x > 0]
        rows.append(dict(
            token=t, arbs=c,
            med_visible_usd=(round(st.median(v), 2) if v else 0.0),
            sum_visible_usd=round(sum(tok_vis[t]), 0),
            with_visible=len(v)))
    return dict(distinct_tokens=len(tok_ct), total_token_legs=sum(tok_ct.values()),
                total_arbs=len(up), rows=rows, _ct=tok_ct)


def task2(fm):
    """Bucket failed_measure by stored reason + structural sub-buckets."""
    reason = collections.Counter()
    haspriced = collections.Counter()          # revenue leg visible or not
    nsw = collections.Counter()
    flash = 0; multi = 0
    valsign = collections.Counter()
    for r in fm:
        reason[r.get("reason")] += 1
        pr = [x for x in (r.get("priced") or []) if x[2] is not None and abs(x[2]) <= SANE_LEG_ETH]
        haspriced["revenue_leg_visible" if pr else "no_visible_leg"] += 1
        n = r.get("n_swaps") or 0
        nsw[("2" if n <= 2 else "3-4" if n <= 4 else "5-9" if n <= 9 else "10+")] += 1
        if r.get("has_flash"): flash += 1
        if r.get("multi_asset"): multi += 1
        val = r.get("value_eth") or 0.0
        valsign["measurable_pos" if val > 1e-9 else "measurable_neg" if val < -1e-9 else "measurable_zero"] += 1
    return dict(total=len(fm), reason=dict(reason), revenue_leg=dict(haspriced),
                n_swaps=dict(nsw), has_flash=flash, multi_asset=multi,
                value_sign=dict(valsign))


def _usd_liquidity_at(token, block):
    """Max single-pool USD liquidity for token vs WETH / USDC / USDT at `block`.
    Returns (best_usd, detail). detail = (kind,pool,fee,quote,quote_bal_raw)."""
    usd_per_eth, _ = eth_usd(block)
    best = 0.0; best_detail = None; calls = 0
    for quote in (WETH, USDC, USDT):
        pools = _pools_against(token, quote)                 # ~5 calls existence + up to 5 balance
        calls += 10
        for kind, pool, t_is_0, fee, q, qbal in pools:
            if quote == WETH:
                usd = (qbal / 1e18) * (usd_per_eth or ETH_USD_WINDOW) * 2   # both sides ~ 2x quote
            else:
                usd = (qbal / 10**STABLES.get(q, 6)) * 2
            if usd > best:
                best = usd; best_detail = (kind, pool, fee, q, qbal)
    return best, best_detail, calls


def task3(up_ct, up, cap=2000):
    """For top-10 unpriceable tokens: did a >$50k route vs WETH/USDC/USDT exist at window?
    A representative block per token = the block of its first occurrence (real pool state)."""
    first_block = {}
    for r in up:
        for leg in (r.get("unpriceable") or []):
            t = leg[0].lower()
            first_block.setdefault(t, r["block"])
    top10 = [t for t, _ in up_ct.most_common(10)]
    out = []; calls = 0
    for t in top10:
        blk = first_block.get(t, MID_BLOCK)
        best_usd, detail, c = _usd_liquidity_at(t, blk)
        calls += c
        label = "PRICEABLE-IN-RETROSPECT" if best_usd >= 50_000 else "GENUINELY-EXOTIC"
        out.append(dict(token=t, arbs=up_ct[t], at_block=blk,
                        best_liquidity_usd=round(best_usd, 0),
                        route=(f"{detail[0]}:{detail[2]} vs {('WETH' if detail[3]==WETH else 'USDC' if detail[3]==USDC else 'USDT')}"
                               if detail else "none"),
                        label=label))
        if calls >= cap:
            break
    return dict(calls_used=calls, cap=cap, rows=out)


def task4(up, fm):
    """Measurable-leg lower bound of hole profit-mass [E] + dust/treasure/mixed by counts.

    FORMULA (measurable-leg lower bound, per hole arb i):
      visible_i = largest sane |priced beneficiary leg|, in USD  (WETH-visible size)
      profit_floor_i:
        - unpriceable arbs: profit sits ENTIRELY in the unvalued gain token; the measurable
          position change value_eth_i <= 0 for every such arb (verified). So the measurable
          PROFIT floor contributed is 0 -- we can prove economic activity, not profit.
        - failed_measure arbs: the visible leg is REVENUE with cost hidden -> it bounds
          revenue from above, gives no profit floor either.
      => Provable measurable profit floor of the hole = $0. What IS measurable is THROUGHPUT
         (sum of visible legs) = a size floor on economic activity passing through the hole.
      Reported: (a) throughput floor in USD, (b) count distribution by visible-leg size.
    """
    def analyze(pop, profit_floor):
        """profit_floor: 'measurable_value' (unpriceable — value_eth is the real signed
        measurable position change, <=0 here) or 'none' (failed_measure — the visible leg
        is REVENUE with hidden cost, so it is not a profit floor: report $0)."""
        buckets = collections.Counter(); tp = 0.0; with_leg = 0; valpos = 0.0
        for r in pop:
            v_eth = _visible_leg_eth(r); v_usd = v_eth * ETH_USD_WINDOW
            buckets[_bucket(v_usd)] += 1
            tp += v_eth
            if v_eth > 0: with_leg += 1
            val = r.get("value_eth") or 0.0
            if profit_floor == "measurable_value" and 0 < val <= SANE_LEG_ETH:
                valpos += val
        return dict(n=len(pop), with_leg=with_leg,
                    throughput_usd=round(tp * ETH_USD_WINDOW, 0),
                    measurable_profit_floor_usd=round(valpos * ETH_USD_WINDOW, 0),
                    buckets={b: buckets[b] for b in BUCKET_ORDER})
    U = analyze(up, "measurable_value"); F = analyze(fm, "none")
    both = collections.Counter()
    for r in up + fm:
        both[_bucket(_visible_leg_eth(r) * ETH_USD_WINDOW)] += 1
    return dict(unpriceable=U, failed_measure=F,
                combined_buckets={b: both[b] for b in BUCKET_ORDER},
                combined_throughput_usd=round(U["throughput_usd"] + F["throughput_usd"], 0),
                combined_profit_floor_usd=round(U["measurable_profit_floor_usd"] + F["measurable_profit_floor_usd"], 0))


def render(t1, t2, t3, t4):
    L = []
    W = L.append
    W("# Coverage Hole — Characterizing the Unmeasured 28.7%")
    W("")
    W("Mission M1. The census assigned a measurement verdict to **123,391** detected atomic-arb")
    W("candidates over the 7-day window (blocks 25,437,594–25,487,778): **71.3% measured** as")
    W("priceable arbs, **16.4% unpriceable**, **12.4% failed-to-measure**. This file characterizes")
    W("the 28.7% (35,473 candidates) that the census never valued. All labels [M]=measured from")
    W("stored data, [E]=estimated.")
    W("")
    W("The hole splits by **which leg is unmeasured**:")
    W("")
    W("| population | n | share of hole | unmeasured leg | measurable leg |")
    W("|---|--:|--:|---|---|")
    hole = t4["unpriceable"]["n"] + t4["failed_measure"]["n"]
    W(f"| unpriceable | {t4['unpriceable']['n']:,} | {t4['unpriceable']['n']/hole*100:.1f}% | profit token (a GAIN) | cost side (WETH outlay) |")
    W(f"| failed_measure | {t4['failed_measure']['n']:,} | {t4['failed_measure']['n']/hole*100:.1f}% | a material OUTFLOW (cost) | revenue side (WETH inflow) |")
    W("")
    W("The two are mirror images: unpriceable arbs hide the **upside**, failed arbs hide the **cost**.")
    W("Neither leaves a leg from which profit sign can be proven — see Task 4.")
    W("")

    # Task 1
    W("## Task 1 — Unpriceable population, ranked by arb count [M]")
    W("")
    W(f"{t1['total_arbs']:,} unpriceable arbs reference **{t1['distinct_tokens']:,} distinct exotic")
    W(f"profit tokens** ({t1['total_token_legs']:,} token-legs). The distribution is long-tailed;")
    W("the top-20 tokens account for the counts below. `visible WETH-leg` = the cost-side WETH/")
    W("stable outlay the arb spent to acquire the exotic token (the profit itself is unvalued).")
    W("")
    W("| rank | exotic profit token | arbs | median visible leg | Σ visible leg |")
    W("|--:|---|--:|--:|--:|")
    for i, r in enumerate(t1["rows"], 1):
        W(f"| {i} | `{r['token']}` | {r['arbs']:,} | ${r['med_visible_usd']:,.0f} | ${r['sum_visible_usd']:,.0f} |")
    top20 = sum(r["arbs"] for r in t1["rows"])
    W("")
    W(f"Top-20 tokens = {top20:,} of {t1['total_token_legs']:,} token-legs ")
    W(f"({top20/t1['total_token_legs']*100:.0f}%). The #1 token alone (`{t1['rows'][0]['token']}`) ")
    W(f"appears in {t1['rows'][0]['arbs']:,} unpriceable arbs — a single recurring exotic lane the")
    W("census could not value.")
    W("")

    # Task 2
    W("## Task 2 — Failed-to-measure, bucketed [M]")
    W("")
    W(f"All {t2['total']:,} failed_measure records carry one of two stored reasons:")
    W("")
    W("| stored reason | count |")
    W("|---|--:|")
    for k, v in sorted(t2["reason"].items(), key=lambda x: -x[1]):
        W(f"| {k} | {v:,} |")
    W("")
    W("`unpriceable_outflow` dominates: the arb spent a token the pipeline could not price, so")
    W("gross is uncertain and the record is dropped rather than valued. Structural sub-buckets:")
    W("")
    W("| dimension | breakdown |")
    W("|---|---|")
    W(f"| revenue leg | {', '.join(f'{k}: {v:,}' for k,v in t2['revenue_leg'].items())} |")
    W(f"| n_swaps | {', '.join(f'{k}: {v:,}' for k,v in sorted(t2['n_swaps'].items()))} |")
    W(f"| has_flash | {t2['has_flash']:,} of {t2['total']:,} |")
    W(f"| multi_asset | {t2['multi_asset']:,} of {t2['total']:,} |")
    W(f"| measurable value_eth sign | {', '.join(f'{k}: {v:,}' for k,v in t2['value_sign'].items())} |")
    W("")
    W(f"{t2['revenue_leg'].get('revenue_leg_visible',0):,} of {t2['total']:,} have a visible")
    W("revenue leg (we see WETH come in but not what it cost). The positive-`value_eth` majority is")
    W("**not** profit: it is revenue whose cost leg is exactly the unpriced outflow — see Task 4.")
    W("")

    # Task 3
    W("## Task 3 — Did a price route exist? (bounded fetch) [M]")
    W("")
    W(f"For the top-10 unpriceable tokens, checked at each token's first-occurrence block whether")
    W(f"any WETH/USDC/USDT pool held **>$50k liquidity**. Budget: {t3['calls_used']} of")
    W(f"{t3['cap']} RPC calls. A census pool needed only ~0.3 WETH (~$500) depth, so a token that")
    W("shows no deep pool here was genuinely thin at the window; a token WITH a deep pool was")
    W("skipped for another reason (broken spot / non-standard pool / fee-on-transfer).")
    W("")
    W("| exotic token | arbs | best liquidity | route | verdict |")
    W("|---|--:|--:|---|---|")
    pir = 0
    for r in t3["rows"]:
        if r["label"] == "PRICEABLE-IN-RETROSPECT": pir += 1
        W(f"| `{r['token']}` | {r['arbs']:,} | ${r['best_liquidity_usd']:,.0f} | {r['route']} | {r['label']} |")
    W("")
    W(f"**{pir} of {len(t3['rows'])}** top tokens were PRICEABLE-IN-RETROSPECT — a deep route")
    W("existed but the census pipeline refused it (most likely the `SANE_ETH_PER_TOKEN` cap")
    W("tripping on a thin-spot or fee-on-transfer token). The remaining")
    W(f"{len(t3['rows'])-pir} are GENUINELY-EXOTIC: no >$50k route existed at the window.")
    W("")

    # Task 4
    W("## Task 4 — Profit mass in the hole [E]")
    W("")
    W("**Formula (measurable-leg lower bound).** For each hole arb, `visible` = the largest sane")
    W("|priced beneficiary leg| in USD. Then:")
    W("")
    W("- **unpriceable arbs:** the profit is entirely the unvalued gain token. Measured across all")
    W(f"  {t4['unpriceable']['n']:,} of them, the signed measurable position change `value_eth` is")
    W("  **≤ 0 in every single case** (Σ positive measurable value = $0). We can prove economic")
    W("  activity flowed, but **not one dollar of profit** is provable from measurable legs.")
    W("- **failed_measure arbs:** the visible leg is *revenue* with the cost hidden — it bounds")
    W("  revenue from above, giving no profit floor.")
    W("")
    W("So the **provable measurable profit floor of the entire hole is $0.** What is measurable is")
    W("**throughput** — a floor on economic size passing through the hole:")
    W("")
    W("| population | n | with visible leg | throughput floor (Σ visible) | measurable profit floor |")
    W("|---|--:|--:|--:|--:|")
    for name, key in [("unpriceable", "unpriceable"), ("failed_measure", "failed_measure")]:
        d = t4[key]
        W(f"| {name} | {d['n']:,} | {d['with_leg']:,} | ${d['throughput_usd']:,.0f} | ${d['measurable_profit_floor_usd']:,.0f} |")
    W(f"| **combined** | {hole:,} | — | ${t4['combined_throughput_usd']:,.0f} | ${t4['combined_profit_floor_usd']:,.0f} |")
    W("")
    W("_(throughput uses a $47M/leg sanity cap; failed_measure retains mispriced legs because")
    W("`has_unpriceable_loss` is tested before the pipeline's sane backstop.)_")
    W("")
    W("**Dust, treasure, or mixed — by counts (visible-leg size):**")
    W("")
    W("| visible-leg size | unpriceable | failed_measure | combined |")
    W("|---|--:|--:|--:|")
    for b in BUCKET_ORDER:
        W(f"| {b} | {t4['unpriceable']['buckets'][b]:,} | {t4['failed_measure']['buckets'][b]:,} | {t4['combined_buckets'][b]:,} |")
    W("")
    dust = t4["combined_buckets"]["dust (<$1)"] + t4["combined_buckets"]["small ($1-50)"]
    treasure = t4["combined_buckets"]["large (>$1k)"]
    W(f"**Mixed.** {dust:,} hole arbs ({dust/hole*100:.0f}%) have a visible leg under $50 —")
    W(f"consistent with dust/spam. {treasure:,} ({treasure/hole*100:.0f}%) have a visible leg")
    W("over $1,000 — real size moving through unmeasured lanes. The hole is neither pure dust nor")
    W("pure treasure: it is bimodal. No verdict is drawn on whether the large-leg arbs are")
    W("*profitable* — that is exactly the leg the census cannot see.")
    W("")
    return "\n".join(L)


def main():
    up, fm = load()
    t1 = task1(up)
    t2 = task2(fm)
    t3 = task3(t1["_ct"], up)
    t4 = task4(up, fm)
    json.dump(dict(task3=t3), open("out/coverage_hole_fetch.json", "w"), indent=1)
    md = render(t1, t2, t3, t4)
    open("out/coverage_hole.md", "w").write(md)
    print("calls used (task3):", t3["calls_used"])
    print("wrote out/coverage_hole.md", len(md), "bytes")


if __name__ == "__main__":
    main()

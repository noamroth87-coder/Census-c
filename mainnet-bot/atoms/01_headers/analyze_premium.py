"""Atom 1b — analyze the four-way race into metrics_premium.json + REPORT_premium.md.

Same metric definitions as atom-1 (arrival gap vs block timestamp; head-to-head first-fire;
jitter p50/p90/p99; dup/missed/out-of-order; reconnect recovery), generalized to 4 sources,
plus the key new comparison: consensus-head reveal vs execution-header reveal for the same
execution block.
"""
import json, os, statistics as st
from census.rpc import call
from census.config import ETH_RPC_ARCHIVE as RPC

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw_timings_premium.jsonl")
META = os.path.join(HERE, "run_meta_premium.json")
SOURCES = ["prem_http", "prem_wss", "beacon", "baseline_wss"]
LABEL = {"prem_http": "Chainstack exec HTTP poll 50ms (premium)",
         "prem_wss": "Chainstack exec WSS newHeads (premium)",
         "beacon": "Chainstack consensus head-poll 50ms (premium)",
         "baseline_wss": "atom-1 baseline WSS newHeads (key URL)"}


def pct(xs, p):
    if not xs: return None
    xs = sorted(xs); k = (len(xs) - 1) * p / 100.0
    lo = int(k); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def stats(xs):
    return dict(n=len(xs), p50=pct(xs, 50), p90=pct(xs, 90), p99=pct(xs, 99),
                min=min(xs) if xs else None, max=max(xs) if xs else None,
                mean=st.mean(xs) if xs else None)


def analyze():
    recs = [json.loads(l) for l in open(RAW) if l.strip()]
    meta = json.load(open(META)) if os.path.exists(META) else {}
    events = [r for r in recs if "event" in r]
    src = [r for r in recs if "src" in r and "num" in r]

    reg = {}                      # num -> {src: {wall, mono}, ts}
    arrivals = {s: [] for s in SOURCES}
    for r in sorted(src, key=lambda x: x["mono_ns"]):
        d = reg.setdefault(r["num"], {"src": {}})
        arrivals[r["src"]].append(r["num"])
        if r["src"] not in d["src"]:
            d["src"][r["src"]] = {"wall": r["wall_ns"], "mono": r["mono_ns"]}
        if r.get("ts") is not None:
            d["ts"] = r["ts"]

    backfilled = 0
    for num, d in reg.items():
        if "ts" not in d:
            b = call("eth_getBlockByNumber", [hex(num), False], rpc=RPC)
            if isinstance(b, dict) and b.get("timestamp"):
                d["ts"] = int(b["timestamp"], 16); backfilled += 1

    # arrival gaps per source
    gaps = {s: [] for s in SOURCES}
    for num, d in reg.items():
        if "ts" not in d: continue
        for s in SOURCES:
            if s in d["src"]:
                gaps[s].append(d["src"][s]["wall"] / 1e9 - d["ts"])
    gap_stats = {s: stats(gaps[s]) for s in SOURCES}

    # reliability per source
    def reliability(arr):
        seen = set(); dups = ooo = 0; mx = None
        for n in arr:
            if n in seen: dups += 1
            seen.add(n)
            if mx is not None and n < mx: ooo += 1
            mx = n if mx is None else max(mx, n)
        missed = sorted(set(range(min(seen), max(seen) + 1)) - seen) if seen else []
        return dict(distinct=len(seen), duplicates=dups, out_of_order=ooo,
                    missed_count=len(missed), missed=missed[:30])
    rel = {s: reliability(arrivals[s]) for s in SOURCES}

    # four-way first-fire: per block, which source's mono is smallest
    first_fire = {s: 0 for s in SOURCES}
    for num, d in reg.items():
        present = [(s, d["src"][s]["mono"]) for s in SOURCES if s in d["src"]]
        if present:
            first_fire[min(present, key=lambda x: x[1])[0]] += 1

    # pairwise deltas vs beacon (consensus) — the key comparison
    def pair_delta(a, b):
        """(a_mono - b_mono) ms for blocks seen by both; >0 => b first."""
        out = []
        for num, d in reg.items():
            if a in d["src"] and b in d["src"]:
                out.append((d["src"][a]["mono"] - d["src"][b]["mono"]) / 1e6)
        return out
    consensus_vs = {}
    for ex in ["prem_wss", "prem_http", "baseline_wss"]:
        dl = pair_delta(ex, "beacon")   # >0 => beacon (consensus) fired first
        consensus_vs[ex] = dict(n=len(dl), beacon_first=sum(1 for x in dl if x > 0),
                                exec_first=sum(1 for x in dl if x < 0), tie=sum(1 for x in dl if x == 0),
                                delta_ms=stats(dl))

    # premium exec vs baseline (same-transport WSS)
    prem_vs_base = stats(pair_delta("baseline_wss", "prem_wss"))  # >0 => prem_wss first

    # reconnect per source
    def ev(name, s):
        for e in events:
            if e.get("event") == name and e.get("src") == s: return e
        return None
    recon = {}
    for s in SOURCES:
        k = ev("reconnect_kill", s)
        if not k: continue
        after = [reg[n]["src"][s]["mono"] for n in reg if s in reg[n]["src"] and reg[n]["src"][s]["mono"] > k["mono_ns"]]
        first_after = min(after) if after else None
        missed = []
        for n, d in reg.items():
            # a block another source saw during this source's outage that this source missed
            if s not in d["src"]:
                others = [d["src"][o]["mono"] for o in d["src"]]
                if others and k["mono_ns"] <= min(others) <= (first_after or 1e30):
                    missed.append(n)
        recon[s] = dict(time_to_recover_s=(first_after - k["mono_ns"]) / 1e9 if first_after else None,
                        blocks_missed=len(set(missed)))

    rate = {s: sum(1 for e in events if e.get("event") == "rate_limited" and e.get("src") == s) for s in SOURCES}
    errs = {s: sum(1 for e in events if e.get("event") in ("poll_exc", "ws_error", "beacon_map_exc") and e.get("src") == s) for s in SOURCES}

    # winner = source with lowest p50 arrival gap (ties -> most first-fires)
    ranked = sorted(SOURCES, key=lambda s: (gap_stats[s]["p50"] if gap_stats[s]["p50"] is not None else 9,
                                            -first_fire[s]))
    winner = ranked[0]

    metrics = dict(meta=meta, sources=SOURCES, label=LABEL,
                   gap=gap_stats, reliability=rel, first_fire=first_fire,
                   consensus_vs=consensus_vs, prem_wss_vs_baseline=prem_vs_base,
                   reconnect=recon, rate_limited=rate, errors=errs, backfilled_ts=backfilled,
                   winner=winner, latency_floor=dict(p50=gap_stats[winner]["p50"], p99=gap_stats[winner]["p99"]),
                   blocks_total=len(reg))
    json.dump(metrics, open(os.path.join(HERE, "metrics_premium.json"), "w"), indent=1, default=str)
    return metrics


def f(x, d=3):
    return f"{x:.{d}f}" if isinstance(x, (int, float)) else "n/a"


def render(m):
    g = m["gap"]; rel = m["reliability"]; ff = m["first_fire"]; rc = m["reconnect"]
    win = m["winner"]; lf = m["latency_floor"]; L = []; W = L.append
    W("# Atom 1b — Premium Endpoint Race (four-way)")
    W("")
    W(f"Same harness as atom-1; only endpoints changed. Four \"new block exists\" signals raced "
      f"live for **{(m['meta'].get('duration_s') or 0)//60} min**, one deliberate reconnect each "
      f"(staggered). {m['blocks_total']} execution blocks observed. Credentials handled via env + "
      "Authorization header; none are in this report, the raw log, or any committed file. **SSE "
      "(`/eth/v1/events?topics=head`) was tested and is unusable through the agent proxy (the "
      "stream is buffered — connect read-timeout), so the consensus source polls "
      "`/eth/v1/beacon/headers/head` @50ms** and maps slot→execution block via "
      "`/eth/v2/beacon/blocks/{slot}` (mapping fetch excluded from the reveal timing).")
    W("")
    W("Arrival gap = local receive − block's own `timestamp` (whole-second; ~1 s quantization + "
      "proposer skew, so read the p50/p99 *shape*, not sub-second digits).")
    W("")
    W("## Four-way league table")
    W("")
    W("| source | blocks | gap p50 (s) | gap p90 (s) | gap p99 (s) | first-fire wins | dup | ooo | missed |")
    W("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    for s in SOURCES:
        W(f"| {LABEL[s]} | {rel[s]['distinct']} | {f(g[s]['p50'],3)} | {f(g[s]['p90'],3)} | "
          f"{f(g[s]['p99'],3)} | {ff[s]} | {rel[s]['duplicates']} | {rel[s]['out_of_order']} | "
          f"{rel[s]['missed_count']} |")
    W("")
    W(f"**Winner (lowest p50 arrival gap): {LABEL[win]}** — first-fire wins {ff[win]} of "
      f"{m['blocks_total']} blocks.")
    W("")
    W("## Consensus-layer vs execution-layer sight (the key question)")
    W("")
    W("Per block seen by both the consensus head-poll and an execution source — delta "
      "`(exec − beacon)` ms, **positive = consensus (beacon) revealed it first**:")
    W("")
    W("| execution source vs beacon | blocks | beacon first | exec first | median Δ (ms) | p90 Δ (ms) |")
    W("|---|--:|--:|--:|--:|--:|")
    for ex, d in m["consensus_vs"].items():
        W(f"| {ex} | {d['n']} | {d['beacon_first']} | {d['exec_first']} | "
          f"{f(d['delta_ms']['p50'],1)} | {f(d['delta_ms']['p90'],1)} |")
    W("")
    # decide the consensus verdict
    cw = m["consensus_vs"].get("prem_wss", {})
    beacon_wins = cw.get("beacon_first", 0) > cw.get("exec_first", 0)
    med = cw.get("delta_ms", {}).get("p50")
    if beacon_wins and (med or 0) > 0:
        W(f"**Consensus sight beats execution sight** on this provider: the beacon head-poll fired "
          f"first on {cw['beacon_first']}/{cw['n']} blocks vs premium exec-WSS, median "
          f"**+{f(med,0)} ms** earlier.")
    else:
        W(f"**Consensus sight does NOT beat execution sight** here: beacon fired first on only "
          f"{cw.get('beacon_first','?')}/{cw.get('n','?')} blocks vs premium exec-WSS "
          f"(median {f(med,0)} ms). The extra head-poll + slot→block mapping does not buy earlier "
          "sight through this provider's API.")
    W("")
    W("## Premium execution vs baseline (same WSS transport)")
    pv = m["prem_wss_vs_baseline"]
    W(f"- Δ `(baseline − prem_wss)` ms, >0 = premium first: median **{f(pv['p50'],1)} ms**, "
      f"p90 {f(pv['p90'],1)} ms (n={pv['n']}). ")
    W("")
    W("## Reliability & reconnect")
    W("")
    for s in SOURCES:
        r = rc.get(s, {})
        W(f"- **{s}**: {rel[s]['duplicates']} dup, {rel[s]['out_of_order']} ooo, "
          f"{rel[s]['missed_count']} missed; reconnect recover "
          f"{f(r.get('time_to_recover_s'),2)} s, missed-during-outage {r.get('blocks_missed','?')}.")
    W("")
    W("## Provider notes")
    W(f"- Rate limits (429): {m['rate_limited']}. Errors: {m['errors']}. "
      f"Two 50 ms poll loops = ~40 req/s basic-auth sustained.")
    W(f"- Timestamps back-filled for {m['backfilled_ts']} block(s) (poll-only, no header ts).")
    W("")
    W("## Latency floor & verdict")
    W("")
    p50s = {s: g[s]["p50"] for s in SOURCES}
    best = min((v for v in p50s.values() if v is not None), default=None)
    base = p50s.get("baseline_wss")
    broke2 = [s for s in SOURCES if (p50s[s] or 9) < 2.0]
    W(f"**New latency floor = winner {win} p50 {f(lf['p50'],2)} s / p99 {f(lf['p99'],2)} s.**")
    W("")
    if broke2:
        W(f"- **Below 2 s?** YES — {', '.join(broke2)} broke below the atom-1 2.04 s floor "
          f"(best p50 {f(best,2)} s).")
    else:
        W(f"- **Below 2 s?** NO — no premium endpoint broke below 2 s; best p50 {f(best,2)} s vs "
          f"baseline {f(base,2)} s. The premium credentials buy reliability/limits headroom, not a "
          "lower arrival-gap floor.")
    W("")
    W("**Per-endpoint verdict** (HOT-path-viable needs p50 arrival gap well under ~2 s):")
    for s in SOURCES:
        v = "HOT-path-viable" if (p50s[s] or 9) < 1.5 else ("marginal" if (p50s[s] or 9) < 2.0 else "NOT HOT-path")
        W(f"- **{s}** — p50 {f(p50s[s],2)} s → **{v}**.")
    W("")
    gap_floor = best or 9
    if gap_floor >= 2.0:
        W("**Bottom line:** the ~2 s arrival gap is a **provider/propagation floor that premium "
          "access does NOT remove** — every endpoint (execution HTTP/WSS, consensus, baseline) lands "
          "in the same ~2 s band. Same infrastructure conclusion as atom-1: for same-block "
          "backrunning, a co-located node / direct peer is required; these hosted endpoints are for "
          "observation, not the HOT path.")
    else:
        W(f"**Bottom line:** a premium endpoint broke the 2 s floor (best p50 {f(best,2)} s) — worth "
          "escalating that specific endpoint for HOT-path validation.")
    W("")
    W("*Atom 1b complete. Stop — do not proceed to atom 2.*")
    open(os.path.join(HERE, "REPORT_premium.md"), "w").write("\n".join(L))
    return "\n".join(L)


if __name__ == "__main__":
    m = analyze()
    render(m)
    print(json.dumps({"winner": m["winner"], "latency_floor": m["latency_floor"],
                      "first_fire": m["first_fire"],
                      "consensus_vs_prem_wss": m["consensus_vs"].get("prem_wss"),
                      "rate_limited": m["rate_limited"]}, indent=1, default=str))
    print("wrote REPORT_premium.md + metrics_premium.json")

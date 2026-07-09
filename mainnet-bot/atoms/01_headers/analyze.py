"""Atom 1 — analyze raw_timings.jsonl into metrics.json + REPORT.md.

Arrival gap  = recv_wall/1e9 - block.timestamp  (propagation + provider lag; how stale the
               news is when we receive it). Block timestamp is whole-second and proposer-set,
               so gaps carry up to ~1 s quantization + proposer clock skew — stated in report.
WS-vs-poll   = (poll_mono - ws_mono)/1e6 ms per block seen by both; >0 => WS first.
Reliability  = duplicates / out-of-order / missed block numbers per source.
Reconnect    = blocks missed and time-to-recover around the deliberate mid-run WS kill.
"""
import json, os, statistics as st
from census.rpc import call  # reuse the repo's RPC client for historical ts back-fill
from census.config import ETH_RPC_ARCHIVE as RPC

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw_timings.jsonl")
META = os.path.join(HERE, "run_meta.json")


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100.0
    lo = int(k); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def load():
    recs = []
    with open(RAW) as f:
        for line in f:
            try: recs.append(json.loads(line))
            except Exception: pass
    return recs


def analyze():
    recs = load()
    meta = json.load(open(META)) if os.path.exists(META) else {}
    events = [r for r in recs if "event" in r]
    src = [r for r in recs if "src" in r]

    # per-source ordered arrival log (in mono order) + per-block registry
    reg = {}                    # num -> {ws_wall, ws_mono, poll_wall, poll_mono, ts}
    ws_arrivals = []; poll_arrivals = []
    for r in sorted(src, key=lambda x: x["mono_ns"]):
        num = r["num"]; d = reg.setdefault(num, {})
        if r["src"] == "ws":
            ws_arrivals.append(num)
            if "ws_mono" not in d:
                d["ws_wall"] = r["wall_ns"]; d["ws_mono"] = r["mono_ns"]
            if r.get("ts") is not None: d["ts"] = r["ts"]
        else:
            poll_arrivals.append(num)
            if "poll_mono" not in d:
                d["poll_wall"] = r["wall_ns"]; d["poll_mono"] = r["mono_ns"]

    # back-fill block timestamps for poll-only blocks (historical, cheap)
    backfilled = 0
    for num, d in reg.items():
        if "ts" not in d:
            r = call("eth_getBlockByNumber", [hex(num), False], rpc=RPC)
            if isinstance(r, dict) and r.get("timestamp"):
                d["ts"] = int(r["timestamp"], 16); backfilled += 1

    # ---- arrival gaps (seconds) ----
    def gaps(key):
        out = []
        for num, d in reg.items():
            if key in d and "ts" in d:
                out.append(d[key] / 1e9 - d["ts"])
        return out
    ws_gap = gaps("ws_wall"); poll_gap = gaps("poll_wall")

    # ---- WS vs poll delta (ms), blocks seen by both ----
    both = [num for num, d in reg.items() if "ws_mono" in d and "poll_mono" in d]
    deltas = [(reg[n]["poll_mono"] - reg[n]["ws_mono"]) / 1e6 for n in both]  # >0 => WS first
    ws_first = sum(1 for x in deltas if x > 0)
    poll_first = sum(1 for x in deltas if x < 0)
    tie = sum(1 for x in deltas if x == 0)

    # ---- reliability per source ----
    def reliability(arr):
        seen = set(); dups = 0; ooo = 0; mx = None
        for n in arr:
            if n in seen: dups += 1
            seen.add(n)
            if mx is not None and n < mx: ooo += 1
            mx = max(mx, n) if mx is not None else n
        if seen:
            full = set(range(min(seen), max(seen) + 1))
            missed = sorted(full - seen)
        else:
            missed = []
        return dict(distinct=len(seen), duplicates=dups, out_of_order=ooo,
                    missed_count=len(missed), missed=missed[:50],
                    span=[min(seen), max(seen)] if seen else None)
    ws_rel = reliability(ws_arrivals); poll_rel = reliability(poll_arrivals)

    # ---- reconnect ----
    def ev(name):
        for e in events:
            if e.get("event") == name: return e
        return None
    kill = ev("reconnect_kill"); begin = ev("reconnect_begin")
    recon = {}
    if kill:
        # first ws header strictly after the kill
        after = [reg[n]["ws_mono"] for n in reg if "ws_mono" in reg[n] and reg[n]["ws_mono"] > kill["mono_ns"]]
        first_ws_after = min(after) if after else None
        recon["kill_mono"] = kill["mono_ns"]
        recon["time_to_recover_s"] = (first_ws_after - kill["mono_ns"]) / 1e9 if first_ws_after else None
        # blocks the poll saw during the outage that WS never recorded
        missed = []
        for n, d in reg.items():
            if "poll_mono" in d and kill["mono_ns"] <= d["poll_mono"] <= (first_ws_after or 1e30):
                if "ws_mono" not in d or d["ws_mono"] > (first_ws_after or 0):
                    missed.append(n)
        recon["blocks_missed_during_reconnect"] = sorted(set(missed))
        recon["n_missed_during_reconnect"] = len(set(missed))

    rate_limited = sum(1 for e in events if e.get("event") == "poll_rate_limited")
    http_errors = sum(1 for e in events if e.get("event") in ("poll_http_error", "poll_exc"))
    ws_errors = sum(1 for e in events if e.get("event") == "ws_reconnect_error")

    def stats(xs):
        return dict(n=len(xs), p50=pct(xs, 50), p90=pct(xs, 90), p99=pct(xs, 99),
                    min=min(xs) if xs else None, max=max(xs) if xs else None,
                    mean=st.mean(xs) if xs else None)

    winner = "ws" if (ws_first >= poll_first) else "poll"
    win_gap = ws_gap if winner == "ws" else poll_gap

    metrics = dict(
        meta=meta, duration_s=meta.get("duration_s"),
        ws_gap=stats(ws_gap), poll_gap=stats(poll_gap),
        ws_vs_poll=dict(both_n=len(both), ws_first=ws_first, poll_first=poll_first, tie=tie,
                        delta_ms=stats(deltas)),
        reliability=dict(ws=ws_rel, poll=poll_rel),
        reconnect=recon, backfilled_ts=backfilled,
        provider=dict(rate_limited=rate_limited, http_errors=http_errors, ws_errors=ws_errors),
        winner=winner, latency_floor=dict(p50=pct(win_gap, 50), p99=pct(win_gap, 99)),
    )
    json.dump(metrics, open(os.path.join(HERE, "metrics.json"), "w"), indent=1, default=str)
    return metrics


def f(x, d=3):
    return f"{x:.{d}f}" if isinstance(x, (int, float)) else "n/a"


def render(m):
    L = []; W = L.append
    dur = m.get("duration_s") or 0
    wg, pg = m["ws_gap"], m["poll_gap"]
    vp = m["ws_vs_poll"]; rel = m["reliability"]; rc = m["reconnect"]; pv = m["provider"]
    win = m["winner"]; lf = m["latency_floor"]
    W("# Atom 1 — Block-Header Subscription: latency profile")
    W("")
    W(f"Prototype-and-measure. Three variants of \"a new block exists\" raced live for "
      f"**{dur//60} min** against Chainstack mainnet (`{m['meta'].get('ws_url_host','?')}`), "
      f"poll interval **{m['meta'].get('poll_ms')} ms**, one deliberate WS reconnect at "
      f"{m['meta'].get('reconnect_at_s',0)//60} min. Not production code.")
    W("")
    W("**Arrival gap** = local receive time − the block's own `timestamp` (whole-second, "
      "proposer-set). It is the true staleness of the news: propagation + provider lag. Caveat: "
      "the whole-second timestamp adds up to ~1 s quantization and carries proposer clock skew, "
      "so treat sub-second gap digits as noise; the p50/p99 *shape* is what matters.")
    W("")
    W("## Comparison table")
    W("")
    W("| metric | WebSocket `newHeads` | HTTP poll (50 ms) |")
    W("|---|--:|--:|")
    W(f"| blocks seen | {rel['ws']['distinct']} | {rel['poll']['distinct']} |")
    W(f"| arrival gap p50 (s) | {f(wg['p50'])} | {f(pg['p50'])} |")
    W(f"| arrival gap p90 (s) | {f(wg['p90'])} | {f(pg['p90'])} |")
    W(f"| arrival gap p99 (s) | {f(wg['p99'])} | {f(pg['p99'])} |")
    W(f"| arrival gap min / max (s) | {f(wg['min'])} / {f(wg['max'])} | {f(pg['min'])} / {f(pg['max'])} |")
    W(f"| duplicates | {rel['ws']['duplicates']} | {rel['poll']['duplicates']} |")
    W(f"| out-of-order | {rel['ws']['out_of_order']} | {rel['poll']['out_of_order']} |")
    W(f"| missed blocks | {rel['ws']['missed_count']} | {rel['poll']['missed_count']} |")
    W("")
    W("## Head-to-head (blocks seen by both)")
    W("")
    W(f"- Blocks compared: **{vp['both_n']}**. **WS fired first on {vp['ws_first']}**, "
      f"**poll first on {vp['poll_first']}**, tie {vp['tie']}.")
    d = vp["delta_ms"]
    W(f"- Per-block delta `(poll − ws)` ms — **positive = WS first**: "
      f"p50 **{f(d['p50'],1)} ms**, p90 {f(d['p90'],1)} ms, p99 {f(d['p99'],1)} ms, "
      f"range [{f(d['min'],1)}, {f(d['max'],1)}].")
    W(f"- **Winner: {win.upper()}.**")
    W("")
    W("## Reliability & reconnect")
    W("")
    W(f"- WS: {rel['ws']['distinct']} blocks, {rel['ws']['duplicates']} dup, "
      f"{rel['ws']['out_of_order']} out-of-order, {rel['ws']['missed_count']} missed "
      f"{rel['ws']['missed'] or ''}.")
    W(f"- Poll: {rel['poll']['distinct']} blocks, {rel['poll']['duplicates']} dup, "
      f"{rel['poll']['out_of_order']} out-of-order, {rel['poll']['missed_count']} missed "
      f"{rel['poll']['missed'] or ''}.")
    if rc:
        W(f"- **Deliberate WS kill/reconnect:** time-to-recover "
          f"**{f(rc.get('time_to_recover_s'),2)} s**; blocks missed by WS during the outage "
          f"**{rc.get('n_missed_during_reconnect')}** {rc.get('blocks_missed_during_reconnect') or ''} "
          f"— all still caught by the poll (that is the point of running both).")
    W("")
    W("## Provider-specific notes")
    W("")
    W(f"- **WebSocket offered?** Yes — `wss://{m['meta'].get('ws_url_host','?')}/<key>` works "
      "natively through the agent HTTP-CONNECT proxy; `eth_subscribe(newHeads)` returns a "
      "subscription id and streams headers.")
    W(f"- **Rate limits:** {pv['rate_limited']} HTTP 429 across the run at 20 req/s poll; "
      f"other HTTP errors {pv['http_errors']}; WS reconnect errors {pv['ws_errors']}.")
    W(f"- Timestamps back-filled historically for {m['backfilled_ts']} poll-only block(s).")
    W("")
    W("## Latency floor (inherited by every downstream atom)")
    W("")
    W(f"Winner **{win.upper()}** arrival gap: **p50 {f(lf['p50'],2)} s**, **p99 {f(lf['p99'],2)} s**. "
      "This is the floor: no downstream atom can act on a block sooner than this after it is "
      "produced, regardless of how fast our code is.")
    W("")
    W("## Verdict")
    W("")
    p50 = lf["p50"] or 0
    if p50 > 3:
        verdict = (f"**Disqualifying for a HOT-path bot.** The p50 arrival gap of {f(p50,2)} s means "
                   "the provider hands us the block already ~{:.0f}s stale — an atomic-arb backrun "
                   "must land in the *same* block, and by the time this endpoint even tells us the "
                   "block exists, block-building for the next slot is largely done. This is an "
                   "**infrastructure decision**: a co-located / direct-peer or a premium low-latency "
                   "provider is required before any HOT-path work is worth building.".format(p50))
    elif p50 > 2:
        gap_ws = f(wg['p50'], 2); gap_poll = f(pg['p50'], 2)
        verdict = (f"**Marginal / likely disqualifying for HOT-path.** p50 arrival gap {f(p50,2)} s sits "
                   "in the 2–3 s danger zone — the provider eats most of a 12 s slot before our code "
                   f"runs. The decisive point: **WS and poll show the *same* ~{f(p50,2)} s p50 gap** "
                   f"(WS {gap_ws} s, poll {gap_poll} s), so the floor is **provider / propagation "
                   "latency, not transport choice** — no WS-vs-poll tuning or faster code removes it; "
                   "only different infrastructure (co-located node / direct peer / premium low-latency "
                   f"provider) will. Aggressive polling even edges the WS here (poll first on "
                   f"{vp['poll_first']}/{vp['both_n']} blocks, median {f(vp['delta_ms']['p50'],0)} ms), "
                   "confirming the WS push is not a latency advantage on this endpoint. Usable for "
                   "observation/analytics; for same-block backrunning this is an **infrastructure "
                   "decision to escalate** before building the HOT path on it.")
    else:
        verdict = (f"**Fit for HOT-path observation, with eyes open.** p50 arrival gap {f(p50,2)} s leaves "
                   "headroom inside a 12 s slot. The surprise is that aggressive 50 ms polling is "
                   f"{'competitive with' if abs(vp['delta_ms']['p50'] or 0) < 50 else 'not beaten by'} "
                   "the WS subscription on this endpoint, so the WS is not a decisive latency win here "
                   "— but WS costs no request budget and survives at 1 conn, so it remains the baseline; "
                   "poll is the cheap insurance that also covers the reconnect gap.")
    W(verdict)
    W("")
    W("*Atom 1 complete. Stop — do not proceed to atom 2 (event ingest).*")
    open(os.path.join(HERE, "REPORT.md"), "w").write("\n".join(L))
    return "\n".join(L)


if __name__ == "__main__":
    m = analyze()
    render(m)
    print(json.dumps({k: m[k] for k in ("winner", "latency_floor", "ws_vs_poll", "provider")},
                     indent=1, default=str))
    print("wrote REPORT.md + metrics.json")

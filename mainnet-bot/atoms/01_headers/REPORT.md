# Atom 1 — Block-Header Subscription: latency profile

Prototype-and-measure. Three variants of "a new block exists" raced live for **30 min** against Chainstack mainnet (`ethereum-mainnet.core.chainstack.com`), poll interval **50 ms**, one deliberate WS reconnect at 15 min. Not production code.

**Arrival gap** = local receive time − the block's own `timestamp` (whole-second, proposer-set). It is the true staleness of the news: propagation + provider lag. Caveat: the whole-second timestamp adds up to ~1 s quantization and carries proposer clock skew, so treat sub-second gap digits as noise; the p50/p99 *shape* is what matters.

## Comparison table

| metric | WebSocket `newHeads` | HTTP poll (50 ms) |
|---|--:|--:|
| blocks seen | 149 | 151 |
| arrival gap p50 (s) | 2.053 | 2.037 |
| arrival gap p90 (s) | 3.582 | 3.525 |
| arrival gap p99 (s) | 4.895 | 4.486 |
| arrival gap min / max (s) | 0.737 / 5.156 | 0.697 / 5.205 |
| duplicates | 0 | 0 |
| out-of-order | 0 | 0 |
| missed blocks | 1 | 0 |

## Head-to-head (blocks seen by both)

- Blocks compared: **149**. **WS fired first on 31**, **poll first on 118**, tie 0.
- Per-block delta `(poll − ws)` ms — **positive = WS first**: p50 **-51.6 ms**, p90 32.1 ms, p99 82.3 ms, range [-872.4, 145.0].
- **Winner: POLL.**

## Reliability & reconnect

- WS: 149 blocks, 0 dup, 0 out-of-order, 1 missed [25495085].
- Poll: 151 blocks, 0 dup, 0 out-of-order, 0 missed .
- **Deliberate WS kill/reconnect:** time-to-recover **11.56 s**; blocks missed by WS during the outage **1** [25495085] — all still caught by the poll (that is the point of running both).

## Provider-specific notes

- **WebSocket offered?** Yes — `wss://ethereum-mainnet.core.chainstack.com/<key>` works natively through the agent HTTP-CONNECT proxy; `eth_subscribe(newHeads)` returns a subscription id and streams headers.
- **Rate limits:** 0 HTTP 429 across the run at 20 req/s poll; other HTTP errors 0; WS reconnect errors 0.
- Timestamps back-filled historically for 2 poll-only block(s).

## Latency floor (inherited by every downstream atom)

Winner **POLL** arrival gap: **p50 2.04 s**, **p99 4.49 s**. This is the floor: no downstream atom can act on a block sooner than this after it is produced, regardless of how fast our code is.

## Verdict

**Marginal / likely disqualifying for HOT-path.** p50 arrival gap 2.04 s sits in the 2–3 s danger zone — the provider eats most of a 12 s slot before our code runs. The decisive point: **WS and poll show the *same* ~2.04 s p50 gap** (WS 2.05 s, poll 2.04 s), so the floor is **provider / propagation latency, not transport choice** — no WS-vs-poll tuning or faster code removes it; only different infrastructure (co-located node / direct peer / premium low-latency provider) will. Aggressive polling even edges the WS here (poll first on 118/149 blocks, median -52 ms), confirming the WS push is not a latency advantage on this endpoint. Usable for observation/analytics; for same-block backrunning this is an **infrastructure decision to escalate** before building the HOT path on it.

*Atom 1 complete. Stop — do not proceed to atom 2 (event ingest).*
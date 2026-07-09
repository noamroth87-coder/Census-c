# Atom 1b — Premium Endpoint Race (four-way)

Same harness as atom-1; only endpoints changed. Four "new block exists" signals raced live for **30 min**, one deliberate reconnect each (staggered). 148 execution blocks observed. Credentials were handled via env + Authorization header; none appear in this report, the raw log, or any committed file. **SSE (`/eth/v1/events?topics=head`) was tested and is unusable through the agent proxy — the stream is buffered (connect read-timeout), so the consensus source polls `/eth/v1/beacon/headers/head` @50ms** and maps slot→execution block via `/eth/v2/beacon/blocks/{slot}` (mapping fetch excluded from the reveal timing).

**Read the numbers correctly.** Arrival gap = local receive − block's own `timestamp`. That timestamp is whole-second and proposer-set, so each block's gap carries up to ~1 s of quantization. Comparing p50 gaps *across* sources at the ~100 ms level is therefore inside the noise — the trustworthy discriminator is **first-fire** (a per-block monotonic-clock race in which the timestamp cancels).

## Four-way league table

| source | blocks | gap p50 (s) | gap mean (s) | gap p99 (s) | first-fire wins | dup | ooo | missed |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Chainstack exec HTTP poll 50ms (premium) | 148 | 2.053 | 2.331 | 5.067 | 71 | 0 | 0 | 0 |
| Chainstack exec WSS newHeads (premium) | 147 | 1.986 | 2.229 | 5.298 | 38 | 1 | 0 | 0 |
| Chainstack consensus head-poll 50ms (premium) | 123 | 2.433 | 2.521 | 4.980 | 25 | 0 | 0 | 25 |
| atom-1 baseline WSS newHeads (key URL) | 146 | 1.971 | 2.232 | 5.258 | 14 | 1 | 0 | 1 |

**Winner (first-fire): Chainstack exec HTTP poll 50ms (premium)** — fired first on **71 of 148 blocks**, more than any other source. The three execution sources sit in one indistinguishable ~2.0 s p50 band (prem_http 2.05, prem_wss 1.99, baseline 1.97 — all within quantization); the beacon path is clearly worse (p50 2.43 s).

## Consensus-layer vs execution-layer sight (the key question)

Per block seen by both the consensus head-poll and an execution source — delta `(exec − beacon)` ms, **positive = consensus (beacon) revealed it first** (this delta is quantization-free — same block, timestamp cancels):

| execution source vs beacon | blocks | beacon first | exec first | median Δ (ms) | p90 Δ (ms) |
|---|--:|--:|--:|--:|--:|
| prem_wss | 122 | 49 | 73 | -18.8 | 153.1 |
| prem_http | 123 | 49 | 74 | -26.1 | 366.6 |
| baseline_wss | 121 | 56 | 65 | -12.8 | 119.2 |

**No — consensus sight does NOT beat execution sight here.** vs premium exec-WSS, beacon fired first on only 49/122 blocks (execution first on 73), median **-18.8 ms** (execution ahead). And the consensus path is worse on every other axis: p50 gap 2.43 s (vs ~2.0 s execution) and **25 missed blocks** (below) vs 0–1 for execution. The head-poll + slot→block mapping does not buy earlier sight — it costs latency and completeness. This is the one that *could* have broken the 2 s floor; it did not.

## Premium execution vs baseline (same WSS transport)
- Δ `(baseline − prem_wss)` ms, >0 = premium first: median **13.1 ms**, p90 86.1 ms (n=146). Premium WSS edges the baseline by ~13 ms median — real but far inside the ~2 s arrival-gap floor, so not decision-changing.

## Reliability & reconnect

- **beacon missed 25 blocks in bursts** (e.g. [25495290, 25495291, 25495303, 25495304, 25495305, 25495306]… — runs of 3–5 consecutive blocks), i.e. the consensus head-poll / slot-mapping stalls for ~40–60 s at a time then recovers. Execution sources missed 0–1. This alone disqualifies the beacon path for reliable block sight.
- **Deliberate reconnect — poll sources (clean):** prem_http recovered in 2.50 s, beacon 3.25 s; 0 blocks missed during either outage (a poll session-reset is sub-slot).
- **Deliberate reconnect — WSS sources (pre-empted):** the scheduled prem_wss (10 min) and baseline_wss (15 min) kills did not register as deliberate events — **the provider recycles WSS connections on its own before then**, and the supervisor re-established silently. Both WSS sources still delivered the most blocks (147–148, 0–1 missed), so recovery was seamless; but the *measured* deliberate-reconnect number is only clean for the two poll sources. The provider-driven WSS cycling is itself the reliability note here.

## Provider notes
- **Rate limits (429): 0** across all four sources — two 50 ms poll loops = ~40 req/s basic-auth sustained for 30 min with no throttling.
- Transient errors: prem_http 1, beacon 1 (single one-off exceptions, self-recovered); prem_wss/baseline 0.
- Timestamps back-filled for 0 block(s).

## Latency floor & verdict

**Latency floor ≈ 2.0 s p50** (execution sources 1.97–2.05 s; means 2.23–2.33 s). p99 ≈ 5.1 s.

- **Did any premium endpoint break below 2 s?** **No.** The p50 spread across execution sources (1.97–2.05 s) is smaller than the whole-second timestamp quantization, so it is not a real difference — premium execution sits in the *same* ~2 s band as atom-1's 2.04 s baseline. Premium credentials bought **reliability/rate-limit headroom, not a lower arrival floor**.
- **Did consensus-layer sight beat execution-layer sight?** **No** — beacon was slower (median ~19 ms behind exec-WSS), higher-p50 (2.43 s), and lossy (25 burst-missed blocks).

**Per-endpoint verdict** (HOT-path same-block backrun needs p50 gap well under ~2 s):
- **prem_http** — p50 2.05 s, first-fire 71 → **marginal (best-available, still ~2 s)**.
- **prem_wss** — p50 1.99 s, first-fire 38 → **marginal (best-available, still ~2 s)**.
- **beacon** — p50 2.43 s, first-fire 25 → **NOT HOT-path** — lossy + slowest.
- **baseline_wss** — p50 1.97 s, first-fire 14 → **marginal (best-available, still ~2 s)**.

**Bottom line:** the ~2 s arrival gap is a **provider/propagation floor that premium access does not remove** — execution HTTP, execution WSS, consensus, and the baseline all land in the same ~2 s band, and the consensus layer (the one that could have beaten it) is slower and lossier. Same infrastructure conclusion as atom-1: for same-block backrunning a co-located node / direct peer is required; these hosted endpoints are for observation, not the HOT path. If forced to pick one here, **premium exec HTTP poll** wins the first-fire race (71/148) at no reliability cost.

*Atom 1b complete. Stop — do not proceed to atom 2.*
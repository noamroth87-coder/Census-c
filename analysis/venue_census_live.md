# Live Venue Census — structural (no pricing)

What a swap-cycle watcher must decode to *see* atomic-arb activity on Ethereum mainnet, ranked by
where that activity happens. Built fresh from live blocks — **no shadow/prior data used.** All
counts [M]; every % has its count beside it; UNKNOWN is counted, never guessed.

## Method & limitations (read first)

- **Arb-shaped, by log structure only — NOT priced, NOT true arb detection.** A tx is flagged
  arb-shaped if it emits **≥2 Swap events among {V2, V3, V4}** (matched by event signature) AND
  forms a cycle: (i) one non-pool address is an actor in ≥2 of the swaps (the same contract
  trades across them) AND (ii) the V2/V3 pools' token graph closes a loop (union-find: an edge
  joins two already-connected tokens ⇒ flow returns toward its start). This over- and
  under-counts by design; it ranks *where swap-cycle activity is*, it does not value it.
- **V4 caveat (large):** V4 swaps emit from the singleton PoolManager and carry only a `poolId`,
  not cheaply-resolvable tokens, so the token-cycle test cannot run on them. A tx containing V4
  is confirmed by trader-continuity alone (`v4_inferred`). **447 of 503 arb-shaped txs (88.9%)
  are `v4_inferred`; only 56 (11.1%) are `strict` (token-cycle proven, V2/V3-only).** So the
  cycle is *proven* for 11%; the 89% V4 set is arb-*shaped* but its return-to-start is unverified
  — it may include V4-routed non-arb flow.
- **Under-count:** detection requires ≥2 *Uniswap-family* swaps, so arbs made purely of
  Curve/Balancer/other legs are invisible; AMMs whose Swap signature is not in the fetched set
  (Maverick, Dodo, novel forks) are invisible entirely. Curve/Balancer appear here only as legs
  of V2/V3/V4 arbs.
- **Activity-weighted, not gross-weighted.** A low-frequency venue can still hold outsized
  profit; this census counts tx touches, not dollars. (The priced census found V4 ≈ 64–82% of
  *gross*; here V4 is 88.9% of arb-shaped *tx count* — same order, different unit.)
- **Single recent sample, ~18 min of chain** (91 blocks) — a snapshot, not the eternal
  distribution. A protocol quiet in this window could dominate in others.

## Sample & budget [M]

- Blocks **25,495,478 – 25,495,568** (91 scanned, stepped back from head 25,495,573), ~18 min.
- Stopped at the **500-arb-shaped target** (503 flagged) before the 1,000-block cap.
- Candidates (≥2 V2/V3/V4 swaps): **702**; arb-shaped: **503** (71.7% of candidates).
- **RPC calls: 774 of 15,000 cap** — 92 `eth_getLogs` (one per block + one range query for the
  V4 pool count) + ~395 `token0/token1` (cycle test) + **287 `factory()`** (fork labels, cap 300).
  One `getLogs` per block over all Swap topics, grouped by tx, as specified.

## Task 1 — Protocol / factory breakdown [M]

By event signature (free): V2, V3, V4, Curve (`TokenExchange` ×2), Balancer. Forks within V2/V3
split by `factory()` on every V2/V3 pool seen (287 calls, all pools labeled — none deferred):

| signature | fork labels (pools sampled) |
|---|---|
| **V2** (116 pools) | Uniswap V2 **73**, SushiSwap V2 **19**, PancakeSwap V2 2, ShibaSwap 1, **UNKNOWN-fork 21** |
| **V3** (171 pools) | Uniswap V3 **151**, SushiSwap V3 **11**, **UNKNOWN-fork 9** |
| **V4** | Uniswap V4 (singleton PoolManager) — **328 distinct poolIds** in range |
| Curve | 22 pools (everything-else) |
| Balancer | 1 pool (everything-else) |

**UNKNOWN-fork = 30 pools (21 V2 + 9 V3)** whose `factory()` is not a recognized address —
counted, not guessed. Note: they are still V2/V3 *by signature*, so a V2/V3 event decoder reads
them with the same ABI — UNKNOWN-fork does **not** threaten watcher completeness (see Task 4).

## Task 2 — Coverage table (the deliverable) [M]

Ranked by share of the 503 arb-shaped txs. "Distinct pools": V2/V3/Curve/Balancer counted within
arb-shaped txs; **V4 = 328 poolIds range-wide** (per-arb poolId subset not retained — stated).

| protocol | % of arb-shaped txs (count) | distinct pools | pure | mixed |
|---|--:|--:|--:|--:|
| **Uniswap V4** | **88.9% (447)** | 328 poolIds | 140 (31%) | 307 (69%) |
| **Uniswap V3** | **62.2% (313)** | 171 | 25 (8%) | 288 (92%) |
| **Uniswap V2** | **21.3% (107)** | 116 | 6 (6%) | 101 (94%) |
| Curve | 8.7% (44) | 22 | 0 (0%) | 44 (100%) |
| Balancer | 2.4% (12) | 1 | 0 (0%) | 12 (100%) |

**Cumulative tx-coverage (the load-bearing column) — the watcher's decode-priority list:**

| decode… | arb-shaped txs seen | coverage |
|---|--:|--:|
| **V4 alone** | 447 | **88.9%** |
| **+ V3** | 497 | **98.8%** |
| **+ V2** | 503 | **100.0%** |
| + Curve / + Balancer | 503 | **+0.0%** (always co-occur with V2/V3/V4 — already detected) |

## Task 3 — Mixed-arb dependency [M]

"Pure" = the arb touches only that protocol (reachable by decoding it alone); "mixed" = it spans
protocols. The share that is **pure** is what a protocol uniquely unlocks; the **mixed** share is
detected via *any* of its legs, so decoding one partner already surfaces the arb.

- **V4 — must-have.** 140 arbs (27.8% of all 503) are **V4-only** — invisible without a V4
  decoder. Another 307 V4 arbs are mixed. Decoding V4 alone sees **88.9%** of all arb-shaped txs.
- **V3 — must-have for the tail.** Only 25 arbs (5%) are V3-only, but V3 appears in 62.2%; its
  92%-mixed nature means most V3 arbs are *also* caught by their V4/V2 legs — yet the 56 non-V4
  arbs (the 11.1% `strict` set) are dominated by V3, so **V3 is what lifts coverage past 90%.**
- **V2 — incremental.** 6 arbs (1.2%) are V2-only; V2 is 94% mixed. Decoding V2 adds the final
  1.2% (497→503).
- **Curve / Balancer — zero standalone reach here.** 100% mixed, 0 pure: every Curve/Balancer
  touch rides on a V2/V3/V4 arb that is *already* detected. They add **0%** tx-coverage — a
  v2 decode for *completeness of legs*, never a must-have for *seeing the arb*.

**Must-have vs incremental:** V4 (unlocks 27.8% uniquely, 88.9% total) and V3 (carries the
non-V4 tail to ≥90%) are must-haves; V2 is a 1.2% incremental; Curve/Balancer are leg-completion
only.

## Task 4 — Watcher requirement [M]

**Minimum protocol set for ≥90% of arb-shaped tx coverage: Uniswap V4 + Uniswap V3 → 98.8%.**
V4 alone is 88.9% (just short of 90). The incremental tail: **+V2 → 100%** (the last 1.2%);
**Curve and Balancer add 0%** tx-coverage (always mixed with a decoded protocol) and are pure
leg-completion, safely deferrable to v2. Fork variants (Sushi, Pancake, Shiba, and the 30
UNKNOWN-fork pools) need **no extra decoder** — they share the V2/V3 Swap ABI.

**UNKNOWN worth investigating before the watcher is called complete:** not the fork-UNKNOWN
(same ABI, already decoded), but two structural blind spots — (1) the **88.9% `v4_inferred`
share**, whose cycle is unproven because V4 tokens are opaque: before trusting V4's dominance,
resolve V4 `poolId → currencies` (via the PoolManager `Initialize` events) so V4 arbs get the
same token-cycle test as V2/V3; (2) **AMMs whose Swap signature is not in the fetched set**
(Maverick, Dodo, etc.) — a one-off scan of unrecognized swap-like topics in the range would
size that gap. Everything else the watcher needs is V4 + V3 (+V2 for the last 1.2%).

---

*Structural heuristic, single ~18-min live sample; counts [M], UNKNOWN counted not guessed,
774/15,000 calls used (factory 287/300). Venue shares are a sample of these blocks, not the
eternal distribution. venue_census_live.md — analysis only; nothing else started.*

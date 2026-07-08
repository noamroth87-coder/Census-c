# Dossier — bot contract `0xbdb3ba9ffe…` (census cluster "0x46700", the statistical bidder)

## Profile header

- **Executor contract:** `0xbdb3ba9ffe392549e1f8658dd2630c141fdf47b6` — 11,703 bytes runtime. Deployed block 24,620,633 (2026-03-09 14:51 UTC) by deployer `0x00ff842be7e390605e7e3664ebfa0e432806500d`. Verified source: **UNKNOWN via RPC** (bytecode only; would need an explorer).
- **Census cluster (2 EOAs):** `0x5b43453fce…` (1,532 census arbs) and `0x4670008ed091…` (14 census arbs) — both call the contract as `tx.to`; that shared-executor co-call is the clustering evidence (union-find on beneficiary↔tx.from).
- **DISCOVERY [M]:** the contract is **not exclusive to that 2-EOA cluster**. In an 800-tx structural sample it is driven by **30 distinct operator EOAs** (top: `0x5b43453f…`×285, `0x497a169e…`×128, `0x6a5ac574…`×68, `0x5d1783dd…`×53, `0x5e2a3daa…`×52). The census cluster is **one small limb** of a larger operation sharing one custom executor — the single deployer `0x00ff842be7…` for a contract fronted by 30+ EOAs points to one entity (or a shared bot-as-a-service), but common ownership is **[E], not proven** on-chain.

## Task 1 — 14-day window & scope (the main enumeration)

- **14-day window [M]:** blocks 25,388,229–25,489,029. Via `eth_getLogs` (transfers to/from the contract) the executor moved tokens in **81,964 txs** (~5,854/day).
- **Budget-forced scope (as the task allows).** Correct per-tx gross requires the full trace+price pipeline (this bot unwraps WETH and leaves multi-token dust, so a cheap log-delta gross is wrong by ~1000×). Full-pricing 82k txs vastly exceeds the 5,000-call cap. So the enumeration splits three ways, each labelled: (a) **confirmed 2-EOA limb — 7 days, FULLY measured** from the census (1,546 landed arbs, per-tx gross/gas/priority/net/tx-index); (b) **contract entity — 14-day activity timeline** from getLogs (counts/timing only, complete); (c) an **800-tx structural sample** (receipt+header) for EOA/venue/complexity/bid/tx-index. Per-tx P&L for the full 14-day contract population is **UNMEASURED within budget** — stated, not estimated.

- **Sample composition [M]:** of 800 contract txs, 224 arb-shaped (28%), 450 route/user-like, 126 non-DEX. So the executor is a **general MEV/execution contract**, not a pure arb bot — only ~28% of its txs are arb-shaped.

## Task 2 — P&L profile (confirmed 2-EOA limb, 7-day census) [M]

| Metric | Value |
|---|--:|
| Landed arbs (7d) | 1,546 [M] |
| Reverted attempts by limb (census, `to`=contract) | ~3 [M] → visible win rate ≈ 99.8% (attempt floor) |
| Total gross | 35.015 ETH ($61,576) |
| Costs: gas | 18.344 ETH (of which priority-fee bid 17.997 ETH) |
| Costs: builder coinbase | 0.0000 ETH |
| **Window net** | **16.672 ETH** ($29,318) |
| Net per day | 2.382 ETH/day ($4,188/day) |
| Net per arb — median / p75 | $1.55 / $15.06 |
| % arbs individually net ≤ $0 | 37% |

**Day-by-day net [M]** (steady grind vs spiky):

| Day (UTC) | net ETH | net $ |
|---|--:|--:|
| 07-01 | 0.791 | 1,392 |
| 07-02 | 3.878 | 6,820 |
| 07-03 | 2.578 | 4,533 |
| 07-04 | 1.224 | 2,152 |
| 07-05 | 1.835 | 3,227 |
| 07-06 | 4.359 | 7,665 |
| 07-07 | 0.831 | 1,462 |
| 07-08 | 1.175 | 2,066 |

- Variance read [E]: daily net ranges 0.791–4.359 ETH; mean 2.084, stdev 1.299. **Steady grind** — no single day dominates. [E]

## Task 3 — Operating rhythm [M]

Hour-of-day (UTC) activity — contract-level attempts (getLogs, 14d) vs limb lands (census, 7d):

| Hour | Contract txs (14d) | Limb lands (7d) |
|--:|--:|--:|
| 00 | 3,405 | 58 |
| 01 | 3,137 | 71 |
| 02 | 3,264 | 52 |
| 03 | 3,029 | 34 |
| 04 | 2,877 | 44 |
| 05 | 3,095 | 40 |
| 06 | 3,140 | 68 |
| 07 | 3,158 | 59 |
| 08 | 3,270 | 64 |
| 09 | 3,100 | 83 |
| 10 | 3,503 | 68 |
| 11 | 3,649 | 75 |
| 12 | 4,138 | 57 |
| 13 | 4,538 | 77 |
| 14 | 4,258 | 83 |
| 15 | 3,829 | 80 |
| 16 | 3,633 | 68 |
| 17 | 3,365 | 74 |
| 18 | 3,258 | 56 |
| 19 | 3,293 | 59 |
| 20 | 3,237 | 68 |
| 21 | 3,281 | 80 |
| 22 | 3,175 | 62 |
| 23 | 3,332 | 66 |

- Dead/quiet hour ≈ 04:00 UTC (lowest contract activity) — possible maintenance/ops timezone signal [E].

Day-of-week (contract, 14d): Mon 11,557, Tue 9,902, Wed 12,146, Thu 13,136, Fri 12,898, Sat 10,375, Sun 11,950

- **tx-index in block [M]:** the 2-EOA **limb lands at block-TOP** — median idx 1 (p25 0, p75 12), **55% at idx 0-1** — but its builder coinbase is ≈0 (0.0000 ETH total, 100% priority-fee). So it buys top-of-block with **raw priority-fee bids, not a builder relationship** (the broader contract sample sits mid-block, median idx 21). **No builder moat:** outbiddable on priority fee, and beatable by any searcher running coinbase-transfer bundles that builders order above priority-fee txs [M].**

## Task 4 — Strategy fingerprint [M, sample]

- **(1) Venues [M]:** of 800 sampled txs, 517 touch Uniswap-V2/V3 pools, 343 touch Uniswap-V4 (singleton), 192 touch **both in one tx** — it arbs across the V2/V3↔V4 boundary, a sophisticated capability. (Curve/Balancer not separately counted; the census venue universe is dominated by Uni V2/V3/V4 so blind spots there are minor.)
- **(2) Path complexity [M]:** swap-hops per tx range 1–73; median 1, p75 4. Long tails (20–73 hops) show multi-pool cyclic paths, not simple 2-hop loops — **no complexity ceiling** evident.
- **(3) Bid behaviour [M]:** priority-fee bid median 0.000597 ETH, p25 0.000123, p75 0.002226. From the census limb, priority-fee % of gross has a wide spread (the statistical-bidder signature: it lets 37% of lands run individually negative). Whether the formula is flat-gwei / flat-% / size-scaled is **[E] not resolvable from this sample** — needs per-tx gross paired with bid, which the budget did not allow at scale.
- **(4) Contract [M]:** 11,703 bytes (mid-sized; not a minimal hand-tuned assembly bot, not bloated). Deployed 2026-03-09, ~106 days before the window opened. Source verification and gas-per-hop-vs-baseline require an explorer / disassembly — **out of RPC scope, [E] deferred**.

## Task 5 — Flaws (mechanical, each with evidence) [M unless marked]

| Flaw | Evidence | Exploitability |
|---|---|---|
| Dead hour | lowest contract activity ≈ 04:00 UTC (Task 3) | [E] reduced competition/response in that window |
| No builder moat | block-top (idx median 1) bought via priority fee only; builder coinbase ≈0 (0.0000 ETH) (Task 3) | a coinbase-transfer bundle is ordered above priority-fee txs → beats it for the same slot regardless of its tip |
| Loss-tolerance boundary | 37% of limb lands are net≤$0; it lands rather than reverts (≈3 reverts) | it will overpay to land — an ε-higher bid flips its marginal wins to losses; bleed it on contested small arbs |
| Bid predictability | statistical bidder tolerates negative lands (Task 2); exact formula [E] unresolved | IF formula is flat-% or flat-gwei [E], it is outbiddable by exactly ε |
| Complexity/venue breadth = attack surface | trades V2/V3+V4, up to 73 hops (Task 4) | not a blind spot but a large surface; long paths cost more gas, thinning margin on small arbs |
| Gas headroom | contract 11,703B, long multi-hop paths | [E] per-hop gas vs an optimal router not measured (needs disassembly) |

## Standing unmeasurables (closing)

The load-bearing caveat here is **not** hypothetical: this cluster is demonstrably **one limb of something bigger** — ≥30 operator EOAs drive the same executor, and the 2-EOA census view captures a small slice of a ~5,854-tx/day machine. Same-entity common ownership across those EOAs is inferred [E], not proven. Also unmeasured within budget: full 14-day per-tx P&L for the contract population; off-chain revenue and cross-address netting; whether any operator also builds blocks (block-level integrated profit). Numbers here are the measured 2-EOA limb (7d, full) + contract-level activity/structure (14d, counts/sample). Every per-tx-P&L statement is scoped to the limb; contract-entity P&L is explicitly not claimed.

*Dossier complete. Budget ≈4.7k/5k calls. Scratch file — not the census.*
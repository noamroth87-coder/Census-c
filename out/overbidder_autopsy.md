# Overbidder autopsy — rational whales or dumb money?

> Stored data only, zero RPC. Population = clusters that won a collision (contest-intensity probe) with total bid >64% of gross, plus the repeat-rivalry winner `0x4670008ed0…`. Window P&L (Tasks 1 & 5) is the load-bearing analysis; bid-geometry (Task 3) is supporting color. All [M].

Overbidder population (5 winner clusters): `0x1722261741…`, `0x37bdcf54cb…`, `0x4670008ed0…`, `0x7d344a2d90…`, `0xace0000086…`

## Task 1 — Window-level P&L per overbidder (whole census measured set) [M]

| Cluster (operator EOA) | Arbs landed | Gross ETH | Costs ETH (gas+builder) | of which priority | **Window net ETH [M]** | net $ | % arbs net≤0 | Reverted attempts | est revert-gas ETH [E] | **adj net incl. reverts [E]** |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `0x17222617419e…` | 1,020 | 0.4522 | 0.4176 | 0.0000 | **0.0346** | 61 | 4% | 0 | 0.0000 | **0.0346** |
| `0x37bdcf54cb1f…` | 2,952 | 2.4290 | 1.9507 | 0.0006 | **0.4783** | 843 | 0% | 0 | 0.0000 | **0.4783** |
| `0x4670008ed091…` | 1,546 | 35.0152 | 18.3437 | 17.9971 | **16.6715** | 29,318 | 37% | 3 | 0.0002 | **16.6713** |
| `0x7d344a2d90ef…` | 8,485 | 5.5107 | 4.6100 | 3.3310 | **0.9007** | 1,581 | 2% | 3 | 0.0002 | **0.9005** |
| `0xace0000086ad…` | 349 | 1.7940 | 1.4904 | 0.0000 | **0.3035** | 533 | 0% | 0 | 0.0000 | **0.3035** |

*Window net [M] = gross − gas − builder (priority fee is inside gas). **Reverted attempts are NOT in the measured set** — the census stored only reverted txs' `to`, not their gas — so their gas burn is ESTIMATED [E] as (revert count × median successful-arb gas 0.00006 ETH ≈ $0.109). Reverts likely halt early and use less gas, so this est is an UPPER bound. 'adj net' = window net − est revert-gas: it is the load-bearing number for rational-vs-burner, and it is what flips small winners negative once they pay for their own failed races.*

## Task 2 — Integration cross-reference [M]

| Cluster | Builder-routing label (Follow-up 2) | Mempool-origin mix (pub/priv/undet) |
|---|---|---|
| `0x17222617419e…` | NOT-PROFILED | 0/100/0% |
| `0x37bdcf54cb1f…` | NOT-PROFILED | 0/100/0% |
| `0x4670008ed091…` | NOT-PROFILED | 100/0/0% |
| `0x7d344a2d90ef…` | NOT-PROFILED | 96/4/0% |
| `0xace0000086ad…` | NOT-PROFILED | 0/100/0% |

## Task 3 — Bid-pattern geometry [M, supporting]

**(1) High-bid lane concentration — INSUFFICIENT-DATA (pools not stored).** The census slim records do not retain per-arb pool sets, and the contest probe's pool data was not persisted, so the pool/lane fingerprint cannot be computed from stored data without a fetch (out of scope). Weak proxy below: each cluster's **profit-asset** concentration (top assets by arb count) — a coarse stand-in for 'lane', not a pool fingerprint.

| Cluster | Top profit-assets (arb count) [proxy] |
|---|---|
| `0x17222617419e…` | 0xc02aaa39:1013, native_eth:7 |
| `0x37bdcf54cb1f…` | 0xc02aaa39:2915, native_eth:37 |
| `0x4670008ed091…` | 0xa0b86991:720, 0xdac17f95:694, 0xc02aaa39:666 |
| `0x7d344a2d90ef…` | 0xc02aaa39:8217, native_eth:295, 0x6b175474:204 |
| `0xace0000086ad…` | 0xc02aaa39:214, 0xa0b86991:154, 0x6b175474:24 |

**(2) Bid escalation vs rival presence.** For each cluster, its collision events (distinct blocks) with bid% and rival (loser) count:

| Cluster | Collision events (block: bid% / #rivals) | Escalation read |
|---|---|---|
| `0x17222617419e…` | 25476501: 75%/1r | INSUFFICIENT-N (n=1 events) |
| `0x37bdcf54cb1f…` | 25472427: 65%/1r | INSUFFICIENT-N (n=1 events) |
| `0x4670008ed091…` | 25457708: 54%/5r; 25459615: 267%/3r | INSUFFICIENT-N (n=2 events) |
| `0x7d344a2d90ef…` | 25439989: 65%/1r | INSUFFICIENT-N (n=1 events) |
| `0xace0000086ad…` | 25465391: 95%/1r | INSUFFICIENT-N (n=1 events) |

## Task 4 — Classification table (mechanical, rule inputs shown) [M]

Rules: **RATIONAL-INTEGRATED** = net>0 AND routing∈{CONCENTRATED,INTEGRATED}; **RATIONAL-STATISTICAL** = net>0 AND routing=DISTRIBUTED; **DEFENDER-CANDIDATE** = net>0 AND high bids in ≤3 lanes; **BURNER** = net<0; **INSUFFICIENT-DATA** = a required field missing. Multiple labels allowed. Lane data is unavailable ⇒ DEFENDER-CANDIDATE cannot be evaluated.

| Cluster | window net ETH | routing | lane-data | adj net (incl. reverts) | Label(s) |
|---|--:|---|---|--:|---|
| `0x17222617419e…` | 0.0346 | NOT-PROFILED | unavailable | 0.0346 | INSUFFICIENT-DATA(routing not profiled; net>0 so not BURNER on landed set); DEFENDER-CANDIDATE→INSUFFICIENT-DATA(no lane data) |
| `0x37bdcf54cb1f…` | 0.4783 | NOT-PROFILED | unavailable | 0.4783 | INSUFFICIENT-DATA(routing not profiled; net>0 so not BURNER on landed set); DEFENDER-CANDIDATE→INSUFFICIENT-DATA(no lane data) |
| `0x4670008ed091…` | 16.6715 | NOT-PROFILED | unavailable | 16.6713 | INSUFFICIENT-DATA(routing not profiled; net>0 so not BURNER on landed set); DEFENDER-CANDIDATE→INSUFFICIENT-DATA(no lane data) |
| `0x7d344a2d90ef…` | 0.9007 | NOT-PROFILED | unavailable | 0.9005 | INSUFFICIENT-DATA(routing not profiled; net>0 so not BURNER on landed set); DEFENDER-CANDIDATE→INSUFFICIENT-DATA(no lane data) |
| `0xace0000086ad…` | 0.3035 | NOT-PROFILED | unavailable | 0.3035 | INSUFFICIENT-DATA(routing not profiled; net>0 so not BURNER on landed set); DEFENDER-CANDIDATE→INSUFFICIENT-DATA(no lane data) |

## Task 5 — Loser-side check (window P&L + burn rate) [M]

| Loser cluster | Landed arbs | Window net ETH [M] | net $ | % net≤0 | Reverted txs | est revert-gas ETH [E] | **adj net [E]** |
|---|--:|--:|--:|--:|--:|--:|--:|
| `0x0bc9936aa6e8…` | 26 | 0.0341 | 57 | 35% | 4,992 | 0.3086 | **-0.2745** |
| `0x53c2c71df6d1…` | 3 | -0.0000 | -0 | 33% | 6,240 | 0.3858 | **-0.3858** |
| `0x6d37fb5342be…` | 472 | 0.2532 | 445 | 15% | 2,116 | 0.1308 | **0.1224** |
| `0xf00eabc409c5…` | 1 | 0.0140 | 22 | 0% | 782 | 0.0483 | **-0.0343** |

Losers whose bot `to` is NOT in any census winner cluster (never landed a measured arb — pure-reverter candidates), with reverted-tx counts:

| loser bot (to) | reverted txs in window |
|---|--:|
| `0x5597278e3b…` | 1,480 |
| `0x278d858f05…` | 31,392 |
| `0x0f54099d78…` | 29 |

**Dumb-money graveyard candidates** (net-negative once estimated revert-gas is included):

- `0x0bc9936aa6e8…`: 26 landed arbs, window net 0.0341 ETH, 4,992 reverted attempts → **adj net -0.2745 ETH [E]** — burning capital on failed races, within measurement bounds.
- `0x53c2c71df6d1…`: 3 landed arbs, window net -0.0000 ETH, 6,240 reverted attempts → **adj net -0.3858 ETH [E]** — burning capital on failed races, within measurement bounds.
- `0xf00eabc409c5…`: 1 landed arbs, window net 0.0140 ETH, 782 reverted attempts → **adj net -0.0343 ETH [E]** — burning capital on failed races, within measurement bounds.

> Note: `0x0bc9936…` (the repeat-rivalry loser) is window-net-**positive** on landed arbs but its thousands of reverts make its revert-gas-adjusted net the deciding figure — see the table. The starkest burn signal is the non-census pure-reverter `0x278d858f…` with 31,392 reverted txs and zero measured landings: a spray-and-revert bot whose entire on-chain footprint is failed attempts.

## Standing unmeasurables (closing) [stated]

Every P&L here is **within per-tx on-chain measurement bounds**. NOT captured: off-chain revenue (CEX/OTC legs, payment-for-order-flow, rebates); cross-address same-entity P&L (a cluster's true owner may run other unlinked addresses that net against these); and **block-level integrated profit** — if an operator also builds blocks, its searcher 'loss' can be recouped as builder revenue invisible to per-tx accounting. **Revert-gas is ESTIMATED [E], not measured** — the census kept only reverted txs' `to`, not their gas — so the 'adj net' column uses a median-gas proxy (likely an over-estimate since reverts halt early); the true figure sits between window net [M] and adj net [E]. So a **BURNER** label means 'net-negative on the arbs+reverts we can attribute on-chain', not 'unprofitable entity'. Bid-geometry lane fingerprints are unavailable (pools not stored) and the collision sample is 17 events, so bid-pattern reads are INSUFFICIENT-N. The load-bearing result is the window-level P&L (Tasks 1 & 5), read with the revert-gas caveat.

*Autopsy complete. Zero RPC calls. Scratch file — not the census.*
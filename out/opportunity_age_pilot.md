# Opportunity-age pilot — how fast is fast enough

> **PILOT / SAMPLE-SIZE CAVEAT [prominent].** This is a **live 10-minute reading (~50 blocks)**, not the distribution. Counts are tiny; treat every number as a directional pilot, not a population estimate. Scratch analysis — NOT part of the census.

Live window: blocks 25488681–25488730 (50 blocks processed [M]). Detected arbs ≥$10 gross: **10** [M]. RPC calls used: **1422** (cap 2,000).

**Age definition [M].** AGE-0 = opportunity created in the capture block itself (an earlier tx in the same block swaps in ≥1 of the arb's own pools — a same-block backrun; robustly detected). AGE-N = the arb's cyclic trade was already profitable above gas N blocks earlier, found by re-reading the same pools' spot state backward (marginal spot-price product, net of fees, vs the captured gas; depth cap 10 ⇒ 10+). **UNTRACEABLE** = age couldn't be determined: the cycle couldn't be reconstructed for backward pricing (V4 singleton flash-accounting / non-cyclic / Curve-Balancer routing) or creation was pending-flow not visible on-chain. **Method limit, stated:** this chain's arbs are V4-heavy and only a minority form cleanly-reconstructable cycles, so exact AGE-N (N≥1) is measurable for few arbs; the AGE-0 vs not-AGE-0 signal is the robust one.

## 1. Age distribution [M]

| Scope | Arbs | AGE-0 | AGE-1 | AGE-2+ | UNTRACEABLE |
|---|--:|--:|--:|--:|--:|
| ≥$10 | 10 | 3 (30%) | 0 | 0 | 7 (70%) |
| ≥$100 | 2 | 0 (0%) | 0 | 0 | 2 (100%) |
| ≥$1k | 0 | 0 (0%) | 0 | 0 | 0 (0%) |

## 2. AGE-1+ arbs — exposed profit & exposure seconds [M]

**No AGE-1+ arbs measured in this pilot window.** (Either opportunities were captured in their creation block, or the older ones fell into UNTRACEABLE because their V4/complex cycle couldn't be re-priced backward. Listed, not dropped.)

## 3. Per-arb table (all detected ≥$10) [M]

| block | gross $ | age class | pools | tx |
|--:|--:|---|--:|---|
| 25488683 | 58 | UNTRACEABLE | 2 | `0xeff02a9101…` |
| 25488690 | 23 | UNTRACEABLE | 6 | `0x77264fd911…` |
| 25488706 | 13 | UNTRACEABLE | 7 | `0xfd23bd7fe9…` |
| 25488707 | 650 | UNTRACEABLE | 1 | `0xafeb460483…` |
| 25488707 | 521 | UNTRACEABLE | 4 | `0x792bb149fb…` |
| 25488713 | 43 | AGE-0 | 1 | `0x2187bbcf93…` |
| 25488720 | 12 | UNTRACEABLE | 9 | `0x1a802b1308…` |
| 25488721 | 15 | UNTRACEABLE | 3 | `0x10b715ff79…` |
| 25488723 | 18 | AGE-0 | 4 | `0x30505a44a7…` |
| 25488724 | 10 | AGE-0 | 5 | `0xa79c7b4139…` |

## 4. Coverage & untraceable list [M]

- Blocks processed: **50** [M]. Arbs ≥$10 seen: **10** [M]. Backtraced to an age: **3**. UNTRACEABLE: **7** (70%).

Untraceable arbs (seen, not dropped) — reason:

| tx | block | gross $ | reason |
|---|--:|--:|---|
| `0xeff02a9101d3…` | 25488683 | 58 | noncyclic_or_v4_route |
| `0x77264fd91128…` | 25488690 | 23 | unreadable_or_novel_pool |
| `0xfd23bd7fe9c0…` | 25488706 | 13 | noncyclic_or_v4_route |
| `0xafeb46048363…` | 25488707 | 650 | noncyclic_or_v4_route |
| `0x792bb149fb22…` | 25488707 | 521 | unreadable_or_novel_pool |
| `0x1a802b130804…` | 25488720 | 12 | noncyclic_or_v4_route |
| `0x10b715ff796c…` | 25488721 | 15 | noncyclic_or_v4_route |

*Pilot complete. Scratch file — not the census.*
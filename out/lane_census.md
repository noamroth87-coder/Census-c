# Lane census — densifying the hunting map's top rows

Full re-measurement of the top-40 negative-space + top-10 thin-edge venues from the coverage map, replacing its ×35 noisy sample with **real per-lane arb data**. All [M] unless marked.

## Method & the 14-day budget cut [M]

- **Window: the full 7-day census window** (blocks 25,437,594–25,487,778), **complete not sampled** — 2,972 real arbs across the 50 lanes via census reuse (lane swap-logs ∩ census arbs; zero-fetch). This is the densification: e.g. the top lanes carry hundreds–thousands of arbs, not the coverage map's `5/day` from one sampled arb.
- **14-day extension: BUDGET-CUT (stated).** The non-census 7-day gap is 27,620 swap-txs (mostly non-arb); filtering it for arbs would need >27k receipts, far over the 12,000 cap, and a strict rank-order 14-day pass is exhausted by a single mega-lane at rank 21. So per the cut rule I report the **full 7-day census window for ALL 50 lanes** rather than a ragged 20-lane 14-day cut — more complete, uniformly comparable. 14-day figures ≈ 2× flow where regime-stable [E].
- **Fetches used:** 2,864 of 12,000 (getLogs lane swaps + one receipt per reuse arb for sight-class). Regime & flow from stored census + blockstats (free).
- **Regime line:** base fee **0.227 gwei** (90-day median from the volatility scan); ≤ = calm, > = volatile. 15.7% of census blocks are volatile.

## Task 5 — The final lane table (sorted by slot-value) [M; slot-value E]

slot-value [E] = arbs/day × median net × (1 − top-1 share) — a **comparator, not a forecast**.

| # | Venue | arbs (7d) | arbs/day | med net $ | p75 net $ | winners | top-1 % | incumbent | labels | BOOBY | regime | sight | slot-value [E] |
|--:|---|--:|--:|--:|--:|--:|--:|---|---|:--:|---|---|--:|
| 1 | `v2:0x2a6c340bcbb0a79d3deecd3bc5cbc2605ea9259f` | 181 | 25.9 | 59.95 | 232.95 | 28 | 70% | `0x1f2997c93a…` | NOT-PROFILED |  | ALL-WEATHER | MIXED(70%) | 471.1 |
| 2 | `v3:0xeb85a25bad302fb7d74c7e6a5421fa8358207a54` | 203 | 29.0 | 27.05 | 38.91 | 21 | 58% | `0x2761a03953…` | NOT-PROFILED |  | ALL-WEATHER | OPEN-SIGHT(86%) | 332.3 |
| 3 | `v3:0xebd2c61d1f40829368dee0185b420e2258955339` | 13 | 1.9 | 73.88 | 131.75 | 8 | 31% | `0x5f7f3e256a…` | NOT-PROFILED |  | ALL-WEATHER | OPEN-SIGHT(85%) | 95.0 |
| 4 | `v3:0x47d486c622db94ddcdc1b75ed08aecdfe92a7a7f` | 59 | 8.4 | 14.88 | 26.69 | 14 | 27% | `0x004b38217d…` | NOT-PROFILED; multi-lane×3 |  | ALL-WEATHER | GATED(8%) | 91.4 |
| 5 | `v3:0x3416cf6c708da44db2624d63ea0aaef7113527c6` | 1459 | 208.4 | 0.30 | 4.18 | 510 | 13% | `0xf204f3acb0…` | NOT-PROFILED |  | ALL-WEATHER | MIXED(60%) | 53.8 |
| 6 | `v3:0x0b599ebf4e05af48b56d38e2dde520570c366460` | 15 | 2.1 | 6.54 | 31.60 | 10 | 33% | `0x1b2e668df1…` | NOT-PROFILED |  | ALL-WEATHER | OPEN-SIGHT(93%) | 9.3 |
| 7 | `v2:0xab905aba2cf13128f1233f68800d85a275eddbcf` | 22 | 3.1 | 3.42 | 25.63 | 13 | 14% | `0xb158653c0a…` | NOT-PROFILED |  | ALL-WEATHER | OPEN-SIGHT(91%) | 9.3 |
| 8 | `v2:0x5b670a54cd8c4e6f03d5bbbedcbaa68c8b2ca2d9` | 28 | 4.0 | 2.20 | 6.78 | 14 | 25% | `0x4f9a5dd222…` | NOT-PROFILED |  | ALL-WEATHER | MIXED(64%) | 6.6 |
| 9 | `v3:0x09117bff68b5939319e61b226bf1f3f5f985eba1` | 50 | 7.1 | 1.10 | 28.91 | 15 | 28% | `0x6ced635bc4…` | NOT-PROFILED |  | ALL-WEATHER | MIXED(64%) | 5.7 |
| 10 | `v3:0x5c8096f161508c3030363b8c25249dad5b18657e` | 9 | 1.3 | 3.63 | 59.38 | 9 | 11% | `0x7d344a2d90…` | NOT-PROFILED; overbidder(RATIONAL); multi-lane×6 |  | ALL-WEATHER | GATED(11%) | 4.2 |
| 11 | `v3:0x48da0965ab2d2cbf1c17c09cfb5cbe67ad5b1406` | 268 | 38.3 | 0.10 | 12.79 | 103 | 10% | `0x7d344a2d90…` | NOT-PROFILED; overbidder(RATIONAL); multi-lane×6 |  | ALL-WEATHER | MIXED(40%) | 3.6 |
| 12 | `v3:0xbda5cfc64fdf65a45dd1f054ce41b6473c443ec2` | 6 | 0.9 | 4.09 | 20.75 | 4 | 50% | `0x574be01300…` | NOT-PROFILED |  | CALM-ONLY | OPEN-SIGHT(100%) | 1.8 |
| 13 | `v3:0x307c4d0a83931c3eebe501f8f0c0b4c249bcf206` | 45 | 6.4 | 0.30 | 0.60 | 17 | 47% | `0x790f117af8…` | NOT-PROFILED |  | ALL-WEATHER | GATED(16%) | 1.0 |
| 14 | `v2:0x6060ad7b2abb5716adc82c669353e5c5f3b9fb4d` | 10 | 1.4 | 0.97 | 14.52 | 7 | 30% | `0x882dd7a835…` | NOT-PROFILED; multi-lane×2 |  | ALL-WEATHER | OPEN-SIGHT(90%) | 1.0 |
| 15 | `v3:0x8ea7e79bfdab7100c87f97d2cf21a0b25c4ae0d6` | 34 | 4.9 | 0.15 | 4.92 | 21 | 12% | `0x6c97c77b5e…` | NOT-PROFILED |  | ALL-WEATHER | OPEN-SIGHT(100%) | 0.7 |
| 16 | `v2:0xa43b79be77e9dd4dc2998854350b60ae9627d8ee` | 7 | 1.0 | 0.75 | 5.63 | 6 | 29% | `0xa31922c36f…` | NOT-PROFILED |  | ALL-WEATHER | OPEN-SIGHT(100%) | 0.5 |
| 17 | `v3:0xe950877d5e89417e6083f6c973dbf4682eae8f2a` | 18 | 2.6 | 0.18 | 25.97 | 16 | 11% | `0x7d344a2d90…` | NOT-PROFILED; overbidder(RATIONAL); multi-lane×6 |  | ALL-WEATHER | MIXED(39%) | 0.4 |
| 18 | `v2:0x4798b81fb132b1ce2ae9a1f609c8be0bee8dfe4d` | 5 | 0.7 | 0.76 | 17.64 | 4 | 40% | `0x7d344a2d90…` | NOT-PROFILED; overbidder(RATIONAL); multi-lane×6 |  | CALM-ONLY | GATED(20%) | 0.3 |
| 19 | `v3:0xe76532bae172876b6c7170ce02309715502c360b` | 10 | 1.4 | 0.18 | 54.97 | 8 | 20% | `0xa7c8e413dc…` | NOT-PROFILED |  | ALL-WEATHER | MIXED(50%) | 0.2 |
| 20 | `v2:0xdadc9459c36b345e2e2007d2d2746f44a0b3b2df` | 36 | 5.1 | 0.03 | 3.75 | 15 | 17% | `0x979159f671…` | NOT-PROFILED; multi-lane×2 |  | CALM-ONLY | OPEN-SIGHT(78%) | 0.1 |
| 21 | `v2:0x69b39b89f9274a16e8a19b78e5eb47a4d91dac9e` | 66 | 9.4 | 0.02 | 0.36 | 21 | 17% | `0x37bdcf54cb…` | NOT-PROFILED; overbidder(RATIONAL) |  | ALL-WEATHER | OPEN-SIGHT(82%) | 0.1 |
| 22 | `v2:0x0f641efbeff4be14762a276d4d3744ce40526653` | 5 | 0.7 | 0.28 | 39.04 | 4 | 40% | `0x32eef6c0ab…` | NOT-PROFILED; multi-lane×2 |  | ALL-WEATHER | GATED(0%) | 0.1 |
| 23 | `v2:0xb28025242552ad02f17273111db6d513069d5809` | 9 | 1.3 | 0.09 | 2.93 | 8 | 22% | `0x7d344a2d90…` | NOT-PROFILED; overbidder(RATIONAL); multi-lane×6 |  | CALM-ONLY | OPEN-SIGHT(89%) | 0.1 |
| 24 | `v2:0xc2963865fc947be4de733dd30e1d55d435eddee5` | 11 | 1.6 | 0.05 | 0.41 | 8 | 18% | `0xfa7b153477…` | NOT-PROFILED |  | CALM-ONLY | OPEN-SIGHT(91%) | 0.1 |
| 25 | `v3:0x435664008f38b0650fbc1c9fc971d0a3bc2f1e47` | 23 | 3.3 | 0.01 | 0.69 | 16 | 17% | `0x0afa3a8770…` | NOT-PROFILED |  | ALL-WEATHER | MIXED(61%) | 0.0 |
| 26 | `v3:0x1e1dfff79d95725aaafd6b47af4fbc28d859ce28` | 152 | 21.7 | 0.00 | 0.20 | 46 | 30% | `0x7556699aa8…` | NOT-PROFILED |  | ALL-WEATHER | MIXED(49%) | 0.0 |
| 27 | `v3:0x8d5e3ac5355491facc86b8371d59918ad1b91fd0` | 63 | 9.0 | 0.00 | 0.01 | 19 | 24% | `0x7c1fb21f23…` | NOT-PROFILED |  | ALL-WEATHER | GATED(0%) | 0.0 |
| 28 | `v2:0xc1576448b8e9ad83abadf38dffd4000bf51ac2f0` | 34 | 4.9 | 0.00 | 0.02 | 10 | 44% | `0xae2fc48352…` | NOT-PROFILED; multi-lane×4 |  | ALL-WEATHER | OPEN-SIGHT(85%) | 0.0 |
| 29 | `v2:0x610d7053f4ca90d50ddee40d48a1fa2d32942c86` | 22 | 3.1 | 0.00 | 0.02 | 6 | 41% | `0xae2fc48352…` | NOT-PROFILED; multi-lane×4 |  | ALL-WEATHER | OPEN-SIGHT(77%) | 0.0 |
| 30 | `v2:0xa416df4d96cd547337a3e8893bf3f01c2a2af5c0` | 10 | 1.4 | 0.01 | 4.93 | 7 | 20% | `0x00000027f4…` | NOT-PROFILED |  | ALL-WEATHER | OPEN-SIGHT(90%) | 0.0 |
| 31 | `v3:0x738ea57616fa9dab407e9e7920d446eaf4e7eaaa` | 5 | 0.7 | 0.01 | 598.52 | 4 | 40% | `0x004b38217d…` | NOT-PROFILED; multi-lane×3 |  | CALM-ONLY | GATED(0%) | 0.0 |
| 32 | `v3:0xe744f5e2edfdcb9fdb43b288ecb8b21c8487e888` | 16 | 2.3 | 0.00 | 1.40 | 11 | 12% | `0x882dd7a835…` | NOT-PROFILED; multi-lane×2 |  | ALL-WEATHER | MIXED(69%) | 0.0 |
| 33 | `v2:0x682831244b0e97946abc52cb1893cce398de3a35` | 26 | 3.7 | 0.00 | 0.01 | 9 | 46% | `0xae2fc48352…` | NOT-PROFILED; multi-lane×4 |  | ALL-WEATHER | MIXED(69%) | 0.0 |
| 34 | `v2:0x679bc5a7473e28c35030ae31e540db603089021a` | 23 | 3.3 | 0.00 | 0.03 | 5 | 61% | `0xae2fc48352…` | NOT-PROFILED; multi-lane×4 |  | ALL-WEATHER | MIXED(70%) | 0.0 |
| 35 | `v2:0x4de126d4940bb9a183e9b692d7f7dd5abb2638c5` | 6 | 0.9 | 0.00 | 13.23 | 5 | 33% | `0x004b38217d…` | NOT-PROFILED; multi-lane×3 |  | CALM-ONLY | GATED(17%) | 0.0 |

**THIN-FLOW lanes (<5 arbs in 7d — raw events, not distributions):**

| Venue | kind | arbs (7d) | raw nets $ |
|---|---|--:|---|
| `v3:0x241fc1cdbf9f741933e5fa515c5b884da93b81b6` | neg | 3 | 583.57, 0.16, 0.03 |
| `v2:0x0846f55387ab118b4e59eee479f1a3e8ea4905ec` | neg | 3 | 583.57, 0.01, 67.52 |
| `v2:0x4de8c60541fdadd33404ccb2c8b83907ce617341` | neg | 1 | 121.46 |
| `v3:0x7261bb346ccc02911e4b07f933ccd69dc51ee3e1` | neg | 3 | 0.28, 47.09, 30.99 |
| `v3:0x826b34e62320108a9fa38a080360d693a8a73111` | neg | 2 | 0.12, 27.83 |
| `v3:0x88faa10c3115c168057a540d22d6991d7fa4b67c` | neg | 2 | 23.19, 0.01 |
| `v2:0x8bee0e6f0b163f929e16a351473ce47771ce9a67` | neg | 1 | 21.22 |
| `v2:0x480994d1c15b8ea73c5a1fd8230df921f7b4c8db` | neg | 3 | 0.34, 3.24, 20.50 |
| `v3:0xfc545f345e2afc52652cd6f76323c5ddc847bd6d` | thin | 1 | 3.02 |
| `v3:0xe41552e6212cb6f7faa381c7bc9434c58bf28ce1` | thin | 1 | 0.02 |
| `v3:0xa7bc6c09907fa2ded89f1c8d05374621cb1f88c5` | thin | 0 | (none) |
| `v3:0x8592064903ef23d34e4d5aaaed40abf6d96af186` | thin | 0 | (none) |
| `v3:0x813b1bce815c15774f85f8ff6b0dcbbb75a1d995` | thin | 0 | (none) |
| `v3:0x79a6683d82f25535ff3fd2753e03e0961060e882` | thin | 1 | 0.00 |
| `v3:0x66bb2ecf89c92a11044a46411d0c9e0bc9e31340` | thin | 2 | 0.28, 5.41 |

## Task 2 — Incumbent census highlights [M]

- **BOOBY-TRAP lanes (0):** incumbent is a CONCENTRATED-routing cluster or a >100%-of-gross bidder — contesting these provokes a defended P&L. none in the 50.
- **Multi-lane incumbents (7):** a cluster leading several lanes is a broader opponent than a single-lane one. `0x7d344a2d90…`×6, `0xae2fc48352…`×4, `0x004b38217d…`×3, `0xdf37c587f7…`×2, `0x882dd7a835…`×2, `0x32eef6c0ab…`×2

## Task 3 — Regime split [M]
- Regime mix across 35 measured lanes: ALL-WEATHER 28, CALM-ONLY 7. (Regime line 0.227 gwei; census window is 84% calm blocks so CALM-ONLY dominates — true-STORM per-lane persistence is bounded by the calm census window; see Spec 1 for aggregate storm behavior.)

## Task 4 — Sight-barrier classification [M]
- Sight mix: MIXED 12, OPEN-SIGHT 15, GATED 8 (share of each lane's arbs that are pure-V2/V3 = pilot-traceable; >70% OPEN-SIGHT, <30% GATED).
- **Anomaly check:** OPEN-SIGHT lanes with high margin (>\$50) and ≤2 winners should be swarmed by fast contests yet aren't — 0 such lanes. **Stated not smoothed:** either a hidden barrier the pilot heuristic can't see (private order-flow, or the pool is thin so few arbs exist), or a measurement gap. Per-lane reverted-tx contest is **invisible** (reverts emit no pool logs → not getLoggable), so contest intensity here can't be confirmed from revert-counting.

## Pre-registered entry thresholds (DRAFT — pending your confirmation)

Before any build targets a lane, confirm ALL of: **arbs/day ≥ 5**, **median net ≥ \$0.50**, **no BOOBY-TRAP flag**. These are DRAFT gates, not yet active.

- Lanes passing the DRAFT gates (4): `v2:0x2a6c340bcbb`, `v3:0xeb85a25bad3`, `v3:0x47d486c622d`, `v3:0x09117bff68b`.

## Unmeasurables (closing)

- **Entity coverage via unlinked executors:** the negative-space assumes absence = this executor's absence; the same operator via another contract/EOA is invisible.
- **Private-flow contests:** losing bundles dropped in builder simulation, and per-lane reverted attempts (no pool logs), are not counted — contest intensity is a lower bound.
- **14-day bound:** measured on the 7-day census window (full); the other 7 days and true-storm per-lane persistence are budget-cut.

*Lane census complete. Phase B closes. Scratch file — not the census.*
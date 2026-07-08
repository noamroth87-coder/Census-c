# Coverage Hole — Characterizing the Unmeasured 28.7%

Mission M1. The census assigned a measurement verdict to **123,391** detected atomic-arb
candidates over the 7-day window (blocks 25,437,594–25,487,778): **71.3% measured** as
priceable arbs, **16.4% unpriceable**, **12.4% failed-to-measure**. This file characterizes
the 28.7% (35,473 candidates) that the census never valued. All labels [M]=measured from
stored data, [E]=estimated.

The hole splits by **which leg is unmeasured**:

| population | n | share of hole | unmeasured leg | measurable leg |
|---|--:|--:|---|---|
| unpriceable | 20,234 | 57.0% | profit token (a GAIN) | cost side (WETH outlay) |
| failed_measure | 15,239 | 43.0% | a material OUTFLOW (cost) | revenue side (WETH inflow) |

The two are mirror images: unpriceable arbs hide the **upside**, failed arbs hide the **cost**.
Neither leaves a leg from which profit sign can be proven — see Task 4.

## Task 1 — Unpriceable population, ranked by arb count [M]

20,234 unpriceable arbs reference **2,410 distinct exotic
profit tokens** (24,421 token-legs). The distribution is long-tailed;
the top-20 tokens account for the counts below. `visible WETH-leg` = the cost-side WETH/
stable outlay the arb spent to acquire the exotic token (the profit itself is unvalued).

| rank | exotic profit token | arbs | median visible leg | Σ visible leg |
|--:|---|--:|--:|--:|
| 1 | `0x47883e389bb6be3650b0c0935b300b50a95fc072` | 3,310 | $0 | $0 |
| 2 | `0x19640000000ba88d36206beb10d0e86011c8d08c` | 1,325 | $13 | $138,425 |
| 3 | `0xaca92e438df0b2401ff60da7e4337b687a2435da` | 1,215 | $36 | $545,898 |
| 4 | `0x1223334444a7466fbf985b14e1f4edaf3883bca6` | 978 | $8 | $11,965 |
| 5 | `0x10dea67478c5f8c5e2d90e5e9b26dbe60c54d800` | 968 | $471 | $2,658,233 |
| 6 | `0x904567252d8f48555b7447c67dca23f0372e16be` | 873 | $2,949 | $19,262,054 |
| 7 | `0xc8fb80fcc03f699c70ff0cc08c09106288888888` | 481 | $89 | $840,952 |
| 8 | `0xe76c5b78f93909d34404e9eb4c1f19e7582a5de1` | 473 | $193 | $894,621 |
| 9 | `0x94314a14df63779c99c0764a30e0cd22fa78fc0e` | 427 | $96 | $2,175,059 |
| 10 | `0xde4ee8057785a7e8e800db58f9784845a5c2cbd6` | 354 | $3,373 | $13,529,445 |
| 11 | `0x230f1e241c621d5af670dad83ebcdd18971e2995` | 316 | $276 | $1,370,188 |
| 12 | `0xb30fe1cf884b48a22a50d22a9282004f2c5e9406` | 277 | $88 | $64,974 |
| 13 | `0xcedbea37c8872c4171259cdfd5255cb8923cf8e7` | 258 | $27 | $26,078 |
| 14 | `0x32708538a107253b51a735a724330a23106ca4ca` | 257 | $157 | $66,734 |
| 15 | `0x17205fab260a7a6383a81452ce6315a39370db97` | 254 | $2,449 | $6,284,143 |
| 16 | `0x4647e1fe715c9e23959022c2416c71867f5a6e80` | 244 | $265 | $529,805 |
| 17 | `0xdbdb4d16eda451d0503b854cf79d55697f90c8df` | 232 | $1,849 | $3,757,537 |
| 18 | `0x9ff7b37b84c05dfb08b4f50adb17a80a3fefd6ed` | 228 | $31 | $31,844 |
| 19 | `0x98a878b1cd98131b271883b390f68d2c90674665` | 222 | $3,968 | $1,342,902 |
| 20 | `0x12d9fe4c9494dc363c6290bfdbb2bd9ed6358c13` | 168 | $6 | $11,324 |

Top-20 tokens = 12,860 of 24,421 token-legs 
(53%). The #1 token alone (`0x47883e389bb6be3650b0c0935b300b50a95fc072`) 
appears in 3,310 unpriceable arbs — a single recurring exotic lane the
census could not value.

## Task 2 — Failed-to-measure, bucketed [M]

All 15,239 failed_measure records carry one of two stored reasons:

| stored reason | count |
|---|--:|
| unpriceable_outflow | 15,238 |
| implausible_valuation | 1 |

`unpriceable_outflow` dominates: the arb spent a token the pipeline could not price, so
gross is uncertain and the record is dropped rather than valued. Structural sub-buckets:

| dimension | breakdown |
|---|---|
| revenue leg | no_visible_leg: 1,201, revenue_leg_visible: 14,038 |
| n_swaps | 10+: 1,827, 2: 8,291, 3-4: 3,276, 5-9: 1,845 |
| has_flash | 28 of 15,239 |
| multi_asset | 3,076 of 15,239 |
| measurable value_eth sign | measurable_zero: 1,244, measurable_pos: 13,307, measurable_neg: 688 |

14,038 of 15,239 have a visible
revenue leg (we see WETH come in but not what it cost). The positive-`value_eth` majority is
**not** profit: it is revenue whose cost leg is exactly the unpriced outflow — see Task 4.

## Task 3 — Did a price route exist? (bounded fetch) [M]

For the top-10 unpriceable tokens, checked at each token's first-occurrence block whether
any WETH/USDC/USDT pool held **>$50k liquidity**. Budget: 300 of
2000 RPC calls. A census pool needed only ~0.3 WETH (~$500) depth, so a token that
shows no deep pool here was genuinely thin at the window; a token WITH a deep pool was
skipped for another reason (broken spot / non-standard pool / fee-on-transfer).

| exotic token | arbs | best liquidity | route | verdict |
|---|--:|--:|---|---|
| `0x47883e389bb6be3650b0c0935b300b50a95fc072` | 3,310 | $0 | none | GENUINELY-EXOTIC |
| `0x19640000000ba88d36206beb10d0e86011c8d08c` | 1,325 | $64 | v3:3000 vs WETH | GENUINELY-EXOTIC |
| `0xaca92e438df0b2401ff60da7e4337b687a2435da` | 1,215 | $0 | v3:100 vs WETH | GENUINELY-EXOTIC |
| `0x1223334444a7466fbf985b14e1f4edaf3883bca6` | 978 | $348 | v3:3000 vs WETH | GENUINELY-EXOTIC |
| `0x10dea67478c5f8c5e2d90e5e9b26dbe60c54d800` | 968 | $5 | v3:3000 vs WETH | GENUINELY-EXOTIC |
| `0x904567252d8f48555b7447c67dca23f0372e16be` | 873 | $0 | v3:10000 vs USDC | GENUINELY-EXOTIC |
| `0xc8fb80fcc03f699c70ff0cc08c09106288888888` | 481 | $0 | none | GENUINELY-EXOTIC |
| `0xe76c5b78f93909d34404e9eb4c1f19e7582a5de1` | 473 | $0 | none | GENUINELY-EXOTIC |
| `0x94314a14df63779c99c0764a30e0cd22fa78fc0e` | 427 | $0 | none | GENUINELY-EXOTIC |
| `0xde4ee8057785a7e8e800db58f9784845a5c2cbd6` | 354 | $150 | v2:None vs WETH | GENUINELY-EXOTIC |

**0 of 10** top tokens were PRICEABLE-IN-RETROSPECT — a deep route
existed but the census pipeline refused it (most likely the `SANE_ETH_PER_TOKEN` cap
tripping on a thin-spot or fee-on-transfer token). The remaining
10 are GENUINELY-EXOTIC: no >$50k route existed at the window.

## Task 4 — Profit mass in the hole [E]

**Formula (measurable-leg lower bound).** For each hole arb, `visible` = the largest sane
|priced beneficiary leg| in USD. Then:

- **unpriceable arbs:** the profit is entirely the unvalued gain token. Measured across all
  20,234 of them, the signed measurable position change `value_eth` is
  **≤ 0 in every single case** (Σ positive measurable value = $0). We can prove economic
  activity flowed, but **not one dollar of profit** is provable from measurable legs.
- **failed_measure arbs:** the visible leg is *revenue* with the cost hidden — it bounds
  revenue from above, giving no profit floor.

So the **provable measurable profit floor of the entire hole is $0.** What is measurable is
**throughput** — a floor on economic size passing through the hole:

| population | n | with visible leg | throughput floor (Σ visible) | measurable profit floor |
|---|--:|--:|--:|--:|
| unpriceable | 20,234 | 16,229 | $87,652,943 | $0 |
| failed_measure | 15,239 | 13,998 | $225,804,455 | $0 |
| **combined** | 35,473 | — | $313,457,398 | $0 |

_(throughput uses a $47M/leg sanity cap; failed_measure retains mispriced legs because
`has_unpriceable_loss` is tested before the pipeline's sane backstop.)_

**Dust, treasure, or mixed — by counts (visible-leg size):**

| visible-leg size | unpriceable | failed_measure | combined |
|---|--:|--:|--:|
| dust (<$1) | 4,734 | 1,555 | 6,289 |
| small ($1-50) | 6,513 | 4,660 | 11,173 |
| mid ($50-1k) | 6,026 | 5,001 | 11,027 |
| large (>$1k) | 2,961 | 4,023 | 6,984 |

**Mixed.** 17,462 hole arbs (49%) have a visible leg under $50 —
consistent with dust/spam. 6,984 (20%) have a visible leg
over $1,000 — real size moving through unmeasured lanes. The hole is neither pure dust nor
pure treasure: it is bimodal. No verdict is drawn on whether the large-leg arbs are
*profitable* — that is exactly the leg the census cannot see.

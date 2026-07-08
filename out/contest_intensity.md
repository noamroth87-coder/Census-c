# Contest-intensity probe — do incumbents actually fight?

> Scratch analysis (not the census). Measures how often two+ actors visibly compete for the same opportunity (a landed arb + a same-block reverted tx sharing a pool) and who wins. All [M].

## Task 1 — Collision inventory (stored data) [M]

| Metric | Count |
|---|--:|
| Total landed-reverted txs recorded in detection | 204,430 |
| Intended-pools identifiable from stored data | 0 |
| TARGET-UNKNOWN | 204,430 (100.0%) |
| Collisions identifiable from stored data | 0 |

The census retained only the **`to` address** of each reverted tx (no tx hash, calldata, or pre-revert logs — reverted txs emit none), and measured arbs were stored without their pool set. So intended pools cannot be recovered from stored data and the shared-pool join is uncomputable ⇒ **100% TARGET-UNKNOWN**, which exceeds the 50% trigger for the bounded fetch (Task 2).

*Supplementary stored-only signal (NOT a pool-confirmed collision):* 46,995 of 204,430 reverted txs (23.0%) have a `to` that is a known arb-bot address — i.e. failed arb attempts by identifiable searchers, a floor on contest activity but silent about which opportunity they targeted.

## Task 2 — Bounded fetch (TARGET-UNKNOWN > 50%) [M, sampled]

**Sample plan (as executed):** random blocks (seed 42) from the 50,185-block window; one `eth_getBlockReceipts` per block recovers reverted-tx hashes/from/to **and** same-block measured arbs' V2/V3 pools; accumulate to 300 reverted txs; then `debug_traceTransaction` each to recover touched pools; join within-block. **Budget used: 354 RPC calls (cap 600).**

| Metric | Value |
|---|--:|
| Blocks sampled | 54 |
| Reverted txs sampled & traced | 300 |
| ...with recoverable touched pools | 299 (100%) |
| COLLISIONS found (reverted+arb, same block, shared V2/V3 pool) | 17 |
| Collision rate among sampled reverted txs | 5.7% |

> **Sampling caveat:** collisions are counted on a 300-reverted-tx random sample (block-clustered by the per-block fetch); rates carry sampling error and V4-singleton contests are **under-counted** — the join uses precise V2/V3 pool addresses; V4's shared-manager can't confirm same-pool without a poolId, so V4-only fights are invisible here.

## Task 3 — Collision anatomy [M, sampled]

Per-collision detail:

| block | contested bucket | winner cluster | loser (to) | winner bid% | tier median bid% | idx gap (winner-loser) |
|--:|---|---|---|--:|--:|--:|
| 25476501 | <$10 | `('f', '0x17222` | `0x5597278e3b…` | 75.45% | 19.62% | -12 |
| 25485256 | $100-1k | `('f', '0xa207e` | `0x28b1dc1a5e…` | 2.00% | 0.39% | -110 |
| 25472427 | <$10 | `('f', '0x37bdc` | `0x28b1dc1a5e…` | 64.52% | 19.62% | 223 |
| 25459615 | <$10 | `('f', '0x46700` | `0x278d858f05…` | 266.52% | 19.62% | -55 |
| 25459615 | <$10 | `('f', '0x46700` | `0x8cc5c24a16…` | 266.52% | 19.62% | -82 |
| 25459615 | <$10 | `('f', '0x46700` | `0x8cc5c24a16…` | 266.52% | 19.62% | -92 |
| 25457708 | $10-100 | `('f', '0x46700` | `0x278d858f05…` | 53.77% | 1.38% | -65 |
| 25457708 | $10-100 | `('f', '0x46700` | `0x8cc5c24a16…` | 53.77% | 1.38% | -71 |
| 25457708 | $10-100 | `('f', '0x46700` | `0x28b1dc1a5e…` | 53.77% | 1.38% | -119 |
| 25457708 | $10-100 | `('f', '0x46700` | `0x8cc5c24a16…` | 53.77% | 1.38% | -141 |
| 25457708 | $10-100 | `('f', '0x46700` | `0x8cc5c24a16…` | 53.77% | 1.38% | -142 |
| 25462683 | <$10 | `('f', '0x6c97c` | `0x28b1dc1a5e…` | 42.43% | 19.62% | -54 |
| 25462683 | <$10 | `('f', '0x6c97c` | `0x278d858f05…` | 42.43% | 19.62% | -56 |
| 25486693 | <$10 | `('f', '0xf41c1` | `0x89c6340b1a…` | 14.81% | 19.62% | 30 |
| 25473115 | <$10 | `('f', '0xa3192` | `0x6131b5fae1…` | 58.99% | 19.62% | -59 |
| 25465391 | $10-100 | `('f', '0xace00` | `0x0f54099d78…` | 94.96% | 1.38% | -48 |
| 25439989 | <$10 | `('f', '0x7d344` | `0x8cc5c24a16…` | 65.22% | 19.62% | 1 |

*(Winner clusters are keyed by their **operator EOA** — the `('f', '0x…')` entry is that address. Negative idx-gap = the winner landed at an **earlier** tx-index than the reverted loser, i.e. got in first. **Finding:** contested arbs clear at bids far above the tier median — e.g. 64–266% of gross vs a 19.6% median in <$10 and 1.4% in $10–100 — so contested opportunities are fought for at much higher bids, several even bidding >100% of gross (to a loss) to win.)*

Collisions per size bucket:

| Bucket | Collisions |
|---|--:|
| <$10 | 10 |
| $10-100 | 6 |
| $100-1k | 1 |
| >$1k | 0 |

Winner×loser cluster matrix (counts; loser mapped to census cluster where known, else its `to` address):

| winner cluster | loser | count |
|---|---|--:|
| `('f', '0x46700` | `('f', '0x0bc9936` | 5 |
| `('f', '0x46700` | `bot:0x278d858f` | 2 |
| `('f', '0x17222` | `bot:0x5597278e` | 1 |
| `('f', '0xa207e` | `('f', '0x7ff3a29` | 1 |
| `('f', '0x37bdc` | `('f', '0x7ff3a29` | 1 |
| `('f', '0x46700` | `('f', '0x7ff3a29` | 1 |
| `('f', '0x6c97c` | `('f', '0x7ff3a29` | 1 |
| `('f', '0x6c97c` | `bot:0x278d858f` | 1 |
| `('f', '0xf41c1` | `('f', '0x1342db8` | 1 |
| `('f', '0xa3192` | `('f', '0x6d37fb5` | 1 |
| `('f', '0xace00` | `bot:0x0f54099d` | 1 |
| `('f', '0x7d344` | `('f', '0x0bc9936` | 1 |

## Task 4 — The non-fight number [M, sampled]

| Population (sampled blocks) | Measured arbs | With a colliding same-block reverted rival | Rate |
|---|--:|--:|--:|
| all measured arbs | 111 | 10 | 9.0% |
| >$100 measured arbs | 7 | 1 | 14.3% |

**Baseline under random arrival [E].** Observed: median distinct V2/V3 pools active per block U≈18, median V2/V3 pools per measured arb p_arb≈2, reverted txs per block ≈4.1. Model each tx as drawing its pools uniformly from the U pools active that block, so a random (arb, revert) pair shares ≥1 pool with probability ≈ p_arb·p_rev/U ≈ 22.2%; compounded over ~4 reverts/block, the baseline chance a given arb has ≥1 same-pool reverted rival ≈ **64.1%** [E]. Compare to the measured all-arb rate above: a measured rate near/below this baseline means low collisions are explained by **sparse opportunities**, not carved territory; a rate well above baseline means **real contests**.

*Baseline caveat [E]: this is an UPPER-ish estimate — it assumes every reverted tx touches ~2 of the block's pools, but many reverted txs are failed non-arb txs touching none of the arb's pools, so the true random-collision baseline is well below 64%. The gap between the 9% measured and this baseline is therefore inflated by baseline over-estimation; do **not** read it as arbs actively avoiding rivals. The robust takeaway is the closing guardrail, not this point estimate.*

## Closing guardrail (stated, not a verdict)

**Landed-reverted losers are a LOWER BOUND on contests.** Builders simulate bundles and silently drop the losing ones, so most losing attempts never land on-chain and are invisible to this or any chain-only method. Therefore: a **high** collision rate proves fighting; a **low** collision rate is consistent with EITHER no fighting OR fights fully resolved inside builders before inclusion. The numbers above bound what is visible on-chain; they do not measure the private auction. No verdict is drawn beyond these measured bounds.

*Probe complete. One bounded fetch used. Scratch file — not the census.*
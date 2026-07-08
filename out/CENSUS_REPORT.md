# ETH Mainnet Atomic-Arbitrage Census

**Window [M]:** blocks `25,437,594` → `25,487,778` (50,185 blocks processed, 7.00 days), fixed at run start.
**Chain:** ETH mainnet via Chainstack archive node (Geth). **Total txs scanned [M]:** 16,152,634.

**Coverage:** measured **71.3%** of detected atomic arbs (87,918 fully-measured of 123,391 detected arb-shaped txs). Remainder: 20,234 unpriceable (16.4%), 15,239 failed-to-measure (12.4%). Both listed below and counted here.

> Every number is labeled **[M]** measured or **[E]** derived/estimated. Profit is measured on-chain in WETH/ETH terms; **USD is a derived column** (ETH→USD via Chainlink ETH/USD at each arb's block, cross-checked vs a Uniswap-V3 USDC/WETH spot). Token→ETH via deepest on-chain WETH/USDC/USDT pool spot at the arb block.

## 1. Headline [M]

| Metric | Value |
|---|---|
| Confirmed atomic arbs (measured) | **87,918** [M] |
| Arbs/day | **12,560** [M] |
| Distinct winner addresses (beneficiaries) | 7,904 [M] |
| Distinct winner clusters (operator-linked) | 7,703 [M] |
| Top-1 cluster share of total net profit | 17.6% [M] |
| Top-5 cluster share of total net profit | 42.1% [M] |
| Net profit USD — median | $0.02 [M/derived] |
| Net profit USD — p25 / p75 | $0.00 / $0.63 [M/derived] |
| Gross profit USD — median | $0.28 [M/derived] |
| Builder payment as % of gross — median | 0.00% [M] |
| Gas cost USD — median | $0.11 [M/derived] |
| Total net profit (measured arbs) | $1,401,115 [M/derived] |

### Landed vs. reverted vs. attempts

- **Landed-succeeded arbs [M]:** 87,918 confirmed (+ 20,234 unpriceable + 15,239 failed-to-measure).
- **Landed-reverted attempts by known arb addresses [M, lower bound]:** 47,053 (reverted txs in-window whose `to` is a confirmed winner contract/EOA; of 204,430 total reverted txs).
- **True attempt count: UNMEASURABLE** — reverted txs emit no logs, and mempool-dropped / non-landed bundle attempts are not observable from chain state. Not estimated.

## 2. Size buckets (by gross USD) [M]

| Bucket | Count | Median net $ | p25 net $ | p75 net $ | Median builder %gross | Median gas $ |
|---|--:|--:|--:|--:|--:|--:|
| <$10 | 78,577 | 0.01 | 0.00 | 0.22 | 0.00% | 0.10 |
| $10-100 | 7,089 | 17.64 | 10.92 | 33.74 | 0.00% | 0.33 |
| $100-1k | 1,953 | 195.57 | 129.16 | 348.38 | 0.00% | 0.77 |
| >$1k | 299 | 1,615.79 | 1,157.91 | 2,444.49 | 0.00% | 1.03 |

## 3. Winner census — top 10 clusters [M]

| # | Lead address | Contracts / ops | Arbs | Median net $ | Cluster net $ | Median bid %gross | Mempool (majority) | Median tx-idx | Backrun dist (median) |
|--:|---|---|--:|--:|--:|--:|---|--:|--:|
| 1 | `0x1f2f10d1c407…` | 1c/1op | 3,825 | 0.00 | 246,959 | 0.00% | public | 60 | 1 |
| 2 | `0x6aba0315493b…` | 1c/197op | 753 | 85.23 | 198,406 | 0.00% | public | 13 | 4 |
| 3 | `0xbee3211ab312…` | 1c/10op | 580 | 1.99 | 55,669 | 14.49% | private | 19 | 4 |
| 4 | `0x01fdc48ba090…` | 1c/2op | 41 | 930.51 | 47,000 | 0.63% | private | 7 | 1 |
| 5 | `0x45e9b0494217…` | 1c/6op | 61 | 248.89 | 41,738 | 3.27% | private | 4 | 1 |
| 6 | `0x9008d19f58aa…` | 1c/16op | 3,855 | 0.71 | 38,660 | 0.00% | public | 43 | 12 |
| 7 | `0xbdb3ba9ffe39…` | 1c/2op | 1,546 | 1.55 | 28,943 | 0.00% | public | 1 | 1 |
| 8 | `0xd13be92afe00…` | 1c/1op | 1 | 26,741.59 | 26,742 | 0.00% | public | 150 | 1 |
| 9 | `0x5d98f54d8297…` | 1c/1op | 45 | 7.91 | 17,887 | 2.06% | private | 32 | 12 |
| 10 | `0x33b41fe18d3a…` | 1c/3op | 24 | 250.78 | 13,212 | 0.00% | public | 135 | 12 |

- *Contracts/ops* = distinct beneficiary contracts / distinct operator EOAs in the cluster (clustered by shared operator EOA — the funder/controller proxy; explicit deployer clustering not performed, see methods).
- *Backrun dist* = median in-block position gap to the nearest preceding tx sharing a swap pool (victim-adjacency proxy, measured on up to 40 arbs/cluster). Share with a same-block same-pool predecessor: #1:65%, #2:62%, #3:75%, #4:100%, #5:98%, #6:70%, #7:50%, #8:100%, #9:72%, #10:83%.

### Mempool-origin flag (heuristic) [M/E]

- `likely_public(priority_fee_only)`: 62,851 (71.5%)
- `private_bundle(coinbase_xfer)`: 21,607 (24.6%)
- `undetermined`: 3,460 (3.9%)

> Heuristic, not ground truth: coinbase transfer to the builder ⇒ private-bundle order flow; priority-fee-only with no coinbase transfer ⇒ likely public mempool. True mempool origin is not recoverable from chain state alone; flag labeled [E] where inferred.

## 4. Unpriceable list [M]

20,234 detected arb-shaped txs whose profit is denominated in a token with no reliable on-chain price at the arb block (no sufficiently-deep WETH/USDC/USDT pool). Profit **not valued, not dropped**.

Most common unpriceable profit tokens (address: #arbs):
- `0x47883e389bb6be3650b0c0935b300b50a95fc072`: 3310
- `0x19640000000ba88d36206beb10d0e86011c8d08c`: 1325
- `0xaca92e438df0b2401ff60da7e4337b687a2435da`: 1215
- `0x1223334444a7466fbf985b14e1f4edaf3883bca6`: 978
- `0x10dea67478c5f8c5e2d90e5e9b26dbe60c54d800`: 968
- `0x904567252d8f48555b7447c67dca23f0372e16be`: 873
- `0xc8fb80fcc03f699c70ff0cc08c09106288888888`: 481
- `0xe76c5b78f93909d34404e9eb4c1f19e7582a5de1`: 473
- `0x94314a14df63779c99c0764a30e0cd22fa78fc0e`: 427
- `0xde4ee8057785a7e8e800db58f9784845a5c2cbd6`: 354

### Excluded: non-atomic high-margin events [M]

1,130 txs (0.9% of all arb-shaped txs) were detected as arb-shaped but **excluded as NON-arbitrage**: profit ≥50% of the DEX pool volume of the profit asset (ratio>0.5 ⇒ >200% single-tx return), impossible for spread arbitrage. These are redemptions / inventory-realization / pool-drains / exploits. Excluded from all arb stats and from the coverage denominator. Their *apparent* value (gross **$410,616,801**, net **$410,460,569**) is NOT arb profit: had they been counted, measured net profit would jump from $1,401,115 to $411,861,684 — a **294×** inflation from this thin tail. Isolating them is the single most important correctness step in the census.

## 5. Failed-to-measure list [M]

15,239 detected arb-shaped txs that could not be measured. Reasons:

- `unpriceable_outflow`: 15,238
- `implausible_valuation`: 1

> `unpriceable_outflow`: beneficiary spent a token with no reliable price, so net profit is genuinely indeterminate (can't tell arb from loss). `trace_failed`/`exc:*`/`receipt_fetch_fail`: RPC/trace error. `non_standard_transfer_events`: token used non-standard (non-indexed / rebasing) Transfer events; balance-delta not reconstructable from logs.

## 6. Methods appendix

### Detection heuristic [M]
- **Primitive:** `eth_getBlockReceipts` per block (all logs, gas, status, effective gas price, tx index) + `eth_getBlockByNumber` header (miner, base fee, timestamp). Every tx classified.
- **Balance-delta method (not event-amount method):** per-tx net balance delta per (address, token) accumulated from ERC-20 `Transfer` + WETH `Deposit`/`Withdrawal` logs; native ETH deltas + builder coinbase transfers from `debug_traceTransaction` (callTracer) on each candidate. Fee-on-transfer/rebasing tokens: measured as balance deltas; tokens with non-standard Transfer events are routed to failed-to-measure rather than mis-valued.
- **Beneficiary:** restricted to the arbitrageur-controlled address — tx.to (bot contract) or tx.from (EOA) — never a pool. Any address emitting a Swap/Sync/Mint/Burn event is excluded as an AMM pool. Revenue is the beneficiary's balance delta, which may differ from tx.from (gross≠net trap handled).
- **Atomic-arb definition:** ≥2 DEX swaps forming a value cycle; beneficiary ends value-positive (gross > ~$0.01) after pricing ALL signed deltas. Confirmation is **value-based**, not raw-unit (a −54 USDC buy is not 'dust' — decimals-aware thresholds throughout).
- **Exclusions (misclassification guards):** liquidations (Aave/Compound/Maker liquidation events) excluded; JIT liquidity (Mint+Burn same tx) excluded; sandwich legs fail the single-tx cyclic test (a front-run leg ends holding the victim token, not net base asset). Flash-loan-wrapped and aggregator-routed arbs ARE captured (flash-loan repayment nets to ~0 in the borrowed token; the balance-delta cycle still resolves).
- **Non-atomic-arb exclusion (self-financing / margin test):** profit in an asset cannot exceed what was swapped through DEX pools. Events where profit ≥50% of the profit-asset's pool volume (a >200% single-tx return, impossible for a spread arb) are excluded as redemptions / inventory-realization / pool-drains / exploits — gated to gross>2 ETH so V4/aggregator-settled small arbs (whose pool volume is undercounted) are not swept up. This one guard removed a handful of events that otherwise carried ~98% of naive 'profit'. Borderline events just under the 0.5 cut are retained and may include some non-arb value extraction.
- **Known bounds (documented, not hidden):** (a) arbs sweeping profit to a separate treasury address inside the tx fall to route_or_user; (b) pure native-ETH-settled arbs with no positive logged-token delta are under-counted; (c) token-denominated profits without a priceable pool are listed as unpriceable. These reduce recall, never inflate measured profit.

### Price sources [M]
- **ETH/USD:** Chainlink ETH/USD aggregator `latestRoundData()` via `eth_call` at each arb block, staleness-checked (updatedAt within 2h); falls back to Uniswap-V3 USDC/WETH 0.05% pool spot. Method logged per conversion. (Validated: the two sources agreed to ~0.2% at spot-check.)
- **Token→ETH:** deepest on-chain token/WETH pool (Uniswap V3 fee tiers 0.01–1% + V2); if none deep enough, token/USDC or token/USDT pool spot then stable→ETH. Depth-gated (≥0.3 WETH or ≈$300 stable) else unpriceable. Pool spot read at the arb block (archive).
- **Profit denomination:** raw output is WETH/ETH-denominated; USD is a derived column with its conversion source labeled. Token amounts are never treated as USD.

### Control results (run BEFORE the batch) — PASSED

Three hand-verified true arbs (independent manual recomputation of balance deltas, coinbase payment, and gas matched the pipeline):
- `0xbe05aed76c771b8336…` — multi-asset WETH arb: gross $23.95, net $0.72. beneficiary WETH delta +0.013821, coinbase 0, gas 0.013406 — all match independent recompute.
- `0xad444e4c47992dfeba…` — FLASH-LOAN-wrapped WETH arb: gross $0.49, net $0.04. FlashLoan event present; WETH +0.000281, coinbase-to-builder 0.000234, gas 0.000022 — all match.
- `0xed38f6fd8cd3477cab…` — USDT-denominated arb: gross $10.9, net $10.75. native ETH 0, coinbase 0, gas 0.000082 match; token legs priced via validated pool spot.

Negative controls (must NOT be counted as arbs):
- `0x0230a0139118ebf540…` — expected reject (USDC buy, not arb) → got route_or_user (gross -$54.33).
- `0x0bb6a39b4df583aa54…` — expected failed_measure (unpriceable outflow) → got failed_measure (unpriceable_outflow).

Bugs caught & fixed by the control before batch: flat DUST_WEI decimals trap in cyclic test (a -54 USDC buy read as dust); same decimals trap in unpriceable-loss check (a -12232 6-dec token outflow read as dust); pool address selected as beneficiary.

### Sample gate (run BEFORE the batch) — PASSED
- On 200 spread blocks: failed-to-measure 11.0% (stop rule: >20% ⇒ abort). Unpriceable 17.9%. Gate passed; proceeded to full window.

### Stopping
- Window fixed at start (last 7 days by block timestamp); not extended mid-run. Whole window processed, then stopped. No opportunistic scope extension.
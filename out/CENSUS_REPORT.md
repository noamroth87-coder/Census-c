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

---

## Follow-up: cost-to-win and competition cross-sections

*Computed only from the 87,918 fully-measured (confirmed) arbs in the existing dataset (the 71.3% coverage population), window 7.00 days. No re-scanning. Builder payment = coinbase transfer + any direct ETH/token transfer to the block's fee recipient within the tx, as measured from callTracer + logs; ratios computed in ETH terms then shown as %. All [M].*

### Task 1 — Spend-to-win (builder payment & total cost as % of gross) [M]

Zero-builder-payment arbs (no coinbase/direct transfer to the builder; they bid via priority fee only, which is inside gas) are reported as a **separate row**, not blended into the payer medians. `builder%` = builder payment ÷ gross; `cost%` = (builder + gas) ÷ gross.

| Scope | Row | Count | Share | builder% p25 | builder% med | builder% p75 | cost% p25 | cost% med | cost% p75 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| **Overall** | builder-payers | 21,606 | 24.6% | 31.55% | 71.16% | 100.00% | 85.34% | 97.68% | 120.65% |
| **Overall** | zero-builder | 66,312 | 75.4% | — | — | — | 14.46% | 80.83% | 97.81% |
| <$10 | builder-payers | 20,185 | 25.7% | 32.55% | 69.90% | 100.00% | 85.98% | 97.82% | 122.50% |
| <$10 | zero-builder | 58,392 | 74.3% | — | — | — | 29.89% | 87.92% | 98.06% |
| $10-100 | builder-payers | 1,005 | 14.2% | 71.06% | 96.78% | 106.91% | 77.13% | 97.90% | 111.72% |
| $10-100 | zero-builder | 6,084 | 85.8% | — | — | — | 0.53% | 1.55% | 6.03% |
| $100-1k | builder-payers | 357 | 18.3% | 0.56% | 1.40% | 63.32% | 0.71% | 1.55% | 64.98% |
| $100-1k | zero-builder | 1,596 | 81.7% | — | — | — | 0.14% | 0.38% | 1.19% |
| >$1k | builder-payers | 59 | 19.7% | 0.08% | 0.35% | 2.43% | 0.10% | 0.43% | 2.50% |
| >$1k | zero-builder | 240 | 80.3% | — | — | — | 0.03% | 0.09% | 0.21% |

### Task 2 — Size-bucket × competition [M]

| Bucket | Count | Count/day | Median net $ | p75 net $ | Distinct clusters | Top-1 cluster % of bucket net | Top-5 % of bucket net | Median gas used | Median tx index |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| <$10 | 78,577 | 11,225 | 0.01 | 0.22 | 6,143 | 11.6% | 28.4% | 326,606 | 70 |
| $10-100 | 7,089 | 1,013 | 17.64 | 33.74 | 1,913 | 8.9% | 25.3% | 415,333 | 30 |
| $100-1k | 1,953 | 279 | 195.57 | 348.38 | 530 | 19.4% | 43.9% | 731,614 | 16 |
| >$1k | 299 | 43 | 1,615.79 | 2,444.49 | 116 | 30.4% | 57.1% | 750,698 | 10 |

> Cluster = set of arbs linked by a shared operator EOA (`tx.from`) or beneficiary contract (union-find). Top-k share is of that bucket's total measured net. Where a bucket's net is dominated by a few clusters the share is high; a negative/near-zero bucket net can distort shares (noted inline if it occurs).

### Task 3 — Mempool-origin × profit cross-tab [M/E]

| Origin | Count | Share of total net | Median net $ | Median builder% of gross |
|---|--:|--:|--:|--:|
| likely-public | 62,851 | 86.0% | 0.03 | 0.00% |
| private-bundle | 21,607 | 13.3% | 0.00 | 71.15% |
| undetermined | 3,460 | 0.7% | 0.63 | 0.00% |

**Heuristic & how much to trust it.** The origin flag is *inferred from settlement mechanics, not observed*: an arb that transfers ETH/tokens to the block's fee recipient inside the tx (a coinbase payment) is flagged **private-bundle** (that is how searchers pay builders for off-mempool inclusion); an arb with no such transfer that instead carries a positive priority fee is flagged **likely-public**; anything else is **undetermined**. **Known failure modes:** (1) a private-bundle searcher can pay entirely via priority fee and emit no coinbase transfer — it is then indistinguishable from public flow and mislabeled likely-public, so *private is under-counted*; (2) some public-mempool bots also send a small coinbase tip, inflating private; (3) builders that receive payment via a *separate* bundle tx (not the arb tx itself) are invisible here. **Bottom line: the coinbase-transfer signal reliably identifies a floor on private flow, but the public/private split is a lower bound on private and cannot be treated as ground truth — treat it as directional, not exact.**

### Task 4 — Top-10 cluster profiles [M]

| # | Lead address | Arbs | Total net $ | Median net $ | Median builder% | Median gas used | Mempool mix (pub/priv/undet) | Dominant bucket (share of its net) | Clustering confidence |
|--:|---|--:|--:|--:|--:|--:|---|---|---|
| 1 | `0x1f2f10d1c4…` | 3,825 | 246,959 | 0.00 | 0.00% | 340,692 | 92/0/8% | >$1k (82%) | single address (direct) |
| 2 | `0x6aba031549…` | 753 | 198,406 | 85.23 | 0.00% | 771,621 | 100/0/0% | $100-1k (51%) | funding-linked via 197 operator EOA(s), 1 contract(s); deployer not established |
| 3 | `0xbee3211ab3…` | 580 | 55,669 | 1.99 | 14.49% | 496,033 | 0/100/0% | $100-1k (93%) | funding-linked via 10 operator EOA(s), 1 contract(s); deployer not established |
| 4 | `0x01fdc48ba0…` | 41 | 47,000 | 930.51 | 0.63% | 636,381 | 0/100/0% | >$1k (86%) | funding-linked via 2 operator EOA(s), 1 contract(s); deployer not established |
| 5 | `0x45e9b04942…` | 61 | 41,738 | 248.89 | 3.27% | 554,781 | 11/87/2% | >$1k (72%) | funding-linked via 6 operator EOA(s), 1 contract(s); deployer not established |
| 6 | `0x9008d19f58…` | 3,855 | 38,660 | 0.71 | 0.00% | 609,552 | 100/0/0% | $100-1k (39%) | funding-linked via 16 operator EOA(s), 1 contract(s); deployer not established |
| 7 | `0xbdb3ba9ffe…` | 1,546 | 28,943 | 1.55 | 0.00% | 879,000 | 100/0/0% | $100-1k (81%) | funding-linked via 2 operator EOA(s), 1 contract(s); deployer not established |
| 8 | `0xd13be92afe…` | 1 | 26,742 | 26,741.59 | 0.00% | 1,948,730 | 100/0/0% | >$1k (100%) | single address (direct) |
| 9 | `0x5d98f54d82…` | 45 | 17,887 | 7.91 | 2.06% | 429,896 | 7/93/0% | >$1k (80%) | single address (direct) |
| 10 | `0x33b41fe18d…` | 24 | 13,212 | 250.78 | 0.00% | 566,442 | 100/0/0% | >$1k (65%) | funding-linked via 3 operator EOA(s), 1 contract(s); deployer not established |

**Adjacency profile — NOT AVAILABLE from the stored dataset.** Per-arb victim-adjacency (backrun distance / share landing at victim-index+1 in the same block) requires each block's full receipt set to identify the specific victim swap; that is not stored in `arbs.jsonl` and recomputing it would require re-fetching block receipts (a re-crawl), which is out of scope for this follow-up. What IS stored is each arb's absolute `tx_index`; the median tx index per cluster is given below as a positional proxy (low index ⇒ top-of-block placement, typical of competitive backrunning; high index ⇒ later placement).

| # | Lead address | Median tx index | % at index 0-1 (block top) |
|--:|---|--:|--:|
| 1 | `0x1f2f10d1c4…` | 60 | 4% |
| 2 | `0x6aba031549…` | 13 | 12% |
| 3 | `0xbee3211ab3…` | 19 | 11% |
| 4 | `0x01fdc48ba0…` | 7 | 0% |
| 5 | `0x45e9b04942…` | 4 | 0% |
| 6 | `0x9008d19f58…` | 43 | 4% |
| 7 | `0xbdb3ba9ffe…` | 1 | 55% |
| 8 | `0xd13be92afe…` | 150 | 0% |
| 9 | `0x5d98f54d82…` | 32 | 2% |
| 10 | `0x33b41fe18d…` | 135 | 0% |

### Task 5 — Dust boundary (gross below which median net ≤ $0) [M/derived]

- **Break-even gross threshold [M/derived]:** ≈ **$0.034** gross profit. Arbs grossing below this have a **median net ≤ \$0** — builder payment + gas meet or exceed gross; above it the running median net turns positive. Found by bisecting the measured (gross, net) pairs for the sign change of the sub-\$T median net.
- **Share below the boundary:** **7,532 of 87,918 arbs = 8.6%** gross below $0.034. (This chain's gas is cheap — ~\$0.10 median — so the break-even sits far below $1; on a higher-gas chain it would be much higher.)
- **For context:** 19.6% of all 87,918 measured arbs are individually net ≤ \$0 (landed winners that failed to clear their own costs) [M].

Supporting — median net by gross band:

| Gross band | Count | Median net $ |
|---|--:|--:|
| $0-1 | 60,409 | 0.01 |
| $1-2 | 6,671 | 0.71 |
| $2-5 | 7,189 | 2.18 |
| $5-10 | 4,308 | 5.62 |
| $10-25 | 3,973 | 13.02 |
| $25-100 | 3,116 | 37.54 |
| ≥$100 | 2,252 | 228.07 |

---

## Follow-up 2: bid visibility and builder integration

*Stored measured set + ONE bounded fetch of 496 block headers (fee-recipient + extra-data only; no receipts, no tx re-scan). Builders identified from extra-data tags, else labelled by fee-recipient address. Baseline builder share is computed over the 496 fetched blocks — these are arb-hosting blocks, not a uniform block sample, and n≈500 is noisy; raw counts are shown so significance is judgeable.*

### Task 1 — Priority-fee audit & total bid (stored data) [M]

Priority fee = (effective gas price − base fee) × gas used, USD-derived at the arb block. Total bid = priority fee + builder payment (coinbase/direct), as % of gross.

| Bucket | Count | Priority fee $ p25 | med | p75 | Total-bid %gross p25 | med | p75 |
|---|--:|--:|--:|--:|--:|--:|--:|
| >$1k | 299 | 0.0199 | 0.4668 | 2.4898 | 0.01% | 0.08% | 0.29% |
| $100-1k | 1,953 | 0.0191 | 0.3541 | 1.6447 | 0.08% | 0.39% | 1.45% |

> **FLAG:** median total bid in the >$1k tier is **0.08% of gross** — near-zero. Payment for inclusion is either genuinely absent (these winners are not paying to win on-chain) or **invisible** to on-chain measurement (off-chain / out-of-band settlement). On-chain data alone cannot distinguish the two; that is the motivation for Tasks 2–4.

### Task 2 — Builder identity for >$1k blocks (bounded fetch) [M]

297 distinct blocks host the 299 >$1k arbs; all fetched. Builder distribution (by block), with the fetched-set baseline for reference:

| Builder | >$1k blocks | >$1k share | Baseline share (all fetched) |
|---|--:|--:|--:|
| Titan | 182 | 61.3% | 63.9% |
| BuilderNet | 37 | 12.5% | 12.1% |
| Quasar | 32 | 10.8% | 12.5% |
| bobTheBuilder | 21 | 7.1% | 4.2% |
| Eureka | 17 | 5.7% | 5.4% |
| fee-recipient:0x6c42a0b5 | 2 | 0.7% | 0.4% |
| beaverbuild | 2 | 0.7% | 0.4% |
| BTCS Builder+ | 2 | 0.7% | 0.4% |
| fee-recipient:0x3bee5122 | 2 | 0.7% | 0.4% |

### Task 3 — Winner × builder cross-tab, >$1k tier (top 10 clusters by arb count) [M]

Verdict is mechanical: **INTEGRATED** = top-builder share >80% AND >2× that builder's baseline; **CONCENTRATED** = >2× baseline but ≤80%; **DISTRIBUTED** = roughly tracks baseline. All >$1k blocks were fetched, so labeled=total here. Small arb counts ⇒ read verdicts with the raw counts.

| # | Lead address | Arbs (labeled/total) | Distinct builders | Top builder | Top share | Baseline share | Verdict | Raw builder counts |
|--:|---|--:|--:|---|--:|--:|---|---|
| 1 | `0x1f2f10d1c4…` | 60/60 | 3 | Titan | 92% | 64% | DISTRIBUTED | Titan:55, BuilderNet:4, beaverbuild:1 |
| 2 | `0x6aba031549…` | 45/45 | 5 | Titan | 58% | 64% | DISTRIBUTED | Titan:26, Quasar:9, BuilderNet:5, Eureka:4, beaverbuild:1 |
| 3 | `0x01fdc48ba0…` | 20/20 | 3 | bobTheBuilder | 45% | 4% | CONCENTRATED | bobTheBuilder:9, Titan:7, BuilderNet:4 |
| 4 | `0x45e9b04942…` | 14/14 | 3 | bobTheBuilder | 43% | 4% | CONCENTRATED | bobTheBuilder:6, Titan:6, BuilderNet:2 |
| 5 | `0x5d98f54d82…` | 8/8 | 2 | Titan | 75% | 64% | DISTRIBUTED | Titan:6, Quasar:2 |
| 6 | `0x33b41fe18d…` | 6/6 | 3 | Titan | 67% | 64% | DISTRIBUTED | Titan:4, Eureka:1, Quasar:1 |
| 7 | `0xad17043228…` | 5/5 | 3 | Quasar | 40% | 12% | CONCENTRATED | Quasar:2, Titan:2, BuilderNet:1 |
| 8 | `0x49719d256a…` | 5/5 | 3 | Titan | 60% | 64% | DISTRIBUTED | Titan:3, BuilderNet:1, Quasar:1 |
| 9 | `0x2beb773c60…` | 4/4 | 2 | Titan | 75% | 64% | DISTRIBUTED | Titan:3, Quasar:1 |
| 10 | `0x219fc40c4c…` | 4/4 | 3 | Titan | 50% | 64% | DISTRIBUTED | Titan:2, Eureka:1, BuilderNet:1 |

### Task 4 — Winner × builder cross-tab, $100–1k tier (top 5 clusters by net) [M, PARTIAL]

**Partial coverage:** the $100–1k top-5 clusters span 795 blocks not in the >$1k set; the 500-block cap left budget for only a systematic ~199-block sample of them, so each cluster's builder mix is measured on the fetched subset (labeled/total column). Verdicts on partial samples — weigh by the counts.

| # | Lead address | Arbs (labeled/total) | Distinct builders | Top builder | Top share | Baseline share | Verdict | Raw builder counts |
|--:|---|--:|--:|---|--:|--:|---|---|
| 1 | `0x6aba031549…` | 71/300 | 4 | Titan | 58% | 64% | DISTRIBUTED | Titan:41, Quasar:16, BuilderNet:8, Eureka:6 |
| 2 | `0xbee3211ab3…` | 53/193 | 5 | Titan | 57% | 64% | DISTRIBUTED | Titan:30, Quasar:11, BuilderNet:9, Eureka:2, bombora:1 |
| 3 | `0x1f2f10d1c4…` | 36/106 | 2 | Titan | 92% | 64% | DISTRIBUTED | Titan:33, BuilderNet:3 |
| 4 | `0xbdb3ba9ffe…` | 33/154 | 1 | Titan | 100% | 64% | DISTRIBUTED | Titan:33 |
| 5 | `0x9008d19f58…` | 15/59 | 4 | Titan | 40% | 64% | DISTRIBUTED | Titan:6, Quasar:4, BuilderNet:3, Eureka:2 |

### What this analysis still cannot see (known-unmeasurable, stated not estimated)

- **Off-chain / out-of-band payments** to builders (fiat, CEX transfers, cross-chain) — invisible on L1.
- **Searcher–builder profit sharing** and rebates settled off-chain or netted periodically, not per-block.
- **Exclusive order-flow agreements** (a searcher routing exclusively to one builder by contract, not visible as an on-chain payment).
- **Vertical integration where searcher and builder are the same entity** but use unlinked addresses — a low on-chain bid then reflects self-building, not a cheap win; the builder cross-tab hints at it (INTEGRATED label) but cannot prove common ownership.
- **Priority-fee-only private bundles**: a private bundle that pays purely via priority fee is indistinguishable from public flow, so the bid-visibility split is a lower bound on private payment.
- **Bundle-level payments** made in a *separate* tx of the same bundle (not the arb tx) are not attributed here.

---

## Follow-up 3: refund detection and true bid — census close

*Final bounded fetch: 297 `eth_getBlockReceipts` (one call/block ⇒ every tx's index, from/to, logs) + 239 traces (arb + successor of BACKRUN arbs, for native-ETH refunds) = **536 RPC calls**, under the 3,000 cap. Receipt-fetch failures: 0.0% (<15% ⇒ proceeded). Scope: the 297 blocks holding the 299 >$1k measured arbs. All [M].*

### Task 1 — Backrun-adjacency of >$1k arbs [M]

Predecessor = the tx immediately before the arb in-block. **BACKRUN** = predecessor is a swap touching ≥1 of the arb's own pools, by a different party (the victim). **SELF-SEQUENCED** = predecessor sent/received by the arb's own cluster. **STANDALONE** = unrelated predecessor (or arb is first in block).

| Class | Count | Share |
|---|--:|--:|
| BACKRUN | 122 | 40.8% |
| SELF-SEQUENCED | 7 | 2.3% |
| STANDALONE | 170 | 56.9% |
| **total** | 299 | 100% |

Per top cluster (by >$1k arb count):

| Lead address | Arbs | BACKRUN | SELF-SEQ | STANDALONE |
|---|--:|--:|--:|--:|
| `0x1f2f10d1c4…` | 60 | 55 | 0 | 5 |
| `0x6aba031549…` | 45 | 5 | 1 | 39 |
| `0x01fdc48ba0…` *(CONC)* | 20 | 20 | 0 | 0 |
| `0x45e9b04942…` *(CONC)* | 14 | 13 | 0 | 1 |
| `0x5d98f54d82…` | 8 | 0 | 0 | 8 |
| `0x33b41fe18d…` | 6 | 0 | 0 | 6 |
| `0xad17043228…` *(CONC)* | 5 | 0 | 0 | 5 |
| `0x49719d256a…` | 5 | 0 | 0 | 5 |

### Task 2 — Refund detection on BACKRUN arbs [M]

Victim = predecessor's originating address. A transfer to the victim (token/WETH in logs, or native ETH via trace) inside the arb tx or its in-block successor, **≥1% of the arb's gross**, = REFUNDED. That refund is the real competitive bid returned to order flow.

| Metric | Value |
|---|--:|
| BACKRUN arbs | 122 |
| REFUNDED (≥1% gross to victim) | 0 (0.0%) |

> **No BACKRUN arb refunds ≥1% of gross were detected on-chain.** Either these winners run no OFA/refund program, or refunds settle by a path invisible to receipts+traces (see closing unmeasurables). The real competitive bid in this tier is not visible on-chain.

### Task 3 — True winner take, >$1k tier [M/derived]

True net = gross − gas − builder payment − refund. (Priority fee is already inside *gas* = gas_used × effective gas price, so it is not subtracted twice; the OFA refund is the extra bid on top.) True net margin = true net ÷ gross.

| Category | Count | Median true-net margin % | p75 true-net margin % |
|---|--:|--:|--:|
| REFUNDED | 0 | — | — |
| BACKRUN-unrefunded | 122 | 99.72% | 99.91% |
| STANDALONE | 170 | 99.94% | 99.98% |
| SELF-SEQUENCED | 7 | 99.86% | 99.94% |

Per top cluster — dominant category (and CONCENTRATED clusters explicitly):

| Lead address | Arbs | Dominant category | Median true-net margin % | CONC? |
|---|--:|---|--:|:--:|
| `0x1f2f10d1c4…` | 60 | BACKRUN-unrefunded | 99.57% |  |
| `0x6aba031549…` | 45 | STANDALONE | 99.87% |  |
| `0x01fdc48ba0…` | 20 | BACKRUN-unrefunded | 99.76% | yes |
| `0x45e9b04942…` | 14 | BACKRUN-unrefunded | 99.13% | yes |
| `0x5d98f54d82…` | 8 | STANDALONE | 99.90% |  |
| `0x33b41fe18d…` | 6 | STANDALONE | 99.99% |  |
| `0xad17043228…` | 5 | STANDALONE | 99.97% | yes |
| `0x49719d256a…` | 5 | STANDALONE | 99.98% |  |

### Census closing summary [M]

Per size bucket: **addressable** arbs/day (excluding the 3 CONCENTRATED clusters' volume), and median true-net margin. Refund/OFA is measured only in the >$1k tier (this fetch); for smaller tiers 'true net' = gross − gas − builder (refund unmeasured — stated, not assumed zero).

| Bucket | Arbs | Addressable arbs/day | Median true-net margin % | Refund measured? |
|---|--:|--:|--:|:--:|
| <$10 | 78,577 | 11,225 | 8.63% | no (unmeasured) |
| $10-100 | 7,089 | 1,010 | 97.82% | no (unmeasured) |
| $100-1k | 1,953 | 273 | 99.45% | no (unmeasured) |
| >$1k | 299 | 37 | 99.90% | yes |

**Known-unmeasurables that still apply (stated, not estimated):** off-chain / out-of-band builder payments; searcher–builder profit-sharing and periodic netting; exclusive order-flow agreements; same-entity searcher+builder on unlinked addresses (self-building reads as a low bid); priority-fee-only private bundles (private flow is a lower bound); bundle-level payments in a separate tx not attributed here; OFA refunds settled off-chain or via the builder rather than an on-chain transfer to the victim; and the census's own coverage bound — 71.3% of detected arbs measured, the rest unpriceable or failed-to-measure. **The census is the measured map within these bounds; it is not a claim about what happens outside them.**

*Census complete.*
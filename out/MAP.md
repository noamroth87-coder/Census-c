# THE MAP — Ethereum-Mainnet Atomic-Arbitrage Census, Consolidated

*Final mobile consolidation. Zero fetches — reads every committed file (census + Follow-ups 1–3,
opportunity-age pilot, overbidder autopsy, contest intensity, dossier, volatility replay [Spec 1],
coverage map [Spec 2], lane census, coverage hole [M1], entity atlas [M2], storm2 [M3]). No new
measurement; where files disagree the map shows both with which file revised which. All work dated
2026-07-08 unless a window is stated. This closes the mobile phase; Phase D synthesis starts here.*

**Base facts.** Census window = blocks 25,437,594–25,487,778 (50,185 blocks, 7.00 days, one **quiet
week**, base fee ~0.08 gwei), 16,152,634 txs scanned. Detection = balance-delta method (ERC-20/WETH
logs, never event amounts); valuation on-chain (Chainlink ETH/USD + pool spot); WETH stays WETH, USD
a derived column. ETH/USD ≈ $1,568 in-window.

---

## 1. Claims ledger

**Confidence grade:** **A** = multi-window and/or multi-method (survived quiet + storm1 + storm2, or
cross-checked two ways). **B** = single-window, full-population measured (the quiet census week). **C**
= sampled or estimated [E]. **Category:** SETTLED (answered, stable) · CLOSABLE-NEEDS-X (answerable with
stated extra data) · GATED-ON-BUILD (only a live bot resolves it) · NEVER-CLOSABLE (invisible to any
chain-only method).

| # | Claim (load-bearing) | Evidence base | n | Grade | Revised by | Category |
|---|---|---|--:|:--:|---|---|
| C01 | 87,918 confirmed atomic arbs; **12,560 arbs/day** | balance-delta, full window | 87,918 | B | dir. confirmed A (both storms ↑) | SETTLED |
| C02 | Coverage **71.3%** measured / 16.4% unpriceable / 12.4% failed | verdict split | 123,391 | B | M1 characterized the hole | SETTLED |
| C03 | Net profit **median $0.02**, p75 $0.63; **19.6% of arbs net ≤ $0** | per-arb net | 87,918 | B | — | SETTLED |
| C04 | Total measured net **$1,401,115** | Σ net | 87,918 | B | M2 replicated exactly | SETTLED |
| C05 | Size buckets: <$10 78,577 (med net $0.01) · $10–100 7,089 ($17.64) · $100–1k 1,953 ($195.57) · >$1k 299 ($1,615.79) | bucketed | 87,918 | B | — | SETTLED |
| C06 | Break-even at **$0.034 gross**; 8.6% of arbs below it | bisection | 87,918 | B | storm: rises w/ gas → $1.017 (s1)/$0.135 (s2) | SETTLED (level regime-var) |
| C07 | Builder payment **median 0.00% of gross**; 75.4% pay zero builder (priority-fee only) | coinbase trace | 87,918 | B | — | SETTLED |
| C08 | Mempool split ≈ **71.5% public / 24.6% private / 3.9% undet** (heuristic, lower-bound on private) | coinbase heuristic | 87,918 | C | — | GATED-ON-BUILD |
| C09 | Concentration **top-1 17.6% / top-5 42.1%** of net | cluster net | 7,703 cl | A | M2: unchanged at entity level (not understated) | SETTLED |
| C10 | Top clusters are **independent operators**; top-20 collapse into 20 entities (0 merges) | funder+deployer fetch | 20/112 | C | — | SETTLED (within fetch) |
| C11 | Shared custom executors (0x66a9893c: 21 clusters/181 EOAs; 0x4c82d1: 2,186 EOAs) are **bot-as-a-service**, not one entity | funder disambiguation | 4 execs | C | — | SETTLED |
| C12 | **>$1k tier true-net margin ≈ 99.9%** (gross−gas−builder−refund) | trace, all >$1k | 299 | B | — | SETTLED |
| C13 | **OFA refunds = 0** of 122 backrun arbs (≥1% gross to victim) | tx+successor scan | 122 | B | — | SETTLED |
| C14 | >$1k builders: **Titan 61%**, then BuilderNet/Quasar; **0 INTEGRATED, 3 CONCENTRATED** winner-clusters | extra-data tags | 297 blk | B | — | SETTLED |
| C15 | Apex `0xbdb3ba9f`: contract 11,703B, deployer **0x00ff842b**, deployed blk 24,620,633 | bytecode + binary search | — | B | M2 reproduced deployer 0x00ff842b | SETTLED |
| C16 | Apex is **≥30 EOAs on one shared contract**, ~5,854 tx/day; only **28%** of sampled txs arb-shaped | 800-tx struct sample | 800 | C | — | SETTLED (sample) |
| C17 | Apex 2-EOA census limb: 1,546 arbs, net **16.67 ETH ($29,318)/7d**, 37% arbs net ≤ $0, win rate ~99.8% | census, full pricing | 1,546 | B | — | SETTLED |
| C18 | Apex has **no builder moat** — block-top via 100% priority fee, coinbase 0.0000 ETH | census | 1,546 | B | dossier+census agree → A | SETTLED |
| C19 | Apex **bid formula NOT-EXTRACTABLE** (priority/gross CV 3.89; gwei CV 3.59; corr r=0.52) | census bids | 1,546 | B | coverage-map & dossier agree | CLOSABLE-NEEDS-longer-window |
| C20 | **Apex concentration is NOT regime-dependent** | quiet 17.6 / storm1 32.8 / storm2 13.5 | 3 win | A | **storm2 (M3) revised Spec1's "apex expansion"** | SETTLED |
| C21 | Regime-robust weather effects (both storms ↑): arbs/day, net sizes, reverted-tx share, dust boundary, priority-fee % | quiet+s1+s2 | — | A | magnitude scales w/ gas not price | SETTLED |
| C22 | Same-block backrun (**AGE-0) = 30%** of ≥$10 arbs; 70% untraceable; **no AGE-1+ measured** | live 10-min poll | 10 | C | — | GATED-ON-BUILD |
| C23 | Visible on-chain contest rate **5.7% of reverts / 9% of arbs** — an explicit **lower bound** | 300-tx sample | 300 | C | — | GATED-ON-BUILD |
| C24 | Contested arbs clear at **64–266% of gross** (vs 19.6% median <$10) — some bid to a loss to win | collision sample | 17 | C | — | SETTLED (sample) |
| C25 | Overbidding **pays for whales**: all 5 overbidder clusters net-positive on landed arbs; 3 "dumb-money" losers flip negative on est. revert-gas | stored + [E] gas | 5+4 | C | — | SETTLED ([E] gas) |
| C26 | **Coverage hole is bimodal/mixed**, not dust: 49% of hole arbs <$50 visible leg, 20% >$1k; measurable **profit floor = $0** (profit-determining leg is the unmeasured one) | stored legs | 35,473 | B | M1 (new) | SETTLED |
| C27 | Top-10 unpriceable tokens: **0/10 had a >$50k route** — GENUINELY-EXOTIC | pool check | 10 | C | M1 | SETTLED |
| C28 | Hunting-map **4 lanes pass DRAFT gates** (arbs/day ≥5, med net ≥$0.50, no BOOBY): v2:0x2a6c34, v3:0xeb85a25b, v3:0x47d486c6, v3:0x09117bff | census reuse, full 7d | 2,972 | B | **lane_census revised coverage-map's noisy ×35 ranking** | SETTLED |
| C29 | **0 BOOBY-TRAP lanes** in top-50; regime 28 ALL-WEATHER / 7 CALM-ONLY; sight 15 OPEN / 12 MIXED / 8 GATED | lane census | 50 | B | — | SETTLED |
| C30 | Quiet-hour is **metric-dependent** — dossier ~04:00 UTC (total tx) vs coverage-map ~17:00 UTC (swap-touches); not a robust window | 14d getLogs | — | C | files disagree, both shown | NEVER-CLOSABLE (soft) |

---

## 2. The market model

**A dual market, split by profit tier and by order-flow visibility.**

**Market A — the retail-dust floor (<$10 gross).** 78,577 arbs (89% of count), median net **$0.01**
[C05]. Cheap-gas chain (median gas $0.11) puts break-even at **$0.034 gross** [C06], so a vast tail of
sub-cent arbs clears. Highly fragmented (top-1 cluster of this bucket 11.6%). Mostly public mempool.
This is a volume-not-margin game; a build here competes on latency and gas-efficiency, not edge.

**Market B — the contested-value tier ($100+ gross).** 2,252 arbs, median net $195–$1,616 [C05].
True-net margin **~99.9%** [C12] — winners keep almost everything; **no OFA refunds** [C13]. More
concentrated (>$1k top-1 30.4%). Builder mix tilts to **Titan (61%)** but **no cluster is INTEGRATED**
with a builder — 3 are merely CONCENTRATED [C14]. Entry here is a bidding contest, not a moat.

**Three tiers, with entry specs:**

| Tier | Count/day | Median net | Structure | Entry spec |
|---|--:|--:|---|---|
| Dust (<$10) | 11,225 | $0.01 | fragmented, public | same-block backrun + gas-optimal routing; margin ≈ gas |
| Mid ($10–1k) | 1,292 | $18–$196 | semi-concentrated | priority-fee bidding, block-top placement |
| Whale (>$1k) | 43 | $1,616 | 30% top-1, Titan-heavy | out-bid on priority fee; **coinbase-transfer bundle beats priority-only incumbents** |

**Regime behavior [C20, C21].** Two storms (gas-driven + price-driven) tested against the quiet week.
**Robust (both storms agree):** arbs/day up, net sizes up, reverted-tx share up (more contention),
dust boundary up (small arbs stop clearing), priority-fee % up — **magnitude scales with gas, not
price**. **NOT a regime effect (storms disagree):** apex/top-1 concentration — storm1 showed 32.8%
(Spec 1 called it "apex expansion") but storm2 showed 13.5%; **withdrawn** [C20].

**Entity atlas summary [C09–C11].** 7,703 clusters → the top clusters are **genuinely independent**
operators (0 merges among the top-20; census concentration 17.6%/42.1% is **not** understated). Shared
custom executor contracts (e.g. 0x66a9893c across 181 EOAs) are **bot-as-a-service infrastructure**,
not single entities — the correct reading of the apex's own 0xbdb3ba9f/30-EOA pattern: shared *contract*
≠ shared *operator*. CoW settlement is the one census over-merge (many solvers → one cluster), biasing
concentration slightly *up*, not down.

---

## 3. The hunting map — final

The lane_census (full 7-day census-window re-measurement, 2,972 real arbs, zero-fetch reuse) **replaced
the coverage-map's ×35-scaled 1–2-arb noise**. Coverage-map's #1 lane ("$1,196 median, 5/day") was
exposed as 3 arbs median $0.01 [C28]. Incumbent entities from M2. Grades inherited from ledger
(lane stats = B single-window; slot-value = C [E]).

**The 4 DRAFT-gate-passing lanes** (arbs/day ≥5, med net ≥$0.50, no BOOBY):

| Lane | arbs/day | med net | top-1 | incumbent → entity (M2) | sight | regime | slot-val [C] |
|---|--:|--:|--:|---|---|---|--:|
| `v2:0x2a6c34…` | 25.9 | $59.95 | 70% | `0x1f2997c93a` → **#2 net entity ($198,406)** | MIXED 70% | ALL-WEATHER | 471 |
| `v3:0xeb85a25b…` | 29.0 | $27.05 | 58% | `0x2761a03953` (own cl, 117 arbs $3,673) | OPEN 86% | ALL-WEATHER | 332 |
| `v3:0x47d486c6…` | 8.4 | $14.88 | 27% | `0x004b38217d` (cl 0x196c00c1b0, 2,979 arbs; multi-lane×3) | GATED 8% | ALL-WEATHER | 91 |
| `v3:0x09117bff…` | 7.1 | $1.10 | 28% | `0x6ced635bc4` (sub-50-arb) | MIXED 64% | ALL-WEATHER | 6 |

*Warning: the highest-slot-value lane's incumbent is the market's **#2 net earner** — the best lane has a
whale defending it. Lane #2 (own small cluster, OPEN-sight) is the softest genuine entry.*

**The 8 GATED-sight lanes** (<30% of arbs are pilot-traceable pure-V2/V3 — a hidden-flow barrier):

| Lane | arbs/day | med net | incumbent → entity | note |
|---|--:|--:|---|---|
| `v3:0x47d486c6…` (#4) | 8.4 | $14.88 | `0x004b38217d` (2,979-arb cl) | also gate-passing |
| `v3:0x5c8096f1…` (#10) | 1.3 | $3.63 | `0x7d344a2d90` → **largest cluster (8,485 arbs), overbidder RATIONAL** | multi-lane×6 |
| `v3:0x307c4d0a…` (#13) | 6.4 | $0.30 | `0x790f117af8` (1,539-arb cl, $1,458) | |
| `v2:0x4798b81f…` (#18) | 0.7 | $0.76 | `0x7d344a2d90` (as #10) | multi-lane×6 |
| `v2:0x0f641efb…` (#22) | 0.7 | $0.28 | `0x32eef6c0ab` (51-arb cl, $356) | |
| `v3:0x8d5e3ac5…` (#27) | 9.0 | $0.00 | `0x7c1fb21f23` (1,260-arb cl, $2,163) | |
| `v3:0x738ea576…` (#31) | 0.7 | $0.01 | `0x004b38217d` (as #4) | multi-lane×3 |
| `v2:0x4de126d4…` (#35) | 0.9 | $0.00 | `0x004b38217d` (as #4) | multi-lane×3 |

GATED lanes are dominated by a few multi-lane incumbents (0x004b38217d ×3, 0x7d344a2d90 ×2) — contesting
one means contesting a broader operator. All lane incumbents are **their own entity** (no M2 merges).

---

## 4. The adversary file

**Apex entity — `0xbdb3ba9ffe…` [C15–C19].** One 11,703-byte executor contract, deployer
**0x00ff842b** (reproduced independently in M2), deployed ~106 days pre-window. Driven by **≥30 operator
EOAs** at ~5,854 tx/day — a general MEV/execution machine (only 28% of txs arb-shaped), of which the
census sees a **2-EOA limb**: 1,546 arbs, **net 16.67 ETH ($29,318)/7d**, block-top placement (median
tx-index 1, 55% at idx 0–1), venues spanning Uni V2/V3/V4 up to 73 hops, win rate ~99.8%. It is one
limb of a bigger operation; the full contract-wide P&L is unmeasured [C16, gap G4].

**Surviving attack vectors (measured, still open):**
- **No builder moat** [C18] — it buys block-top with 100% priority fee, coinbase 0.0000 ETH. A
  **coinbase-transfer bundle orders above it**. This is the single most exploitable measured finding.
- **37% loss tolerance** [C17, C25] — it lands rather than reverts even when net ≤ $0; an ε-higher bid
  flips its marginal wins to losses. Overbidding is a proven-profitable strategy for whales [C25].

**Withdrawn attack vectors (with why):**
- ~~"Apex tightens its grip in volatility" (Spec 1, storm1 32.8%)~~ — **withdrawn 2026-07-08 by storm2
  (M3)**: storm2 showed 13.5%, the opposite sign. Concentration is not regime-dependent [C20].
- ~~"ε-overbid the apex on a known bid formula"~~ — **not actionable**: the bid formula is
  NOT-EXTRACTABLE from n=1,546 in both the dossier and the coverage map [C19] (CV ~3.6–3.9, r=0.52).
  Needs a longer window or a live probe.
- ~~"Hunt the coverage-map's top negative-space lanes ($1,196 median / 5-per-day)"~~ — **withdrawn by
  lane_census**: those rows were ×35-scaled 1–2-arb noise; real median was $0.01 [C28].

**Dumb-money graveyard [C25]:** pure-reverter `0x278d858f` burned 31,392 reverted txs; 3 loser clusters
flip net-negative once estimated revert-gas is included. Loss is real but the gas is **estimated [E]**
(census kept only reverts' `to`, not gas) — true burn sits between window-net [M] and adj-net [E].

---

## 5. The gap register

| # | Gap (what mobile could not reach) | What closes it |
|---|---|---|
| G1 | **True attempt count** — reverted txs emit no logs, so win-rate denominators are lower bounds [C01 note] | NEVER (chain-only) |
| G2 | **Private-auction fights** — losing bundles dropped inside builders; on-chain contest rate 5.7% is a floor [C23] | HARNESS (relay/builder data feed) |
| G3 | **Off-chain revenue** — CEX/OTC, PFOF, rebates, cross-address netting; block-level integrated builder-operator profit | NEVER (chain-only) |
| G4 | **Full 14-day per-tx apex P&L** — 82k txs > budget; log-delta gross wrong ~1000× (WETH unwrap) [C16] | HARNESS (re-crawl w/ trace pricing) |
| G5 | **V4-singleton contests & coverage** — poolId not decoded; V4-only fights invisible, V4 venues under-enumerated [C23, C30] | HARNESS (V4 poolId decode) |
| G6 | **Apex bid formula** — no flat/scaled model fits n=1,546 [C19] | LONGER WINDOW + live bid probe |
| G7 | **Coverage-hole exotic profits** — 16.4% unpriceable; top tokens have no >$50k route; profit floor $0 [C26, C27] | NEVER (no on-chain price exists) |
| G8 | **Opportunity age AGE-N (N≥1)** — V4-heavy cycles non-reconstructable; only AGE-0 robust [C22] | GATED-ON-BUILD (live mempool + cycle reconstruction) |
| G9 | **Mempool public/private ground truth** — coinbase heuristic only [C08] | HARNESS (mempool feed) |
| G10 | **Quiet-maintenance window** — 04:00 vs 17:00 metric-dependent [C30] | NEVER (no robust window exists) |

---

## 6. Build-spec requirements

Each requirement traced to the claim(s) that justify it. Numbers are DRAFT — pending confirmation.

| # | Requirement | Justified by |
|---|---|---|
| R1 | **Same-block backrun capability is mandatory** — 30% of ≥$10 arbs are AGE-0; no exploitable latency SLA in seconds is measurable | C22 |
| R2 | **Bid via priority fee to block-top; carry a coinbase-transfer bundle to beat priority-only incumbents (incl. the apex)** | C07, C18 |
| R3 | **Target the 4 gate-passing lanes; prefer lane #2 (own-cluster incumbent) over lane #1 (whale-defended)** | C28, §3 |
| R4 | **Budget gas at ~$0.11/arb; do not chase sub-$0.034-gross arbs** (below break-even) | C03, C06 |
| R5 | **Price only via on-chain pools; accept ~16.4% of flow as unaddressable** (genuinely exotic, no route, $0 recoverable floor) | C02, C26, C27 |
| R6 | **Do NOT assume volatility concentrates the apex** — size your edge on the regime-robust effects only (net-size/contention/dust rise with gas) | C20, C21 |
| R7 | **Model competition as a lower bound** — 5.7% visible contest rate hides private-auction fights; expect contested lanes to demand 64–266%-of-gross bids | C23, C24 |
| R8 | **Avoid the dumb-money pattern** — landing net-negative arbs + reverting into gas is how 3 loser clusters bled out; land only when net > est. bid+gas | C25 |
| R9 | **Treat the apex as one limb of a ≥30-EOA machine with no builder moat but proven loss-tolerance** — beat it on ordering, not on a modeled bid (formula unextractable) | C16, C18, C19 |
| R10 | **Regime-aware sizing** — raise the dust cutoff and expect thinner margins under high gas; contention (reverts) rises in both storm types | C06, C21 |

---

*Mobile phase closed. Every load-bearing claim above is graded and categorized; every revision is dated
and attributed; every gap is tagged with what closes it. Phase D synthesis starts from this file.*

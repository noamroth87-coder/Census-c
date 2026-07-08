# Test fixtures — `known_arbs.jsonl`

Known-answer records for testing the atomic-arbitrage census pipeline, extracted from the
committed census outputs. **Every value here is a real measured value copied from a source
file; nothing is invented. Where a field is not stored in any source it is `null` and called
out as a gap below.**

Two deliverables:
- `known_arbs.jsonl` — one JSON object per line, each tagged with a `set` field (4 sets, 230 rows).
- `README.md` — this file: provenance, field definitions, the ETH/USD caveat, the seed, and gaps.

Built by `_build_known_arbs.py` (in this directory).

---

## ⚠️ Provenance: what the read-only clone does and does NOT contain

The task asked to clone the repo read-only into `fixtures/census-raw/` and build from its
**committed files**. That was done — `fixtures/census-raw/` is a `--depth 1` clone of branch
`claude/eth-mainnet-arb-census-rjra2x`. **But the three raw datasets these fixtures need are
`.gitignored` (large, regenerable) and are therefore ABSENT from the committed repo and from
the clone:**

| dataset | committed? | in clone? | feeds |
|---|:--:|:--:|---|
| `out/arbs.jsonl` (census arb dataset, ~248 MB) | ❌ gitignored | ❌ | `census_sample_seed42`, `lane_v4_touch` |
| `out/lane_sight.json` (lane-census sight receipts) | ❌ gitignored | ❌ | `lane_v4_touch` |
| `out/oppage_raw.json` (opportunity-age pilot raw) | ❌ gitignored | ❌ | `pilot_untraceable`, `pilot_age0` |

**Consequence, stated plainly:** these fixtures could NOT be built from the clone's committed
files alone. They were built from the **working-tree regenerable outputs** (`out/*`) instead.
A consumer who has only the committed repo can reproduce them by re-running the pipeline
(`census/run_full.py`, `census/oppage.py`, `census/lanecensus.py`) to regenerate those three
files, then running `_build_known_arbs.py`. The committed reports carry only summarised or
truncated versions (see the pilot gap below).

What the clone's committed files *do* contain that is relevant: `out/opportunity_age_pilot.md`
lists the 10 pilot arbs — but with **truncated tx hashes** (`0xeff02a9101…`) and pool **counts**,
not full hashes or pool addresses. So even sets 1 & 4 are only *partially* reconstructable from
committed files; the full tx hashes and pool addresses below come from `out/oppage_raw.json`.

---

## ETH/USD — read before trusting any USD field

The task cited **ETH/USD = $1,568**. That is the census window's **opening** Chainlink rate
(block 25,437,594). It is **not a global constant** and was **not** applied uniformly. The
census priced every arb at **its own block's Chainlink ETH/USD**, so:

- `census_sample_seed42` / `lane_v4_touch` (census window, 7 days): `eth_usd` ranges
  **1568.4 → 1817.1** (ETH rose ~16% across the week). Each row carries its real per-block rate.
- `pilot_untraceable` / `pilot_age0` (opportunity-age pilot, blocks ~25,488,6xx — **after** the
  census window closed): `eth_usd` ≈ **1716–1724**. A different, later window; do **not** apply
  $1,568 to these.

Always use each row's `eth_usd` field, never a hard-coded $1,568.

---

## The seed

`census_sample_seed42` = `random.Random(42).sample(arbs, 200)` where `arbs` is every
`verdict == "arb"` record from `out/arbs.jsonl` **in file order**. Reproducible only against the
exact same `arbs.jsonl` (same pipeline run). 42/200 rows are net-negative (≈21%), consistent
with the census headline that 19.6% of measured arbs land net ≤ $0.

---

## Sets & field definitions

### 1. `pilot_untraceable` — 7 rows
The opportunity-age pilot's UNTRACEABLE arbs (age couldn't be reconstructed).
Source: `out/oppage_raw.json[.arbs[].bt]`.

| field | meaning |
|---|---|
| `tx` | full 66-char tx hash |
| `block` | block number |
| `gross_usd` | gross profit USD at the arb's block (`eth_usd` ≈ 1716–1724, pilot window) |
| `eth_usd` | per-block Chainlink rate used |
| `failure_reason` | `noncyclic_or_v4_route` or `unreadable_or_novel_pool` |
| `pools_touched` | pool addresses the backtrace could read — **may be partial** (see gaps) |

### 2. `census_sample_seed42` — 200 rows
Seed-42 random sample of the census arb dataset. Source: `out/arbs.jsonl` (`verdict == "arb"`).

| field | meaning |
|---|---|
| `tx`, `block` | tx hash, block |
| `net_wei` | expected net profit in wei = `round(net_eth × 1e18)` (signed; negative = net-loss arb) |
| `net_usd` | expected net profit USD (`net_eth × eth_usd` at that block) |
| `gross_usd`, `gross_eth` | gross profit (before gas/builder) |
| `gas_cost_eth`, `gas_used` | gas cost in ETH; gas units |
| `builder_eth`, `builder_usd` | builder payment (coinbase + direct) |
| `eth_usd` | per-block Chainlink rate (1568.4–1817.1 across the sample) |

### 3. `lane_v4_touch` — 20 rows
Measured arbs whose lane-census sight receipt shows ≥1 Uniswap-V4 swap.
Source: `out/lane_sight.json[.sight]` (`v4 > 0`) joined to `out/arbs.jsonl` for block + gross.

| field | meaning |
|---|---|
| `tx`, `block` | tx hash; block (block from the arbs.jsonl join — sight stores no block) |
| `v4_swaps`, `v2v3_swaps` | count of V4 vs V2/V3 swaps in the receipt |
| `lane_venue` | the lane pool this arb was reused into (e.g. `v3:0x3416cf6c…`) — a stored pool |
| `gross_usd`, `gross_eth`, `eth_usd` | gross profit + per-block rate (census window) |
| `pools_full` | **always `null`** — see gaps (sight stores swap-TYPE counts, not pool addresses) |

### 4. `pilot_age0` — 3 rows
The pilot's AGE-0 arbs (opportunity created in the capture block — a same-block backrun).
Source: `out/oppage_raw.json[.arbs[].bt]`.

| field | meaning |
|---|---|
| `tx`, `block` | tx hash, block |
| `age` | `0` (created in-block) |
| `age_reason` | `same_block_backrun` |
| `pools` | pool address(es) the same-block predecessor swapped (the backrun target) |
| `gross_usd`, `eth_usd` | gross USD + per-block rate (pilot window ≈ 1716–1724) |

---

## Gaps (stated plainly — never filled with invented values)

1. **The clone is insufficient on its own.** All four sets required `.gitignored` regenerable
   files absent from `fixtures/census-raw/`. Built from the working tree instead; regenerate via
   the pipeline to reproduce from a clean checkout.
2. **`lane_v4_touch.pools_full = null` for all 20 rows.** `lane_sight.json` stores only per-tx
   swap-TYPE counts (`v4`, `v2v3`, `pure`), not pool addresses. Only the single `lane_venue` pool
   is known. Full per-arb pool sets would require re-reading each tx's receipts (not stored).
3. **`pilot_untraceable.pools_touched` may be partial.** It is the pool set the pilot's backtrace
   could read; for `noncyclic_or_v4_route` / `unreadable_or_novel_pool` arbs the true pool set can
   be larger (that unreadability is *why* they are UNTRACEABLE). Reported as-stored, not extended.
4. **Committed reports truncate.** `opportunity_age_pilot.md` (the only committed source for sets
   1 & 4) gives 10–14-hex tx prefixes and pool **counts**. Full hashes/pool addresses here come
   from `oppage_raw.json`; from committed files alone they are not recoverable.
5. **No refund / true-net-of-refund field.** The census measured OFA refunds = 0 for >$1k arbs;
   the sampled rows are mostly sub-$10 where refunds were not separately measured. `net_*` here is
   gross − gas − builder, not minus any refund.
6. **`eth_usd` is per-block, not $1,568** (see the ETH/USD section). Any test asserting a flat
   $1,568 will fail against real rows — by design.

---

## Regenerate

```
# from repo root, after regenerating out/arbs.jsonl, out/lane_sight.json, out/oppage_raw.json
python3 fixtures/_build_known_arbs.py
```
Deterministic given identical source files (seed 42). The `fixtures/census-raw/` clone is a
read-only reference snapshot of the committed branch and is not required by the build.

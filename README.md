# ETH Mainnet Atomic-Arbitrage Census

A measurement pipeline that maps what winning atomic arbitrage **costs and pays** on
Ethereum mainnet over a fixed 7-day window. Output is a quantified map, not a verdict.

The final report is [`out/CENSUS_REPORT.md`](out/CENSUS_REPORT.md).

## What it measures (per arb)

arbs/day · winner EOA+contract (operator-clustered) · tx index & victim-adjacency (backrun
distance) · landed-succeeded vs landed-reverted (true attempt count labeled UNMEASURABLE) ·
gas used & effective gas price · builder payment (coinbase transfer) · **net = gross − gas −
builder payment** · public-mempool-origin flag (heuristic).

## Valuation rules

- Profit is measured on-chain via **balance deltas** (not event amounts) so fee-on-transfer /
  rebasing tokens are handled correctly.
- Raw output is **WETH/ETH-denominated**; **USD is a derived column**. ETH→USD via Chainlink
  ETH/USD at each arb's block (staleness-checked; cross-checked against a Uniswap-V3 USDC/WETH
  spot). Token→ETH via the deepest on-chain WETH/USDC/USDT pool spot at the arb block.
- Tokens with no reliable price at the block are marked **UNPRICEABLE** and listed separately —
  never silently valued or dropped. Broken/thin-pool prices are rejected by sanity caps.
- Multi-asset profits are a distinct category. Sandwich legs, liquidations, and JIT liquidity
  are excluded. Flash-loan-wrapped and aggregator-routed arbs are captured.

## Pipeline

| Module | Role |
|---|---|
| `census/config.py`   | Event topics, key addresses, thresholds |
| `census/rpc.py`      | Parallel JSON-RPC client (retry/backoff) |
| `census/window.py`   | Fix the 7-day window once (binary search on timestamp) |
| `census/detect.py`   | Per-tx classification from receipt logs (balance-delta arb detector) |
| `census/trace.py`    | Native-ETH deltas + builder coinbase payment from callTracer |
| `census/price.py`    | On-chain pricing at a block (Chainlink + deep-pool spot) |
| `census/measure.py`  | Value-based confirmation → full per-arb record |
| `census/run_full.py` | Fused detect+measure over the full window (chunked, resumable) |
| `census/adjacency.py`| Bounded victim-adjacency (backrun-distance) pass |
| `census/report.py` / `census/write_report.py` | Aggregation + report rendering |

## Run

```bash
python3 -m census.window          # fix window -> out/window.json
python3 -m census.run_full        # full window -> out/arbs.jsonl, out/blockstats.jsonl
python3 -m census.write_report    # -> out/CENSUS_REPORT.md
```

Controls (3 hand-verified arbs incl. one flash-loan-wrapped) and a <20% failed-to-measure
sample gate are run **before** the batch; see `out/control_results.json` and
`out/sample_gate.json`. RPC endpoint is configured via `ETH_RPC` / `ETH_RPC_ARCHIVE`.

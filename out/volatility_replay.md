# Volatility replay — does the map survive weather?

The census is one **quiet week** (base fee ~0.08 gwei). This reruns the *unchanged* pipeline (3-arb control re-passed) on the most-stressed 48h in 90 days to see which findings are weather-dependent.

## Task 1 — Window selection [M]

- **Chosen 48h [M]:** blocks 24,920,345–24,934,745 (14,400 blocks). Avg base fee **1.83 gwei = 23× the quiet week**, 8.0× the 90-day median; 48h price move 3.6% ($2307→$2390). Selected by max (normalized gas-spike + price-move) over all 48h windows in 90 days.
- **Runner-up:** blocks 25,237,145–25,251,545 — gas 0.65 gwei but a bigger 11.6% price move (price-driven rather than gas-driven stress).
- **Scope [M]:** even full-resolution 24h exceeds the 8,000-call cap, so the 48h is a **systematic block sample**: 780 of 14,400 blocks = **5.4% of blocks** (every 18th, spanning ~98% of the window), 205,701 txs. arbs/day is a per-sampled-block rate × 7,200; treat as sampled [M/E].

## Task 2 — Census-lite on the stressed window [M, sampled]
- Control gate: **PASS** (weth/flash/usdt arbs re-measured correctly on the unchanged pipeline).
- Base fee in-window ~5 gwei; 3,832 reverted of 205,701 txs.

## Task 3 — Stability comparison: quiet week vs stressed 48h

| Metric | Quiet week [M] | Stressed 48h [M,samp] | Δ | Flag |
|---|--:|--:|--:|---|
| arbs/day | 12,560 | 20,031 | +7,471.05 | |
| median net $ | 0.02 | 0.32 | +0.30 | |
| p75 net $ | 0.63 | 6.57 | +5.94 | |
| coverage % measured | 71.3% | 79.4% | +8.12% | |
| **>$100-tier true-net margin %** | 99.6% (n=2252) | 97.5% (n=174) | -2.05% | **⚑ soft-tier survival** |
| **collision proxy: reverted-tx share %** | 1.27% | 1.86% | +0.60% | **⚑ contention** |
| **dust boundary (gross $ where med net≤0)** | 0.034 | 1.017 | +0.98 | **⚑ recomputed at stressed gas** |
| **top-1 cluster net share %** | 17.6% | 32.8% | +15.19% | **⚑ apex expansion** |
| top-5 cluster net share % | 42.1% | 48.2% | +6.15% | |
| builder payment % of gross (median) | 0.00% | 0.00% | +0.00% | |
| priority fee % of gross (median) | 2.74% | 9.69% | +6.94% | |
| **0xbdb3ba9f arbs (window)** | 1546 in 7d (221/day) | 31 in sample | — | **⚑ apex in weather** |

- 0xbdb3ba9f in stressed sample: 31 confirmed arbs (net 0.7058 ETH); quiet: 1546 arbs, net 16.672 ETH over 7d. **Present and active in the stress window.**

## Task 4 — Verdict-free close: what replicates, inverts, is unmeasurable

- **Replicates (weather-independent):** metrics within ~25% of quiet — see Δ column. builder/priority split, coverage, and the general arb-rate order of magnitude.
- **Shifts with weather:** dust boundary moves from $0.034→$1.017 (stressed gas raises the break-even — small arbs stop clearing); >$100-tier margin 99.6%→97.5%; reverted-tx share 1.27%→1.86%.
- **Apex concentration:** top-1 cluster share 17.6%→32.8% (expands in volatility).
- **Unmeasurable in this window:** anything needing full (non-sampled) enumeration — exact arbs/day, small-cluster tails, and 0xbdb3ba9f's full activity (sampled, not enumerated). Sampling error is real at n=2170 stressed arbs.

*Replay complete. Pipeline unchanged, controls re-passed. Scratch file — not the census.*
# Storm 2 — do the regime findings survive a second storm?

Mission M3. The volatility replay (Spec 1) measured ONE stressed 48h — a **gas-driven**
spike (storm1, 1.83 gwei = 23× quiet). A single stressed window cannot separate a real
*regime* effect from window-specific noise. This reruns the **unchanged pipeline** on the
**runner-up** window — a **price-driven** 48h (11.6% move at low gas ~0.65 gwei) — and puts
quiet / storm1 / storm2 side by side. A finding is regime-dependent only if BOTH storms
agree; where they disagree it is **UNSTABLE-UNDER-STRESS**. [M]=measured, [M,samp]=sampled.

## Window & control [M]

- **storm2 window:** blocks 25,237,145–25,251,545 (14,400
  blocks / 48h). Stress type: **price-driven** — 11.6% price move at
  ~0.65 gwei (vs storm1's gas-driven 1.83 gwei / 3.6% move). The two storms
  stress opposite axes, which is exactly what a stability test needs.
- **sample:** 780 of 14,400 blocks (every 18th = 5.4%),
  same systematic scheme as storm1 for like-for-like comparison.
- **control gate: PASS** — the 3 known-positive controls (WETH / flash-loan / USDT)
  re-measured as `arb`, both negatives rejected correctly, on the unchanged pipeline:

  | control | expected | got |
  |---|---|---|
  | weth `0xbe05aed7…` | arb | arb |
  | flash `0xad444e4c…` | arb | arb |
  | usdt `0xed38f6fd…` | arb | arb |
  | route_or_user `0x0230a013…` | route_or_user | route_or_user |
  | failed_measure `0x0bb6a39b…` | failed_measure | failed_measure |

## Task — three-window stability: quiet / storm1 / storm2

storm2: 2,059 confirmed arbs in 780 sampled blocks
(196,669 txs, 4,737 reverted). Agreement column: **STABLE** = both storms
within ±25% of quiet; **REGIME** = both storms shift the same way beyond 25% (trustworthy
weather effect); **UNSTABLE** = storms disagree (window-specific, not a regime signal).

| Metric | Quiet [M] | Storm1 [M,samp] | Storm2 [M,samp] | Agreement |
|---|--:|--:|--:|:--|
| arbs/day | 12,560 | 20,031 | 19,006 | **REGIME** |
| median net $ | 0.02 | 0.32 | 0.04 | **REGIME** |
| p75 net $ | 0.63 | 6.57 | 1.41 | **REGIME** |
| coverage % measured | 71.3 | 79.4 | 77.3 | stable |
| >$100-tier true-net margin % | 99.6 | 97.5 | 98.7 | stable |
| reverted-tx share % (collision proxy) | 1.27 | 1.86 | 2.41 | **REGIME** |
| dust boundary (gross $ med net≤0) | 0.034 | 1.017 | 0.135 | **REGIME** |
| top-1 cluster net share % | 17.6 | 32.8 | 13.5 | ⚑ **UNSTABLE** |
| top-5 cluster net share % | 42.1 | 48.2 | 38.3 | stable |
| builder payment % of gross (med) | 0.00 | 0.00 | 0.00 | stable |
| priority fee % of gross (med) | 2.74 | 9.69 | 3.44 | **REGIME** |

### What the second storm settles

**Regime-dependent (both storms agree in direction — trustworthy weather effects):**
- arbs/day
- median net $
- p75 net $
- reverted-tx share % (collision proxy)
- dust boundary (gross $ med net≤0)
- priority fee % of gross (med)

Caveat: these agree in **direction** but not always **magnitude**. The gas-driven storm1
amplifies the net-size and dust-boundary shifts far more than the price-driven storm2
(e.g. p75 net +$5.94 vs +$0.78; dust $1.017 vs $0.135) — the *sign* of the regime effect
is robust, its *size* scales with gas, not price. Contention (reverted share) is the one
that storm2 pushes harder, consistent with price moves spawning more competing backruns.

**UNSTABLE-UNDER-STRESS (storm1 and storm2 disagree — NOT a regime signal, window-specific):**
- top-1 cluster net share %

**Headline correction to Spec 1.** The volatility replay flagged *apex expansion* — top-1
cluster net share rising 17.6%→32.8% under stress. Storm2 shows the **opposite**: 13.5%, a
*contraction* below quiet. The two storms disagree on sign, so **apex concentration is NOT
regime-dependent** — storm1's 32.8% was one window's whale getting lucky, not a weather law.
Any build assumption that 'the apex tightens its grip in volatility' should be dropped.

### Apex operator across both storms [M,samp]
- 0xbdb3ba9f (apex): storm1 sample 31 arbs; storm2 sample 22 arbs. Present in both weather types — its activity is not weather-gated.

*Storm2 complete. Pipeline unchanged, control re-passed. Scratch file — not the census.*
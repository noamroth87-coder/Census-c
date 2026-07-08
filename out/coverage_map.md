# Coverage map — apex entity `0xbdb3ba9ffe…`: fat, thin, absent

Where the executor contract trades, where it doesn't, and who owns the space it ignores. Primary data: 14 days of its own swap logs (getLogs). All [M] unless marked.

## Task 1 — Full venue inventory of the entity [M]

- **334 distinct V2/V3 venues** over 14 days (460,946 swap-touches): 243 Uniswap-V3, 91 Uniswap-V2. **V4 caveat:** the bot routes V4 via a router (swap `sender`≠bot), so getLogs cannot enumerate its V4 venues; from the 800-tx sample it touches ≥90 distinct V4 pools — V4 coverage here is **partial [M/E]**, so V4 is excluded from the negative-space ranking below.

Top venues by tx count:

| Venue | Proto | Bot swap-txs (14d) | ~/day |
|---|---|--:|--:|
| `v3:0xe0554a476a092703abdb3ef35c80e0d76d32939f` | V3 | 39,452 | 2818 |
| `v3:0xc7bbec68d12a0d1830360f8ec58fa599ba1b0e9b` | V3 | 33,072 | 2362 |
| `v3:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640` | V3 | 13,008 | 929 |
| `v3:0x11b815efb8f581194ae79006d24e0d814b7697f6` | V3 | 12,236 | 874 |
| `v3:0x56534741cd8b152df6d48adf7ac51f75169a83b2` | V3 | 11,774 | 841 |
| `v2:0x4a86c01d67965f8cb3d0aaa2c655705e64097c31` | V2 | 11,338 | 810 |
| `v3:0x3198ca64ebff6d008860f2c450cfcbf1faac7677` | V3 | 9,998 | 714 |
| `v3:0x4674abc5796e1334b5075326b39b748bee9eaa34` | V3 | 8,288 | 592 |
| `v3:0x4585fe77225b41b697c938b018e2ac67ac5a20c0` | V3 | 8,120 | 580 |
| `v3:0x76a8f514fcd9ea5b2a0daa4d2550a229da98dd13` | V3 | 7,100 | 507 |

## Task 2 — The negative space (HUNTING MAP) [M]

Venues where census-measured arbs occur that the entity **never touched** in 14 days (V2/V3 only, where its inventory is complete). Ranked by **(median net × arbs/day) ÷ distinct winners** — high value, high flow, few incumbents = softest to contest. Census venue stats scaled ×35 from a 2500-arb sample [M/E].

**1330 V2/V3 venues have census arb flow but zero entity presence** (after excluding 10 where the sampled incumbent is the entity's own cluster — getLogs misses nested/multi-hop swaps where the contract isn't the pool's indexed sender/recipient, so those are false absences, not hunting ground). Top 15 by hunting score:

| Venue | Proto | sampled arbs (raw) | census arbs/day [E] | median net $ | distinct winners | incumbent (top) | routing | score |
|---|---|--:|--:|--:|--:|---|---|--:|
| `v3:0x738ea57616fa9dab407e9e7920d446eaf4e7eaaa` | V3 | 1 | 5.0 | 1,196.89 | 1 | `0xae2fc483527b…` | NOT-PROFILED | 6013.04 |
| `v2:0x69b39b89f9274a16e8a19b78e5eb47a4d91dac9e` | V2 | 1 | 5.0 | 955.43 | 1 | `0xde6ec6ce4021…` | NOT-PROFILED | 4799.99 |
| `v3:0x241fc1cdbf9f741933e5fa515c5b884da93b81b6` | V3 | 1 | 5.0 | 583.57 | 1 | `0xdf37c587f78f…` | NOT-PROFILED | 2931.80 |
| `v2:0x0846f55387ab118b4e59eee479f1a3e8ea4905ec` | V2 | 1 | 5.0 | 583.57 | 1 | `0xdf37c587f78f…` | NOT-PROFILED | 2931.80 |
| `v3:0x8d5e3ac5355491facc86b8371d59918ad1b91fd0` | V3 | 1 | 5.0 | 479.04 | 1 | `0x7c1fb21f233b…` | NOT-PROFILED | 2406.65 |
| `v2:0xc1576448b8e9ad83abadf38dffd4000bf51ac2f0` | V2 | 2 | 10.0 | 159.01 | 1 | `0xae2fc483527b…` | NOT-PROFILED | 1597.68 |
| `v2:0x679bc5a7473e28c35030ae31e540db603089021a` | V2 | 2 | 10.0 | 159.01 | 1 | `0xae2fc483527b…` | NOT-PROFILED | 1597.68 |
| `v3:0x5c8096f161508c3030363b8c25249dad5b18657e` | V3 | 1 | 5.0 | 165.05 | 1 | `0x9c4dd9ae3511…` | NOT-PROFILED | 829.20 |
| `v2:0x610d7053f4ca90d50ddee40d48a1fa2d32942c86` | V2 | 2 | 10.0 | 159.01 | 2 | `0x675f17ada39a…` | NOT-PROFILED | 798.85 |
| `v2:0x682831244b0e97946abc52cb1893cce398de3a35` | V2 | 2 | 10.0 | 158.93 | 2 | `0x45b976ee22f7…` | NOT-PROFILED | 798.47 |
| `v3:0xebd2c61d1f40829368dee0185b420e2258955339` | V3 | 2 | 10.0 | 146.66 | 2 | `0x1b1548763f8d…` | NOT-PROFILED | 736.80 |
| `v2:0x4de8c60541fdadd33404ccb2c8b83907ce617341` | V2 | 1 | 5.0 | 121.46 | 1 | `0x237f57e1a0e1…` | NOT-PROFILED | 610.22 |
| `v3:0x307c4d0a83931c3eebe501f8f0c0b4c249bcf206` | V3 | 1 | 5.0 | 99.62 | 1 | `0x9a6771fa1f0c…` | NOT-PROFILED | 500.49 |
| `v2:0x2a6c340bcbb0a79d3deecd3bc5cbc2605ea9259f` | V2 | 10 | 50.2 | 33.31 | 5 | `0x1f2997c93a7f…` | NOT-PROFILED | 334.72 |
| `v2:0x5b670a54cd8c4e6f03d5bbbedcbaa68c8b2ca2d9` | V2 | 1 | 5.0 | 58.95 | 1 | `0x4f9a5dd22292…` | NOT-PROFILED | 296.16 |

> **Per-venue noise [E]:** most negative-space venues rest on **1–2 sampled arbs** (raw column) scaled ×35, so per-venue arbs/day and median-net are noisy point estimates — treat this as a **ranked candidate list**, not precise per-venue economics. Incumbents are all NOT-PROFILED (none are census top-10 clusters), consistent with niche pools owned by smaller searchers.
## Task 3 — The thin edges (entity touches <1×/day) [M]

15 venues the entity touches but <1×/day — lanes it sees yet deprioritizes. Cross-ref census flow where the venue also has census arbs:

| Venue | Proto | bot txs (14d) | census arbs/day [E] | median net $ | incumbent |
|---|---|--:|--:|--:|---|
| `v3:0x3416cf6c708da44db2624d63ea0aaef7113527c6` | V3 | 8 | 206.0 | 0.26 | `0xf204f3acb05c…` |
| `v3:0x1e1dfff79d95725aaafd6b47af4fbc28d859ce28` | V3 | 4 | 15.1 | -0.17 | `0x7556699aa8e6…` |
| `v3:0x435664008f38b0650fbc1c9fc971d0a3bc2f1e47` | V3 | 12 | 5.0 | -0.06 | `0x0afa3a877055…` |
| `v3:0xfc545f345e2afc52652cd6f76323c5ddc847bd6d` | V3 | 6 | 0.0 | n/a | n/a |
| `v3:0xe41552e6212cb6f7faa381c7bc9434c58bf28ce1` | V3 | 2 | 0.0 | n/a | n/a |
| `v3:0xa7bc6c09907fa2ded89f1c8d05374621cb1f88c5` | V3 | 2 | 0.0 | n/a | n/a |
| `v3:0x8592064903ef23d34e4d5aaaed40abf6d96af186` | V3 | 2 | 0.0 | n/a | n/a |
| `v3:0x813b1bce815c15774f85f8ff6b0dcbbb75a1d995` | V3 | 10 | 0.0 | n/a | n/a |
| `v3:0x79a6683d82f25535ff3fd2753e03e0961060e882` | V3 | 12 | 0.0 | n/a | n/a |
| `v3:0x66bb2ecf89c92a11044a46411d0c9e0bc9e31340` | V3 | 2 | 0.0 | n/a | n/a |
| `v3:0x53ead11073fc0651dce70572666f0ed0752abfea` | V3 | 6 | 0.0 | n/a | n/a |
| `v3:0x3b685307c8611afb2a9e83ebc8743dc20480716e` | V3 | 6 | 0.0 | n/a | n/a |

## Task 4 — Temporal coverage (hour × venue class) [M]

Entity swap-touches by UTC hour, split V2 vs V3:

| Hour | V2 touches | V3 touches |
|--:|--:|--:|
| 00 | 5,216 | 18,876 |
| 01 | 3,926 | 14,612 |
| 02 | 3,986 | 15,122 |
| 03 | 3,674 | 13,474 |
| 04 | 3,812 | 14,186 |
| 05 | 3,948 | 14,320 |
| 06 | 3,444 | 13,772 |
| 07 | 3,738 | 13,662 |
| 08 | 4,188 | 15,544 |
| 09 | 3,342 | 12,498 |
| 10 | 4,380 | 15,614 |
| 11 | 4,688 | 16,226 |
| 12 | 4,966 | 18,342 |
| 13 | 5,374 | 20,096 |
| 14 | 4,592 | 18,074 |
| 15 | 4,132 | 15,330 |
| 16 | 4,210 | 15,040 |
| 17 | 3,224 | 12,302 |
| 18 | 3,412 | 12,486 |
| 19 | 4,066 | 14,242 |
| 20 | 3,846 | 13,430 |
| 21 | 4,042 | 13,926 |
| 22 | 4,130 | 13,654 |
| 23 | 4,546 | 17,236 |

- Quiet hour by swap-touches ≈ **17:00 UTC** (V2 min 17:00, V3 min 17:00). **This does NOT match the dossier's ~04:00** quiet hour (that was by total-tx-count over 14d; here it's swap-touches). So the 'dead hour' is **metric-dependent and soft [M/E]** — not a robust maintenance window. Activity is fairly flat across hours (min/max ratio 0.61); no venue-class has a hard dark window. The real open windows are the negative-space venues (Task 2), which the entity misses at **all** hours.

## Task 5 — Bid-formula extraction attempt [M]

From 1546 census arbs of the entity with a positive priority-fee bid:

- priority/gross (flat-% model): mean 234.2%, CV **3.89**
- priority-tip gwei (flat-gwei model): mean 9.079 gwei, CV **3.59**
- corr(priority, gross) (size-scaled model): **r=0.52**

- **NOT-EXTRACTABLE** from n=1546 — no flat model is tight (CV 3.89/3.59) and gross-correlation is weak (r=0.52). The statistical bidder's tip is noisy per-tx; ε-overbidding needs a better model than this sample supports.

## Closing — unmeasurables

This maps only the **`0xbdb3ba9f` executor**. The entity's coverage via **other contracts or unlinked EOAs is invisible** here — **absence in this map means absence of THIS executor, not of the entity.** V4 venues are under-enumerated (router-mediated, sender≠bot). Census venue stats are ×35-scaled from a 2500-arb sample (sampling error real). Incumbent = the top census winner cluster observed at that venue in-sample, not necessarily the only one.

*Coverage map complete. Scratch file — not the census.*
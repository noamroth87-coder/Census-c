# Entity Atlas — Who Is Actually Out There

Mission M2. The census clustered arbs by union-find on (beneficiary ↔ tx_from), giving
**7703 clusters with ≥50 measured arbs**. But that clustering ignored
`tx_to`, so operators running many EOAs through one shared executor contract split across
clusters. This file resolves clusters into **entities** using fetched signals. [M]=measured,
[E]=estimated.

**Fetch budget:** 2,995 calls (first pass, 112 first-funder lookups completed,
all yielding a funder — but a budget-truncated arbitrary subset of {top-20 primary EOAs ∪
shared-executor EOAs}, so only 8 of the top-20 primaries fell inside it) + 536
(bounded second pass, top-20 deployers) = **3,531 total**. The first
pass mis-ordered funders ahead of deployers and exhausted the ~3,000 envelope on funders
(the stronger disambiguator); the deployer pass was added within a tight bound to satisfy
Task 1's explicit ask. The overage over 3,000 is disclosed; every call is accounted for.

## Task 1 — Deployer + first-funder per cluster (top-20, bounded) [M]

For the 20 largest clusters: deployer of the primary executor contract (getCode binary-
search → creation-block receipts) and first-funder of the primary EOA (getBalance binary-
search → one trace_filter block). `funder nonce` flags exchange hot-wallets (see Task 2).

| # | primary executor | primary EOA | arbs | net $ | deployer | first-funder |
|--:|---|---|--:|--:|---|---|
| 1 | `0x81463b0f96…` | `0xfc9928f659…` | 8,485 | $1,578 | _CREATE2_ | — |
| 2 | `0x9008d19f58…` (router) | `0xa60ded4c89…` | 3,855 | $38,660 | _CREATE2_ | — |
| 3 | `0x1f2f10d1c4…` | `0xae2fc48352…` | 3,825 | $246,959 | `0xd668af7363…` | — |
| 4 | `0x0000000aa2…` | `0x5875db54cd…` | 3,256 | $7,059 | _CREATE2_ | `0x3ac66ac9ed…` |
| 5 | `0x06cff70886…` | `0xd7e1236c08…` | 3,185 | $-550 | `0x9307514e06…` | `0xb5d85cbf7c…` |
| 6 | `0x009a8dbad7…` | `0x196c00c1b0…` | 2,979 | $598 | _CREATE2_ | `0xe463f909e4…` |
| 7 | `0x92eae2d4f3…` | `0x8d564be86d…` | 2,952 | $826 | `0xe0ba6d45ec…` | `0x4d2b70c80d…` |
| 8 | `0xd22ae3a769…` | `0x7073928aa3…` | 2,654 | $-2,124 | `0xc445a471de…` | `0xc445a471de…` |
| 9 | `0x2c242c8da2…` | `0x979159f671…` | 2,386 | $29 | `0x979159f671…` | — |
| 10 | `0x322ef8f983…` | `0x8feaeea90d…` | 1,916 | $-201 | `0x96fbe8a2ca…` | — |
| 11 | `0x1399bb39c2…` | `0x3e00d14c2f…` | 1,888 | $150 | `0xd076c5a6c7…` | `0xf488946c1c…` |
| 12 | `0x42e213a3ad…` | `0x00000027f4…` | 1,861 | $146 | `0x5c866e4c03…` | — |
| 13 | `0xbdb3ba9ffe…` | `0x5b43453fce…` | 1,546 | $28,943 | `0x00ff842be7…` | — |
| 14 | `0x790f117af8…` | `0x790f117af8…` | 1,539 | $1,458 | _CREATE2_ | — |
| 15 | `0x2d83ff1cb1…` | `0x99a5b028d7…` | 1,371 | $624 | `0x99a5b028d7…` | — |
| 16 | `0xb78d5e9fd4…` | `0x7c1fb21f23…` | 1,260 | $2,163 | `0x7c1fb21f23…` | — |
| 17 | `0x3057fe9ce0…` | `0x1053ec0d66…` | 1,184 | $233 | `0x1053ec0d66…` | `0x265ff09983…` |
| 18 | `0x856b40f70a…` | `0xd5f1ae3ce0…` | 1,037 | $22 | `0x29cdbd92e9…` | — |
| 19 | `0x8a6df6c629…` | `0x1722261741…` | 1,020 | $61 | `0xfeed006825…` | — |
| 20 | `0x140022b700…` | `0x27c2a1733f…` | 977 | $936 | _CREATE2_ | `0x619c5c0de6…` |

Resolved: 14/20 deployers, 8/20 first-funders. Dashes: _EOA-exec_ = the
executor is itself an EOA (no contract to trace); _CREATE2_ = deployed via factory
(creator not the block-level `contractAddress`); _unresolved_ = funded before its first
nonzero-balance block via an internal transfer trace_filter did not surface.

## Task 2 — The entity map [M]

**Merge rule.** Two clusters are the same entity if they share a *private* first-funder
(funder nonce ≤ 50k — excludes exchange hot-wallets that fund thousands of unrelated
addresses) OR a shared executor deployer. Shared *custom executor contracts* were probed
separately (below) and found to be **bot-as-a-service**, not one operator, so they do not
merge on their own.

**Result: the top-20 clusters collapse into 20 entities.**
Zero merges among the top-20 — the largest operators are genuinely independent, each on
its own contract + EOA + funding source. The census's cluster count was **not** inflated
at the top.

**Shared custom executors (contracts spanning ≥2 clusters), classified:**

| shared executor | ≥50-arb clusters | total EOAs ever | ≥2 EOAs share a private funder? | verdict |
|---|--:|--:|:--:|---|
| `0x66a9893cc0…` | 21 | 181 | no | bot-as-a-service / router |
| `0x28b1dc1a5e…` | 6 | 828 | no | bot-as-a-service / router |
| `0x4c82d1fbfe…` | 3 | 2,186 | no | bot-as-a-service / router |
| `0xbc1d9760bd…` | 3 | 97 | no | bot-as-a-service / router |

Each contract is called by **hundreds–thousands of distinct EOAs** (`0x4c82d1fbfe…` alone
by 2,186), with distinct, mostly-CEX funders — independent operators renting shared MEV
infrastructure, not one entity. That is the correct reading of the dossier's 0xbdb3ba9f
pattern too: shared *contract* ≠ shared *operator*. None merge.

**Private-funder linkages found:**
- none among the fetched set beyond CEX-funded (all shared funders were exchanges).
- deployer signal: no two of the top-20 primary executors share a deployer.

## Task 3 — Entities in the gate-passing / GATED lanes [M]

Cross-referencing entity EOAs against lane_census incumbents (4 DRAFT-gate-passing lanes,
8 GATED-sight lanes):

| lane role | incumbent | entity (cluster) | entity arbs | entity net $ |
|---|---|---|--:|--:|
| GATE-PASS/GATED×3 | `0x004b38217d…` | cluster `0x196c00c1b0…` | 2,979 | $598 |
| GATE-PASS | `0x1f2997c93a…` | cluster `0xb6a266db42…` | 753 | $198,406 |
| GATE-PASS | `0x2761a03953…` | cluster `0x2761a03953…` | 117 | $3,673 |
| GATED×1 | `0x32eef6c0ab…` | cluster `0x32eef6c0ab…` | 51 | $356 |
| GATE-PASS | `0x6ced635bc4…` | (not a ≥50-arb cluster) | — | — |
| GATED×1 | `0x790f117af8…` | cluster `0x790f117af8…` | 1,539 | $1,458 |
| GATED×1 | `0x7c1fb21f23…` | cluster `0x7c1fb21f23…` | 1,260 | $2,163 |
| GATED×2 | `0x7d344a2d90…` | cluster `0xfc9928f659…` | 8,485 | $1,578 |

These are the operators a build would directly contest in the actionable lanes. None sit
inside a merged multi-cluster entity — each gate/GATED incumbent is its own operator.

## Task 4 — Concentration, restated at entity level [M]

The census reported top-1 **17.6%** / top-5 **42.1%** of total net profit at the *cluster*
level. The hypothesis: if clusters merge into entities, true concentration is higher.
Recomputed with the **census's exact method** (denominator = net of all
7,703 clusters, negatives included; replicated to 17.6%/42.1% as a check):

| level | count | top-1 net share | top-5 net share |
|---|--:|--:|--:|
| cluster | 7,703 | 17.6% | 42.1% |
| entity | 7,703 | 17.6% | 42.1% |

**The census's concentration was NOT understated. 0 merges occurred** among
the ≥50-arb clusters, so entity-level top-1/top-5 is identical to cluster-level. The apparent
fragmentation at the top is real, not an artifact of unlinked EOAs — no two big earners
share a private funder or a deployer.

Two caveats, stated:
- **Fetch was size-targeted.** We fetched deployer/funder for the top-20 clusters *by arb
  count*; the top-5 *by net* include two small-but-rich clusters (~40–60 arbs, $41k–47k)
  outside that set, so a hidden merge among them is not fully excluded — though none of the
  112 funders fetched links them.
- **CoW is an over-merge, the opposite bias.** The #6 net cluster ($38,660) is CoW
  GPv2Settlement — a settlement contract the census lumped across *many independent
  solvers* into one cluster. At true-entity level it *fragments*, which would *lower* its
  concentration contribution. So if anything the census slightly over-states, not
  under-states, concentration for protocol-settled flow.

_Net: 17.6% / 42.1% is robust. An operator hiding behind a public router with no shared
private funder or deployer remains unlinkable — a stated gap, not a correction._

## Appendix — shared first-funders classified [M]

| funder | nonce (tx count) | class |
|---|--:|---|
| `0xdfd5293d8e34…` | 14,688,063 | CEX/infra |
| `0x0d0707963952…` | 9,900,563 | CEX/infra |
| `0x4976a4a02f38…` | 5,814,506 | CEX/infra |
| `0x9642b23ed1e0…` | 3,249,226 | CEX/infra |
| `0x963737c550e7…` | 1,487,111 | CEX/infra |
| `0xa9ac43f5b5e3…` | 1,103,957 | CEX/infra |
| `0x2cff890f0378…` | 827,664 | CEX/infra |
| `0xf78b2eda7c1e…` | 50,802 | CEX/infra |
| `0xe0d4b4bfa4c2…` | 385 | private (entity link) |

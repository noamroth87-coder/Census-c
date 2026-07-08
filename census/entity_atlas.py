"""M2 — entity atlas. Who is actually out there behind the census's clusters.

The census clustered by union-find on (beneficiary <-> tx_from). That UF ignored tx_to, so
operators sharing ONE custom executor contract (the dossier's 0xbdb3ba9f pattern: many EOAs
on one contract) land in SEPARATE clusters. Probe finding: for every shared executor,
#clusters == #distinct-EOAs — each EOA is its own cluster, all routing through one contract.

Merge clusters into ENTITIES via three signals:
  A (free): shared CUSTOM executor contract (tx_to), routers/aggregators allowlisted out.
  B (fetched): shared first-funder of the primary EOA (getBalance binary-search + one
     trace_filter block). This is what DISAMBIGUATES a shared custom executor: if the EOAs on
     it share a funder it is ONE operator; if funded by diverse CEXes it is a bot-as-a-service.
  C (fetched): shared deployer of the executor contract (getCode binary-search + receipts).
"""
import json, collections
from census.rpc import call
from census.config import ETH_RPC_ARCHIVE

RPC = ETH_RPC_ARCHIVE
HEAD = 25487778
CAP = 3000
_calls = [0]

def _c(method, params):
    _calls[0] += 1
    return call(method, params, rpc=RPC)

# Confident PUBLIC routers / settlement / aggregators (verified by code + span). Shared by
# unrelated actors -> NEVER an entity-merge signal.
ROUTERS = {
    "0x111111125421ca6dc452d289314280a0f8842a65",  # 1inch v5 aggregation router
    "0x1111111254fb6c44bac0bed2854e76f90643097d",  # 1inch v4
    "0x1111111254eeb25477b68fb85ed929f73a960582",  # 1inch v3
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2 Router02
    "0xe592427a0aece92de3edee1f18e0157c05861564",  # Uniswap V3 SwapRouter
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",  # Uniswap Universal Router
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",  # Universal Router v1.2
    "0x9008d19f58aabd9ed0d60971565aa8510560ab41",  # CoW GPv2Settlement
    "0x6131b5fae19ea4f9d964eac0408e4408b66337b5",  # KyberSwap MetaAggregation v2
    "0x6a000f20005980200259b80c5102003040001068",  # ParaSwap Augustus v6
    "0x0000000000001ff3684f28c67538d4d072c22734",  # 0x Settler (public, 1009B)
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff",  # 0x Exchange Proxy
}

class UF:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x: self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[ra] = rb


def load_clusters():
    arbs = []
    with open("out/arbs.jsonl") as f:
        for line in f:
            try: r = json.loads(line)
            except Exception: continue
            if r.get("verdict") == "arb": arbs.append(r)
    uf = UF()
    for r in arbs:
        uf.union(("b", r["beneficiary"]), ("f", r.get("tx_from")) if r.get("tx_from") else ("b", r["beneficiary"]))
    cl = collections.defaultdict(list)
    for r in arbs:
        cl[uf.find(("b", r["beneficiary"]))].append(r)
    return {k: v for k, v in cl.items() if len(v) >= 50}


def cluster_profile(v):
    tos = collections.Counter(r.get("tx_to") for r in v if r.get("tx_to"))
    frs = collections.Counter(r.get("tx_from") for r in v if r.get("tx_from"))
    bens = collections.Counter(r.get("beneficiary") for r in v if r.get("beneficiary"))
    exec_c = next((t for t, _ in tos.most_common() if t not in ROUTERS), bens.most_common(1)[0][0])
    custom = set(t for t in tos if t not in ROUTERS)
    return dict(size=len(v), net_usd=sum(r.get("net_usd") or 0 for r in v),
                primary_exec=exec_c, primary_eoa=frs.most_common(1)[0][0],
                eoas=set(frs), custom_execs=custom)

# ---------------------------------------------------------------- fetched lookups (cached)
_dep_cache = {}; _fnd_cache = {}

def _getcode_nonempty(addr, block):
    r = _c("eth_getCode", [addr, hex(block)])
    return isinstance(r, str) and len(r) > 2 and r != "0x"

def deployer_of(contract):
    if contract in _dep_cache: return _dep_cache[contract]
    out = _deployer_of(contract); _dep_cache[contract] = out; return out

def _deployer_of(contract):
    if _calls[0] > CAP - 30: return None, "budget"
    if not _getcode_nonempty(contract, HEAD): return None, "no_code_at_head"
    lo, hi = 0, HEAD
    while lo < hi:
        if _calls[0] > CAP - 3: return None, "budget"
        mid = (lo + hi) // 2
        if _getcode_nonempty(contract, mid): hi = mid
        else: lo = mid + 1
    rc = _c("eth_getBlockReceipts", [hex(lo)])
    if not isinstance(rc, list): return None, f"birth={lo},no_receipts"
    for r in rc:
        if (r.get("contractAddress") or "").lower() == contract.lower():
            return (r.get("from") or "").lower(), f"birth={lo}"
    return None, f"birth={lo},factory_create2"

def first_funder(eoa):
    if eoa in _fnd_cache: return _fnd_cache[eoa]
    out = _first_funder(eoa); _fnd_cache[eoa] = out; return out

def _first_funder(eoa):
    if _calls[0] > CAP - 30: return None, "budget"
    def bal_pos(b):
        x = _c("eth_getBalance", [eoa, hex(b)])
        try: return int(x, 16) > 0
        except Exception: return False
    if not bal_pos(HEAD): return None, "zero_balance_at_head"
    lo, hi = 0, HEAD
    while lo < hi:
        if _calls[0] > CAP - 3: return None, "budget"
        mid = (lo + hi) // 2
        if bal_pos(mid): hi = mid
        else: lo = mid + 1
    tf = _c("trace_filter", [{"fromBlock": hex(lo), "toBlock": hex(lo), "toAddress": [eoa]}])
    if isinstance(tf, list):
        for t in tf:
            a = t.get("action", {})
            try: val = int(a.get("value", "0x0"), 16)
            except Exception: val = 0
            if val > 0 and (a.get("to") or "").lower() == eoa:
                return (a.get("from") or "").lower(), f"birth={lo}"
    return None, f"birth={lo},no_inbound_trace"

# ---------------------------------------------------------------- entity merge
def build(clusters, fetch_topn=20):
    prof = {k: cluster_profile(v) for k, v in clusters.items()}
    order = sorted(prof, key=lambda k: -prof[k]["size"])
    top = order[:fetch_topn]

    # signal A: shared custom executor -> which clusters
    exec_to_cl = collections.defaultdict(set)
    for k in clusters:
        for e in prof[k]["custom_execs"]:
            exec_to_cl[e].add(k)
    shared_exec = {e: cs for e, cs in exec_to_cl.items() if len(cs) >= 2}

    uf = UF()
    for k in clusters: uf.find(("c", k))

    # fetch funders: primary EOA of every top-N cluster + every EOA on a shared custom executor
    eoas_to_fund = set(prof[k]["primary_eoa"] for k in top)
    for e, cs in shared_exec.items():
        for k in cs:
            eoas_to_fund |= prof[k]["eoas"]
    funder = {}
    for eoa in eoas_to_fund:
        if _calls[0] > CAP - 30: break
        funder[eoa] = first_funder(eoa)

    # fetch deployer: primary exec of top-N + each shared custom executor
    execs_to_dep = set(prof[k]["primary_exec"] for k in top) | set(shared_exec)
    deployer = {}
    for c in execs_to_dep:
        if _calls[0] > CAP - 30: break
        deployer[c] = deployer_of(c)

    # ---- merge ----
    # A+B: a shared custom executor merges its clusters ONLY if >=2 of its EOAs share a funder
    #      (confirms one operator, not a public bot-as-a-service). Record the classification.
    shared_exec_class = {}
    for e, cs in shared_exec.items():
        cs = list(cs)
        fundset = collections.Counter(funder.get(prof[k]["primary_eoa"], (None,))[0] for k in cs)
        fundset.pop(None, None)
        shares = any(v >= 2 for v in fundset.values())
        shared_exec_class[e] = dict(clusters=cs, n_eoa=sum(len(prof[k]["eoas"]) for k in cs),
                                    funder_groups=dict(fundset), one_operator=shares,
                                    deployer=deployer.get(e))
        if shares:
            for k in cs[1:]: uf.union(("c", cs[0]), ("c", k))
    # C: shared deployer across top-N primary execs
    by_dep = collections.defaultdict(set)
    for k in top:
        d = deployer.get(prof[k]["primary_exec"], (None,))[0]
        if d: by_dep[d].add(k)
    for d, grp in by_dep.items():
        if len(grp) >= 2:
            grp = list(grp)
            for k in grp[1:]: uf.union(("c", grp[0]), ("c", k))
    # B: shared funder across fetched primary EOAs
    by_fnd = collections.defaultdict(set)
    for k in top:
        f = funder.get(prof[k]["primary_eoa"], (None,))[0]
        if f: by_fnd[f].add(k)
    for f, grp in by_fnd.items():
        if len(grp) >= 2:
            grp = list(grp)
            for k in grp[1:]: uf.union(("c", grp[0]), ("c", k))

    ent = collections.defaultdict(list)
    for k in clusters: ent[uf.find(("c", k))].append(k)
    return dict(prof=prof, order=order, top=top, funder=funder, deployer=deployer,
                shared_exec_class=shared_exec_class, entities=ent, uf=uf)


# nonce probe (2026-07-08): shared first-funders classified CEX/infra vs private.
# nonce > 50k => exchange hot-wallet / relayer that funds thousands of unrelated addrs =>
# NOT an entity signal. Only sub-50k private funders link EOAs into one operator.
CEX_NONCE = 50_000
SHARED_FUNDER_NONCE = {
    "0xf78b2eda7c1e20ff9906b31fe3612195bce9d6ce": 50802,
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": 14688063,
    "0x4976a4a02f38326660d17bf34b431dc6e2eb2327": 5814506,
    "0xe0d4b4bfa4c2c085ee6ad9a51096b0478b77d37e": 385,      # private funder (links 3 EOAs)
    "0xa9ac43f5b5e38155a288d1a01d2cbc4478e14573": 1103957,
    "0x9642b23ed1e01df1092b92641051881a322f5d4e": 3249226,
    "0x2cff890f0378a11913b6129b2e97417a2c302680": 827664,
    "0x963737c550e70ffe4d59464542a28604edb2ef9a": 1487111,
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe": 9900563,
}
def is_cex_funder(addr):
    return SHARED_FUNDER_NONCE.get(addr, 0) > CEX_NONCE


def main():
    clusters = load_clusters()
    R = build(clusters, fetch_topn=20)
    dump = dict(calls=_calls[0], n_clusters=len(clusters),
                funder={k: v for k, v in R["funder"].items()},
                deployer={k: v for k, v in R["deployer"].items()},
                shared_exec_class=R["shared_exec_class"])
    json.dump(dump, open("out/entity_atlas_fetch.json", "w"), indent=1, default=str)
    print("clusters>=50:", len(clusters), "calls:", _calls[0])
    # top-20 collapse
    ent_of = {}
    for root, ks in R["entities"].items():
        for k in ks: ent_of[k] = root
    top_ent = collections.defaultdict(list)
    for k in R["top"]: top_ent[ent_of[k]].append(k)
    print("top-20 collapse into", len(top_ent), "entities")
    for e, info in R["shared_exec_class"].items():
        print("  shared-exec", e[:12], "clusters", len(info["clusters"]),
              "one_operator", info["one_operator"], "funder_groups", info["funder_groups"])


if __name__ == "__main__":
    main()

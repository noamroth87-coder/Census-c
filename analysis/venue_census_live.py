"""Live venue census — structural, no pricing. Sample recent mainnet blocks, flag ARB-SHAPED
txs by log structure alone, and rank the AMM protocols/venues swap-cycle activity flows through.

Detection (structural heuristic — over- AND under-counts, by design):
  candidate  = a tx with >=2 Swap events among {V2, V3, V4} (matched by event signature)
  arb-shaped = candidate AND a cycle:
     - trader continuity: one non-pool address is an actor (sender/recipient) in >=2 of the
       swaps (the same contract trades across the swaps), AND
     - token cycle: the V2/V3 pools' token graph contains a cycle (union-find: an edge joins two
       already-connected tokens => the flow returns toward its start). Needs token0()/token1()
       per V2/V3 pool (bounded, cached).
     - V4 legs carry no cheaply-resolvable tokens (singleton PoolManager, poolId-only), so a tx
       containing V4 is confirmed by trader-continuity alone and tagged `v4_inferred`.
  Tags: strict (token cycle proven) / v4_inferred / unverified (tokens unresolved at budget).

Protocol mapping: by event signature (V2/V3/V4/Curve/Balancer), forks within V2/V3 split by
factory() (bounded <=300 calls). All swap families in SWAP_TOPICS are fetched so Curve/Balancer
legs of a flagged arb are counted; AMMs whose Swap signature is NOT in SWAP_TOPICS (Maverick,
Dodo, novel) are invisible — a stated under-count.
"""
import json, os, sys
from collections import defaultdict, Counter
from census.rpc import call
from census.config import (V2_SWAP, V3_SWAP, V4_SWAP, BALANCER_SWAP, SWAP_TOPICS,
                           V2_FACTORY, V3_FACTORY)

HERE = os.path.dirname(os.path.abspath(__file__))
V4_POOLMANAGER = "0x000000000004444c5dc75cb358380d2e3de08a90"
CURVE_A = "0x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140"
CURVE_B = "0xd013ca23e77a65003c2c659c5442c00c805371b7fc1ebd4c206c41d1536bd90b"
SIG_PROTO = {V2_SWAP: "V2", V3_SWAP: "V3", V4_SWAP: "V4",
             BALANCER_SWAP: "Balancer", CURVE_A: "Curve", CURVE_B: "Curve"}
V234 = {"V2", "V3", "V4"}

KNOWN_FACTORY = {
    "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f": "Uniswap V2",
    "0x1f98431c8ad98523631ae4a59f267346ea31f984": "Uniswap V3",
    "0xc0aee478e3658e2610c5f7a4a2e1777ce9e4f2ac": "SushiSwap V2",
    "0xbaceb8ec6b9355dfc0269c18bac9d6e2bdc29c4f": "SushiSwap V3",
    "0x1097053fd2ea711dad45caccc45eff7548fcb362": "PancakeSwap V2",
    "0x0bfbcf9fa4f9c56b0f40a671ad40e0805a091865": "PancakeSwap V3",
    "0x115934131916c8b277dd010ee02de363c09d037c": "ShibaSwap",
}

TARGET_ARBS = int(os.environ.get("VC_TARGET", "500"))
MAX_BLOCKS = int(os.environ.get("VC_MAXBLOCKS", "1000"))
CALL_CAP = 15000
FACTORY_CAP = 300
_calls = [0]

def rpc(method, params):
    _calls[0] += 1
    return call(method, params)

def _addr(topic):
    return "0x" + topic[-40:] if topic and len(topic) >= 42 else None

_tok_cache = {}
def pool_tokens(pool):
    """(token0, token1) for a V2/V3 pool, cached. None on failure/budget."""
    if pool in _tok_cache:
        return _tok_cache[pool]
    if _calls[0] > CALL_CAP - 5:
        return None
    t0 = rpc("eth_call", [{"to": pool, "data": "0x0dfe1681"}, "latest"])
    t1 = rpc("eth_call", [{"to": pool, "data": "0xd21220a7"}, "latest"])
    out = None
    if isinstance(t0, str) and isinstance(t1, str) and len(t0) >= 42 and len(t1) >= 42:
        out = (_addr(t0), _addr(t1))
    _tok_cache[pool] = out
    return out

_fac_cache = {}
def pool_factory(pool):
    if pool in _fac_cache:
        return _fac_cache[pool]
    r = rpc("eth_call", [{"to": pool, "data": "0xc45a0155"}, "latest"])  # factory()
    fac = _addr(r) if isinstance(r, str) and len(r) >= 42 else None
    _fac_cache[pool] = fac
    return fac


class UF:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x: self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb: return True    # edge closes a cycle
        self.p[ra] = rb; return False


def classify(swaps):
    """swaps: list of dict(pool, proto, actors:set). Return (is_arb, tag, protos_touched) or None."""
    n_v234 = sum(1 for s in swaps if s["proto"] in V234)
    if n_v234 < 2:
        return None
    pools = set(s["pool"] for s in swaps)
    # trader continuity: a non-pool address acts in >=2 swaps
    actor_ct = Counter()
    for s in swaps:
        for a in s["actors"]:
            if a and a not in pools:
                actor_ct[a] += 1
    pivot = any(c >= 2 for c in actor_ct.values())
    if not pivot:
        return None
    protos = set(s["proto"] for s in swaps)
    has_v4 = "V4" in protos
    if has_v4:
        return (True, "v4_inferred", protos)
    # token-graph cycle over V2/V3 pools
    uf = UF(); cyclic = False; unresolved = False
    for s in swaps:
        if s["proto"] not in ("V2", "V3"):
            continue
        tk = pool_tokens(s["pool"])
        if tk is None:
            unresolved = True; continue
        if uf.union(tk[0], tk[1]):
            cyclic = True
    if cyclic:
        return (True, "strict", protos)
    if unresolved:
        return (True, "unverified", protos)   # couldn't prove cycle within budget; kept, flagged
    return None


def collect():
    head = int(rpc("eth_blockNumber", []), 16)
    start = head - 5                       # step back from the tip to avoid reorgs
    arb_txs = {}                           # txhash -> dict(block, tag, protos, swaps)
    per_proto_pools = defaultdict(set)
    scanned = 0; bn = start; cand = 0
    while scanned < MAX_BLOCKS and len(arb_txs) < TARGET_ARBS and _calls[0] < CALL_CAP - 300:
        logs = rpc("eth_getLogs", [{"fromBlock": hex(bn), "toBlock": hex(bn),
                                    "topics": [list(SWAP_TOPICS)]}])
        scanned += 1
        if isinstance(logs, list):
            by_tx = defaultdict(list)
            for lg in logs:
                sig = lg["topics"][0].lower()
                proto = SIG_PROTO.get(sig)
                if not proto:
                    continue
                pool = lg["address"].lower()
                tp = lg["topics"]
                if proto == "V4":
                    actors = {_addr(tp[2]) if len(tp) > 2 else None}
                else:
                    actors = {_addr(tp[1]) if len(tp) > 1 else None,
                              _addr(tp[2]) if len(tp) > 2 else None}
                by_tx[lg["transactionHash"]].append(dict(pool=pool, proto=proto, actors=actors))
            for txh, swaps in by_tx.items():
                if sum(1 for s in swaps if s["proto"] in V234) >= 2:
                    cand += 1
                    res = classify(swaps)
                    if res:
                        is_arb, tag, protos = res
                        arb_txs[txh] = dict(block=bn, tag=tag, protos=sorted(protos),
                                            swaps=[(s["pool"], s["proto"]) for s in swaps])
                        for s in swaps:
                            per_proto_pools[s["proto"]].add(s["pool"])
        bn -= 1
    return dict(head=head, start=start, end=bn + 1, scanned=scanned, candidates=cand,
                arb_txs=arb_txs, per_proto_pools={k: sorted(v) for k, v in per_proto_pools.items()})


def factory_sample(data):
    """Label a bounded sample of V2/V3 pools by factory to characterise the fork mix (<=300)."""
    fork = {"V2": Counter(), "V3": Counter()}
    for proto in ("V2", "V3"):
        for pool in data["per_proto_pools"].get(proto, []):
            if _calls[0] >= CALL_CAP - 5 or sum(sum(c.values()) for c in fork.values()) >= FACTORY_CAP:
                break
            fac = pool_factory(pool)
            name = KNOWN_FACTORY.get((fac or "").lower(), "UNKNOWN-fork" if fac else "unresolved")
            fork[proto][name] += 1
    return {k: dict(v) for k, v in fork.items()}


def main():
    data = collect()
    fork = factory_sample(data)
    arb = data["arb_txs"]
    N = len(arb)
    # coverage
    proto_txs = defaultdict(set)          # proto -> set of txhashes touching it
    tag_ct = Counter()
    pure_ct = Counter(); mixed_ct = Counter()
    for txh, r in arb.items():
        tag_ct[r["tag"]] += 1
        ps = set(r["protos"])
        for p in ps:
            proto_txs[p].add(txh)
        for p in ps:
            if len(ps) == 1: pure_ct[p] += 1
            else: mixed_ct[p] += 1
    protos_sorted = sorted(proto_txs, key=lambda p: -len(proto_txs[p]))
    # cumulative tx coverage (greedy union by tx-touch)
    covered = set(); cum = []
    remaining = dict(proto_txs)
    order = []
    pool_local = dict(remaining)
    while pool_local:
        best = max(pool_local, key=lambda p: len(pool_local[p] - covered))
        gain = len(pool_local[best] - covered)
        if gain == 0: break
        covered |= pool_local[best]; order.append(best)
        cum.append((best, len(covered), 100 * len(covered) / N if N else 0))
        del pool_local[best]
    # dependency: for each proto, pure vs mixed among its touchers
    dep = {}
    for p in protos_sorted:
        t = len(proto_txs[p])
        dep[p] = dict(touch=t, touch_pct=100 * t / N if N else 0,
                      pure=pure_ct[p], mixed=mixed_ct[p],
                      pure_pct=100 * pure_ct[p] / t if t else 0,
                      mixed_pct=100 * mixed_ct[p] / t if t else 0,
                      pools=len(data["per_proto_pools"].get(p, [])))
    metrics = dict(
        head=data["head"], start=data["start"], end=data["end"], scanned=data["scanned"],
        candidates=data["candidates"], n_arb=N, calls_used=_calls[0], call_cap=CALL_CAP,
        factory_calls=sum(sum(c.values()) for c in fork.values()), factory_cap=FACTORY_CAP,
        tag=dict(tag_ct), dep=dep, cumulative=cum, protos_sorted=protos_sorted,
        fork=fork, per_proto_pool_counts={k: len(v) for k, v in data["per_proto_pools"].items()})
    json.dump({"metrics": metrics,
               "arb_txs": {k: v for k, v in list(arb.items())[:1000]}},
              open(os.path.join(HERE, "venue_live_raw.json"), "w"), indent=1, default=str)
    print(json.dumps({k: metrics[k] for k in ("scanned", "candidates", "n_arb", "calls_used",
                     "factory_calls", "tag", "cumulative")}, indent=1, default=str))
    return metrics


if __name__ == "__main__":
    main()

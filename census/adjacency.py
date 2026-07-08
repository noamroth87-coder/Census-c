"""Bounded victim-adjacency pass: backrun distance (positions) for a sample of arbs.
For each arb, find its swap-pool set from its own logs, then the nearest PRECEDING tx in
the same block that swapped in one of those pools. backrun_distance = idx - that idx.
None => no same-pool predecessor in-block (not a direct backrun, or victim in a prior block)."""
from census.rpc import call
from census.detect import parse_receipt_logs
from census.trace import h2i

_block_cache = {}
def _block_receipts(bn):
    if bn in _block_cache: return _block_cache[bn]
    r = call("eth_getBlockReceipts", [hex(bn)])
    _block_cache[bn] = r if isinstance(r, list) else []
    if len(_block_cache) > 400: _block_cache.clear()
    return _block_cache[bn]

def pools_of(receipt):
    _, swaps, _ = parse_receipt_logs(receipt.get("logs") or [])
    return set(swaps)

def adjacency_for(arbs_sample):
    """arbs_sample: list of dicts with block, tx_index, txhash.
    Returns list of dicts with backrun_distance + same_block_backrun bool."""
    by_block = {}
    for a in arbs_sample:
        by_block.setdefault(a["block"], []).append(a)
    out = []
    for bn, group in by_block.items():
        receipts = _block_receipts(bn)
        if not receipts:
            for a in group: out.append(dict(a, backrun_distance=None, note="no_receipts"))
            continue
        # map idx -> pools
        idx_pools = {}
        for r in receipts:
            if r.get("status") == "0x1":
                idx_pools[h2i(r.get("transactionIndex"))] = pools_of(r)
        for a in group:
            ai = a["tx_index"]; my = idx_pools.get(ai, set())
            dist = None
            if my:
                for j in range(ai-1, -1, -1):
                    if idx_pools.get(j, set()) & my:
                        dist = ai - j; break
            out.append(dict(block=bn, tx_index=ai, txhash=a["txhash"],
                            backrun_distance=dist))
    return out

"""Trace a candidate arb: native-ETH deltas, builder (coinbase) payment, confirmation."""
from census.rpc import call

def h2i(x):
    if x is None: return 0
    return int(x, 16) if isinstance(x, str) else int(x)

def walk_calls(node, eth_delta, miner, coinbase_acc, depth=0):
    """Recurse callTracer tree. Accumulate native ETH deltas per addr and coinbase payments."""
    frm = (node.get("from") or "").lower()
    to = (node.get("to") or "").lower()
    val = h2i(node.get("value"))
    err = node.get("error")
    # Reverted subcalls don't move value; callTracer usually omits reverted subtrees' effects,
    # but guard: skip value accounting on errored frames.
    if val and not err:
        eth_delta[frm] = eth_delta.get(frm, 0) - val
        eth_delta[to] = eth_delta.get(to, 0) + val
        if to == miner:
            coinbase_acc[0] += val
    for c in node.get("calls", []) or []:
        walk_calls(c, eth_delta, miner, coinbase_acc, depth+1)

def trace_tx(txhash, miner):
    """Return dict: eth_delta {addr:wei}, builder_coinbase_wei, ok(bool)."""
    tr = call("debug_traceTransaction", [txhash, {"tracer": "callTracer"}])
    if not isinstance(tr, dict) or "from" not in tr:
        return dict(ok=False, err=str(tr)[:120], eth_delta={}, builder_coinbase=0)
    eth_delta = {}; coinbase_acc = [0]
    miner = (miner or "").lower()
    walk_calls(tr, eth_delta, miner, coinbase_acc)
    return dict(ok=True, eth_delta=eth_delta, builder_coinbase=coinbase_acc[0],
                top_to=(tr.get("to") or "").lower())

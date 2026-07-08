"""Parallel JSON-RPC client with retry/backoff. No hard cap; polite concurrency."""
import json, time, threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from census.config import ETH_RPC, ETH_RPC_ARCHIVE

_local = threading.local()
def _sess():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=0)
        s.mount("https://", adapter)
        _local.s = s
    return s

def call(method, params, rpc=ETH_RPC, _id=1, retries=5):
    payload = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params}
    delay = 1.0
    last = None
    for attempt in range(retries):
        try:
            r = _sess().post(rpc, json=payload, timeout=60)
            if r.status_code == 200:
                j = r.json()
                if "error" in j and j["error"] is not None:
                    # deterministic RPC errors (revert etc.) shouldn't be retried forever
                    return {"__error__": j["error"]}
                return j.get("result")
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = str(e)
        time.sleep(delay); delay = min(delay*2, 16)
    return {"__rpcfail__": last}

def batch(method, params_list, rpc=ETH_RPC, workers=16):
    """Run the same method over many params concurrently. Returns list aligned to input."""
    out = [None]*len(params_list)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(call, method, p, rpc, i): i for i, p in enumerate(params_list)}
        for f in as_completed(futs):
            out[futs[f]] = f.result()
    return out

def map_fn(fn, items, workers=16):
    """Concurrently apply fn to items; returns list aligned to input order."""
    out = [None]*len(items)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        for f in as_completed(futs):
            out[futs[f]] = f.result()
    return out

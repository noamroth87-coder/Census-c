"""Fix the 7-day census window ONCE at start. Writes out/window.json."""
import json, os
from census.rpc import call
from census.config import WINDOW_DAYS

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
os.makedirs(OUT, exist_ok=True)

def block_ts(bn):
    b = call("eth_getBlockByNumber", [hex(bn), False])
    return int(b["timestamp"], 16), int(b["number"], 16)

def fix_window():
    latest = int(call("eth_blockNumber", []), 16)
    head_ts, _ = block_ts(latest)
    target = head_ts - WINDOW_DAYS*24*3600
    lo, hi = latest - 100000, latest
    # binary search for first block with ts >= target
    while lo < hi:
        mid = (lo+hi)//2
        ts, _ = block_ts(mid)
        if ts < target:
            lo = mid+1
        else:
            hi = mid
    start = lo
    start_ts, _ = block_ts(start)
    w = dict(latest_block=latest, head_ts=head_ts, target_ts=target,
             start_block=start, start_ts=start_ts, end_block=latest,
             n_blocks=latest-start+1,
             span_days=(head_ts-start_ts)/86400.0)
    with open(os.path.join(OUT, "window.json"), "w") as f:
        json.dump(w, f, indent=2)
    return w

if __name__ == "__main__":
    print(json.dumps(fix_window(), indent=2))

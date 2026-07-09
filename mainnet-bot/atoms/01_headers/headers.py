"""Atom 1 — block-header latency harness. Prototype-and-measure, NOT production.

Three variants behind one interface — a callback(block_number:int, recv_ns:int) — plus a
per-event timestamp of the block's own `timestamp` field so we can compute the true arrival
gap (how stale the news is when we get it):

  A. WebSocket  eth_subscribe("newHeads")           -> variant "ws"
  B. HTTP poll  eth_blockNumber every POLL_MS ms      -> variant "poll"  (never cached: unique
     id + Cache-Control:no-cache each request — the known past bug where a cached blockNumber
     lags reality)
  C. Both simultaneously — they share one registry, so per block we know which fired first.

Design notes:
- WS runs on the asyncio loop; poll runs on its own daemon thread with its own requests
  session, so the 50 ms cadence is never blocked by the WS loop or vice-versa.
- Two clocks per event: time.time_ns() (wall) for arrival-gap-vs-block-timestamp, and
  time.monotonic_ns() (mono) for intra-process WS-vs-poll deltas (immune to clock steps).
- NO getBlockByNumber in the hot path: WS headers already carry `timestamp`; any block seen
  only by poll (e.g. during the deliberate reconnect) has its ts back-filled historically by
  analyze.py after the run. Keeps the poll loop tight.
- Raw events are appended to raw_timings.jsonl as they happen (crash-safe).

Deliberate reconnect: once at RECONNECT_AT_S the WS is closed and re-established to measure
blocks missed + time-to-recover.
"""
import asyncio, json, os, threading, time
import requests
import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = "cc5ea38c3664bd8ef5fdae785239d25f"
HOST = "ethereum-mainnet.core.chainstack.com"
WS_URL = f"wss://{HOST}/{KEY}"
HTTP_URL = f"https://{HOST}/{KEY}"

POLL_MS = 50
DURATION_S = int(os.environ.get("ATOM1_DURATION", "1800"))   # 30 min
RECONNECT_AT_S = int(os.environ.get("ATOM1_RECONNECT_AT", "900"))  # kill WS once at 15 min
RAW = os.path.join(HERE, "raw_timings.jsonl")
META = os.path.join(HERE, "run_meta.json")

_flock = threading.Lock()
_fh = None
def emit(rec):
    with _flock:
        _fh.write(json.dumps(rec) + "\n"); _fh.flush()

t0_mono = None
t0_wall = None
stop_flag = threading.Event()


# ---------------------------------------------------------------- poll thread
def poll_loop():
    sess = requests.Session()
    sess.headers.update({"content-type": "application/json", "Cache-Control": "no-cache",
                         "Pragma": "no-cache"})
    last = None
    i = 0
    interval = POLL_MS / 1000.0
    while not stop_flag.is_set():
        loop_start = time.monotonic()
        i += 1
        try:
            payload = {"jsonrpc": "2.0", "id": i, "method": "eth_blockNumber",
                       "params": [], "_cachebust": i}
            r = sess.post(HTTP_URL, json=payload, timeout=5)
            recv_wall = time.time_ns(); recv_mono = time.monotonic_ns()
            if r.status_code == 429:
                emit({"event": "poll_rate_limited", "mono_ns": recv_mono, "wall_ns": recv_wall})
            elif r.status_code == 200:
                res = r.json().get("result")
                if res:
                    num = int(res, 16)
                    if num != last:
                        emit({"src": "poll", "kind": "blocknum", "num": num,
                              "wall_ns": recv_wall, "mono_ns": recv_mono, "ts": None})
                        last = num
            else:
                emit({"event": "poll_http_error", "code": r.status_code, "mono_ns": recv_mono})
        except Exception as e:
            emit({"event": "poll_exc", "err": type(e).__name__, "mono_ns": time.monotonic_ns()})
        # keep a steady POLL_MS cadence
        dt = time.monotonic() - loop_start
        if dt < interval:
            stop_flag.wait(interval - dt)


# ---------------------------------------------------------------- ws coroutine
async def ws_reader(ws):
    """Read headers until the socket closes; record each with capture timestamps."""
    async for msg in ws:
        recv_wall = time.time_ns(); recv_mono = time.monotonic_ns()
        try:
            m = json.loads(msg)
        except Exception:
            continue
        if m.get("method") != "eth_subscription":
            continue
        h = m["params"]["result"]
        num = int(h["number"], 16)
        ts = int(h["timestamp"], 16)
        emit({"src": "ws", "kind": "header", "num": num,
              "wall_ns": recv_wall, "mono_ns": recv_mono, "ts": ts})


async def ws_session(tag):
    """One WS connection: subscribe, then read until cancelled/closed. Returns when closed."""
    async with websockets.connect(WS_URL, open_timeout=25, ping_interval=15, ping_timeout=20,
                                  max_size=4_000_000) as ws:
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe",
                                  "params": ["newHeads"]}))
        sub = await asyncio.wait_for(ws.recv(), timeout=25)
        emit({"event": f"ws_subscribed_{tag}", "mono_ns": time.monotonic_ns(),
              "wall_ns": time.time_ns(), "sub": json.loads(sub).get("result")})
        await ws_reader(ws)


async def ws_supervisor():
    """Run WS; at RECONNECT_AT_S deliberately drop and re-establish exactly once."""
    # first session, cancelled at reconnect time
    first = asyncio.ensure_future(ws_session("initial"))
    await asyncio.sleep(RECONNECT_AT_S)
    emit({"event": "reconnect_kill", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
    first.cancel()
    try:
        await first
    except (asyncio.CancelledError, Exception):
        pass
    emit({"event": "reconnect_begin", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
    # reconnect and run until stop
    second = asyncio.ensure_future(_ws_run_until_stop())
    await second


async def _ws_run_until_stop():
    """After the deliberate kill: (re)connect with retry and read until DURATION ends."""
    backoff = 0.5
    while not stop_flag.is_set():
        try:
            await ws_session("reconnect")
        except Exception as e:
            emit({"event": "ws_reconnect_error", "err": type(e).__name__,
                  "mono_ns": time.monotonic_ns()})
            await asyncio.sleep(backoff); backoff = min(backoff * 2, 8)
        else:
            backoff = 0.5
        if stop_flag.is_set():
            break


async def main():
    global _fh, t0_mono, t0_wall
    _fh = open(RAW, "w")
    t0_mono = time.monotonic_ns(); t0_wall = time.time_ns()
    emit({"event": "start", "mono_ns": t0_mono, "wall_ns": t0_wall,
          "duration_s": DURATION_S, "reconnect_at_s": RECONNECT_AT_S, "poll_ms": POLL_MS})
    pt = threading.Thread(target=poll_loop, daemon=True); pt.start()

    async def stopper():
        await asyncio.sleep(DURATION_S)
        stop_flag.set()
    sup = asyncio.ensure_future(ws_supervisor())
    st = asyncio.ensure_future(stopper())
    await st
    stop_flag.set()
    sup.cancel()
    try:
        await sup
    except (asyncio.CancelledError, Exception):
        pass
    emit({"event": "stop", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
    time.sleep(0.3)
    _fh.flush(); _fh.close()
    json.dump({"start_wall_ns": t0_wall, "start_mono_ns": t0_mono,
               "duration_s": DURATION_S, "reconnect_at_s": RECONNECT_AT_S,
               "poll_ms": POLL_MS, "ws_url_host": HOST}, open(META, "w"), indent=1)
    print("run complete ->", RAW)


if __name__ == "__main__":
    asyncio.run(main())

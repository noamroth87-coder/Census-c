"""Atom 1b — four-way premium endpoint race. Same harness shape as atom-1 (headers.py):
one interface (block_number, recv_ns) per source, two clocks, crash-safe append log, one
deliberate reconnect per source. Only the endpoints/sources change.

Sources (all racing, 30 min):
  prem_http     — Chainstack execution HTTP, tight-poll eth_blockNumber @50ms   (basic auth)
  prem_wss      — Chainstack execution WSS, eth_subscribe newHeads              (basic auth)
  beacon        — Chainstack consensus HTTP, poll /eth/v1/beacon/headers/head @50ms; on a new
                  slot, map slot -> execution block via /eth/v2/beacon/blocks/{slot}
                  (execution_payload.block_number + .timestamp). Records the head-reveal time
                  BEFORE the mapping fetch. SSE (/eth/v1/events?topics=head) was tested and is
                  unusable here — the agent proxy buffers the stream (connect read-timeout), so
                  polling is the fallback the task allows.                        (basic auth)
  baseline_wss  — atom-1's standard key-URL endpoint, eth_subscribe newHeads     (no basic auth)

SECURITY: username/password + URLs are read from env at runtime (see the scratchpad env file,
which is NOT committed). This file contains NO credentials, and the raw log stores endpoint
LABELS only — never a URL with embedded auth.
"""
import asyncio, base64, json, os, threading, time
import requests
import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
U = os.environ["ATOM1B_USER"]; P = os.environ["ATOM1B_PASS"]
AUTH = "Basic " + base64.b64encode(f"{U}:{P}".encode()).decode()
EXEC_HTTP = os.environ["ATOM1B_EXEC_HTTP"]
EXEC_WSS = os.environ["ATOM1B_EXEC_WSS"]
BEACON = os.environ["ATOM1B_BEACON"]
BASE_WSS = os.environ["ATOM1B_BASELINE_WSS"]

POLL_MS = 50
DURATION_S = int(os.environ.get("ATOM1B_DURATION", "1800"))
RAW = os.path.join(HERE, "raw_timings_premium.jsonl")
META = os.path.join(HERE, "run_meta_premium.json")
# staggered single reconnect per source (seconds into the run) so they never all drop at once
RECON = {"prem_wss": 600, "baseline_wss": 900, "prem_http": 1200, "beacon": 1500}
if DURATION_S < 300:  # smoke test: compress the reconnect schedule
    RECON = {"prem_wss": 20, "baseline_wss": 30, "prem_http": 40, "beacon": 50}

_flock = threading.Lock(); _fh = None
def emit(rec):
    with _flock:
        _fh.write(json.dumps(rec) + "\n"); _fh.flush()

stop_flag = threading.Event()


# ---------------------------------------------------------------- poll sources (threads)
def http_poll_loop():
    """Execution eth_blockNumber @POLL_MS, basic auth, one session-reset reconnect."""
    sess = _mk_session()
    last = None; i = 0; interval = POLL_MS / 1000.0; reset_done = False
    t_start = time.monotonic()
    while not stop_flag.is_set():
        loop = time.monotonic(); i += 1
        if not reset_done and time.monotonic() - t_start >= RECON["prem_http"]:
            emit({"event": "reconnect_kill", "src": "prem_http", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
            try: sess.close()
            except Exception: pass
            sess = _mk_session(); reset_done = True
            emit({"event": "reconnect_up", "src": "prem_http", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
        try:
            r = sess.post(EXEC_HTTP, json={"jsonrpc": "2.0", "id": i, "method": "eth_blockNumber", "params": [], "_cb": i}, timeout=5)
            rw = time.time_ns(); rm = time.monotonic_ns()
            if r.status_code == 429:
                emit({"event": "rate_limited", "src": "prem_http", "mono_ns": rm})
            elif r.status_code == 200:
                res = r.json().get("result")
                if res:
                    num = int(res, 16)
                    if num != last:
                        emit({"src": "prem_http", "kind": "blocknum", "num": num, "wall_ns": rw, "mono_ns": rm, "ts": None})
                        last = num
        except Exception as e:
            emit({"event": "poll_exc", "src": "prem_http", "err": type(e).__name__, "mono_ns": time.monotonic_ns()})
        dt = time.monotonic() - loop
        if dt < interval: stop_flag.wait(interval - dt)


def beacon_poll_loop():
    """Consensus head @POLL_MS: detect new slot from /eth/v1/beacon/headers/head, timestamp the
    reveal, then map slot->execution block (block_number + timestamp). One session-reset."""
    sess = _mk_session(); mapper = _mk_session()
    last_slot = None; interval = POLL_MS / 1000.0; reset_done = False
    t_start = time.monotonic()
    while not stop_flag.is_set():
        loop = time.monotonic()
        if not reset_done and time.monotonic() - t_start >= RECON["beacon"]:
            emit({"event": "reconnect_kill", "src": "beacon", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
            try: sess.close()
            except Exception: pass
            sess = _mk_session(); reset_done = True
            emit({"event": "reconnect_up", "src": "beacon", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
        try:
            r = sess.get(BEACON + "/eth/v1/beacon/headers/head", timeout=5)
            rw = time.time_ns(); rm = time.monotonic_ns()
            if r.status_code == 429:
                emit({"event": "rate_limited", "src": "beacon", "mono_ns": rm})
            elif r.status_code == 200:
                slot = int(r.json()["data"]["header"]["message"]["slot"])
                if slot != last_slot:
                    last_slot = slot
                    # map slot -> execution block (follow-up fetch; not part of the reveal timing)
                    try:
                        b = mapper.get(BEACON + f"/eth/v2/beacon/blocks/{slot}", timeout=8)
                        if b.status_code == 200:
                            ep = b.json()["data"]["message"]["body"]["execution_payload"]
                            num = int(ep["block_number"]); ts = int(ep["timestamp"])
                            emit({"src": "beacon", "kind": "head", "num": num, "wall_ns": rw, "mono_ns": rm, "ts": ts, "slot": slot})
                    except Exception as e:
                        emit({"event": "beacon_map_exc", "src": "beacon", "err": type(e).__name__, "slot": slot, "mono_ns": rm})
        except Exception as e:
            emit({"event": "poll_exc", "src": "beacon", "err": type(e).__name__, "mono_ns": time.monotonic_ns()})
        dt = time.monotonic() - loop
        if dt < interval: stop_flag.wait(interval - dt)


def _mk_session():
    s = requests.Session()
    s.headers.update({"Authorization": AUTH, "content-type": "application/json",
                      "Cache-Control": "no-cache", "Pragma": "no-cache"})
    return s


# ---------------------------------------------------------------- wss sources (asyncio)
async def wss_source(label, url, headers):
    async with websockets.connect(url, additional_headers=headers, open_timeout=25,
                                  ping_interval=15, ping_timeout=20, max_size=4_000_000) as ws:
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newHeads"]}))
        await asyncio.wait_for(ws.recv(), timeout=25)
        emit({"event": "ws_subscribed", "src": label, "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
        async for msg in ws:
            rw = time.time_ns(); rm = time.monotonic_ns()
            try: m = json.loads(msg)
            except Exception: continue
            if m.get("method") != "eth_subscription": continue
            h = m["params"]["result"]
            emit({"src": label, "kind": "header", "num": int(h["number"], 16),
                  "wall_ns": rw, "mono_ns": rm, "ts": int(h["timestamp"], 16)})


async def wss_supervisor(label, url, headers):
    """Run the WSS source; deliberately drop+re-establish once at RECON[label]."""
    first = asyncio.ensure_future(wss_source(label, url, headers))
    try:
        await asyncio.wait_for(asyncio.shield(first), timeout=RECON[label])
    except asyncio.TimeoutError:
        emit({"event": "reconnect_kill", "src": label, "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
        first.cancel()
        try: await first
        except BaseException: pass          # CancelledError is BaseException, not Exception
        emit({"event": "reconnect_up", "src": label, "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
    except Exception:
        pass
    # (re)connect with retry until stop
    backoff = 0.5
    while not stop_flag.is_set():
        try:
            await wss_source(label, url, headers)
        except Exception as e:
            emit({"event": "ws_error", "src": label, "err": type(e).__name__, "mono_ns": time.monotonic_ns()})
            await asyncio.sleep(backoff); backoff = min(backoff * 2, 8)


async def main():
    global _fh
    _fh = open(RAW, "w")
    emit({"event": "start", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns(),
          "duration_s": DURATION_S, "poll_ms": POLL_MS, "reconnect_schedule_s": RECON})
    threading.Thread(target=http_poll_loop, daemon=True).start()
    threading.Thread(target=beacon_poll_loop, daemon=True).start()

    async def stopper():
        await asyncio.sleep(DURATION_S); stop_flag.set()
    tasks = [asyncio.ensure_future(wss_supervisor("prem_wss", EXEC_WSS, {"Authorization": AUTH})),
             asyncio.ensure_future(wss_supervisor("baseline_wss", BASE_WSS, {})),
             asyncio.ensure_future(stopper())]
    await tasks[-1]
    stop_flag.set()
    for t in tasks[:-1]: t.cancel()
    for t in tasks[:-1]:
        try: await t
        except Exception: pass
    emit({"event": "stop", "mono_ns": time.monotonic_ns(), "wall_ns": time.time_ns()})
    time.sleep(0.3); _fh.flush(); _fh.close()
    json.dump({"duration_s": DURATION_S, "poll_ms": POLL_MS, "reconnect_schedule_s": RECON,
               "sources": ["prem_http", "prem_wss", "beacon", "baseline_wss"],
               "note": "SSE unusable via proxy (buffered); beacon uses head-poll @50ms"},
              open(META, "w"), indent=1)
    print("premium run complete ->", RAW)


if __name__ == "__main__":
    asyncio.run(main())

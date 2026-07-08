"""Mini-mission: opportunity-age measurement (PILOT). Not part of the census.

Live-poll new blocks for 10 min, detect arbs >=$10 gross with the census heuristic, then
backtrace each: re-read the SAME pools' spot state at prior blocks and find the earliest
block where the same cyclic trade (same pools/direction) was already profitable above gas.
Age = capture_block - creation_block. AGE-0 = created intra-capture-block.

Profitability model (labelled approximation): marginal spot-price product around the arb's
token cycle, net of pool fees, times the captured notional, vs the captured gas cost. Ignores
slippage/depth -> an UPPER bound on how early it was profitable (may over-state age). Pools
whose state can't be read (V4 singleton / Curve / Balancer / unknown) => UNTRACEABLE.
"""
import json, os, time
from collections import defaultdict, Counter
from census.rpc import call as _rawcall
from census.detect import classify_tx
from census.measure import measure_arb
from census.price import decimals, token_to_eth, eth_usd
from census.config import V2_SWAP, V3_SWAP, V4_SWAP, WETH, TRANSFER, USDC, USDT, DAI
from census.trace import h2i
try:
    from eth_hash.auto import keccak
except Exception:
    from Crypto.Hash import keccak as _k
    def keccak(b):
        h = _k.new(digest_bits=256); h.update(b); return h.digest()

ZERO = "0x0000000000000000000000000000000000000000"
V4_POOLS_SLOT = 6   # empirically verified: extsload(keccak(poolId . 6)) = pool slot0

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
BUDGET = 2000
CC = {"n": 0}
def call(method, params, rpc=None):
    CC["n"] += 1
    return _rawcall(method, params)
# route census.trace / census.price RPC through the counter too (honest budget accounting)
import census.trace as _t, census.price as _p
_t.call = call
_p.call = call

# ---------- pool state reading (cached metadata) ----------
_meta = {}   # pool -> (kind, token0, token1, fee) ; kind in {v2,v3,None}
def pool_meta(pool):
    if pool in _meta: return _meta[pool]
    kind = None; t0 = t1 = None; fee = 0.003
    s = call("eth_call", [{"to": pool, "data": "0x3850c7bd"}, "latest"])  # slot0() -> v3
    if isinstance(s, str) and len(s) >= 66:
        kind = "v3"
        f = call("eth_call", [{"to": pool, "data": "0xddca3f43"}, "latest"])  # fee()
        fee = (int(f, 16)/1e6) if isinstance(f, str) and len(f) >= 3 else 0.003
    else:
        r = call("eth_call", [{"to": pool, "data": "0x0902f1ac"}, "latest"])  # getReserves() -> v2
        if isinstance(r, str) and len(r) >= 130:
            kind = "v2"; fee = 0.003
    if kind:
        a = call("eth_call", [{"to": pool, "data": "0x0dfe1681"}, "latest"])  # token0()
        b = call("eth_call", [{"to": pool, "data": "0xd21220a7"}, "latest"])  # token1()
        t0 = ("0x"+a[-40:]).lower() if isinstance(a, str) and len(a) >= 42 else None
        t1 = ("0x"+b[-40:]).lower() if isinstance(b, str) and len(b) >= 42 else None
        if not t0 or not t1: kind = None
    _meta[pool] = (kind, t0, t1, fee)
    return _meta[pool]

def _canon(addr):
    """Map V4 native currency (address 0) to WETH so ETH/WETH cycles close."""
    a = addr.lower()
    return WETH if a == ZERO else a

def leg_rate(leg, block):
    """Marginal spot: units of tout per 1 unit tin at `block`, net of pool fee. None if unreadable."""
    kind = leg["kind"]
    tin, tout = leg["tin"], leg["tout"]
    if kind in ("v2", "v3"):
        pool = leg["pool"]; _, t0, t1, fee = pool_meta(pool)
        if t0 is None: return None
        d0, d1 = decimals(t0), decimals(t1)
        if kind == "v3":
            s = call("eth_call", [{"to": pool, "data": "0x3850c7bd"}, hex(block)])
            if not isinstance(s, str) or len(s) < 66: return None
            sp = int(s[2:66], 16)
            if sp == 0: return None
            p10 = (sp*sp)/(2**192) * 10**(d0-d1)
        else:
            r = call("eth_call", [{"to": pool, "data": "0x0902f1ac"}, hex(block)])
            if not isinstance(r, str) or len(r) < 130: return None
            r0 = int(r[2:66], 16); r1 = int(r[66:130], 16)
            if r0 == 0 or r1 == 0: return None
            p10 = (r1/10**d1)/(r0/10**d0)
        c0, c1 = _canon(t0), _canon(t1)
    else:  # v4
        mgr = leg["mgr"]; pid = leg["poolId"]; fee = leg["fee"]
        c0, c1 = leg["cur0"], leg["cur1"]
        slot = keccak(bytes.fromhex(pid[2:]) + V4_POOLS_SLOT.to_bytes(32, "big"))
        res = call("eth_call", [{"to": mgr, "data": "0x1e2eaeaf" + slot.hex()}, hex(block)])
        if not isinstance(res, str) or len(res) < 66: return None
        sp = int(res[2:66], 16) & ((1 << 160)-1)
        if sp == 0: return None
        d0 = decimals(c0) if c0 != WETH else 18
        d1 = decimals(c1) if c1 != WETH else 18
        # cur0/cur1 here are already canonicalized token addresses in original order
        p10 = (sp*sp)/(2**192) * 10**(d0-d1)
    if tin == c0 and tout == c1:   rate = p10
    elif tin == c1 and tout == c0: rate = 1/p10 if p10 else None
    else: return None
    return rate*(1-fee) if rate else None

def _manager_transfers(logs, mgr):
    """value -> (token, dir) where dir '+' = into mgr (tokenIn), '-' = out of mgr."""
    m = {}
    for lg in logs:
        tp = lg.get("topics") or []
        if tp and tp[0].lower() == TRANSFER and len(tp) == 3:
            frm = ("0x"+tp[1][-40:]).lower(); to = ("0x"+tp[2][-40:]).lower()
            try: val = int(lg["data"][:66], 16)
            except Exception: continue
            if to == mgr: m[val] = (lg["address"].lower(), "+")
            elif frm == mgr: m[val] = (lg["address"].lower(), "-")
    return m

def swap_legs(receipt):
    """Return (legs, ok). Handles V2/V3/V4. ok=False if any swap leg can't be resolved."""
    legs = []; logs = receipt.get("logs") or []
    def s256(x): return x-2**256 if x >= 2**255 else x
    for lg in logs:
        tp = lg.get("topics") or []
        if not tp: continue
        t0h = tp[0].lower(); pool = lg["address"].lower(); data = lg.get("data", "0x")
        if t0h == V2_SWAP and len(data) >= 2+64*4:
            a0i = int(data[2:66], 16); a1i = int(data[66:130], 16)
            km = pool_meta(pool)
            if km[0] is None: return legs, False
            t0, t1 = _canon(km[1]), _canon(km[2])
            if a0i > 0: legs.append(dict(kind="v2", pool=pool, tin=t0, tout=t1, amt_in=a0i))
            elif a1i > 0: legs.append(dict(kind="v2", pool=pool, tin=t1, tout=t0, amt_in=a1i))
        elif t0h == V3_SWAP and len(data) >= 2+64*2:
            a0 = s256(int(data[2:66], 16)); a1 = s256(int(data[66:130], 16))
            km = pool_meta(pool)
            if km[0] is None: return legs, False
            t0, t1 = _canon(km[1]), _canon(km[2])
            if a0 > 0: legs.append(dict(kind="v3", pool=pool, tin=t0, tout=t1, amt_in=a0))
            elif a1 > 0: legs.append(dict(kind="v3", pool=pool, tin=t1, tout=t0, amt_in=a1))
        elif t0h == V4_SWAP and len(data) >= 2+64*6:
            mgr = pool; pid = tp[1]
            a0 = s256(int(data[2:66], 16)); a1 = s256(int(data[66:130], 16))
            fee = int(data[320:384], 16)/1e6
            mt = _manager_transfers(logs, mgr)
            def resolve(amt):
                info = mt.get(abs(amt))
                return info  # (token,dir) or None
            r0, r1 = resolve(a0), resolve(a1)
            # identify currency0/currency1 (canonical) and the in/out direction
            cur0 = _canon(r0[0]) if r0 else WETH   # unmatched => native ETH => WETH
            cur1 = _canon(r1[0]) if r1 else WETH
            if cur0 == cur1: return legs, False
            # pool received the positive-amount currency (tokenIn)
            if a0 > 0: tin, tout, amt = cur0, cur1, abs(a0)
            elif a1 > 0: tin, tout, amt = cur1, cur0, abs(a1)
            else: return legs, False
            legs.append(dict(kind="v4", mgr=mgr, poolId=pid, cur0=cur0, cur1=cur1, fee=fee,
                             tin=tin, tout=tout, amt_in=amt))
        # Curve/Balancer swaps -> unresolved
    return legs, True

def tx_pool_ids(logs):
    """Robust pool-identity set for a tx (no cycle reconstruction needed).
    v2/v3 -> pool address; v4 -> 'v4:'+poolId (distinguishes pools inside the singleton)."""
    ids = set()
    for lg in logs:
        tp = lg.get("topics") or []
        if not tp: continue
        t0h = tp[0].lower()
        if t0h in (V2_SWAP, V3_SWAP):
            ids.add(lg["address"].lower())
        elif t0h == V4_SWAP and len(tp) > 1:
            ids.add("v4:" + tp[1].lower())
    return ids

def is_clean_cycle(legs):
    bal = Counter()
    for l in legs:
        bal[l["tin"]] += 1; bal[l["tout"]] -= 1
    return all(v == 0 for v in bal.values()) and len(legs) >= 2

def gross_rate(legs, block):
    prod = 1.0
    for l in legs:
        r = leg_rate(l, block)
        if r is None: return None
        prod *= r
    return prod

def backtrace(arb, receipt, cap_block, same_block_cause=False):
    """Return dict(age, status, ...). same_block_cause -> AGE-0 (robust, no reconstruction).
    Otherwise attempt spot-cycle backtrace; UNTRACEABLE where the cycle can't be rebuilt."""
    pool_ids = sorted(tx_pool_ids(receipt.get("logs") or []))
    if same_block_cause:
        return dict(age=0, status="AGE-0", pools=pool_ids, reason="same_block_backrun")
    legs, ok = swap_legs(receipt)
    pools = pool_ids
    if not ok or not legs:
        return dict(age=None, status="UNTRACEABLE", reason="unreadable_or_novel_pool", pools=pools)
    if not is_clean_cycle(legs):
        return dict(age=None, status="UNTRACEABLE", reason="noncyclic_or_v4_route", pools=pools)
    # notional in ETH = the WETH leg's input, else captured gross as floor
    notional_eth = None
    for l in legs:
        if l["tin"] == WETH:
            notional_eth = l["amt_in"]/1e18; break
    if notional_eth is None:
        notional_eth = max(arb["gross_eth"], 1e-9)
    gas_eth = arb["gas_cost_eth"]
    thresh_rate = 1 + gas_eth/max(notional_eth, 1e-12)   # spread must cover gas vs notional
    # step back from cap_block-1
    last_profitable = None
    for depth in range(1, 11):
        b = cap_block - depth
        if BUDGET - CC["n"] < len(pools) + 2:   # would blow budget
            return dict(age=None, status="UNTRACEABLE", reason="budget_cap", pools=pools,
                        depth_reached=depth-1)
        gr = gross_rate(legs, b)
        if gr is None:
            return dict(age=None, status="UNTRACEABLE", reason="state_read_fail", pools=pools,
                        depth_reached=depth-1)
        if gr > thresh_rate:
            last_profitable = depth
        else:
            break
    if last_profitable is None:
        return dict(age=0, status="AGE-0", pools=pools, notional_eth=notional_eth,
                    reason="profitable_only_at_capture")
    if last_profitable >= 10:
        return dict(age=10, status="AGE-10+", pools=pools, notional_eth=notional_eth)
    return dict(age=last_profitable, status=f"AGE-{last_profitable}", pools=pools,
                notional_eth=notional_eth)

# ---------- live collection ----------
def live_collect(seconds=600):
    arbs = []; processed = []
    start_head = int(call("eth_blockNumber", []), 16)
    last = start_head - 1
    t0 = time.time()
    print(f"live start head={start_head}, running {seconds}s", flush=True)
    while time.time() - t0 < seconds:
        head = int(call("eth_blockNumber", []), 16)
        while last < head:
            bn = last + 1
            rcpts = call("eth_getBlockReceipts", [hex(bn)])
            hdr = call("eth_getBlockByNumber", [hex(bn), False])
            if isinstance(rcpts, list) and isinstance(hdr, dict):
                ctx = dict(miner=(hdr.get("miner") or "").lower(), base_fee=h2i(hdr.get("baseFeePerGas")),
                           ts=h2i(hdr.get("timestamp")), number=bn)
                # pre-index each tx's pool-ids for same-block-cause detection
                idx_pools = {}
                for r in rcpts:
                    if r.get("status") == "0x1":
                        idx_pools[h2i(r.get("transactionIndex"))] = tx_pool_ids(r.get("logs") or [])
                eu, _ = eth_usd(bn, ctx["ts"])   # 1 cached call/block
                nfound = 0
                for r in rcpts:
                    if r.get("status") != "0x1": continue
                    res = classify_tx(r)
                    if res["cls"] != "arb_candidate": continue
                    # CHEAP pre-filter: numeraire lower-bound on gross (no pool discovery)
                    b = res.get("beneficiary"); d = (res.get("deltas") or {}).get(b, {})
                    lb = 0.0
                    if eu:
                        lb += max(d.get(WETH, 0), 0)/1e18 * eu
                        for st, dec in ((USDC, 6), (USDT, 6), (DAI, 18)):
                            lb += max(d.get(st, 0), 0)/10**dec
                    if lb < 8:   # can't plausibly be >=$10 on numeraire legs -> skip full measure
                        continue
                    try: rec = measure_arb(r, ctx)
                    except Exception: continue
                    if rec["verdict"] == "arb" and (rec.get("gross_usd") or 0) >= 10:
                        ai = h2i(r.get("transactionIndex")); my = idx_pools.get(ai, set())
                        # same-block cause: an EARLIER tx swaps in one of this arb's pools
                        cause = any(my & idx_pools.get(j, set()) for j in range(ai))
                        rec["_receipt"] = r; rec["_ts"] = ctx["ts"]; rec["_cause"] = cause
                        arbs.append(rec); nfound += 1
                processed.append(bn)
                if nfound: print(f"  block {bn}: {nfound} arb>=$10 (calls={CC['n']})", flush=True)
            last = bn
            if CC["n"] > BUDGET*0.85:   # leave headroom for backtrace
                print("  live budget headroom reached; stopping live early", flush=True)
                return arbs, processed, start_head, last
        time.sleep(3)
    return arbs, processed, start_head, last

def run():
    secs = int(os.environ.get("OPPAGE_SECONDS", "600"))
    arbs, processed, start_head, end_head = live_collect(secs)
    print(f"live done: {len(processed)} blocks, {len(arbs)} arbs>=$10, calls={CC['n']}", flush=True)
    for a in arbs:
        bt = backtrace(a, a["_receipt"], a["block"], same_block_cause=a.get("_cause", False))
        a["_bt"] = bt
    data = dict(processed=len(processed), start=start_head, end=end_head, calls=CC["n"],
                arbs=[{k: v for k, v in a.items() if not k.startswith("_")} | {"bt": a["_bt"], "ts": a["_ts"]}
                      for a in arbs])
    json.dump(data, open(os.path.join(OUT, "oppage_raw.json"), "w"), default=str)
    print(f"backtrace done, total calls={CC['n']}", flush=True)
    render_report(data)
    print("DONE", flush=True)
    return arbs, processed

def render_report(data):
    from census.report import pct, med
    def f2(x, d=2): return f"{x:,.{d}f}" if x is not None else "n/a"
    arbs = data["arbs"]
    def agecat(bt):
        s = bt["status"]
        if s == "AGE-0": return "AGE-0"
        if s == "UNTRACEABLE": return "UNTRACEABLE"
        if s == "AGE-1": return "AGE-1"
        return "AGE-2+"   # AGE-2..AGE-10+
    def gbucket(g): return [b for b, lo in (("≥$1k", 1000), ("≥$100", 100), ("≥$10", 10)) if g >= lo]
    L = []; A = L.append
    A("# Opportunity-age pilot — how fast is fast enough")
    A("")
    A("> **PILOT / SAMPLE-SIZE CAVEAT [prominent].** This is a **live 10-minute reading (~50 blocks)**, "
      "not the distribution. Counts are tiny; treat every number as a directional pilot, not a "
      "population estimate. Scratch analysis — NOT part of the census.")
    A("")
    A(f"Live window: blocks {data['start']}–{data['end']} ({data['processed']} blocks processed [M]). "
      f"Detected arbs ≥$10 gross: **{len(arbs)}** [M]. RPC calls used: **{data['calls']}** (cap 2,000).")
    A("")
    A("**Age definition [M].** AGE-0 = opportunity created in the capture block itself (an earlier tx "
      "in the same block swaps in ≥1 of the arb's own pools — a same-block backrun; robustly detected). "
      "AGE-N = the arb's cyclic trade was already profitable above gas N blocks earlier, found by "
      "re-reading the same pools' spot state backward (marginal spot-price product, net of fees, vs the "
      "captured gas; depth cap 10 ⇒ 10+). **UNTRACEABLE** = age couldn't be determined: the cycle "
      "couldn't be reconstructed for backward pricing (V4 singleton flash-accounting / non-cyclic / "
      "Curve-Balancer routing) or creation was pending-flow not visible on-chain. **Method limit, "
      "stated:** this chain's arbs are V4-heavy and only a minority form cleanly-reconstructable cycles, "
      "so exact AGE-N (N≥1) is measurable for few arbs; the AGE-0 vs not-AGE-0 signal is the robust one.")
    A("")
    # ---- Task 1: age distribution ----
    A("## 1. Age distribution [M]")
    A("")
    A("| Scope | Arbs | AGE-0 | AGE-1 | AGE-2+ | UNTRACEABLE |")
    A("|---|--:|--:|--:|--:|--:|")
    for scope in ("≥$10", "≥$100", "≥$1k"):
        sub = [a for a in arbs if scope in gbucket(a["gross_usd"])]
        c = Counter(agecat(a["bt"]) for a in sub)
        n = len(sub) or 1
        A(f"| {scope} | {len(sub)} | {c['AGE-0']} ({100*c['AGE-0']/n:.0f}%) | {c['AGE-1']} | "
          f"{c['AGE-2+']} | {c['UNTRACEABLE']} ({100*c['UNTRACEABLE']/n:.0f}%) |")
    A("")
    # ---- Task 2: AGE-1+ exposed profit ----
    A("## 2. AGE-1+ arbs — exposed profit & exposure seconds [M]")
    A("")
    agepos = [a for a in arbs if a["bt"]["status"] not in ("AGE-0", "UNTRACEABLE")]
    if not agepos:
        A("**No AGE-1+ arbs measured in this pilot window.** (Either opportunities were captured in "
          "their creation block, or the older ones fell into UNTRACEABLE because their V4/complex cycle "
          "couldn't be re-priced backward. Listed, not dropped.)")
    else:
        A("| tx | block | gross $ | age (blocks) | exposed ~seconds (age×12s) |")
        A("|---|--:|--:|--:|--:|")
        for a in agepos:
            age = a["bt"]["age"]
            A(f"| `{a['txhash'][:14]}…` | {a['block']} | {f2(a['gross_usd'],0)} | {age} | {age*12} |")
    A("")
    # ---- Task 3: per-arb table ----
    A("## 3. Per-arb table (all detected ≥$10) [M]")
    A("")
    A("| block | gross $ | age class | pools | tx |")
    A("|--:|--:|---|--:|---|")
    for a in sorted(arbs, key=lambda x: (x["block"], -x["gross_usd"])):
        A(f"| {a['block']} | {f2(a['gross_usd'],0)} | {a['bt']['status']} | {len(a['bt']['pools'])} | `{a['txhash'][:12]}…` |")
    A("")
    # ---- Task 4: blocks + untraceable ----
    A("## 4. Coverage & untraceable list [M]")
    A("")
    unt = [a for a in arbs if a["bt"]["status"] == "UNTRACEABLE"]
    A(f"- Blocks processed: **{data['processed']}** [M]. Arbs ≥$10 seen: **{len(arbs)}** [M]. "
      f"Backtraced to an age: **{len(arbs)-len(unt)}**. UNTRACEABLE: **{len(unt)}** "
      f"({100*len(unt)/max(len(arbs),1):.0f}%).")
    A("")
    if unt:
        A("Untraceable arbs (seen, not dropped) — reason:")
        A("")
        A("| tx | block | gross $ | reason |")
        A("|---|--:|--:|---|")
        for a in unt:
            A(f"| `{a['txhash'][:14]}…` | {a['block']} | {f2(a['gross_usd'],0)} | {a['bt'].get('reason','')} |")
    A("")
    A("*Pilot complete. Scratch file — not the census.*")
    with open(os.path.join(OUT, "opportunity_age_pilot.md"), "w") as f:
        f.write("\n".join(L))
    print("wrote out/opportunity_age_pilot.md", flush=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # validate full pipeline on stored census arbs (compute same-block cause from block receipts)
        rows = [json.loads(l) for l in open(os.path.join(OUT, "arbs.jsonl"))]
        cand = [r for r in rows if r["verdict"] == "arb" and (r.get("gross_usd") or 0) >= 10][:20]
        from collections import Counter as C
        dist = C()
        for r in cand:
            rcpts = call("eth_getBlockReceipts", [hex(r["block"])])
            idxp = {h2i(x.get("transactionIndex")): tx_pool_ids(x.get("logs") or [])
                    for x in rcpts if x.get("status") == "0x1"}
            arb_rc = next((x for x in rcpts if x["transactionHash"] == r["txhash"]), None)
            ai = h2i(arb_rc.get("transactionIndex")); my = idxp.get(ai, set())
            cause = any(my & idxp.get(j, set()) for j in range(ai))
            bt = backtrace(r, arb_rc, r["block"], same_block_cause=cause)
            dist[bt["status"]] += 1
            print(f"gross=${r['gross_usd']:>6.0f} blk={r['block']} idx={ai} -> {bt['status']:11} "
                  f"reason={bt.get('reason','')} pools={len(bt['pools'])}")
        print("dist:", dict(dist), "calls:", CC["n"])
    else:
        run()

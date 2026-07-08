"""On-chain pricing at a given block. Never treat token amount as USD.

ETH/USD: Chainlink ETH/USD feed (primary, staleness-checked) with UniV3 USDC/WETH
spot as cross-check/fallback. Method logged per conversion.
Token->WETH: deepest UniV3/UniV2 token/WETH pool spot at the block. Tokens without a
reliable pool -> UNPRICEABLE (value_eth=None), listed separately, never silently valued.
"""
from census.rpc import call
from census.config import (
    ETH_RPC_ARCHIVE, CHAINLINK_ETH_USD, USDC_WETH_V3_005, V3_FACTORY, V2_FACTORY,
    WETH, USDC, USDT, STABLES,
)

RPC = ETH_RPC_ARCHIVE
def _call(to, data, block):
    r = call("eth_call", [{"to": to, "data": data}, hex(block)], rpc=RPC)
    if isinstance(r, dict):  # error/fail
        return None
    return r

_dec_cache = {}
def decimals(token):
    token = token.lower()
    if token == WETH: return 18
    if token in _dec_cache: return _dec_cache[token]
    r = _call(token, "0x313ce567", 25487778)  # decimals() at head (immutable)
    d = int(r, 16) if r and len(r) >= 3 else None
    if d is None or d > 36: d = 18
    _dec_cache[token] = d
    return d

_ethusd_cache = {}
def eth_usd(block, block_ts=None):
    """Return (usd_per_eth, method). Cache per block."""
    if block in _ethusd_cache: return _ethusd_cache[block]
    method = None; price = None
    r = _call(CHAINLINK_ETH_USD, "0xfeaf968c", block)  # latestRoundData()
    if r and len(r) >= 2+64*5:
        d = r[2:]
        ans = int(d[64:128], 16)
        updated = int(d[192:256], 16)
        if ans > 0:
            stale = (block_ts is not None and updated < block_ts - 7200)  # >2h stale
            price = ans/1e8
            method = f"chainlink_eth_usd(updatedAt={updated}{',STALE' if stale else ''})"
            if stale: price = None; method = None  # fall through to pool
    if price is None:
        r = _call(USDC_WETH_V3_005, "0x3850c7bd", block)  # slot0()
        if r and len(r) > 66:
            sqrtP = int(r[2:66], 16)
            p = (sqrtP**2)/(2**192)  # WETH(1e18) per USDC(1e6) raw
            if p > 0:
                price = 1e12/p  # USDC per WETH
                method = "univ3_usdc_weth_005_spot"
    out = (price, method)
    _ethusd_cache[block] = out
    return out

HEAD = 25487778
def _pools_against(token, quote):
    """Find all token/quote pools (V3 fee tiers + V2), return list of
    (kind, pool, token_is_0, fee, quote) with quote-asset balance as depth proxy."""
    token = token.lower(); quote = quote.lower()
    t0, t1 = (token, quote) if token < quote else (quote, token)
    token_is_0 = token < quote
    found = []
    for fee in (100, 500, 3000, 10000):
        data = "0x1698ee82" + t0[2:].rjust(64, "0") + t1[2:].rjust(64, "0") + hex(fee)[2:].rjust(64, "0")
        r = _call(V3_FACTORY, data, HEAD)
        if r and int(r, 16) != 0:
            pool = "0x" + r[-40:]
            qbal = _call(quote, "0x70a08231" + pool[2:].rjust(64, "0"), HEAD)
            found.append(("v3", pool, token_is_0, fee, quote, int(qbal, 16) if qbal else 0))
    data = "0xe6a43905" + t0[2:].rjust(64, "0") + t1[2:].rjust(64, "0")
    r = _call(V2_FACTORY, data, HEAD)
    if r and int(r, 16) != 0:
        pool = "0x" + r[-40:]
        qbal = _call(quote, "0x70a08231" + pool[2:].rjust(64, "0"), HEAD)
        found.append(("v2", pool, token_is_0, None, quote, int(qbal, 16) if qbal else 0))
    return found

_pool_cache = {}
def _find_pool(token):
    """Discover deepest token/{WETH|USDC|USDT} pool. Prefer WETH; fall back to stables so
    tokens that only pair with a stablecoin are still priceable. Returns
    (kind, pool, token_is_0, fee, quote) or None. Cached per token."""
    token = token.lower()
    if token in _pool_cache: return _pool_cache[token]
    # WETH first (depth in WETH wei)
    weth_pools = _pools_against(token, WETH)
    best = None
    if weth_pools:
        p = max(weth_pools, key=lambda x: x[5])
        if p[5] >= MIN_WETH_DEPTH:
            best = p[:5]
    if best is None:
        # stable-paired: depth in stable smallest-unit; require >= ~$300 => 3e8 (6dec)
        stable_best = None; stable_depth = -1
        for q in (USDC, USDT):
            for p in _pools_against(token, q):
                if p[5] > stable_depth:
                    stable_depth = p[5]; stable_best = p
        if stable_best and stable_depth >= 3*10**8:
            best = stable_best[:5]
    _pool_cache[token] = best
    return best

MIN_WETH_DEPTH = 3 * 10**17     # 0.3 WETH minimum pool depth to price reliably
SANE_ETH_PER_TOKEN = 2000.0     # >2000 ETH (~$3.4M) per single token unit => broken pool, reject

def token_to_eth(token, raw_amount, block):
    """Value a raw token amount in ETH at `block`. Returns (value_eth, method).
    value_eth None => UNPRICEABLE."""
    token = token.lower()
    dec = decimals(token)
    human = raw_amount / (10**dec)
    if token == WETH:
        return human, "weth_native"
    if token in STABLES:
        usd, m = eth_usd(block)
        if usd: return (raw_amount/(10**STABLES[token]))/usd, f"stable/{m}"
        return None, "stable_no_ethusd"
    pool = _find_pool(token)
    if not pool:
        return None, "no_pool"
    kind, pooladdr, token_is_0, fee, quote = pool
    qdec = 18 if quote == WETH else STABLES.get(quote, 18)
    # quote_per_token (human) from pool spot at the arb block
    if kind == "v3":
        r = _call(pooladdr, "0x3850c7bd", block)  # slot0
        if not r or len(r) < 66: return None, "v3_slot0_fail"
        sqrtP = int(r[2:66], 16)
        p_raw = (sqrtP**2)/(2**192)  # token1_wei per token0_wei
        d0 = dec if token_is_0 else qdec
        d1 = qdec if token_is_0 else dec
        token1_per_token0 = p_raw * 10**(d0-d1)  # human
        quote_per_token = token1_per_token0 if token_is_0 else (1/token1_per_token0 if token1_per_token0 else 0)
        src = f"univ3:{pooladdr[:10]}:{fee}"
    else:
        r = _call(pooladdr, "0x0902f1ac", block)  # getReserves
        if not r or len(r) < 130: return None, "v2_reserves_fail"
        r0 = int(r[2:66], 16); r1 = int(r[66:130], 16)
        if token_is_0:
            if r0 == 0: return None, "v2_zero"
            quote_per_token = (r1/10**qdec)/(r0/10**dec)
        else:
            if r1 == 0: return None, "v2_zero"
            quote_per_token = (r0/10**qdec)/(r1/10**dec)
        src = f"univ2:{pooladdr[:10]}"
    # eth per ONE human token
    if quote == WETH:
        eth_per_token = quote_per_token; qtag = "WETH"
    else:
        usd, m = eth_usd(block)
        if not usd:
            return None, "stable_quote_no_ethusd"
        eth_per_token = quote_per_token/usd; qtag = ("USDC" if quote == USDC else "USDT") + "->" + m
    # sanity: no real token is worth > SANE_ETH_PER_TOKEN ETH per unit. A larger figure means a
    # thin/broken/manipulated pool -> refuse to value (unpriceable), never emit a garbage number.
    if not (0 <= eth_per_token <= SANE_ETH_PER_TOKEN):
        return None, f"implausible_unit_price({eth_per_token:.2e}eth/token,{src})"
    return human*eth_per_token, f"{src}({qtag})@{block}"

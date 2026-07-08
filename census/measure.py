"""Combine detection + trace + pricing into a full per-arb measurable record."""
from census.detect import classify_tx, numeraire_profit
from census.trace import trace_tx, h2i
from census.price import token_to_eth, eth_usd, decimals
from census.config import WETH, DUST_WEI, GROSS_MIN_ETH, NUMERAIRE, NUMERAIRE_DUST

ETH_PSEUDO = "native_eth"
MIN_TOKEN_UNITS = 1e-3   # >=0.001 token units => a material amount worth flagging as unpriceable
DUST_TOKEN_UNITS = 1e-9  # <1e-9 token units => incidental dust residual, ignore entirely
SANE_GROSS_ETH = 30000.0 # a single atomic arb grossing >30000 ETH (~$50M) is implausible => mispriced

def material(token, raw):
    """Decimals-aware materiality: is |raw| a non-trivial amount of this token?
    NEVER compare raw deltas of different-decimal tokens with a flat wei threshold."""
    return abs(raw) >= (10**decimals(token)) * MIN_TOKEN_UNITS

def is_dust(token, raw):
    """Below a billionth of a token: incidental residual (e.g. raw=1 wei of an 18-dec token)."""
    return abs(raw) < (10**decimals(token)) * DUST_TOKEN_UNITS

def measure_arb(receipt, block_ctx, res=None):
    """block_ctx: dict(miner, base_fee, ts, number). res: optional precomputed classify_tx.
    Returns full record dict."""
    if res is None:
        res = classify_tx(receipt)
    txh = receipt["transactionHash"]
    miner = block_ctx["miner"].lower()
    beneficiary = res["beneficiary"]
    deltas = res["deltas"]

    # ---- trace for native ETH deltas + coinbase ----
    tr = trace_tx(txh, miner)
    eth_delta = tr.get("eth_delta", {})
    builder_coinbase_wei = tr.get("builder_coinbase", 0)

    # beneficiary asset deltas: logged tokens (>0 kept as profit) + native ETH
    ben_tokens = dict(deltas.get(beneficiary, {}))
    ben_eth = eth_delta.get(beneficiary, 0)

    blk = block_ctx["number"]; ts = block_ctx["ts"]
    usd_per_eth, usd_method = eth_usd(blk, ts)

    priced = []; unpriceable_gain = []
    value_eth = 0.0            # V_signed: signed sum of priced beneficiary deltas
    has_unpriceable_loss = False
    # value ALL beneficiary asset deltas SIGNED (a -54 USDC 'buy' must count negatively)
    assets = dict(ben_tokens)
    if ben_eth != 0:
        assets[ETH_PSEUDO] = ben_eth
    for asset, raw in assets.items():
        if asset == ETH_PSEUDO:
            if abs(raw) < 10**12:              # <1e-6 ETH native dust
                continue
            ve = raw/1e18; priced.append((asset, raw, ve, "native_eth")); value_eth += ve
            continue
        if is_dust(asset, raw):
            continue                            # incidental residual (raw=1..2 of an 18-dec token)
        ve, method = token_to_eth(asset, raw, blk)
        if ve is None:
            if not material(asset, raw):
                continue                        # sub-material unpriceable delta: ignore
            if raw > 0:
                unpriceable_gain.append((asset, raw))
            else:
                has_unpriceable_loss = True     # MATERIAL outflow we cannot value -> gross uncertain
            continue
        priced.append((asset, raw, ve, method)); value_eth += ve

    # ---- builder payment: native ETH to miner + tokens to miner ----
    builder_eth = builder_coinbase_wei/1e18
    builder_method = "coinbase_native"
    miner_tokens = deltas.get(miner, {})
    for t, v in miner_tokens.items():
        if v > DUST_WEI:
            mv, _ = token_to_eth(t, v, blk)
            if mv: builder_eth += mv; builder_method = "coinbase_native+token_to_miner"

    # ---- gas ----
    gas_used = h2i(receipt.get("gasUsed"))
    egp = h2i(receipt.get("effectiveGasPrice"))
    gas_cost_eth = gas_used*egp/1e18
    base_fee = block_ctx.get("base_fee", 0)
    priority_to_builder_eth = gas_used*max(egp-base_fee, 0)/1e18

    V = value_eth  # net position captured (coinbase already netted out)
    gross_eth = V + builder_eth
    net_eth = V - gas_cost_eth

    def usd(x):
        return x*usd_per_eth if (usd_per_eth and x is not None) else None

    # mempool-origin heuristic: coinbase transfer => private bundle; else priority-fee-only => likely public
    if builder_coinbase_wei > 0:
        mempool = "private_bundle(coinbase_xfer)"
    elif priority_to_builder_eth > 0:
        mempool = "likely_public(priority_fee_only)"
    else:
        mempool = "undetermined"

    # ---- self-financing check (redemption / inventory-realization guard) ----
    # A real atomic arb skims a spread: profit is a small fraction of the asset volume swapped
    # through pools. A redemption pulls the profit asset from a NON-pool contract, so profit far
    # exceeds recognized pool volume. We flag ONLY egregious + high-value cases (ratio > 5x AND
    # gross > 2 ETH) so that V4 flash-accounting / aggregator-settled small arbs (whose profit
    # token legitimately arrives from a non-pool settlement address, undercounting pool_volume)
    # are NOT swept up. Native ETH exempt (tracked via traces, not logs).
    # A real atomic arb skims a thin spread: profit is a SMALL fraction of pool volume (empirically
    # <5%; ratio<0.05). Profit >= 50% of the pool volume of that asset (ratio>0.5) implies a >200%
    # single-tx return -- not arbitrage but redemption / inventory-realization / pool-drain / exploit.
    # Gate on gross>2 ETH so V4/aggregator-settled small arbs (whose pool_volume is undercounted)
    # are not swept up. Flagged records are EXCLUDED as non-atomic, not counted as arbs.
    pool_vol = (res.get("meta") or {}).get("pool_volume", {})
    high_margin = any(
        raw > 0 and not is_dust(asset, raw) and raw > pool_vol.get(asset, 0) * 0.5
        for asset, raw in ben_tokens.items())

    # ---- value-based confirmation / routing ----
    # verdict in {arb, unpriceable, route_or_user, failed_measure}
    num_prof = numeraire_profit(ben_tokens)
    if not tr.get("ok", False):
        verdict = "failed_measure"; reason = "trace_failed"
    elif high_margin and gross_eth > 2.0:
        verdict = "excluded_nonatomic"; reason = "high_margin_nonatomic"  # redemption/inventory/drain, not atomic arb
    elif has_unpriceable_loss:
        verdict = "failed_measure"; reason = "unpriceable_outflow"
    elif abs(gross_eth) > SANE_GROSS_ETH or abs(net_eth) > SANE_GROSS_ETH:
        verdict = "failed_measure"; reason = "implausible_valuation"  # residual mispricing backstop
    elif gross_eth > GROSS_MIN_ETH:
        verdict = "arb"; reason = None
    elif unpriceable_gain and gross_eth <= GROSS_MIN_ETH:
        # primary profit is a token we cannot price -> UNPRICEABLE (never silently valued)
        verdict = "unpriceable"; reason = "unpriceable_profit_token"
    else:
        # priced cycle nets <= dust: a sell / wash / mis-triggered candidate, not a real arb
        verdict = "route_or_user"; reason = "gross_below_min"

    multi_asset = len([1 for a, raw, ve, m in priced if ve > 0 and abs(ve) > GROSS_MIN_ETH]) >= 2
    fully_unpriceable = (verdict == "unpriceable")

    return dict(
        verdict=verdict, reason=reason,
        txhash=txh, block=blk, tx_index=h2i(receipt.get("transactionIndex")),
        status=receipt.get("status"),
        beneficiary=beneficiary, tx_from=(receipt.get("from") or "").lower(),
        tx_to=(receipt.get("to") or "").lower(),
        n_swaps=res["n_swaps"], has_flash=res["has_flash"], multi_asset=multi_asset,
        cand_kind=res.get("cand_kind"),
        priced=priced, unpriceable=unpriceable_gain,
        value_eth=V, gross_eth=gross_eth, net_eth=net_eth,
        gross_usd=usd(gross_eth), net_usd=usd(net_eth),
        eth_usd=usd_per_eth, eth_usd_method=usd_method,
        builder_eth=builder_eth, builder_method=builder_method, builder_usd=usd(builder_eth),
        priority_to_builder_eth=priority_to_builder_eth,
        gas_used=gas_used, effective_gas_price=egp, gas_cost_eth=gas_cost_eth, gas_cost_usd=usd(gas_cost_eth),
        mempool_origin=mempool,
        fully_unpriceable=fully_unpriceable,
        trace_ok=tr.get("ok", False),
    )

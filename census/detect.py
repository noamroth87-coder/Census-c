"""Atomic-arb detection from block receipts (log-only balance deltas).

Core idea (pool-agnostic): compute net balance delta per (address, token) from ERC20
Transfer + WETH Deposit/Withdrawal logs. An atomic-arb beneficiary is an address that:
  - ends NON-NEGATIVE in every token it touched (>= -dust), and
  - ends STRICTLY POSITIVE in >= 1 token, and
  - was involved in >= 2 DEX swap events (a value cycle).
A DEX pool always ends a swap down one token, so pools are auto-excluded by the
non-negative-in-all rule. Routers/aggregators are excluded explicitly (profit never
accrues to the router). Native-ETH deltas are added later from traces for candidates.
"""
from census.config import (
    TRANSFER, WETH_DEPOSIT, WETH_WITHDRAW, SWAP_TOPICS, LIQUIDATION_TOPICS,
    V3_MINT, V3_BURN, FLASH_TOPICS, WETH, ROUTERS, DUST_WEI,
)

V2_SYNC = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
# Any address emitting one of these AMM events in the tx is a pool, never the arbitrageur.
AMM_EVENT_TOPICS = set(SWAP_TOPICS) | {V2_SYNC, V3_MINT, V3_BURN}

def h2i(x):
    return int(x, 16) if isinstance(x, str) else int(x)

def topic_addr(t):
    return "0x" + t[-40:]

def parse_receipt_logs(logs):
    """Return (deltas, swaps, meta) for one tx.
    deltas: {addr: {token: int}}  net balance change from Transfer + WETH dep/wd.
    swaps: list of pool addresses where a swap occurred.
    meta: flags dict (n_swaps, has_liq, has_flash, has_mint, has_burn, tokens set,
          swap_actors set, transfer_parse_error bool).
    """
    deltas = {}
    swaps = []
    swap_actors = set()
    amm_addrs = set()
    tokens = set()
    xfers = []  # (token, frm, to, val) for pool-volume pass
    has_liq = has_flash = has_mint = has_burn = False
    parse_error = False

    def add(addr, token, amt):
        addr = addr.lower(); token = token.lower()
        d = deltas.setdefault(addr, {})
        d[token] = d.get(token, 0) + amt

    for lg in logs:
        topics = lg.get("topics") or []
        if not topics:
            continue
        t0 = topics[0].lower()
        addr = lg["address"].lower()
        data = lg.get("data", "0x")
        if t0 in AMM_EVENT_TOPICS:
            amm_addrs.add(addr)
        if t0 == TRANSFER:
            # standard: from,to indexed; value in data. Non-standard (transfer w/o 3 topics) flagged.
            if len(topics) == 3 and len(data) >= 66:
                try:
                    frm = topic_addr(topics[1]); to = topic_addr(topics[2]); val = h2i(data[:66])
                    add(frm, addr, -val); add(to, addr, val); tokens.add(addr)
                    xfers.append((addr, frm.lower(), to.lower(), val))
                except Exception:
                    parse_error = True
            elif len(topics) == 1 and len(data) >= 194:
                # ERC20 with non-indexed from/to (rare) -> ambiguous, mark parse error (measure via trace)
                parse_error = True
            # NFT Transfer (4 topics) ignored for value accounting
        elif t0 == WETH_DEPOSIT and addr == WETH and len(topics) >= 2:
            try:
                add(topic_addr(topics[1]), WETH, h2i(data[:66])); tokens.add(WETH)
            except Exception:
                parse_error = True
        elif t0 == WETH_WITHDRAW and addr == WETH and len(topics) >= 2:
            try:
                add(topic_addr(topics[1]), WETH, -h2i(data[:66])); tokens.add(WETH)
            except Exception:
                parse_error = True
        elif t0 in SWAP_TOPICS:
            swaps.append(addr)
            for tp in topics[1:3]:
                if len(tp) == 66:
                    swap_actors.add(topic_addr(tp))
        elif t0 in LIQUIDATION_TOPICS:
            has_liq = True
        elif t0 == V3_MINT:
            has_mint = True
        elif t0 == V3_BURN:
            has_burn = True
        elif t0 in FLASH_TOPICS:
            has_flash = True

    # pool-volume per token: how much of each token actually flowed through DEX pools.
    # An atomic arb cannot skim more of an asset than was swapped through pools; a redemption /
    # inventory-realization moves the asset via a NON-pool contract and fails this bound.
    pool_volume = {}
    for token, frm, to, val in xfers:
        if frm in amm_addrs or to in amm_addrs:
            pool_volume[token] = pool_volume.get(token, 0) + val

    meta = dict(n_swaps=len(swaps), pools=swaps, amm_addrs=amm_addrs, swap_actors=swap_actors,
                tokens=tokens, pool_volume=pool_volume, has_liq=has_liq, has_flash=has_flash,
                has_mint=has_mint, has_burn=has_burn, parse_error=parse_error)
    return deltas, swaps, meta

from census.config import NUMERAIRE, NUMERAIRE_DUST

def numeraire_profit(d):
    """Return dict of numeraire assets the address is net-positive in above decimals-aware dust."""
    return {t: v for t, v in d.items() if t in NUMERAIRE and v > NUMERAIRE_DUST[t]}

def _cand_kind(d):
    """Candidate trigger for one address's deltas, or None."""
    if numeraire_profit(d):
        return "numeraire"
    if d.get(WETH, 0) < -DUST_WEI:       # WETH withdrawal -> possible native-ETH settle
        return "eth_settle"
    if any(t not in NUMERAIRE and v > 0 for t, v in d.items()):
        return "token_denominated"
    return None

def pick_beneficiary(deltas, tx_from, tx_to, amm_addrs):
    """The arbitrageur controls tx.from (EOA) or tx.to (bot contract). Consider BOTH
    (excluding pools/routers) and pick the one that actually shows an arb signal, preferring
    numeraire profit; this avoids being fooled by a pass-through tx_to that nets ~0 while the
    EOA holds the profit. Precision-over-recall bound: arbs sweeping profit to a separate
    treasury fall to route_or_user (documented)."""
    tx_from = (tx_from or "").lower(); tx_to = (tx_to or "").lower()
    amm_addrs = set(a.lower() for a in (amm_addrs or []))
    rank = {"numeraire": 3, "eth_settle": 2, "token_denominated": 1, None: 0}
    best = (None, None, -1)
    for addr in (tx_to, tx_from):
        if not addr or addr in ROUTERS or addr in amm_addrs or not deltas.get(addr):
            continue
        k = _cand_kind(deltas[addr])
        if rank[k] > best[2]:
            best = (addr, k, rank[k])
    return best[0], best[1]

def classify_tx(receipt, tx_from=None, tx_to=None):
    """Classify one tx receipt (log-only, cheap). 'cls' in:
      liquidation | jit | non_dex | route_or_user | arb_candidate | failed_measure
    arb_candidate is CONFIRMED later in measure_arb via value-based gross (prices signed
    deltas). This avoids the flat-dust decimals trap: a -54 USDC 'buy' is NOT dust and must
    be caught by pricing, not raw thresholds. Candidate triggers:
      (a) beneficiary net-positive in a numeraire (WETH/stable) above decimals-aware dust, or
      (b) beneficiary has a WETH withdrawal (-WETH) with >=2 swaps => possible native-ETH-settle
          (confirmed via trace), or
      (c) beneficiary net-positive in a non-numeraire token (token-denominated arb candidate).
    Only status==0x1 txs carry logs (reverts emit none)."""
    logs = receipt.get("logs") or []
    tx_from = tx_from or receipt.get("from")
    tx_to = tx_to or receipt.get("to")
    deltas, swaps, meta = parse_receipt_logs(logs)

    res = dict(cls="non_dex", n_swaps=meta["n_swaps"], has_flash=meta["has_flash"],
               has_liq=meta["has_liq"], meta=meta, beneficiary=None, deltas=deltas,
               cand_kind=None)

    if meta["has_liq"]:
        res["cls"] = "liquidation"; return res
    if meta["n_swaps"] < 2:
        res["cls"] = "non_dex" if meta["n_swaps"] == 0 else "route_or_user"
        return res
    if meta["has_mint"] and meta["has_burn"]:
        res["cls"] = "jit"; return res

    ben, kind = pick_beneficiary(deltas, tx_from, tx_to, meta["amm_addrs"])
    if ben is None or kind is None:
        res["cls"] = "route_or_user"
        if meta["parse_error"]:
            res["cls"] = "failed_measure"; res["reason"] = "non_standard_transfer_events"
        return res

    res["cls"] = "arb_candidate"; res["cand_kind"] = kind
    res["beneficiary"] = ben
    if meta["parse_error"]:
        res["needs_trace_verify"] = True
    return res

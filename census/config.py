"""Configuration & on-chain constants for the ETH mainnet atomic-arb census."""
import os

ETH_RPC = os.environ.get("ETH_RPC", "https://ethereum-mainnet.core.chainstack.com/cc5ea38c3664bd8ef5fdae785239d25f")
ETH_RPC_ARCHIVE = os.environ.get("ETH_RPC_ARCHIVE", ETH_RPC)

WINDOW_DAYS = 7
BLOCK_TIME = 12  # seconds (measured on-chain)

# ---- Event topic0 signatures ----
TRANSFER      = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # ERC20 Transfer(from,to,value)
WETH_DEPOSIT  = "0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c"  # Deposit(dst,wad)
WETH_WITHDRAW = "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65"  # Withdrawal(src,wad)
V2_SWAP       = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"  # UniV2 Swap
V3_SWAP       = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"  # UniV3 Swap
V4_SWAP       = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"  # UniV4 Swap (PoolManager)
BALANCER_SWAP = "0x2170c741c41531aec20e7c107c24eecfdd15e69c9bb0a8dd37b1840b9e0b207b"  # Balancer Vault Swap
CURVE_TOKEN_EXCHANGE   = "0x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140"  # TokenExchange
CURVE_TOKEN_EXCHANGE_U = "0xd013ca23e77a65003c2c659c5442c00c805371b7fc1ebd4c206c41d1536bd90b"  # TokenExchangeUnderlying

SWAP_TOPICS = {V2_SWAP, V3_SWAP, V4_SWAP, BALANCER_SWAP, CURVE_TOKEN_EXCHANGE, CURVE_TOKEN_EXCHANGE_U}

# ---- Exclusion event signatures ----
# Liquidations
AAVE_V2_LIQ   = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"  # LiquidationCall
AAVE_V3_LIQ   = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
COMPOUND_LIQ  = "0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52"  # LiquidateBorrow
MAKER_BITE    = "0x99b5620489b6ef926d4518936cfec15d305452712b88bd59da2d9c10fb0953e8"
LIQUIDATION_TOPICS = {AAVE_V2_LIQ, AAVE_V3_LIQ, COMPOUND_LIQ, MAKER_BITE}

# JIT liquidity (UniV3)
V3_MINT = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
V3_BURN = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"

# ---- Flash-loan event signatures ----
AAVE_V2_FLASH   = "0x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac"  # FlashLoan
AAVE_V3_FLASH   = "0xefefaba5e921573100900a3ad9cf29f222d995fb3b6045797eaea7521bd8d6f0"  # FlashLoan (v3)
BALANCER_FLASH  = "0x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0"  # FlashLoan
DYDX_FLASH      = None
UNIV3_FLASH     = "0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633"  # Flash
MAKER_FLASH     = "0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885"  # (dss-flash) generic
FLASH_TOPICS = {AAVE_V2_FLASH, AAVE_V3_FLASH, BALANCER_FLASH, UNIV3_FLASH, MAKER_FLASH}

# ---- Key addresses ----
WETH  = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC  = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT  = "0xdac17f958d2ee523a2206206994597c13d831ec7"
DAI   = "0x6b175474e89094c44da98b954eedeac495271d0f"
WBTC  = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"

CHAINLINK_ETH_USD = "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"
V3_FACTORY = "0x1f98431c8ad98523631ae4a59f267346ea31f984"
V2_FACTORY = "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"
USDC_WETH_V3_005 = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # deepest ETH/USD pool

# Known routers/aggregators — a tx whose *beneficiary* is one of these is a user route, not an arb bot.
# (Bots occasionally reuse routers, but profit never accrues to the router itself.)
ROUTERS = {
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # UniV2 router
    "0xe592427a0aece92de3edee1f18e0157c05861564",  # UniV3 SwapRouter
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",  # UniV3 SwapRouter02
    "0x66a9893cc07d91d95644aedd05d03f95e1dba8af",  # UniversalRouter
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",  # UniversalRouter (old)
    "0x1111111254eeb25477b68fb85ed929f73a960582",  # 1inch v5
    "0x111111125421ca6dc452d289314280a0f8842a65",  # 1inch v6
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff",  # 0x exchange proxy
    "0x6131b5fae19ea4f9d964eac0408e4408b66337b5",  # KyberSwap meta
    "0x881d40237659c251811cec9c364ef91dc08d300c",  # Metamask router
    "0x000000000022d473030f116ddee9f6b43ac78ba3",  # Permit2
}

# Stable/blue-chip tokens directly priceable
STABLES = {USDC: 6, USDT: 6, DAI: 18}

DUST_WEI = 10**13  # ~1e-5 ETH; used only for WETH/ETH-scale noise, NOT cross-token (decimals differ!)

# Numeraire assets: an atomic arb extracts value into one of these liquid base assets.
# Detection profits are measured in these; value-based, decimals-aware.
NUMERAIRE = {WETH: 18, USDC: 6, USDT: 6, DAI: 18}
# Per-asset raw dust ~ $0.01-scale, decimals-aware (avoids the flat-threshold decimals trap).
NUMERAIRE_DUST = {WETH: 5*10**12, USDC: 10**4, USDT: 10**4, DAI: 5*10**15}
GROSS_MIN_ETH = 5e-6   # ~$0.01: below this a "profit" is noise, not a counted arb

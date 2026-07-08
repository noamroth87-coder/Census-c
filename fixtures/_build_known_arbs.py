"""Build fixtures/known_arbs.jsonl from the census outputs.

PROVENANCE NOTE (read fixtures/README.md): the read-only clone at fixtures/census-raw/
contains only the COMMITTED files — reports + code. The three raw datasets this fixture
draws from are .gitignored (large, regenerable) and therefore ABSENT from the clone:
    out/arbs.jsonl        (census arb dataset)      -> sets census_sample_seed42, lane_v4_touch
    out/lane_sight.json   (lane-census sight recs)  -> set lane_v4_touch
    out/oppage_raw.json   (opportunity-age pilot)   -> sets pilot_untraceable, pilot_age0
This script therefore reads the WORKING-TREE regenerable outputs (out/*), not the clone.
Every value written is a real measured value; nothing is invented. Where a field is not
stored in the source, it is emitted as null and documented as a gap in the README.
"""
import json, random

OUT = "out"
SEED = 42
ETH_USD_CENSUS = 1568.424        # census-window Chainlink rate (task's $1,568)

def _load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            try: rows.append(json.loads(line))
            except Exception: pass
    return rows

records = []

# ---- Set A: pilot 7 UNTRACEABLE + Set D: pilot 3 AGE-0 (from oppage_raw.json 'bt') ----
opp = json.load(open(f"{OUT}/oppage_raw.json"))
for a in opp["arbs"]:
    bt = a.get("bt") or {}
    status = bt.get("status")
    if status == "UNTRACEABLE":
        records.append(dict(
            set="pilot_untraceable",
            tx=a["txhash"], block=a["block"],
            gross_usd=round(a["gross_usd"], 4), eth_usd=a["eth_usd"],
            failure_reason=bt.get("reason"),
            pools_touched=bt.get("pools"),      # pools the backtrace could read (may be partial)
            source="out/oppage_raw.json[.arbs[].bt]  (gitignored; committed pilot .md truncates tx & gives pool COUNT only)"))
    elif status == "AGE-0":
        records.append(dict(
            set="pilot_age0",
            tx=a["txhash"], block=a["block"], age=bt.get("age"),
            age_reason=bt.get("reason"),
            pools=bt.get("pools"),
            gross_usd=round(a["gross_usd"], 4), eth_usd=a["eth_usd"],
            source="out/oppage_raw.json[.arbs[].bt]  (gitignored; committed pilot .md truncates tx & gives pool COUNT only)"))

# ---- Set B: seed-42 random 200-arb sample from the census arb dataset ----
arbs = [r for r in _load_jsonl(f"{OUT}/arbs.jsonl") if r.get("verdict") == "arb"]
rng = random.Random(SEED)
sample = rng.sample(arbs, 200)          # random.Random(42).sample(arbs_in_file_order, 200)
for r in sample:
    net_eth = r.get("net_eth")
    records.append(dict(
        set="census_sample_seed42",
        tx=r["txhash"], block=r["block"],
        net_wei=(int(round(net_eth * 1e18)) if net_eth is not None else None),
        net_usd=(round(r["net_usd"], 6) if r.get("net_usd") is not None else None),
        gross_usd=(round(r["gross_usd"], 6) if r.get("gross_usd") is not None else None),
        gross_eth=r.get("gross_eth"),
        gas_cost_eth=r.get("gas_cost_eth"), gas_used=r.get("gas_used"),
        builder_eth=r.get("builder_eth"), builder_usd=r.get("builder_usd"),
        eth_usd=r.get("eth_usd"),
        source="out/arbs.jsonl (gitignored, regenerable; verdict==arb) | seed=random.Random(42).sample(arbs_in_file_order,200)"))

# ---- Set C: 20 V4-touching measured arbs via lane-census sight receipts ----
ls = json.load(open(f"{OUT}/lane_sight.json"))
sight = ls["sight"]                       # {txhash: {v4, v2v3, pure}}
lane_of = {}                              # txhash -> lane venue (a pool/venue id)
for lane, txs in ls["lane_arbs"].items():
    for t in txs: lane_of.setdefault(t, lane)
# join to arbs.jsonl for block + gross (sight stores neither)
by_tx = {r["txhash"]: r for r in arbs}
v4 = 0
for tx, cls in sight.items():
    if v4 >= 20: break
    if cls.get("v4", 0) <= 0: continue
    r = by_tx.get(tx)
    if not r: continue                    # keep only measured arbs we can attach block+gross to
    records.append(dict(
        set="lane_v4_touch",
        tx=tx, block=r["block"],
        v4_swaps=cls.get("v4"), v2v3_swaps=cls.get("v2v3"),
        lane_venue=lane_of.get(tx),       # the lane pool this arb was reused into (a stored pool)
        gross_usd=(round(r["gross_usd"], 6) if r.get("gross_usd") is not None else None),
        gross_eth=r.get("gross_eth"), eth_usd=r.get("eth_usd"),
        pools_full=None,                  # GAP: lane_sight stores swap-TYPE counts, not pool addrs
        source="out/lane_sight.json[.sight] (v4>0) + out/arbs.jsonl for block/gross (both gitignored)"))
    v4 += 1

with open("fixtures/known_arbs.jsonl", "w") as f:
    for rec in records:
        f.write(json.dumps(rec) + "\n")

from collections import Counter
c = Counter(r["set"] for r in records)
print("wrote fixtures/known_arbs.jsonl:", dict(c), "total", len(records))

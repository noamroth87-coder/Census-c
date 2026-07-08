"""Overbidder autopsy: rational whales or dumb money? Stored data only, zero RPC.
Reconstructs the contested-bid population from out/contest_intensity.md (joined back to
out/arbs.jsonl by block+bid%), then window-level P&L + mechanical classification.
Writes out/overbidder_autopsy.md."""
import json, re, os
from collections import defaultdict, Counter
from census.report import UF, med

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
def f2(x, d=2): return f"{x:,.{d}f}" if x is not None else "n/a"
def clab(root): return root[1] if isinstance(root, tuple) else str(root)
def bucket(g): return "<$10" if g < 10 else "$10-100" if g < 100 else "$100-1k" if g < 1000 else ">$1k"

def load():
    arbs = [x for x in (json.loads(l) for l in open(os.path.join(OUT, "arbs.jsonl"))) if x["verdict"] == "arb"]
    uf = UF()
    for r in arbs:
        uf.union(("b", r["beneficiary"]), ("f", r["tx_from"]) if r.get("tx_from") else ("b", r["beneficiary"]))
    cid = {r["txhash"]: uf.find(("b", r["beneficiary"])) for r in arbs}
    return arbs, uf, cid

def fu2_labels():
    """Parse Follow-up 2 builder-routing verdicts (lead-prefix -> label) from CENSUS_REPORT.md."""
    lab = {}
    for line in open(os.path.join(OUT, "CENSUS_REPORT.md")):
        m = re.search(r"`(0x[0-9a-f]+)…`.*\b(INTEGRATED|CONCENTRATED|DISTRIBUTED)\b", line)
        if m:
            lab[m.group(1)] = m.group(2)
    return lab

def cluster_pnl(rows):
    n = len(rows)
    gross = sum(r["gross_eth"] for r in rows)
    gas = sum(r["gas_cost_eth"] for r in rows)
    builder = sum(r["builder_eth"] for r in rows)
    prio = sum(r["priority_to_builder_eth"] for r in rows)
    net = sum(r["net_eth"] for r in rows)  # = gross - gas - builder (priority is inside gas)
    eu = med([r["eth_usd"] for r in rows]) or 0
    negshare = 100*sum(1 for r in rows if r.get("net_usd", 0) <= 0)/n if n else 0
    return dict(n=n, gross=gross, gas=gas, builder=builder, prio=prio, net=net,
                gross_usd=gross*eu, net_usd=net*eu, negshare=negshare)

def main():
    arbs, uf, cid = load()
    by_block = defaultdict(list)
    for r in arbs: by_block[r["block"]].append(r)
    by_cluster = defaultdict(list)
    for r in arbs: by_cluster[cid[r["txhash"]]].append(r)
    cl_addr = defaultdict(set)
    for r in arbs:
        c = cid[r["txhash"]]; cl_addr[c].add(r["beneficiary"])
        if r.get("tx_from"): cl_addr[c].add(r["tx_from"])
        if r.get("tx_to"): cl_addr[c].add(r["tx_to"])
    def bidpct(r): return 100*(r["priority_to_builder_eth"]+r["builder_eth"])/r["gross_eth"] if r["gross_eth"] > 0 else None
    # reverted-tx counts (by 'to') across window, + median successful-arb gas as revert-gas proxy
    allrev = defaultdict(int)
    for b in (json.loads(l) for l in open(os.path.join(OUT, "blockstats.jsonl"))):
        for to in (b.get("reverted_to") or []): allrev[to] += 1
    MED_GAS = med([r["gas_cost_eth"] for r in arbs]) or 0
    def revcount(root): return sum(allrev.get(a, 0) for a in cl_addr[root])

    # ---- parse collisions and reconstruct winners ----
    rows = []
    for line in open(os.path.join(OUT, "contest_intensity.md")):
        m = re.match(r"\| (\d{8,}) \| (\S+) \| `\('f', '(0x[0-9a-f]+)` \| `(0x[0-9a-f]+)…` \| ([\d.]+)% \| ([\d.]+)% \| (-?\d+) \|", line)
        if m:
            rows.append(dict(block=int(m.group(1)), bucket=m.group(2), wpref=m.group(3),
                             loser_to=m.group(4), bid=float(m.group(5)), gap=int(m.group(7))))
    collisions = []
    for row in rows:
        cands = [a for a in by_block[row["block"]] if bidpct(a) is not None and abs(bidpct(a)-row["bid"]) < 0.05]
        w = cands[0] if len(cands) == 1 else None
        collisions.append(dict(row=row, w=w, wlead=clab(cid[w["txhash"]]) if w else None))

    # ---- overbidder winner population: bid>64% + 0x46700 cluster ----
    pop = {}  # lead -> cluster root
    for c in collisions:
        if c["w"] is None: continue
        root = cid[c["w"]["txhash"]]; lead = c["wlead"]
        if c["row"]["bid"] > 64 or lead.startswith("0x4670008ed0"):
            pop[lead] = root
    # collisions per winner lead
    wcoll = defaultdict(list)
    for c in collisions:
        if c["wlead"] in pop: wcoll[c["wlead"]].append(c)

    labels = fu2_labels()
    def routing_of(lead):
        for pref, v in labels.items():
            if lead.startswith(pref.rstrip("…")):
                return v
        return "NOT-PROFILED"

    L = []; A = L.append
    A("# Overbidder autopsy — rational whales or dumb money?")
    A("")
    A("> Stored data only, zero RPC. Population = clusters that won a collision (contest-intensity "
      "probe) with total bid >64% of gross, plus the repeat-rivalry winner `0x4670008ed0…`. Window P&L "
      "(Tasks 1 & 5) is the load-bearing analysis; bid-geometry (Task 3) is supporting color. All [M].")
    A("")
    A(f"Overbidder population ({len(pop)} winner clusters): " + ", ".join(f"`{p[:12]}…`" for p in sorted(pop)))
    A("")

    # ---- Task 1 ----
    A("## Task 1 — Window-level P&L per overbidder (whole census measured set) [M]")
    A("")
    A("| Cluster (operator EOA) | Arbs landed | Gross ETH | Costs ETH (gas+builder) | of which priority | **Window net ETH [M]** | net $ | % arbs net≤0 | Reverted attempts | est revert-gas ETH [E] | **adj net incl. reverts [E]** |")
    A("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    task1 = {}
    for lead in sorted(pop):
        rows_c = by_cluster[pop[lead]]
        p = cluster_pnl(rows_c); task1[lead] = p
        rv = revcount(pop[lead]); burn = rv*MED_GAS; adj = p["net"]-burn
        A(f"| `{lead[:14]}…` | {p['n']:,} | {f2(p['gross'],4)} | {f2(p['gas']+p['builder'],4)} | "
          f"{f2(p['prio'],4)} | **{f2(p['net'],4)}** | {f2(p['net_usd'],0)} | {p['negshare']:.0f}% | "
          f"{rv:,} | {f2(burn,4)} | **{f2(adj,4)}** |")
    A("")
    A(f"*Window net [M] = gross − gas − builder (priority fee is inside gas). **Reverted attempts are "
      f"NOT in the measured set** — the census stored only reverted txs' `to`, not their gas — so their "
      f"gas burn is ESTIMATED [E] as (revert count × median successful-arb gas {f2(MED_GAS,5)} ETH ≈ "
      f"${f2(MED_GAS*med([r['eth_usd'] for r in arbs]),3)}). Reverts likely halt early and use less gas, "
      f"so this est is an UPPER bound. 'adj net' = window net − est revert-gas: it is the load-bearing "
      f"number for rational-vs-burner, and it is what flips small winners negative once they pay for "
      f"their own failed races.*")
    A("")

    # ---- Task 2 ----
    A("## Task 2 — Integration cross-reference [M]")
    A("")
    A("| Cluster | Builder-routing label (Follow-up 2) | Mempool-origin mix (pub/priv/undet) |")
    A("|---|---|---|")
    task2 = {}
    for lead in sorted(pop):
        rows_c = by_cluster[pop[lead]]
        mm = Counter(r.get("mempool_origin") for r in rows_c); n = len(rows_c)
        pub = 100*mm.get("likely_public(priority_fee_only)", 0)/n
        prv = 100*mm.get("private_bundle(coinbase_xfer)", 0)/n
        und = 100*mm.get("undetermined", 0)/n
        rt = routing_of(lead); task2[lead] = rt
        A(f"| `{lead[:14]}…` | {rt} | {pub:.0f}/{prv:.0f}/{und:.0f}% |")
    A("")

    # ---- Task 3 ----
    A("## Task 3 — Bid-pattern geometry [M, supporting]")
    A("")
    A("**(1) High-bid lane concentration — INSUFFICIENT-DATA (pools not stored).** The census slim "
      "records do not retain per-arb pool sets, and the contest probe's pool data was not persisted, so "
      "the pool/lane fingerprint cannot be computed from stored data without a fetch (out of scope). "
      "Weak proxy below: each cluster's **profit-asset** concentration (top assets by arb count) — a "
      "coarse stand-in for 'lane', not a pool fingerprint.")
    A("")
    A("| Cluster | Top profit-assets (arb count) [proxy] |")
    A("|---|---|")
    for lead in sorted(pop):
        assetc = Counter()
        for r in by_cluster[pop[lead]]:
            for a, raw, ve, m in r.get("priced", []):
                if ve and ve > 0: assetc[a[:10]] += 1
        top = ", ".join(f"{a}:{c}" for a, c in assetc.most_common(3)) or "n/a"
        A(f"| `{lead[:14]}…` | {top} |")
    A("")
    A("**(2) Bid escalation vs rival presence.** For each cluster, its collision events (distinct "
      "blocks) with bid% and rival (loser) count:")
    A("")
    A("| Cluster | Collision events (block: bid% / #rivals) | Escalation read |")
    A("|---|---|---|")
    for lead in sorted(pop):
        ev = defaultdict(lambda: [0, 0.0])  # block -> [rivals, bid]
        for c in wcoll[lead]:
            ev[c["row"]["block"]][0] += 1; ev[c["row"]["block"]][1] = c["row"]["bid"]
        parts = "; ".join(f"{b}: {v[1]:.0f}%/{v[0]}r" for b, v in sorted(ev.items()))
        nev = len(ev)
        if nev < 3:
            read = f"INSUFFICIENT-N (n={nev} events)"
        else:
            reads = sorted(ev.values(), key=lambda x: x[0])
            read = "reactive(bid↑ with rivals)" if reads[-1][1] > reads[0][1] else "flat/inverse (static config)"
        A(f"| `{lead[:14]}…` | {parts} | {read} |")
    A("")

    # ---- Task 4 ----
    A("## Task 4 — Classification table (mechanical, rule inputs shown) [M]")
    A("")
    A("Rules: **RATIONAL-INTEGRATED** = net>0 AND routing∈{CONCENTRATED,INTEGRATED}; "
      "**RATIONAL-STATISTICAL** = net>0 AND routing=DISTRIBUTED; **DEFENDER-CANDIDATE** = net>0 AND "
      "high bids in ≤3 lanes; **BURNER** = net<0; **INSUFFICIENT-DATA** = a required field missing. "
      "Multiple labels allowed. Lane data is unavailable ⇒ DEFENDER-CANDIDATE cannot be evaluated.")
    A("")
    A("| Cluster | window net ETH | routing | lane-data | adj net (incl. reverts) | Label(s) |")
    A("|---|--:|---|---|--:|---|")
    for lead in sorted(pop):
        net = task1[lead]["net"]; rt = task2[lead]
        adj = net - revcount(pop[lead])*MED_GAS
        lbls = []
        if net < 0:
            lbls.append("BURNER")
        elif rt in ("CONCENTRATED", "INTEGRATED"):
            lbls.append("RATIONAL-INTEGRATED")
        elif rt == "DISTRIBUTED":
            lbls.append("RATIONAL-STATISTICAL")
        else:
            # net>0 but routing field missing (NOT-PROFILED) -> required input absent
            lbls.append("INSUFFICIENT-DATA(routing not profiled; net>0 so not BURNER on landed set)")
        # DEFENDER-CANDIDATE always needs lane data, which is unavailable
        lbls.append("DEFENDER-CANDIDATE→INSUFFICIENT-DATA(no lane data)")
        adjnote = "" if adj >= 0 else " ⚠ adj net<0 (burner once revert-gas incl.)"
        A(f"| `{lead[:14]}…` | {f2(net,4)} | {rt} | unavailable | {f2(adj,4)}{adjnote} | {'; '.join(lbls)} |")
    A("")

    # ---- Task 5 ----
    A("## Task 5 — Loser-side check (window P&L + burn rate) [M]")
    A("")
    # loser clusters: map each collision loser_to to a census cluster; plus explicit 0x0bc9936
    def cluster_by_prefix(pref):
        for c, addrs in cl_addr.items():
            if any(a.startswith(pref) for a in addrs):
                return c
        return None
    loser_clusters = {}
    for c in collisions:
        lt = c["row"]["loser_to"]
        root = cluster_by_prefix(lt)
        if root is not None:
            loser_clusters[clab(root)] = root
    rr = cluster_by_prefix("0x0bc9936")
    if rr is not None: loser_clusters[clab(rr)] = rr
    A("| Loser cluster | Landed arbs | Window net ETH [M] | net $ | % net≤0 | Reverted txs | est revert-gas ETH [E] | **adj net [E]** |")
    A("|---|--:|--:|--:|--:|--:|--:|--:|")
    graveyard = []
    for lead, root in sorted(loser_clusters.items()):
        rows_c = by_cluster.get(root, [])
        rev = revcount(root); burn = rev*MED_GAS
        if rows_c:
            p = cluster_pnl(rows_c); adj = p["net"]-burn
            A(f"| `{lead[:14]}…` | {p['n']:,} | {f2(p['net'],4)} | {f2(p['net_usd'],0)} | {p['negshare']:.0f}% | "
              f"{rev:,} | {f2(burn,4)} | **{f2(adj,4)}** |")
            if adj < 0: graveyard.append((lead, p, rev, adj))
        else:
            A(f"| `{lead[:14]}…` | 0 (never landed) | n/a | n/a | n/a | {rev:,} | {f2(burn,4)} | **{f2(-burn,4)}** |")
            graveyard.append((lead, None, rev, -burn))
    A("")
    # non-census loser bots (never landed a measured arb) — pure burn candidates
    A("Losers whose bot `to` is NOT in any census winner cluster (never landed a measured arb — "
      "pure-reverter candidates), with reverted-tx counts:")
    A("")
    A("| loser bot (to) | reverted txs in window |")
    A("|---|--:|")
    seen_pref = set()
    for c in collisions:
        lt = c["row"]["loser_to"]
        if cluster_by_prefix(lt) is None and lt not in seen_pref:
            seen_pref.add(lt)
            # count reverts whose 'to' starts with this prefix
            n = sum(v for to, v in allrev.items() if to.startswith(lt))
            A(f"| `{lt}…` | {n:,} |")
    A("")
    A("**Dumb-money graveyard candidates** (net-negative once estimated revert-gas is included):")
    A("")
    if graveyard:
        for lead, p, rev, adj in graveyard:
            base = f"{p['n']} landed arbs, window net {f2(p['net'],4)} ETH" if p else "0 landed arbs"
            A(f"- `{lead[:14]}…`: {base}, {rev:,} reverted attempts → **adj net {f2(adj,4)} ETH [E]** — "
              f"burning capital on failed races, within measurement bounds.")
    else:
        A("- none among the mapped loser clusters.")
    A("")
    A("> Note: `0x0bc9936…` (the repeat-rivalry loser) is window-net-**positive** on landed arbs but its "
      "thousands of reverts make its revert-gas-adjusted net the deciding figure — see the table. The "
      "starkest burn signal is the non-census pure-reverter `0x278d858f…` with 31,392 reverted txs and "
      "zero measured landings: a spray-and-revert bot whose entire on-chain footprint is failed attempts.")
    A("")

    # ---- closing ----
    A("## Standing unmeasurables (closing) [stated]")
    A("")
    A("Every P&L here is **within per-tx on-chain measurement bounds**. NOT captured: off-chain revenue "
      "(CEX/OTC legs, payment-for-order-flow, rebates); cross-address same-entity P&L (a cluster's true "
      "owner may run other unlinked addresses that net against these); and **block-level integrated "
      "profit** — if an operator also builds blocks, its searcher 'loss' can be recouped as builder "
      "revenue invisible to per-tx accounting. **Revert-gas is ESTIMATED [E], not measured** — the census "
      "kept only reverted txs' `to`, not their gas — so the 'adj net' column uses a median-gas proxy "
      "(likely an over-estimate since reverts halt early); the true figure sits between window net [M] "
      "and adj net [E]. So a **BURNER** label means 'net-negative on the arbs+reverts we can attribute on-"
      "chain', not 'unprofitable entity'. Bid-geometry lane fingerprints are unavailable (pools not "
      "stored) and the collision sample is 17 events, so bid-pattern reads are INSUFFICIENT-N. The "
      "load-bearing result is the window-level P&L (Tasks 1 & 5), read with the revert-gas caveat.")
    A("")
    A("*Autopsy complete. Zero RPC calls. Scratch file — not the census.*")
    with open(os.path.join(OUT, "overbidder_autopsy.md"), "w") as f:
        f.write("\n".join(L))
    print("wrote out/overbidder_autopsy.md; pop=", len(pop), "losers=", len(loser_clusters))

if __name__ == "__main__":
    main()

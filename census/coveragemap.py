"""Coverage map for apex entity 0xbdb3ba9f: where it's fat, thin, absent. Cap 10000 calls.
Phases: venues (getLogs bot swaps 14d) | census (sample census-arb receipts for venues) | render."""
import json, os, sys, random
from collections import defaultdict, Counter
from census.rpc import call as _rawcall, map_fn
from census.config import V2_SWAP, V3_SWAP, V4_SWAP
from census.report import UF

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CC = {"n": 0}
def call(m, p): CC["n"] += 1; return _rawcall(m, p)
BOT = "0xbdb3ba9ffe392549e1f8658dd2630c141fdf47b6"
PAD = "0x" + BOT[2:].rjust(64, "0")
def h2i(x): return int(x, 16) if isinstance(x, str) else int(x)

def venue_of(lg):
    """Return (venue_id, protocol) for a swap log."""
    t0 = lg["topics"][0].lower()
    if t0 == V2_SWAP: return ("v2:"+lg["address"].lower(), "V2")
    if t0 == V3_SWAP: return ("v3:"+lg["address"].lower(), "V3")
    if t0 == V4_SWAP: return ("v4:"+lg["topics"][1].lower(), "V4")
    return (None, None)

def venues():
    en = json.load(open(os.path.join(OUT, "dossier_enum.json")))
    start, head = en["start"], en["head"]; t0 = en["t0"]; b0 = en["b0"]
    # filters: bot as sender(topic1) or recipient(topic2) for V2/V3; sender(topic2) for V4
    filters = [[V2_SWAP, PAD], [V2_SWAP, None, PAD], [V3_SWAP, PAD], [V3_SWAP, None, PAD],
               [V4_SWAP, None, PAD]]
    ven = defaultdict(lambda: dict(proto=None, n=0, hours=Counter()))
    CHUNK = 3000
    for lo in range(start, head+1, CHUNK):
        hi = min(lo+CHUNK-1, head)
        for topics in filters:
            r = call("eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "topics": topics}])
            if not isinstance(r, list): continue
            seen = set()
            for lg in r:
                vid, proto = venue_of(lg)
                if not vid: continue
                key = (vid, lg["transactionHash"])
                if key in seen: continue
                seen.add(key)
                bn = h2i(lg["blockNumber"]); ts = t0+(bn-b0)*12
                v = ven[vid]; v["proto"] = proto; v["n"] += 1
                v["hours"][__import__("datetime").datetime.utcfromtimestamp(ts).hour] += 1
    out = {vid: dict(proto=v["proto"], n=v["n"], hours=dict(v["hours"])) for vid, v in ven.items()}
    json.dump(dict(start=start, head=head, days=(head-start)/7200, venues=out),
              open(os.path.join(OUT, "cov_venues.json"), "w"))
    print(f"entity venues: {len(out)} distinct, calls={CC['n']}", flush=True)

def census_venues(n=2500):
    """Sample census arbs -> receipts -> pools. Build venue -> (arbs, nets, winner clusters)."""
    from census.detect import parse_receipt_logs
    arbs = [a for a in (json.loads(l) for l in open(os.path.join(OUT, "arbs.jsonl"))) if a["verdict"] == "arb"]
    uf = UF()
    for a in arbs:
        uf.union(("b", a["beneficiary"]), ("f", a["tx_from"]) if a.get("tx_from") else ("b", a["beneficiary"]))
    cid = {a["txhash"]: uf.find(("b", a["beneficiary"])) for a in arbs}
    rng = random.Random(7); samp = arbs[:]; rng.shuffle(samp); samp = samp[:n]
    span_days = json.load(open(os.path.join(OUT, "window.json")))["span_days"]
    def pools_of(a):
        rc = call("eth_getTransactionReceipt", [a["txhash"]])
        if not isinstance(rc, dict): return None
        ids = set()
        for lg in rc.get("logs") or []:
            vid, _ = venue_of(lg) if (lg.get("topics")) else (None, None)
            if vid: ids.add(vid)
        return ids
    results = map_fn(pools_of, samp, workers=16)
    ven = defaultdict(lambda: dict(arbs=0, nets=[], winners=Counter(), proto=None))
    for a, pools in zip(samp, results):
        if not pools: continue
        for vid in pools:
            v = ven[vid]; v["arbs"] += 1; v["nets"].append(a.get("net_usd") or 0)
            v["winners"][cid[a["txhash"]]] += 1
            v["proto"] = vid.split(":")[0].upper()
    # cluster labels + FU2 routing
    fu2 = {}
    for line in open(os.path.join(OUT, "CENSUS_REPORT.md")):
        import re
        m = re.search(r"`(0x[0-9a-f]+)…`.*\b(INTEGRATED|CONCENTRATED|DISTRIBUTED)\b", line)
        if m: fu2[m.group(1)] = m.group(2)
    def clab(root): return root[1] if isinstance(root, tuple) else str(root)
    out = {}
    for vid, v in ven.items():
        winner = v["winners"].most_common(1)[0]
        lead = clab(winner[0])
        rt = next((r for p, r in fu2.items() if lead.startswith(p.rstrip("…"))), "NOT-PROFILED")
        import statistics as st
        out[vid] = dict(proto=v["proto"], arbs=v["arbs"], median_net=st.median(v["nets"]) if v["nets"] else 0,
                        distinct_winners=len(v["winners"]), incumbent=lead[:14], incumbent_share=winner[1]/v["arbs"],
                        incumbent_routing=rt)
    json.dump(dict(sampled=len(samp), scale=len(arbs)/len(samp), span_days=span_days, venues=out),
              open(os.path.join(OUT, "cov_census.json"), "w"))
    print(f"census venues: {len(out)} distinct from {len(samp)} sampled arbs (scale x{len(arbs)/len(samp):.1f}), calls={CC['n']}", flush=True)

if __name__ == "__main__":
    ph = sys.argv[1] if len(sys.argv) > 1 else "venues"
    if ph == "venues": venues()
    elif ph == "census": census_venues(int(sys.argv[2]) if len(sys.argv) > 2 else 2500)


def render():
    import statistics as st
    def f(x,d=2): return f"{x:,.{d}f}" if x is not None else "n/a"
    ev=json.load(open(os.path.join(OUT,"cov_venues.json")))
    cv=json.load(open(os.path.join(OUT,"cov_census.json")))
    en_ven=ev["venues"]; days=ev["days"]
    cen_ven=cv["venues"]; scale=cv["scale"]; span=cv["span_days"]
    # supplement entity V4 venues from dossier structural sample (getLogs missed router-mediated V4)
    samp=json.load(open(os.path.join(OUT,"dossier_sample.json")))["sample"]
    v4_entity=Counter()
    for r in samp:
        for pid in r["pools"]:
            if pid.startswith("v4:"): v4_entity[pid]+=1
    entity_set=set(en_ven.keys()) | set(v4_entity.keys())
    L=[];A=L.append
    A("# Coverage map — apex entity `0xbdb3ba9ffe…`: fat, thin, absent")
    A("")
    A(f"Where the executor contract trades, where it doesn't, and who owns the space it ignores. "
      f"Primary data: 14 days of its own swap logs (getLogs). All [M] unless marked.")
    A("")
    # Task 1
    A("## Task 1 — Full venue inventory of the entity [M]")
    A("")
    from collections import Counter as C
    proto=C(x["proto"] for x in en_ven.values())
    A(f"- **{len(en_ven)} distinct V2/V3 venues** over {days:.0f} days ({sum(x['n'] for x in en_ven.values()):,} "
      f"swap-touches): {proto.get('V3',0)} Uniswap-V3, {proto.get('V2',0)} Uniswap-V2. "
      f"**V4 caveat:** the bot routes V4 via a router (swap `sender`≠bot), so getLogs cannot enumerate its "
      f"V4 venues; from the 800-tx sample it touches ≥{len(v4_entity)} distinct V4 pools — V4 coverage here "
      f"is **partial [M/E]**, so V4 is excluded from the negative-space ranking below.")
    A("")
    A("Top venues by tx count:")
    A("")
    A("| Venue | Proto | Bot swap-txs (14d) | ~/day |")
    A("|---|---|--:|--:|")
    for vid,x in sorted(en_ven.items(),key=lambda kv:-kv[1]["n"])[:10]:
        A(f"| `{vid}` | {x['proto']} | {x['n']:,} | {x['n']/days:.0f} |")
    A("")
    # Task 2 negative space (headline)
    A("## Task 2 — The negative space (HUNTING MAP) [M]")
    A("")
    A("Venues where census-measured arbs occur that the entity **never touched** in 14 days (V2/V3 only, "
      "where its inventory is complete). Ranked by **(median net × arbs/day) ÷ distinct winners** — high "
      "value, high flow, few incumbents = softest to contest. Census venue stats scaled ×"
      f"{scale:.0f} from a {cv['sampled']}-arb sample [M/E].")
    A("")
    ENTITY_ADDRS = ("0x4670008ed0", "0x5b43453fce", "0xbdb3ba9ffe")
    rows=[]; excl_self=0
    for vid,c in cen_ven.items():
        if c["proto"]=="V4": continue     # entity V4 partial -> can't assert absence
        if vid in entity_set: continue    # entity present via getLogs -> not negative space
        if any(c["incumbent"].startswith(p) for p in ENTITY_ADDRS):
            excl_self+=1; continue        # incumbent IS the entity -> false absence (getLogs missed nested swap)
        arbs_day=c["arbs"]*scale/span
        score=(max(c["median_net"],0)*arbs_day)/max(c["distinct_winners"],1)
        rows.append((score,vid,c,arbs_day))
    rows.sort(reverse=True)
    A(f"**{len(rows)} V2/V3 venues have census arb flow but zero entity presence** (after excluding "
      f"{excl_self} where the sampled incumbent is the entity's own cluster — getLogs misses nested/"
      f"multi-hop swaps where the contract isn't the pool's indexed sender/recipient, so those are false "
      f"absences, not hunting ground). Top 15 by hunting score:")
    A("")
    A("| Venue | Proto | sampled arbs (raw) | census arbs/day [E] | median net $ | distinct winners | incumbent (top) | routing | score |")
    A("|---|---|--:|--:|--:|--:|---|---|--:|")
    for score,vid,c,ad in rows[:15]:
        A(f"| `{vid}` | {c['proto']} | {c['arbs']} | {ad:.1f} | {f(c['median_net'])} | {c['distinct_winners']} | "
          f"`{c['incumbent']}…` | {c['incumbent_routing']} | {score:.2f} |")
    A("")
    A(f"> **Per-venue noise [E]:** most negative-space venues rest on **1–2 sampled arbs** (raw column) "
      f"scaled ×{scale:.0f}, so per-venue arbs/day and median-net are noisy point estimates — treat this "
      f"as a **ranked candidate list**, not precise per-venue economics. Incumbents are all NOT-PROFILED "
      f"(none are census top-10 clusters), consistent with niche pools owned by smaller searchers.")
    # Task 3 thin edges
    A("## Task 3 — The thin edges (entity touches <1×/day) [M]")
    A("")
    thin=[(vid,x) for vid,x in en_ven.items() if x["n"]/days < 1]
    A(f"{len(thin)} venues the entity touches but <1×/day — lanes it sees yet deprioritizes. Cross-ref "
      f"census flow where the venue also has census arbs:")
    A("")
    A("| Venue | Proto | bot txs (14d) | census arbs/day [E] | median net $ | incumbent |")
    A("|---|---|--:|--:|--:|---|")
    thin_ranked=[]
    for vid,x in thin:
        c=cen_ven.get(vid)
        cad=(c["arbs"]*scale/span) if c else 0
        thin_ranked.append((cad, vid, x, c))
    for cad,vid,x,c in sorted(thin_ranked,reverse=True)[:12]:
        A(f"| `{vid}` | {x['proto']} | {x['n']} | {cad:.1f} | {f(c['median_net']) if c else 'n/a'} | "
          f"{('`'+c['incumbent']+'…`') if c else 'n/a'} |")
    A("")
    # Task 4 temporal
    A("## Task 4 — Temporal coverage (hour × venue class) [M]")
    A("")
    A("Entity swap-touches by UTC hour, split V2 vs V3:")
    A("")
    hv={"V2":C(),"V3":C()}
    for vid,x in en_ven.items():
        for h,n in x["hours"].items(): hv[x["proto"]][int(h)]+=n
    A("| Hour | V2 touches | V3 touches |")
    A("|--:|--:|--:|")
    for h in range(24): A(f"| {h:02d} | {hv['V2'].get(h,0):,} | {hv['V3'].get(h,0):,} |")
    tot_by_h={h:hv['V2'].get(h,0)+hv['V3'].get(h,0) for h in range(24)}
    qh=min(range(24),key=lambda h:tot_by_h[h])
    A("")
    qv2=min(range(24),key=lambda h:hv['V2'].get(h,0)); qv3=min(range(24),key=lambda h:hv['V3'].get(h,0))
    A(f"- Quiet hour by swap-touches ≈ **{qh:02d}:00 UTC** (V2 min {qv2:02d}:00, V3 min {qv3:02d}:00). "
      f"**This does NOT match the dossier's ~04:00** quiet hour (that was by total-tx-count over 14d; "
      f"here it's swap-touches). So the 'dead hour' is **metric-dependent and soft [M/E]** — not a robust "
      f"maintenance window. Activity is fairly flat across hours (min/max ratio "
      f"{min(tot_by_h.values())/max(tot_by_h.values()):.2f}); no venue-class has a hard dark window. The "
      f"real open windows are the negative-space venues (Task 2), which the entity misses at **all** hours.")
    A("")
    # Task 5 bid formula
    A("## Task 5 — Bid-formula extraction attempt [M]")
    A("")
    botarbs=[a for a in (json.loads(l) for l in open(os.path.join(OUT,"arbs.jsonl"))) if a["verdict"]=="arb" and a["beneficiary"]==BOT]
    pg=[(a["gross_eth"],a["priority_to_builder_eth"],a["gas_used"]) for a in botarbs if a["gross_eth"]>0 and a["priority_to_builder_eth"]>0]
    if len(pg)>=30:
        import statistics as st
        pct=[pr/g for g,pr,_ in pg]                 # priority as fraction of gross
        gwei=[pr/gu*1e9 for g,pr,gu in pg]          # priority tip per gas (gwei)
        def cv_(x): return st.pstdev(x)/st.mean(x) if st.mean(x) else 99
        # correlation priority vs gross
        import math
        n=len(pg); mg=st.mean([g for g,_,_ in pg]); mp=st.mean([pr for _,pr,_ in pg])
        cov=sum((g-mg)*(pr-mp) for g,pr,_ in pg)/n; sg=st.pstdev([g for g,_,_ in pg]); sp=st.pstdev([pr for _,pr,_ in pg])
        corr=cov/(sg*sp) if sg*sp else 0
        A(f"From {len(pg)} census arbs of the entity with a positive priority-fee bid:")
        A("")
        A(f"- priority/gross (flat-% model): mean {st.mean(pct)*100:.1f}%, CV **{cv_(pct):.2f}**")
        A(f"- priority-tip gwei (flat-gwei model): mean {st.mean(gwei):.3f} gwei, CV **{cv_(gwei):.2f}**")
        A(f"- corr(priority, gross) (size-scaled model): **r={corr:.2f}**")
        best=min([("flat-%",cv_(pct)),("flat-gwei",cv_(gwei))],key=lambda x:x[1])
        verdict = ("GUESSABLE" if best[1]<0.5 else ("size-scaled (r>0.6)" if corr>0.6 else "NOT-EXTRACTABLE"))
        A("")
        if verdict=="GUESSABLE":
            A(f"- **{verdict}** — the **{best[0]}** model fits tightly (CV {best[1]:.2f}); its bid is "
              f"predictable and outbiddable by ε above that {best[0]} level.")
        elif corr>0.6:
            A(f"- **Size-scaled bid** (corr r={corr:.2f}) but neither flat model is tight (CV "
              f"{cv_(pct):.2f}/{cv_(gwei):.2f}) — partially predictable; a linear priority≈k·gross fit "
              f"would need more work. Leaning **GUESSABLE-with-slope [E]**.")
        else:
            A(f"- **NOT-EXTRACTABLE** from n={len(pg)} — no flat model is tight (CV {cv_(pct):.2f}/"
              f"{cv_(gwei):.2f}) and gross-correlation is weak (r={corr:.2f}). The statistical bidder's "
              f"tip is noisy per-tx; ε-overbidding needs a better model than this sample supports.")
    else:
        A(f"- **NOT-EXTRACTABLE** — only {len(pg)} usable (gross,bid) pairs.")
    A("")
    A("## Closing — unmeasurables")
    A("")
    A("This maps only the **`0xbdb3ba9f` executor**. The entity's coverage via **other contracts or "
      "unlinked EOAs is invisible** here — **absence in this map means absence of THIS executor, not of "
      "the entity.** V4 venues are under-enumerated (router-mediated, sender≠bot). Census venue stats are "
      f"×{scale:.0f}-scaled from a {cv['sampled']}-arb sample (sampling error real). Incumbent = the "
      "top census winner cluster observed at that venue in-sample, not necessarily the only one.")
    A("")
    A("*Coverage map complete. Scratch file — not the census.*")
    open(os.path.join(OUT,"coverage_map.md"),"w").write("\n".join(L))
    print("wrote out/coverage_map.md; negative-space venues:",len(rows))

if __name__=="__main__" and len(sys.argv)>1 and sys.argv[1]=="render":
    render()

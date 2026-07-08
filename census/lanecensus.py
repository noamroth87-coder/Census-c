"""Lane census: full 14-day re-measurement of 50 hunting-map lanes. Cap 12000 calls.
Phases: enum (getLogs swaps/lane) | measure (classify+measure arb txs) | render."""
import json, os, sys
from collections import defaultdict, Counter
from census.rpc import call as _rawcall, map_fn
from census.config import V2_SWAP, V3_SWAP
from census.detect import classify_tx
from census.measure import measure_arb
from census.trace import h2i
from census.report import UF

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CC = {"n": 0}
def call(m, p): CC["n"] += 1; return _rawcall(m, p)

def enum():
    en = json.load(open(os.path.join(OUT, "dossier_enum.json")))
    start, head, t0, b0 = en["start"], en["head"], en["t0"], en["b0"]
    lanes = json.load(open(os.path.join(OUT, "lane_list.json")))
    CHUNK = 10000
    def swaps_for(lane):
        vid = lane["vid"]; proto = vid.split(":")[0]; addr = vid.split(":")[1]
        topic = V2_SWAP if proto == "v2" else V3_SWAP
        txs = {}
        for lo in range(start, head+1, CHUNK):
            hi = min(lo+CHUNK-1, head)
            r = call("eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi),
                                      "address": addr, "topics": [topic]}])
            if not isinstance(r, list): continue
            for lg in r:
                txs[lg["transactionHash"]] = h2i(lg["blockNumber"])
        return dict(vid=vid, n_swaps=len(txs), txs=txs)
    res = map_fn(swaps_for, lanes, workers=12)
    json.dump(dict(start=start, head=head, t0=t0, b0=b0, lanes=res),
              open(os.path.join(OUT, "lane_swaps.json"), "w"))
    tot = sum(r["n_swaps"] for r in res)
    print(f"enum: {len(res)} lanes, {tot} total swap-txs, calls={CC['n']}", flush=True)
    for r in sorted(res, key=lambda x: -x["n_swaps"])[:8]:
        print(f"  {r['vid'][:24]} : {r['n_swaps']} swap-txs")

if __name__ == "__main__":
    ph = sys.argv[1] if len(sys.argv) > 1 else "enum"
    if ph == "enum": enum()


REGIME_LINE_GWEI = 0.227   # 90-day median base fee (from volatility scan) = calm|volatile line
CONCENTRATED = ("0x01fdc48ba0","0x45e9b04942","0xad17043228")   # FU2 CONCENTRATED routing
OVERBID_100 = ("0x4670008ed0",)                                 # >100%-of-gross bidder (autopsy)
BOOBY = CONCENTRATED + OVERBID_100

def measure():
    from census.config import V2_SWAP as S2, V3_SWAP as S3, V4_SWAP as S4
    arbs = {a["txhash"]: a for a in (json.loads(l) for l in open(os.path.join(OUT,"arbs.jsonl"))) if a["verdict"]=="arb"}
    arbset = set(arbs)
    basefee = {b["bn"]: b.get("base_fee",0) for b in (json.loads(l) for l in open(os.path.join(OUT,"blockstats.jsonl")))}
    ls = json.load(open(os.path.join(OUT,"lane_swaps.json")))
    lanes = {r["vid"]: r for r in ls["lanes"]}
    # per lane: reuse arb txhashes
    lane_arbs = {}
    all_tx = set()
    for vid, r in lanes.items():
        ha = [h for h in r["txs"] if h in arbset]
        lane_arbs[vid] = ha; all_tx |= set(ha)
    print(f"unique reuse arbs to fetch for sight-class: {len(all_tx)}", flush=True)
    def sight_of(h):
        rc = call("eth_getTransactionReceipt", [h])
        if not isinstance(rc, dict): return (h, None)
        nv4 = sum(1 for lg in rc.get("logs") or [] if (lg.get("topics") or [None])[0] and lg["topics"][0].lower()==S4)
        nv2v3 = sum(1 for lg in rc.get("logs") or [] if (lg.get("topics") or [None])[0] and lg["topics"][0].lower() in (S2,S3))
        return (h, dict(v4=nv4, v2v3=nv2v3, pure=(nv4==0)))
    sight = dict(map_fn(sight_of, sorted(all_tx), workers=16))
    json.dump(dict(lane_arbs=lane_arbs, sight=sight, calls=CC["n"]),
              open(os.path.join(OUT,"lane_sight.json"),"w"))
    print(f"measure done, calls={CC['n']}", flush=True)

def render():
    import statistics as st, re
    from census.report import UF
    def f(x,d=2): return f"{x:,.{d}f}" if x is not None else "n/a"
    def med(x): return st.median(x) if x else None
    def q(x,i): return st.quantiles(x,n=4)[i] if len(x)>=4 else med(x)
    arbs = {a["txhash"]: a for a in (json.loads(l) for l in open(os.path.join(OUT,"arbs.jsonl"))) if a["verdict"]=="arb"}
    basefee = {b["bn"]: b.get("base_fee",0) for b in (json.loads(l) for l in open(os.path.join(OUT,"blockstats.jsonl")))}
    S = json.load(open(os.path.join(OUT,"lane_sight.json"))); lane_arbs=S["lane_arbs"]; sight=S["sight"]
    lanelist = json.load(open(os.path.join(OUT,"lane_list.json")))
    span = json.load(open(os.path.join(OUT,"window.json")))["span_days"]
    # global cluster map
    allarbs=list(arbs.values()); uf=UF()
    for a in allarbs: uf.union(("b",a["beneficiary"]),("f",a["tx_from"]) if a.get("tx_from") else ("b",a["beneficiary"]))
    cid={a["txhash"]:uf.find(("b",a["beneficiary"])) for a in allarbs}
    def clab(r): return r[1] if isinstance(r,tuple) else str(r)
    fu2={}
    for line in open(os.path.join(OUT,"CENSUS_REPORT.md")):
        m=re.search(r"`(0x[0-9a-f]+)…`.*\b(INTEGRATED|CONCENTRATED|DISTRIBUTED)\b",line)
        if m: fu2[m.group(1)]=m.group(2)
    OVERBID={"0x1722261741":"overbidder(RATIONAL)","0x37bdcf54cb":"overbidder(RATIONAL)",
             "0x4670008ed0":"overbidder(RATIONAL,>100%bid)","0x7d344a2d90":"overbidder(RATIONAL)","0xace0000086":"overbidder(RATIONAL)"}
    # build per-lane record
    recs=[]
    incumbent_lanes=Counter()  # cluster -> #lanes it leads
    for L in lanelist:
        vid=L["vid"]; ha=lane_arbs.get(vid,[])
        A=[arbs[h] for h in ha]
        recs.append((L,vid,A))
        # count incumbents for multi-lane
    # first pass incumbents
    lane_incumbent={}
    for L,vid,A in recs:
        if not A: lane_incumbent[vid]=None; continue
        wc=Counter(clab(cid[a["txhash"]]) for a in A)
        lane_incumbent[vid]=wc.most_common(1)[0][0]
        incumbent_lanes[wc.most_common(1)[0][0]]+=1
    # assemble rows
    def rt_of(lead): return next((r for p,r in fu2.items() if lead.startswith(p.rstrip("…"))),"NOT-PROFILED")
    def ob_of(lead): return next((lab for p,lab in OVERBID.items() if lead.startswith(p)),None)
    rows=[]
    for L,vid,A in recs:
        n=len(A); ad=n/span
        if n<5:
            rows.append(dict(L=L,vid=vid,n=n,thin=True,arbs=A)); continue
        nets=[a["net_usd"] for a in A]; gross=[a["gross_usd"] for a in A]
        wc=Counter(clab(cid[a["txhash"]]) for a in A); winners=len(wc)
        top1=wc.most_common(1)[0]; top1share=top1[1]/n; inc=top1[0]
        rt=rt_of(inc); ob=ob_of(inc)
        booby=any(inc.startswith(p) for p in BOOBY)
        # >30% clusters' labels
        big_clusters=[(c,k/n) for c,k in wc.items() if k/n>0.30]
        # regime
        calm=sum(1 for a in A if basefee.get(a["block"],0)/1e9 <= REGIME_LINE_GWEI)
        storm=n-calm
        regime="ALL-WEATHER" if calm and storm else ("CALM-ONLY" if calm else "STORM-ONLY")
        calm_net=med([a["net_usd"] for a in A if basefee.get(a["block"],0)/1e9<=REGIME_LINE_GWEI])
        storm_net=med([a["net_usd"] for a in A if basefee.get(a["block"],0)/1e9>REGIME_LINE_GWEI])
        # sight
        pure=sum(1 for a in A if sight.get(a["txhash"],{}).get("pure"))
        sighted=sum(1 for a in A if a["txhash"] in sight)
        pshare=pure/sighted if sighted else 0
        sclass="OPEN-SIGHT" if pshare>0.70 else ("GATED" if pshare<0.30 else "MIXED")
        slot=ad*max(med(nets),0)*(1-top1share)
        rows.append(dict(L=L,vid=vid,n=n,ad=ad,med_net=med(nets),p25=q(nets,0),p75=q(nets,2),
                         gross_med=med(gross),winners=winners,top1share=top1share,inc=inc,rt=rt,ob=ob,
                         booby=booby,regime=regime,calm=calm,storm=storm,calm_net=calm_net,storm_net=storm_net,
                         sclass=sclass,pshare=pshare,big_clusters=big_clusters,slot=slot))
    render_md(rows,incumbent_lanes,span,S["calls"],lanelist)

def render_md(rows,incumbent_lanes,span,calls,lanelist):
    import statistics as st
    def f(x,d=2): return f"{x:,.{d}f}" if x is not None else "n/a"
    L=[];A=L.append
    A("# Lane census — densifying the hunting map's top rows")
    A("")
    A(f"Full re-measurement of the top-40 negative-space + top-10 thin-edge venues from the coverage "
      f"map, replacing its ×35 noisy sample with **real per-lane arb data**. All [M] unless marked.")
    A("")
    A("## Method & the 14-day budget cut [M]")
    A("")
    tot_arbs=sum(r["n"] for r in rows)
    A(f"- **Window: the full 7-day census window** (blocks 25,437,594–25,487,778), **complete not "
      f"sampled** — {tot_arbs:,} real arbs across the 50 lanes via census reuse (lane swap-logs ∩ census "
      f"arbs; zero-fetch). This is the densification: e.g. the top lanes carry hundreds–thousands of "
      f"arbs, not the coverage map's `5/day` from one sampled arb.")
    A(f"- **14-day extension: BUDGET-CUT (stated).** The non-census 7-day gap is 27,620 swap-txs "
      f"(mostly non-arb); filtering it for arbs would need >27k receipts, far over the 12,000 cap, and a "
      f"strict rank-order 14-day pass is exhausted by a single mega-lane at rank 21. So per the cut rule "
      f"I report the **full 7-day census window for ALL 50 lanes** rather than a ragged 20-lane 14-day "
      f"cut — more complete, uniformly comparable. 14-day figures ≈ 2× flow where regime-stable [E].")
    A(f"- **Fetches used:** {calls:,} of 12,000 (getLogs lane swaps + one receipt per reuse arb for "
      f"sight-class). Regime & flow from stored census + blockstats (free).")
    A(f"- **Regime line:** base fee **{REGIME_LINE_GWEI} gwei** (90-day median from the volatility scan); "
      f"≤ = calm, > = volatile. 15.7% of census blocks are volatile.")
    A("")
    # main table sorted by slot-value
    full=[r for r in rows if not r.get("thin")]; thin=[r for r in rows if r.get("thin")]
    full.sort(key=lambda r:-r["slot"])
    A("## Task 5 — The final lane table (sorted by slot-value) [M; slot-value E]")
    A("")
    A("slot-value [E] = arbs/day × median net × (1 − top-1 share) — a **comparator, not a forecast**.")
    A("")
    A("| # | Venue | arbs (7d) | arbs/day | med net $ | p75 net $ | winners | top-1 % | incumbent | labels | BOOBY | regime | sight | slot-value [E] |")
    A("|--:|---|--:|--:|--:|--:|--:|--:|---|---|:--:|---|---|--:|")
    for i,r in enumerate(full,1):
        labs=[r["rt"]]
        if r["ob"]: labs.append(r["ob"])
        if incumbent_lanes[r["inc"]]>1: labs.append(f"multi-lane×{incumbent_lanes[r['inc']]}")
        A(f"| {i} | `{r['vid']}` | {r['n']} | {r['ad']:.1f} | {f(r['med_net'])} | {f(r['p75'])} | "
          f"{r['winners']} | {100*r['top1share']:.0f}% | `{r['inc'][:12]}…` | {'; '.join(labs)} | "
          f"{'⚠' if r['booby'] else ''} | {r['regime']} | {r['sclass']}({100*r['pshare']:.0f}%) | {f(r['slot'],1)} |")
    A("")
    if thin:
        A(f"**THIN-FLOW lanes (<5 arbs in 7d — raw events, not distributions):**")
        A("")
        A("| Venue | kind | arbs (7d) | raw nets $ |")
        A("|---|---|--:|---|")
        for r in thin:
            nets=[f(a['net_usd']) for a in r["arbs"]]
            A(f"| `{r['vid']}` | {r['L']['kind']} | {r['n']} | {', '.join(nets) if nets else '(none)'} |")
        A("")
    # Task 2 detail: incumbents / booby
    A("## Task 2 — Incumbent census highlights [M]")
    A("")
    booby=[r for r in full if r["booby"]]
    A(f"- **BOOBY-TRAP lanes ({len(booby)}):** incumbent is a CONCENTRATED-routing cluster or a "
      f">100%-of-gross bidder — contesting these provokes a defended P&L. "
      + (", ".join(f"`{r['vid'][:16]}`(`{r['inc'][:10]}…`)" for r in booby) if booby else "none in the 50."))
    ml=[(c,n) for c,n in incumbent_lanes.items() if n>1]
    A(f"- **Multi-lane incumbents ({len(ml)}):** a cluster leading several lanes is a broader opponent "
      f"than a single-lane one. " + (", ".join(f"`{c[:12]}…`×{n}" for c,n in sorted(ml,key=lambda x:-x[1])[:6]) if ml else "none — every lane has a distinct incumbent."))
    A("")
    # Task 3/4 summaries
    A("## Task 3 — Regime split [M]")
    from collections import Counter as C
    rc=C(r["regime"] for r in full)
    A(f"- Regime mix across {len(full)} measured lanes: " + ", ".join(f"{k} {v}" for k,v in rc.items()) +
      f". (Regime line {REGIME_LINE_GWEI} gwei; census window is 84% calm blocks so CALM-ONLY dominates — "
      f"true-STORM per-lane persistence is bounded by the calm census window; see Spec 1 for aggregate "
      f"storm behavior.)")
    A("")
    A("## Task 4 — Sight-barrier classification [M]")
    sc=C(r["sclass"] for r in full)
    A(f"- Sight mix: " + ", ".join(f"{k} {v}" for k,v in sc.items()) + f" (share of each lane's arbs that "
      f"are pure-V2/V3 = pilot-traceable; >70% OPEN-SIGHT, <30% GATED).")
    anom=[r for r in full if r["sclass"]=="OPEN-SIGHT" and (r["med_net"] or 0)>50 and r["winners"]<=2]
    A(f"- **Anomaly check:** OPEN-SIGHT lanes with high margin (>\\$50) and ≤2 winners should be swarmed "
      f"by fast contests yet aren't — {len(anom)} such lanes"
      + (": " + ", ".join(f"`{r['vid'][:16]}`(net \\${f(r['med_net'])},{r['winners']}w)" for r in anom) if anom else "")
      + ". **Stated not smoothed:** either a hidden barrier the pilot heuristic can't see (private "
        "order-flow, or the pool is thin so few arbs exist), or a measurement gap. Per-lane reverted-tx "
        "contest is **invisible** (reverts emit no pool logs → not getLoggable), so contest intensity "
        "here can't be confirmed from revert-counting.")
    A("")
    # pre-registered thresholds
    A("## Pre-registered entry thresholds (DRAFT — pending your confirmation)")
    A("")
    A("Before any build targets a lane, confirm ALL of: **arbs/day ≥ 5**, **median net ≥ \\$0.50**, "
      "**no BOOBY-TRAP flag**. These are DRAFT gates, not yet active.")
    passing=[r for r in full if r["ad"]>=5 and (r["med_net"] or 0)>=0.5 and not r["booby"]]
    A("")
    A(f"- Lanes passing the DRAFT gates ({len(passing)}): "
      + (", ".join(f"`{r['vid'][:16]}`" for r in sorted(passing,key=lambda r:-r['slot'])[:12]) if passing else "none") + ".")
    A("")
    A("## Unmeasurables (closing)")
    A("")
    A("- **Entity coverage via unlinked executors:** the negative-space assumes absence = this executor's "
      "absence; the same operator via another contract/EOA is invisible.")
    A("- **Private-flow contests:** losing bundles dropped in builder simulation, and per-lane reverted "
      "attempts (no pool logs), are not counted — contest intensity is a lower bound.")
    A("- **14-day bound:** measured on the 7-day census window (full); the other 7 days and true-storm "
      "per-lane persistence are budget-cut.")
    A("")
    A("*Lane census complete. Phase B closes. Scratch file — not the census.*")
    open(os.path.join(OUT,"lane_census.md"),"w").write("\n".join(L))
    print("wrote out/lane_census.md")

if __name__=="__main__" and len(sys.argv)>1:
    if sys.argv[1]=="measure": measure()
    elif sys.argv[1]=="render": render()

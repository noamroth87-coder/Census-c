"""Follow-up 2: bid visibility & builder integration in the >$1k tier.
Stored data + ONE bounded header fetch (out/builder_headers.json, <=500 blocks). No re-scan."""
import json, os
from collections import defaultdict, Counter
from census.report import UF, pct, med

OUT = os.path.join(os.path.dirname(__file__), "..", "out")

TAGS = [("titan", "Titan"), ("quasar", "Quasar"), ("buildernet", "BuilderNet"),
        ("eureka", "Eureka"), ("bobthebuilder", "bobTheBuilder"), ("beaverbuild", "beaverbuild"),
        ("btcs.com", "BTCS Builder+"), ("builder+", "BTCS Builder+"), ("bombora", "bombora"),
        ("rsync", "rsync"), ("flashbots", "flashbots"), ("illuminate dmocratize", "flashbots"),
        ("penguinbuild", "penguin"), ("builder0x69", "builder0x69"), ("jetbldr", "Jetbldr")]

def decode_extra(h):
    try: return bytes.fromhex(h[2:]).decode("utf-8", "replace")
    except Exception: return ""

def builder_label(bn, hdr):
    h = hdr.get(str(bn)) or hdr.get(bn)
    if not h: return None
    e = decode_extra(h["extra"]).lower()
    for k, v in TAGS:
        if k in e: return v
    return "fee-recipient:" + (h["miner"] or "?")[:10]

def f2(x, d=2): return f"{x:,.{d}f}" if x is not None else "n/a"

def bucket(g): return "<$10" if g < 10 else "$10-100" if g < 100 else "$100-1k" if g < 1000 else ">$1k"

def main():
    arbs = [x for x in (json.loads(l) for l in open(os.path.join(OUT, "arbs.jsonl"))) if x["verdict"] == "arb"]
    hdr = json.load(open(os.path.join(OUT, "builder_headers.json")))
    hdr = {int(k): v for k, v in hdr.items()}
    uf = UF()
    for r in arbs:
        uf.union(("b", r["beneficiary"]), ("f", r["tx_from"]) if r.get("tx_from") else ("b", r["beneficiary"]))
    cid = {r["txhash"]: uf.find(("b", r["beneficiary"])) for r in arbs}

    big = [r for r in arbs if bucket(r["gross_usd"]) == ">$1k"]
    mid = [r for r in arbs if bucket(r["gross_usd"]) == "$100-1k"]

    # baseline builder share over the fetched block set
    fetched_blocks = list(hdr.keys())
    base_ct = Counter(builder_label(bn, hdr) for bn in fetched_blocks)
    base_tot = sum(base_ct.values())
    base_share = {b: c/base_tot for b, c in base_ct.items()}

    L = []; A = L.append
    A(""); A("---"); A("")
    A("## Follow-up 2: bid visibility and builder integration")
    A("")
    A(f"*Stored measured set + ONE bounded fetch of {len(hdr)} block headers (fee-recipient + "
      f"extra-data only; no receipts, no tx re-scan). Builders identified from extra-data tags, else "
      f"labelled by fee-recipient address. Baseline builder share is computed over the {base_tot} "
      f"fetched blocks — these are arb-hosting blocks, not a uniform block sample, and n≈500 is noisy; "
      f"raw counts are shown so significance is judgeable.*")
    A("")

    # ---------- Task 1 ----------
    A("### Task 1 — Priority-fee audit & total bid (stored data) [M]")
    A("")
    A("Priority fee = (effective gas price − base fee) × gas used, USD-derived at the arb block. "
      "Total bid = priority fee + builder payment (coinbase/direct), as % of gross.")
    A("")
    A("| Bucket | Count | Priority fee $ p25 | med | p75 | Total-bid %gross p25 | med | p75 |")
    A("|---|--:|--:|--:|--:|--:|--:|--:|")
    for name, rows in ((">$1k", big), ("$100-1k", mid)):
        pf = [r["priority_to_builder_eth"]*r["eth_usd"] for r in rows if r.get("eth_usd")]
        bid = [100*(r["priority_to_builder_eth"]+r["builder_eth"])/r["gross_eth"] for r in rows if r["gross_eth"] > 0]
        A(f"| {name} | {len(rows):,} | {f2(pct(pf,.25),4)} | {f2(med(pf),4)} | {f2(pct(pf,.75),4)} | "
          f"{f2(pct(bid,.25))}% | {f2(med(bid))}% | {f2(pct(bid,.75))}% |")
    A("")
    med_bid_big = med([100*(r["priority_to_builder_eth"]+r["builder_eth"])/r["gross_eth"] for r in big if r["gross_eth"] > 0])
    if med_bid_big is not None and med_bid_big < 5:
        A(f"> **FLAG:** median total bid in the >$1k tier is **{med_bid_big:.2f}% of gross** — near-zero. "
          f"Payment for inclusion is either genuinely absent (these winners are not paying to win on-chain) "
          f"or **invisible** to on-chain measurement (off-chain / out-of-band settlement). On-chain data "
          f"alone cannot distinguish the two; that is the motivation for Tasks 2–4.")
    A("")

    # ---------- Task 2 ----------
    A("### Task 2 — Builder identity for >$1k blocks (bounded fetch) [M]")
    A("")
    big_blocks = sorted(set(r["block"] for r in big))
    bb_ct = Counter(builder_label(bn, hdr) for bn in big_blocks)
    bb_tot = sum(bb_ct.values())
    A(f"{len(big_blocks)} distinct blocks host the {len(big):,} >$1k arbs; all fetched. Builder "
      f"distribution (by block), with the fetched-set baseline for reference:")
    A("")
    A("| Builder | >$1k blocks | >$1k share | Baseline share (all fetched) |")
    A("|---|--:|--:|--:|")
    for b, c in bb_ct.most_common():
        A(f"| {b} | {c} | {100*c/bb_tot:.1f}% | {100*base_share.get(b,0):.1f}% |")
    A("")

    # ---------- helpers for Task 3/4 ----------
    def cluster_builder_profile(rows, only_fetched=False):
        """Return list of (builder, count) for the blocks this cluster's arbs landed in."""
        labels = []
        n_total = len(rows); n_labeled = 0
        for r in rows:
            lb = builder_label(r["block"], hdr)
            if lb is None:
                if only_fetched: continue
                lb = "not-fetched"
            else:
                n_labeled += 1
            labels.append(lb)
        return Counter(l for l in labels if l != "not-fetched"), n_total, n_labeled

    def verdict(top_share, top_builder):
        bs = base_share.get(top_builder, 1e-9)
        if top_share > 0.80 and top_share > 2*bs: return "INTEGRATED"
        if top_share > 2*bs: return "CONCENTRATED"
        return "DISTRIBUTED"

    def cluster_rows_table(clusters, title, note=""):
        A(f"### {title}")
        A("")
        if note: A(note); A("")
        A("| # | Lead address | Arbs (labeled/total) | Distinct builders | Top builder | Top share | Baseline share | Verdict | Raw builder counts |")
        A("|--:|---|--:|--:|---|--:|--:|---|---|")
        for i, (ck, rows) in enumerate(clusters, 1):
            ct, n_total, n_labeled = cluster_builder_profile(rows)
            if not ct:
                A(f"| {i} | `{Counter(r['beneficiary'] for r in rows).most_common(1)[0][0][:12]}…` | 0/{n_total} | 0 | (no fetched blocks) | — | — | n/a | — |")
                continue
            top_b, top_c = ct.most_common(1)[0]
            tot = sum(ct.values())
            share = top_c/tot
            v = verdict(share, top_b)
            lead = Counter(r["beneficiary"] for r in rows).most_common(1)[0][0]
            raw = ", ".join(f"{b}:{c}" for b, c in ct.most_common())
            A(f"| {i} | `{lead[:12]}…` | {n_labeled}/{n_total} | {len(ct)} | {top_b} | {100*share:.0f}% | "
              f"{100*base_share.get(top_b,0):.0f}% | {v} | {raw} |")
        A("")

    # ---------- Task 3 ----------
    bigcl = defaultdict(list)
    for r in big: bigcl[cid[r["txhash"]]].append(r)
    big_top = sorted(bigcl.items(), key=lambda kv: -len(kv[1]))[:10]
    cluster_rows_table(big_top, "Task 3 — Winner × builder cross-tab, >$1k tier (top 10 clusters by arb count) [M]",
        "Verdict is mechanical: **INTEGRATED** = top-builder share >80% AND >2× that builder's baseline; "
        "**CONCENTRATED** = >2× baseline but ≤80%; **DISTRIBUTED** = roughly tracks baseline. All >$1k "
        "blocks were fetched, so labeled=total here. Small arb counts ⇒ read verdicts with the raw counts.")

    # ---------- Task 4 ----------
    midcl = defaultdict(list)
    for r in mid: midcl[cid[r["txhash"]]].append(r)
    mid_top5 = sorted(midcl.items(), key=lambda kv: -sum(x["net_usd"] for x in kv[1]))[:5]
    total_mid_new = len({r["block"] for ck, rows in mid_top5 for r in rows} - set(big_blocks))
    fetched_mid = len([bn for bn in hdr if bn not in set(big_blocks)])
    cluster_rows_table(mid_top5, "Task 4 — Winner × builder cross-tab, $100–1k tier (top 5 clusters by net) [M, PARTIAL]",
        f"**Partial coverage:** the $100–1k top-5 clusters span {total_mid_new} blocks not in the >$1k set; "
        f"the 500-block cap left budget for only a systematic ~{fetched_mid}-block sample of them, so each "
        f"cluster's builder mix is measured on the fetched subset (labeled/total column). Verdicts on "
        f"partial samples — weigh by the counts.")

    # ---------- unmeasurable ----------
    A("### What this analysis still cannot see (known-unmeasurable, stated not estimated)")
    A("")
    A("- **Off-chain / out-of-band payments** to builders (fiat, CEX transfers, cross-chain) — invisible on L1.")
    A("- **Searcher–builder profit sharing** and rebates settled off-chain or netted periodically, not per-block.")
    A("- **Exclusive order-flow agreements** (a searcher routing exclusively to one builder by contract, not "
      "visible as an on-chain payment).")
    A("- **Vertical integration where searcher and builder are the same entity** but use unlinked addresses — "
      "a low on-chain bid then reflects self-building, not a cheap win; the builder cross-tab hints at it "
      "(INTEGRATED label) but cannot prove common ownership.")
    A("- **Priority-fee-only private bundles**: a private bundle that pays purely via priority fee is "
      "indistinguishable from public flow, so the bid-visibility split is a lower bound on private payment.")
    A("- **Bundle-level payments** made in a *separate* tx of the same bundle (not the arb tx) are not "
      "attributed here.")
    A("")

    with open(os.path.join(OUT, "CENSUS_REPORT.md"), "a") as f:
        f.write("\n".join(L))
    print("appended Follow-up 2:", len(L), "lines; >$1k median total-bid = %.2f%%" % (med_bid_big or 0))

if __name__ == "__main__":
    main()

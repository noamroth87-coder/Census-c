"""Assemble the census report from out/arbs.jsonl + out/blockstats.jsonl."""
import json, os, statistics as st
from collections import defaultdict, Counter

OUT = os.path.join(os.path.dirname(__file__), "..", "out")

def load_jsonl(p):
    rows = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def pct(xs, p):
    if not xs: return None
    xs = sorted(xs); k = (len(xs)-1)*p; f = int(k); c = min(f+1, len(xs)-1)
    return xs[f] + (xs[c]-xs[f])*(k-f)

def med(xs): return st.median(xs) if xs else None
def fmt(x, d=2): return f"{x:.{d}f}" if x is not None else "n/a"

class UF:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[ra] = rb

def build():
    w = json.load(open(os.path.join(OUT, "window.json")))
    control = json.load(open(os.path.join(OUT, "control_results.json")))
    gate = json.load(open(os.path.join(OUT, "sample_gate.json")))
    arb_rows = load_jsonl(os.path.join(OUT, "arbs.jsonl"))
    stats = load_jsonl(os.path.join(OUT, "blockstats.jsonl"))
    span_days = w["span_days"]

    # ---- partition arb-shaped records ----
    arbs = [r for r in arb_rows if r["verdict"] == "arb"]
    unpriceable = [r for r in arb_rows if r["verdict"] == "unpriceable"]
    failed = [r for r in arb_rows if r["verdict"] == "failed_measure"]
    excluded = [r for r in arb_rows if r["verdict"] == "excluded_nonatomic"]
    # detected atomic arbs = confirmed + unpriceable + failed. excluded_nonatomic are
    # affirmatively-determined NON-arbs (redemption/inventory/drain) -> not in the denominator.
    detected = len(arbs) + len(unpriceable) + len(failed)
    measured_pct = 100*len(arbs)/detected if detected else 0

    # ---- block-level aggregates ----
    total_tx = sum(s.get("n_tx", 0) for s in stats)
    cls_tot = Counter()
    for s in stats:
        for k, v in s.get("counts", {}).items():
            cls_tot[k] += v
    n_blocks = len([s for s in stats if "n_tx" in s])

    # ---- operator clustering (union-find on beneficiary <-> tx_from) ----
    uf = UF()
    for r in arbs:
        b = r["beneficiary"]; f = r.get("tx_from")
        uf.union(("b", b), ("f", f) if f else ("b", b))
    clusters = defaultdict(list)
    for r in arbs:
        clusters[uf.find(("b", r["beneficiary"]))].append(r)

    # ---- winner-set for reverted-attempt counting ----
    winner_addrs = set(r["beneficiary"] for r in arbs) | set(r.get("tx_to") for r in arbs) | set(r.get("tx_from") for r in arbs)
    winner_addrs.discard(None)
    reverted_by_known = 0; reverted_total = 0
    for s in stats:
        for to in s.get("reverted_to", []):
            reverted_total += 1
            if to in winner_addrs:
                reverted_by_known += 1

    # ---- headline stats (confirmed arbs) ----
    nets = [r["net_usd"] for r in arbs if r.get("net_usd") is not None]
    grosses = [r["gross_usd"] for r in arbs if r.get("gross_usd") is not None]
    gases = [r["gas_cost_usd"] for r in arbs if r.get("gas_cost_usd") is not None]
    bidshares = [100*r["builder_eth"]/r["gross_eth"] for r in arbs
                 if r.get("gross_eth") and r["gross_eth"] > 0 and r.get("builder_eth") is not None]
    total_net = sum(nets)
    # top-1 / top-5 share by cluster net
    cl_net = sorted(((k, sum(x.get("net_usd") or 0 for x in v)) for k, v in clusters.items()),
                    key=lambda x: -x[1])
    sum_all_net_cl = sum(n for _, n in cl_net) or 1
    top1 = 100*cl_net[0][1]/sum_all_net_cl if cl_net else 0
    top5 = 100*sum(n for _, n in cl_net[:5])/sum_all_net_cl if cl_net else 0

    def bucket(g):
        if g < 10: return "<$10"
        if g < 100: return "$10-100"
        if g < 1000: return "$100-1k"
        return ">$1k"
    buckets = defaultdict(list)
    for r in arbs:
        if r.get("gross_usd") is not None:
            buckets[bucket(r["gross_usd"])].append(r)

    return dict(w=w, control=control, gate=gate, span_days=span_days, n_blocks=n_blocks,
                total_tx=total_tx, cls_tot=dict(cls_tot), excluded=excluded,
                arbs=arbs, unpriceable=unpriceable, failed=failed, detected=detected,
                measured_pct=measured_pct, clusters=clusters, cl_net=cl_net,
                nets=nets, grosses=grosses, gases=gases, bidshares=bidshares,
                total_net=total_net, top1=top1, top5=top5, buckets=buckets,
                reverted_by_known=reverted_by_known, reverted_total=reverted_total)

def bucket_stats(rows):
    nets = [r["net_usd"] for r in rows if r.get("net_usd") is not None]
    bs = [100*r["builder_eth"]/r["gross_eth"] for r in rows if r.get("gross_eth") and r["gross_eth"]>0]
    gas = [r["gas_cost_usd"] for r in rows if r.get("gas_cost_usd") is not None]
    return len(rows), med(nets), pct(nets,.25), pct(nets,.75), med(bs), med(gas)

if __name__ == "__main__":
    d = build()
    print(json.dumps({k: d[k] for k in ("measured_pct","detected","total_tx","n_blocks","top1","top5")}, indent=2))
    print("confirmed arbs:", len(d["arbs"]))

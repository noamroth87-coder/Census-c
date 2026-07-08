"""Full-window run: fused detect+measure per block, chunked & resumable.
Writes out/arbs.jsonl (arb-shaped records) and out/blockstats.jsonl (per-block aggregates).
Progress checkpointed in out/progress.json so a restart resumes from the next chunk."""
import json, os, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from census.rpc import call
from census.detect import classify_tx
from census.measure import measure_arb
from census.trace import h2i

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
ARBS = os.path.join(OUT, "arbs.jsonl")
STATS = os.path.join(OUT, "blockstats.jsonl")
PROG = os.path.join(OUT, "progress.json")
WORKERS = int(os.environ.get("WORKERS", "36"))
CHUNK = int(os.environ.get("CHUNK", "1000"))

def slim(rec):
    """Keep only fields needed downstream; drop bulky priced tuples except summary."""
    keep = {k: rec.get(k) for k in (
        "verdict","reason","txhash","block","tx_index","beneficiary","tx_from","tx_to",
        "n_swaps","has_flash","multi_asset","cand_kind","value_eth","gross_eth","net_eth",
        "gross_usd","net_usd","eth_usd","eth_usd_method","builder_eth","builder_usd",
        "builder_method","priority_to_builder_eth","gas_used","effective_gas_price",
        "gas_cost_eth","gas_cost_usd","mempool_origin")}
    keep["priced"] = [[a, str(raw), round(ve, 10), m] for a, raw, ve, m in rec.get("priced", [])]
    keep["unpriceable"] = [[a, str(raw)] for a, raw in rec.get("unpriceable", [])]
    return keep

def process_block(bn):
    receipts = call("eth_getBlockReceipts", [hex(bn)])
    hdr = call("eth_getBlockByNumber", [hex(bn), False])
    if not isinstance(receipts, list) or not isinstance(hdr, dict):
        return dict(bn=bn, err="fetch_fail")
    miner = (hdr.get("miner") or "").lower()
    base_fee = h2i(hdr.get("baseFeePerGas")); ts = h2i(hdr.get("timestamp"))
    ctx = dict(miner=miner, base_fee=base_fee, ts=ts, number=bn)
    counts = {}; arb_records = []; reverted_to = []
    for r in receipts:
        st = r.get("status")
        if st != "0x1":
            counts["reverted"] = counts.get("reverted", 0) + 1
            reverted_to.append((r.get("to") or "").lower())
            continue
        res = classify_tx(r)
        c = res["cls"]; counts[c] = counts.get(c, 0) + 1
        if c == "arb_candidate":
            try:
                rec = measure_arb(r, ctx, res)
            except Exception as e:
                rec = dict(verdict="failed_measure", reason=f"exc:{type(e).__name__}",
                           txhash=r["transactionHash"], block=bn,
                           tx_index=h2i(r.get("transactionIndex")))
            arb_records.append(slim(rec))
        elif c == "failed_measure":
            arb_records.append(dict(verdict="failed_measure", reason=res.get("reason"),
                                    txhash=r["transactionHash"], block=bn,
                                    tx_index=h2i(r.get("transactionIndex")), cand_kind="parse_fail"))
    return dict(bn=bn, n_tx=len(receipts), counts=counts, base_fee=base_fee, ts=ts,
                miner=miner, arbs=arb_records, reverted_to=reverted_to)

def main():
    w = json.load(open(os.path.join(OUT, "window.json")))
    start, end = w["start_block"], w["end_block"]
    if os.path.exists(PROG):
        nxt = json.load(open(PROG))["next_block"]
    else:
        nxt = start
        open(ARBS, "w").close(); open(STATS, "w").close()
    print(f"full run: blocks {start}..{end} ({end-start+1}), resume at {nxt}, workers={WORKERS}", flush=True)
    t0 = time.time(); total_arbs = 0
    fa = open(ARBS, "a"); fs = open(STATS, "a")
    b = nxt
    while b <= end:
        hi = min(b+CHUNK-1, end)
        blocks = list(range(b, hi+1))
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            results = list(ex.map(process_block, blocks))
        for r in results:
            if r.get("err"):
                fs.write(json.dumps(dict(bn=r["bn"], err=r["err"]))+"\n"); continue
            for a in r["arbs"]:
                fa.write(json.dumps(a)+"\n"); total_arbs += 1
            fs.write(json.dumps(dict(bn=r["bn"], n_tx=r["n_tx"], counts=r["counts"],
                     base_fee=r["base_fee"], ts=r["ts"], miner=r["miner"],
                     reverted_to=r["reverted_to"]))+"\n")
        fa.flush(); fs.flush()
        json.dump({"next_block": hi+1, "done": hi-start+1, "total": end-start+1,
                   "arb_records": total_arbs}, open(PROG, "w"))
        el = time.time()-t0; dn = hi-nxt+1
        print(f"  chunk {b}..{hi}  {dn/el:.1f} blk/s  arb_records={total_arbs}  "
              f"eta={(end-hi)/max(dn/el,0.1)/60:.0f}min", flush=True)
        b = hi+1
    fa.close(); fs.close()
    print(f"DONE {end-start+1} blocks in {(time.time()-t0)/60:.1f} min, arb_records={total_arbs}", flush=True)

if __name__ == "__main__":
    main()

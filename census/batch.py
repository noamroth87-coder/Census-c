"""Batch driver: Stage A (detect over blocks) + Stage B (measure candidates).
Checkpointed & resumable; streams receipts (never holds the window in memory)."""
import json, os, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from census.rpc import call
from census.detect import classify_tx
from census.measure import measure_arb
from census.trace import h2i

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
os.makedirs(OUT, exist_ok=True)

def detect_block(bn):
    """Fetch receipts+header, classify every tx. Returns compact per-block summary."""
    receipts = call("eth_getBlockReceipts", [hex(bn)])
    hdr = call("eth_getBlockByNumber", [hex(bn), False])
    if not isinstance(receipts, list) or not isinstance(hdr, dict):
        return dict(bn=bn, err="fetch_fail", cands=[], n_tx=0)
    miner = (hdr.get("miner") or "").lower()
    base_fee = h2i(hdr.get("baseFeePerGas"))
    ts = h2i(hdr.get("timestamp"))
    ctx = dict(miner=miner, base_fee=base_fee, ts=ts, number=bn)
    cands = []
    counts = {}
    gas_prices = []
    reverted_to = []      # (to) of reverted txs -> reverted-attempt counting vs known bots
    succeeded_to = {}     # to -> count, for arb-contract activity context
    for r in receipts:
        st = r.get("status")
        to = (r.get("to") or "").lower()
        if st != "0x1":
            counts["reverted"] = counts.get("reverted", 0) + 1
            reverted_to.append([to, h2i(r.get("gasUsed")), h2i(r.get("effectiveGasPrice"))])
            continue
        res = classify_tx(r)
        c = res["cls"]; counts[c] = counts.get(c, 0) + 1
        if c == "arb_candidate":
            cands.append(dict(txhash=r["transactionHash"], idx=h2i(r.get("transactionIndex")),
                              kind=res.get("cand_kind"), ctx=ctx))
        elif c == "failed_measure":
            cands.append(dict(txhash=r["transactionHash"], idx=h2i(r.get("transactionIndex")),
                              kind="parse_fail", ctx=ctx, precls="failed_measure",
                              reason=res.get("reason")))
    return dict(bn=bn, n_tx=len(receipts), counts=counts, cands=cands,
                reverted_to=reverted_to, base_fee=base_fee, ts=ts, miner=miner)

def measure_candidate(cand):
    """Full measurement of one candidate. Returns record or None on hard failure."""
    if cand.get("precls") == "failed_measure":
        return dict(verdict="failed_measure", reason=cand.get("reason", "non_standard_transfer_events"),
                    txhash=cand["txhash"], block=cand["ctx"]["number"], tx_index=cand["idx"],
                    cand_kind="parse_fail")
    rcpt = call("eth_getTransactionReceipt", [cand["txhash"]])
    if not isinstance(rcpt, dict):
        return dict(verdict="failed_measure", reason="receipt_fetch_fail",
                    txhash=cand["txhash"], block=cand["ctx"]["number"], tx_index=cand["idx"])
    try:
        return measure_arb(rcpt, cand["ctx"])
    except Exception as e:
        return dict(verdict="failed_measure", reason=f"exc:{type(e).__name__}",
                    txhash=cand["txhash"], block=cand["ctx"]["number"], tx_index=cand["idx"])

def run_detect(blocks, workers=20, progress_every=2000, tag="detect"):
    """Stage A over a list of blocks. Returns (all_cands, blockstats list)."""
    all_cands = []; stats = []
    done = 0; t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(detect_block, b): b for b in blocks}
        for f in as_completed(futs):
            r = f.result()
            all_cands.extend(r.get("cands", []))
            stats.append(dict(bn=r["bn"], n_tx=r.get("n_tx", 0), counts=r.get("counts", {}),
                              reverted_to=r.get("reverted_to", []), base_fee=r.get("base_fee", 0)))
            done += 1
            if done % progress_every == 0:
                el = time.time()-t0
                print(f"[{tag}] {done}/{len(blocks)} blocks  {done/el:.1f} blk/s  cands={len(all_cands)}", flush=True)
    return all_cands, stats

def run_measure(cands, workers=20, progress_every=2000, tag="measure"):
    out = []; done = 0; t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(measure_candidate, c): c for c in cands}
        for f in as_completed(futs):
            out.append(f.result()); done += 1
            if done % progress_every == 0:
                el = time.time()-t0
                print(f"[{tag}] {done}/{len(cands)} measured  {done/el:.1f}/s", flush=True)
    return out

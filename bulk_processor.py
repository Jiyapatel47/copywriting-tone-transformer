"""
bulk_processor.py

Reads a CSV of products, generates marketing copy for every row CONCURRENTLY
(instead of one at a time), and writes the results to an output CSV.

Concurrency is capped with an asyncio.Semaphore so we don't blast Groq with
unlimited simultaneous requests and trigger rate limits (HTTP 429).

Input CSV columns (header row required):
    product_name, description, platform, tone
Optional columns (fall back to defaults if omitted):
    temperature, top_p, max_tokens

Usage:
    python3 bulk_processor.py --input products.csv --output results.csv
    python3 bulk_processor.py --input products.csv --output results.csv --concurrency 10
"""

import argparse
import asyncio
import csv
import sys
import time

from models import CopyRequest
from client import generate_copy_async


def row_to_request(row: dict, row_num: int) -> CopyRequest | None:
    """
    Convert a single CSV row (as a dict) into a validated CopyRequest.
    Returns None (and prints a warning) if the row is invalid, rather than
    raising -- so one bad row doesn't kill the whole batch.
    """
    try:
        return CopyRequest(
            product_name=row["product_name"].strip(),
            description=row["description"].strip(),
            platform=row["platform"].strip().lower(),
            tone=row.get("tone", "professional").strip() or "professional",
            temperature=float(row["temperature"]) if row.get("temperature") else 0.7,
            top_p=float(row["top_p"]) if row.get("top_p") else 1.0,
            max_tokens=int(row["max_tokens"]) if row.get("max_tokens") else 400,
        )
    except (KeyError, ValueError) as e:
        print(f"  [skipping row {row_num}] Invalid data: {e}", file=sys.stderr)
        return None


def parse_csv_rows(file_obj) -> list[CopyRequest]:
    """
    Parse an already-open, text-mode, file-like object (anything csv.DictReader
    accepts) into a list of validated CopyRequests. Works for both a real file
    opened with open() and an in-memory StringIO (e.g. from a Streamlit upload).
    """
    requests = []
    reader = csv.DictReader(file_obj)
    for i, row in enumerate(reader, start=2):  # start=2: row 1 is the header
        req = row_to_request(row, i)
        if req is not None:
            requests.append(req)
    return requests


def load_requests(input_path: str) -> list[CopyRequest]:
    """Read a CSV file from disk and turn each row into a validated CopyRequest."""
    with open(input_path, newline="", encoding="utf-8") as f:
        return parse_csv_rows(f)


async def process_one(
    req: CopyRequest, semaphore: asyncio.Semaphore, index: int, total: int, on_done=None
) -> dict:
    """Generate copy for a single request, respecting the concurrency limit.

    If on_done is provided, it's called with (completed_count, total, result_dict)
    after each request finishes -- lets a UI update a progress bar live.
    """
    async with semaphore:
        print(f"[{index}/{total}] Generating: {req.product_name} ({req.platform})...")
        try:
            result = await generate_copy_async(req)
            outcome = {
                "product_name": req.product_name,
                "platform": req.platform,
                "tone": req.tone,
                "status": "success",
                "headline": result.headline,
                "body": result.body,
                "hashtags": " ".join(result.hashtags) if result.hashtags else "",
                "error": "",
            }
        except Exception as e:
            print(f"[{index}/{total}] FAILED: {req.product_name} -- {e}", file=sys.stderr)
            outcome = {
                "product_name": req.product_name,
                "platform": req.platform,
                "tone": req.tone,
                "status": "failed",
                "headline": "",
                "body": "",
                "hashtags": "",
                "error": str(e),
            }
        if on_done is not None:
            on_done(outcome)
        return outcome


async def run_bulk(requests: list[CopyRequest], concurrency: int, on_done=None) -> list[dict]:
    """Run all requests concurrently, capped at `concurrency` in flight at once."""
    semaphore = asyncio.Semaphore(concurrency)
    total = len(requests)
    tasks = [
        process_one(req, semaphore, i, total, on_done=on_done)
        for i, req in enumerate(requests, start=1)
    ]
    # gather preserves input order in the results list, regardless of which
    # task actually finishes first -- important so output rows line up with
    # whatever order you care about.
    return await asyncio.gather(*tasks)


def write_results(output_path: str, results: list[dict]) -> None:
    fieldnames = ["product_name", "platform", "tone", "status", "headline", "body", "hashtags", "error"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    parser = argparse.ArgumentParser(
        description="Bulk-generate marketing copy from a CSV of products."
    )
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--output", required=True, help="Path to write output CSV")
    parser.add_argument(
        "--concurrency", type=int, default=5,
        help="Max number of requests in flight at once (default: 5)",
    )
    args = parser.parse_args()

    print(f"Loading requests from {args.input}...")
    requests = load_requests(args.input)
    if not requests:
        print("No valid rows found in input CSV. Nothing to do.")
        return
    print(f"Loaded {len(requests)} valid request(s). Concurrency limit: {args.concurrency}\n")

    start = time.time()
    results = asyncio.run(run_bulk(requests, args.concurrency))
    elapsed = time.time() - start

    write_results(args.output, results)

    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - succeeded
    print(f"\nDone in {elapsed:.1f}s -- {succeeded} succeeded, {failed} failed.")
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()

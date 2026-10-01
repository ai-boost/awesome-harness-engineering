#!/usr/bin/env python3
"""
Verify all URLs in README.md.

Features:
- Concurrent requests with configurable limit
- Retry with backoff
- Result caching to avoid re-checking live URLs
- Categorized summary by status and domain
- JSON output for CI integration

Usage:
    python verify_urls.py
    python verify_urls.py --output results.json
    python verify_urls.py --limit 10   # quick test
"""

import re
import asyncio
import aiohttp
import argparse
import time
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


def console_text(value: object) -> str:
    """Return text that can be printed with the active console encoding."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return str(value).encode(encoding, errors="replace").decode(encoding, errors="replace")


class URLStatus(Enum):
    SUCCESS = "success"
    REDIRECTED = "redirected"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class URLResult:
    url: str
    status: URLStatus
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    error_message: Optional[str] = None
    response_time: Optional[float] = None


class URLValidator:
    def __init__(self,
                 max_concurrent: int = 10,
                 timeout: int = 10,
                 max_retries: int = 2,
                 delay: float = 0.1):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.semaphore = asyncio.Semaphore(max_concurrent)

    def extract_urls(self, file_path: str) -> List[str]:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        urls = set()
        for match in re.finditer(r'\[([^\]]*)\]\(([^)\s]+)\)', content):
            url = match.group(2).strip()
            if url.startswith(("http://", "https://")):
                urls.add(url)

        return sorted(urls)

    def load_cache(self, cache_file: str) -> Dict[str, URLResult]:
        if not Path(cache_file).exists():
            return {}
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
            results = {}
            for item in data:
                results[item["url"]] = URLResult(
                    url=item["url"],
                    status=URLStatus(item["status"]),
                    status_code=item.get("status_code"),
                    final_url=item.get("final_url"),
                    error_message=item.get("error_message"),
                    response_time=item.get("response_time"),
                )
            print(f"Loaded {len(results)} cached results from {cache_file}")
            return results
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: cache file invalid, re-validating all URLs: {e}")
            return {}

    def split_urls(self, urls: List[str], cache: Dict[str, URLResult],
                   revalidate_errors: bool = True) -> Tuple[List[str], List[URLResult]]:
        to_check, cached = [], []
        for url in urls:
            if url in cache:
                result = cache[url]
                if revalidate_errors and result.status in (URLStatus.ERROR, URLStatus.TIMEOUT):
                    to_check.append(url)
                else:
                    cached.append(result)
            else:
                to_check.append(url)
        if cached:
            print(f"Skipping {len(cached)} cached URLs")
        if to_check:
            print(f"Checking {len(to_check)} URLs")
        return to_check, cached

    async def check_one(self, session: aiohttp.ClientSession, url: str) -> URLResult:
        async with self.semaphore:
            start = time.time()
            headers = {"User-Agent": "Mozilla/5.0 (compatible; awesome-harness-url-checker/1.0)"}
            for attempt in range(self.max_retries + 1):
                try:
                    async with session.get(
                        url, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        allow_redirects=True
                    ) as resp:
                        elapsed = time.time() - start
                        final = str(resp.url) if str(resp.url) != url else None
                        if resp.status == 200:
                            return URLResult(url, URLStatus.REDIRECTED if final else URLStatus.SUCCESS,
                                             resp.status, final, response_time=elapsed)
                        if resp.status == 404:
                            return URLResult(url, URLStatus.NOT_FOUND, resp.status, response_time=elapsed)
                        if attempt == self.max_retries:
                            return URLResult(url, URLStatus.ERROR, resp.status,
                                             error_message=f"HTTP {resp.status}", response_time=elapsed)
                except asyncio.TimeoutError:
                    if attempt == self.max_retries:
                        return URLResult(url, URLStatus.TIMEOUT,
                                         error_message="timeout", response_time=time.time() - start)
                except Exception as e:
                    if attempt == self.max_retries:
                        return URLResult(url, URLStatus.ERROR,
                                         error_message=str(e), response_time=time.time() - start)
                await asyncio.sleep(self.delay * (attempt + 1))
            await asyncio.sleep(self.delay)
            return URLResult(url, URLStatus.ERROR, error_message="exhausted retries",
                             response_time=time.time() - start)
        return URLResult(url, URLStatus.ERROR, error_message="semaphore exit")  # unreachable

    async def check_all(self, urls: List[str]) -> List[URLResult]:
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, limit_per_host=5)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.check_one(session, url) for url in urls]
            results, done = [], 0
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                done += 1
                # Keep progress output compatible with the default Windows console encoding.
                sym = {"success": "OK", "redirected": "->", "not_found": "X",
                       "timeout": "T", "error": "!"}.get(result.status.value, "?")
                print(f"\r[{done:3d}/{len(urls):3d}] {sym} {console_text(result.url[:70]):<70}",
                      end="", flush=True)
            print()
            return results


def print_summary(results: List[URLResult]):
    print("\n" + "=" * 72)
    print("URL Verification Summary")
    print("=" * 72)
    counts = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    print(f"\nTotal: {len(results)}")
    for status, n in counts.items():
        print(f"  {status.value:12} {n:3d}  ({n/len(results)*100:.1f}%)")

    problems = [r for r in results if r.status in (URLStatus.NOT_FOUND, URLStatus.ERROR, URLStatus.TIMEOUT)]
    if problems:
        print(f"\nProblematic URLs ({len(problems)}):")
        print("-" * 72)
        for r in problems:
            note = f"  [{r.status_code}]" if r.status_code else ""
            msg = f"  -- {console_text(r.error_message)}" if r.error_message else ""
            print(f"{r.status.value:12} {console_text(r.url)}{note}{msg}")

    redirects = [r for r in results if r.status == URLStatus.REDIRECTED]
    if redirects:
        print(f"\nRedirected URLs ({len(redirects)}):")
        print("-" * 72)
        for r in redirects:
            print(f"  {console_text(r.url)}\n    -> {console_text(r.final_url)}")


def save_json(results: List[URLResult], path: str):
    data = [{"url": r.url, "status": r.status.value, "status_code": r.status_code,
             "final_url": r.final_url, "error_message": r.error_message,
             "response_time": r.response_time} for r in results]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {path}")


async def main():
    parser = argparse.ArgumentParser(description="Verify URLs in README.md")
    parser.add_argument("--file", "-f", default="README.md")
    parser.add_argument("--output", "-o", default="url_verification_cache.json")
    parser.add_argument("--concurrent", "-c", type=int, default=10)
    parser.add_argument("--timeout", "-t", type=int, default=10)
    parser.add_argument("--retries", "-r", type=int, default=2)
    parser.add_argument("--delay", "-d", type=float, default=0.1)
    parser.add_argument("--limit", "-l", type=int, help="Check only first N URLs (for testing)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore existing cache")
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"Error: {args.file} not found")
        return

    validator = URLValidator(args.concurrent, args.timeout, args.retries, args.delay)
    urls = validator.extract_urls(args.file)
    print(f"Found {len(urls)} URLs in {args.file}")

    if args.limit:
        urls = urls[:args.limit]
        print(f"Limited to first {args.limit} URLs")

    cache = {} if args.no_cache else validator.load_cache(args.output)
    to_check, cached_results = validator.split_urls(urls, cache)

    new_results = []
    if to_check:
        t0 = time.time()
        print("Checking...")
        new_results = await validator.check_all(to_check)
        print(f"Done in {time.time()-t0:.1f}s")

    all_results = cached_results + new_results
    url_order = {url: i for i, url in enumerate(urls)}
    all_results.sort(key=lambda r: url_order.get(r.url, 9999))

    print_summary(all_results)
    save_json(all_results, args.output)


if __name__ == "__main__":
    asyncio.run(main())

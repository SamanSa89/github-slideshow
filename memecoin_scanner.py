#!/usr/bin/env python3
"""
Memecoin Scanner - Daily report generator using CoinGecko's free public API.

DISCLAIMER: This tool is for informational and educational purposes only.
It does NOT constitute financial advice. Cryptocurrency investments,
especially memecoins, are extremely high-risk and speculative. You could
lose all of your investment. Always do your own research (DYOR) and consult
a qualified financial advisor before making any investment decisions.
The authors of this tool are not responsible for any financial losses.
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from dateutil.parser import parse as parse_date

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://api.coingecko.com/api/v3"

ENDPOINTS = {
    "trending": f"{BASE_URL}/search/trending",
    "meme_by_volume": (
        f"{BASE_URL}/coins/markets"
        "?vs_currency=usd"
        "&category=meme-token"
        "&order=volume_desc"
        "&per_page=100"
        "&page=1"
        "&sparkline=false"
        "&price_change_percentage=24h,7d"
    ),
    "meme_by_change": (
        f"{BASE_URL}/coins/markets"
        "?vs_currency=usd"
        "&category=meme-token"
        "&order=percent_change_desc_24h"
        "&per_page=50"
        "&page=1"
        "&sparkline=false"
        "&price_change_percentage=24h,7d"
    ),
}

# Scoring weights (must sum to 100)
SCORE_WEIGHTS = {
    "volume_mcap_ratio": 30,   # Volume/MCap ratio (liquidity signal)
    "price_change_24h": 25,    # 24 h momentum sweet spot
    "trending": 20,            # Trending on CoinGecko
    "market_cap_range": 15,    # Size sweet spot for growth potential
    "price_change_7d": 10,     # 7-day momentum confirmation
}

RETRY_COUNT = 3
RETRY_BACKOFF_BASE = 2        # seconds
API_SLEEP = 1.5               # seconds between API calls

REPORTS_DIR = Path(__file__).parent / "reports"

TOP_N = 10                    # How many coins to include in the report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch_json(url: str, retries: int = RETRY_COUNT) -> Optional[dict | list]:
    """Fetch JSON from *url* with retry / back-off logic."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "memecoin-scanner/1.0 (educational-tool)",
    }
    for attempt in range(1, retries + 1):
        try:
            log.info("GET %s (attempt %d/%d)", url, attempt, retries)
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 429:
                wait = RETRY_BACKOFF_BASE ** attempt
                log.warning("Rate-limited (429). Sleeping %ss before retry.", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError as exc:
            log.error("Connection error: %s", exc)
        except requests.exceptions.Timeout:
            log.error("Request timed out.")
        except requests.exceptions.HTTPError as exc:
            log.error("HTTP error %s: %s", resp.status_code, exc)
            if resp.status_code < 500:
                # Client error – no point retrying
                return None
        except Exception as exc:  # noqa: BLE001
            log.error("Unexpected error: %s", exc)

        if attempt < retries:
            wait = RETRY_BACKOFF_BASE ** attempt
            log.info("Retrying in %ss …", wait)
            time.sleep(wait)

    log.error("All %d attempts failed for %s", retries, url)
    return None


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def get_trending_ids() -> set[str]:
    """Return coin IDs currently trending on CoinGecko."""
    data = fetch_json(ENDPOINTS["trending"])
    time.sleep(API_SLEEP)
    if not data or "coins" not in data:
        log.warning("Could not fetch trending coins.")
        return set()
    ids = {item["item"]["id"] for item in data.get("coins", [])}
    log.info("Trending coin IDs: %s", ids)
    return ids


def get_meme_coins_by_volume() -> list[dict]:
    """Fetch meme-token coins ordered by 24 h volume descending."""
    data = fetch_json(ENDPOINTS["meme_by_volume"])
    time.sleep(API_SLEEP)
    if not isinstance(data, list):
        log.warning("Unexpected response from meme_by_volume endpoint.")
        return []
    log.info("Fetched %d meme coins (by volume).", len(data))
    return data


def get_meme_coins_by_change() -> list[dict]:
    """Fetch meme-token coins ordered by 24 h price change descending."""
    data = fetch_json(ENDPOINTS["meme_by_change"])
    time.sleep(API_SLEEP)
    if not isinstance(data, list):
        log.warning("Unexpected response from meme_by_change endpoint.")
        return []
    log.info("Fetched %d meme coins (by 24h change).", len(data))
    return data


def merge_coin_lists(primary: list[dict], secondary: list[dict]) -> list[dict]:
    """Merge two coin lists, deduplicating by coin id."""
    seen: set[str] = set()
    merged: list[dict] = []
    for coin in primary + secondary:
        cid = coin.get("id")
        if cid and cid not in seen:
            seen.add(cid)
            merged.append(coin)
    log.info("Merged list contains %d unique coins.", len(merged))
    return merged


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_volume_mcap(coin: dict) -> float:
    """
    Volume/MCap ratio scoring.
    > 0.3  → full 30 pts  (high activity relative to size)
    0.1-0.3 → scaled
    < 0.1  → 0 pts
    """
    volume = coin.get("total_volume") or 0
    mcap = coin.get("market_cap") or 0
    if mcap <= 0:
        return 0.0
    ratio = volume / mcap
    if ratio >= 0.3:
        return float(SCORE_WEIGHTS["volume_mcap_ratio"])
    if ratio >= 0.1:
        # linear scale 0 → 30 across 0.10 … 0.30
        return round((ratio - 0.1) / 0.2 * SCORE_WEIGHTS["volume_mcap_ratio"], 2)
    return 0.0


def score_price_change_24h(coin: dict) -> float:
    """
    24 h price change scoring.
    Sweet spot: 20 % – 200 %  → max 25 pts
    Already up > 1000 %       → 0 pts (blown up / exhausted)
    10 % – 20 %               → partial credit
    Negative                  → 0 pts
    """
    pct = coin.get("price_change_percentage_24h") or 0.0
    if pct > 1000 or pct < 0:
        return 0.0
    if 20 <= pct <= 200:
        return float(SCORE_WEIGHTS["price_change_24h"])
    if 10 <= pct < 20:
        return round((pct - 10) / 10 * SCORE_WEIGHTS["price_change_24h"], 2)
    if 200 < pct <= 1000:
        # diminishing returns above the sweet spot
        return round(max(0, 1 - (pct - 200) / 800) * SCORE_WEIGHTS["price_change_24h"], 2)
    return 0.0


def score_trending(coin: dict, trending_ids: set[str]) -> float:
    """20 pts if coin is currently trending on CoinGecko."""
    return float(SCORE_WEIGHTS["trending"]) if coin.get("id") in trending_ids else 0.0


def score_market_cap(coin: dict) -> float:
    """
    Market-cap sweet spot for explosive growth: $500K – $50M.
    Outside that range scores 0.
    Inside: max 15 pts, peak at $1M – $10M.
    """
    mcap = coin.get("market_cap") or 0
    low, high = 500_000, 50_000_000
    peak_low, peak_high = 1_000_000, 10_000_000
    if mcap < low or mcap > high:
        return 0.0
    if peak_low <= mcap <= peak_high:
        return float(SCORE_WEIGHTS["market_cap_range"])
    if mcap < peak_low:
        return round((mcap - low) / (peak_low - low) * SCORE_WEIGHTS["market_cap_range"], 2)
    # mcap > peak_high
    return round(
        max(0, 1 - (mcap - peak_high) / (high - peak_high)) * SCORE_WEIGHTS["market_cap_range"],
        2,
    )


def score_7d_momentum(coin: dict) -> float:
    """
    7-day momentum confirmation: 10 pts.
    Positive 7d and not already blown up (< 500%) → full score.
    """
    pct_7d = coin.get("price_change_percentage_7d_in_currency") or 0.0
    if pct_7d <= 0:
        return 0.0
    if pct_7d > 500:
        return 0.0
    # Scale: 0 … 100 % → 0 … 10 pts
    return round(min(pct_7d / 100, 1.0) * SCORE_WEIGHTS["price_change_7d"], 2)


def compute_score(coin: dict, trending_ids: set[str]) -> dict:
    """Compute breakdown and total score for a single coin."""
    breakdown = {
        "volume_mcap": score_volume_mcap(coin),
        "price_24h": score_price_change_24h(coin),
        "trending": score_trending(coin, trending_ids),
        "market_cap": score_market_cap(coin),
        "momentum_7d": score_7d_momentum(coin),
    }
    total = round(sum(breakdown.values()), 2)
    return {"total": total, "breakdown": breakdown}


def build_reasons(coin: dict, score: dict, trending_ids: set[str]) -> list[str]:
    """Return human-readable reasons for the score."""
    reasons: list[str] = []
    bd = score["breakdown"]

    volume = coin.get("total_volume") or 0
    mcap = coin.get("market_cap") or 0
    ratio = (volume / mcap) if mcap > 0 else 0
    if bd["volume_mcap"] > 0:
        reasons.append(f"Vol/MCap={ratio:.2f} (high activity)")

    pct_24h = coin.get("price_change_percentage_24h") or 0
    if bd["price_24h"] > 0:
        reasons.append(f"24h +{pct_24h:.1f}% (momentum sweet spot)")

    if bd["trending"] > 0:
        reasons.append("Trending on CoinGecko")

    if bd["market_cap"] > 0:
        reasons.append(f"MCap ${mcap:,.0f} (growth-stage size)")

    pct_7d = coin.get("price_change_percentage_7d_in_currency") or 0
    if bd["momentum_7d"] > 0:
        reasons.append(f"7d +{pct_7d:.1f}% (sustained momentum)")

    return reasons if reasons else ["No strong signals detected"]


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def format_large_number(n: Optional[float]) -> str:
    """Format large numbers as $1.2M, $500K, etc."""
    if n is None:
        return "N/A"
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n:.4f}"


def format_price(p: Optional[float]) -> str:
    if p is None:
        return "N/A"
    if p < 0.000001:
        return f"${p:.10f}"
    if p < 0.01:
        return f"${p:.6f}"
    if p < 1:
        return f"${p:.4f}"
    return f"${p:.2f}"


def generate_markdown_report(
    ranked_coins: list[dict],
    run_at: datetime,
    report_path: Path,
) -> str:
    """Build and return a Markdown report string."""
    date_str = run_at.strftime("%Y-%m-%d")
    time_str = run_at.strftime("%H:%M UTC")

    lines: list[str] = []

    lines.append(f"# Memecoin Scanner Report — {date_str}")
    lines.append("")
    lines.append(f"> Generated at {time_str} via CoinGecko public API.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## ⚠️  DISCLAIMER")
    lines.append("")
    lines.append(
        "> **THIS IS NOT FINANCIAL ADVICE.** This report is generated automatically "
        "for **educational and informational purposes only**. Memecoins are extremely "
        "high-risk, speculative assets. You could lose **all** of your investment. "
        "Never invest more than you can afford to lose. Always do your own research "
        "(DYOR) and consult a qualified financial advisor. The authors of this tool "
        "accept no responsibility for any financial losses."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Scoring Methodology")
    lines.append("")
    lines.append("| Criterion | Max Points | Description |")
    lines.append("|-----------|-----------|-------------|")
    lines.append("| Volume/MCap Ratio | 30 | Vol > 30% of MCap = strong liquidity |")
    lines.append("| 24h Price Change | 25 | Sweet spot: +20% to +200% |")
    lines.append("| Trending Status | 20 | Coin trending on CoinGecko |")
    lines.append("| Market Cap Range | 15 | $500K–$50M = explosive growth potential |")
    lines.append("| 7d Momentum | 10 | Positive sustained trend |")
    lines.append("| **Total** | **100** | |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## Top {len(ranked_coins)} Memecoins")
    lines.append("")

    # Table header
    lines.append(
        "| Rank | Name | Symbol | Price | 24h% | 7d% | MCap | Volume | Score | Why |"
    )
    lines.append("|------|------|--------|-------|------|-----|------|--------|-------|-----|")

    for i, entry in enumerate(ranked_coins, start=1):
        coin = entry["coin"]
        score = entry["score"]
        reasons = entry["reasons"]

        name = coin.get("name", "?")
        symbol = (coin.get("symbol") or "?").upper()
        price = format_price(coin.get("current_price"))
        chg_24h = coin.get("price_change_percentage_24h")
        chg_24h_str = f"{chg_24h:+.1f}%" if chg_24h is not None else "N/A"
        chg_7d = coin.get("price_change_percentage_7d_in_currency")
        chg_7d_str = f"{chg_7d:+.1f}%" if chg_7d is not None else "N/A"
        mcap_str = format_large_number(coin.get("market_cap"))
        vol_str = format_large_number(coin.get("total_volume"))
        score_str = f"{score['total']:.1f}/100"
        why = "; ".join(reasons[:2])  # Keep table compact

        lines.append(
            f"| {i} | {name} | {symbol} | {price} | {chg_24h_str} | {chg_7d_str} "
            f"| {mcap_str} | {vol_str} | {score_str} | {why} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Breakdown")
    lines.append("")

    for i, entry in enumerate(ranked_coins, start=1):
        coin = entry["coin"]
        score = entry["score"]
        reasons = entry["reasons"]
        bd = score["breakdown"]

        name = coin.get("name", "?")
        symbol = (coin.get("symbol") or "?").upper()
        cg_url = f"https://www.coingecko.com/en/coins/{coin.get('id', '')}"

        lines.append(f"### #{i} — {name} ({symbol})")
        lines.append("")
        lines.append(f"- **CoinGecko:** [{name}]({cg_url})")
        lines.append(f"- **Price:** {format_price(coin.get('current_price'))}")
        lines.append(f"- **Market Cap:** {format_large_number(coin.get('market_cap'))}")
        lines.append(f"- **24h Volume:** {format_large_number(coin.get('total_volume'))}")
        lines.append(
            f"- **Price Change:** 24h={coin.get('price_change_percentage_24h', 'N/A'):.1f}%"
            if coin.get("price_change_percentage_24h") is not None
            else "- **Price Change:** 24h=N/A"
        )
        lines.append(f"- **Total Score:** **{score['total']:.1f} / 100**")
        lines.append("")
        lines.append("  | Component | Score |")
        lines.append("  |-----------|-------|")
        lines.append(f"  | Volume/MCap Ratio | {bd['volume_mcap']:.1f} / 30 |")
        lines.append(f"  | 24h Price Change | {bd['price_24h']:.1f} / 25 |")
        lines.append(f"  | Trending Status | {bd['trending']:.1f} / 20 |")
        lines.append(f"  | Market Cap Range | {bd['market_cap']:.1f} / 15 |")
        lines.append(f"  | 7d Momentum | {bd['momentum_7d']:.1f} / 10 |")
        lines.append("")
        lines.append("  **Why this coin:**")
        for reason in reasons:
            lines.append(f"  - {reason}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*Report generated by [memecoin_scanner.py](../memecoin_scanner.py). "
        "Data sourced from [CoinGecko](https://www.coingecko.com) free public API.*"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_scanner() -> int:
    """Run the full scanner pipeline. Returns 0 on success, 1 on fatal error."""
    run_at = datetime.now(timezone.utc)
    date_str = run_at.strftime("%Y-%m-%d")

    log.info("=== Memecoin Scanner starting — %s ===", date_str)

    # --- Fetch data ---
    trending_ids = get_trending_ids()
    coins_by_volume = get_meme_coins_by_volume()
    coins_by_change = get_meme_coins_by_change()

    if not coins_by_volume and not coins_by_change:
        log.error("No coin data retrieved. Aborting.")
        return 1

    all_coins = merge_coin_lists(coins_by_volume, coins_by_change)

    # --- Score ---
    scored: list[dict] = []
    for coin in all_coins:
        score = compute_score(coin, trending_ids)
        reasons = build_reasons(coin, score, trending_ids)
        scored.append({"coin": coin, "score": score, "reasons": reasons})

    # Sort descending by total score, then by 24h change as tiebreaker
    scored.sort(
        key=lambda x: (
            x["score"]["total"],
            x["coin"].get("price_change_percentage_24h") or 0,
        ),
        reverse=True,
    )

    top_coins = scored[:TOP_N]

    if not top_coins:
        log.warning("No coins passed scoring. Report will be empty.")

    # --- Write reports ---
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON report
    json_path = REPORTS_DIR / f"{date_str}.json"
    json_payload = {
        "generated_at": run_at.isoformat(),
        "disclaimer": (
            "NOT FINANCIAL ADVICE. For educational purposes only. "
            "Memecoins are extremely high-risk. Do your own research."
        ),
        "scoring_weights": SCORE_WEIGHTS,
        "top_coins": [
            {
                "rank": i + 1,
                "id": e["coin"].get("id"),
                "name": e["coin"].get("name"),
                "symbol": (e["coin"].get("symbol") or "").upper(),
                "current_price": e["coin"].get("current_price"),
                "market_cap": e["coin"].get("market_cap"),
                "total_volume": e["coin"].get("total_volume"),
                "price_change_24h": e["coin"].get("price_change_percentage_24h"),
                "price_change_7d": e["coin"].get("price_change_percentage_7d_in_currency"),
                "score": e["score"],
                "reasons": e["reasons"],
                "is_trending": e["coin"].get("id") in trending_ids,
            }
            for i, e in enumerate(top_coins)
        ],
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    log.info("JSON report saved: %s", json_path)

    # Markdown report
    md_path = REPORTS_DIR / f"{date_str}.md"
    md_content = generate_markdown_report(top_coins, run_at, md_path)
    md_path.write_text(md_content, encoding="utf-8")
    log.info("Markdown report saved: %s", md_path)

    # Latest symlink-style copy for easy access
    latest_md = REPORTS_DIR / "latest.md"
    latest_md.write_text(md_content, encoding="utf-8")
    latest_json = REPORTS_DIR / "latest.json"
    latest_json.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    # --- Print summary to stdout ---
    print()
    print("=" * 60)
    print(f"  MEMECOIN SCANNER REPORT — {date_str}")
    print("=" * 60)
    print()
    print(
        "  ⚠️  DISCLAIMER: NOT FINANCIAL ADVICE. Educational use only.\n"
        "     Memecoins are extremely high-risk. DYOR.\n"
    )
    print(f"  {'Rank':<5} {'Name':<22} {'Symbol':<8} {'Score':>7}  {'24h%':>8}  Why")
    print(f"  {'-'*5} {'-'*22} {'-'*8} {'-'*7}  {'-'*8}  {'-'*30}")

    for entry in top_coins:
        coin = entry["coin"]
        score = entry["score"]
        reasons = entry["reasons"]
        rank = [i + 1 for i, e in enumerate(top_coins) if e is entry][0]
        chg = coin.get("price_change_percentage_24h")
        chg_str = f"{chg:+.1f}%" if chg is not None else "N/A"
        why_short = reasons[0] if reasons else ""
        print(
            f"  {rank:<5} {coin.get('name', '?'):<22} "
            f"{(coin.get('symbol') or '').upper():<8} "
            f"{score['total']:>6.1f}  {chg_str:>8}  {why_short}"
        )

    print()
    print(f"  Reports saved to: {REPORTS_DIR}")
    print("=" * 60)
    print()

    log.info("=== Scanner finished successfully ===")
    return 0


if __name__ == "__main__":
    sys.exit(run_scanner())

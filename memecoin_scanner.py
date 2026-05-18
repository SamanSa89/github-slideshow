#!/usr/bin/env python3
"""
Memecoin Scanner v2 — Daily report using DexScreener's free public API.

DISCLAIMER: This tool is for informational and educational purposes ONLY.
It does NOT constitute financial advice. Memecoins are extremely high-risk.
You could lose ALL of your investment. DYOR. Consult a financial advisor.
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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEXSCREENER_BASE = "https://api.dexscreener.com"
REPORTS_DIR = Path(__file__).parent / "reports"
TOP_N = 10
RETRY_COUNT = 3
API_SLEEP = 1.2  # seconds between calls to respect rate limits

# Focus on the most active memecoin chains
ALLOWED_CHAINS = {"solana", "ethereum", "bsc", "base", "avalanche"}

# Max Telegram message length
TELEGRAM_MAX_CHARS = 4000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def fetch_json(url: str, retries: int = RETRY_COUNT) -> Optional[dict | list]:
    headers = {"Accept": "application/json", "User-Agent": "memecoin-scanner/2.0"}
    for attempt in range(1, retries + 1):
        try:
            log.info("GET %s (attempt %d/%d)", url, attempt, retries)
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 429:
                wait = 2 ** attempt
                log.warning("Rate-limited (429). Sleeping %ss.", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as exc:
            log.error("HTTP %s: %s", resp.status_code, exc)
            if resp.status_code < 500:
                return None
        except Exception as exc:
            log.error("Error: %s", exc)
        if attempt < retries:
            time.sleep(2 ** attempt)
    log.error("All %d attempts failed: %s", retries, url)
    return None


# ---------------------------------------------------------------------------
# DexScreener data fetching
# ---------------------------------------------------------------------------

def get_boosted_tokens() -> list[dict]:
    """Top boosted/promoted tokens — strong proxy for trending memecoins."""
    data = fetch_json(f"{DEXSCREENER_BASE}/token-boosts/top/v1")
    time.sleep(API_SLEEP)
    if not isinstance(data, list):
        log.warning("No boosted token data returned.")
        return []
    filtered = [t for t in data if t.get("chainId") in ALLOWED_CHAINS]
    log.info("Boosted tokens on allowed chains: %d", len(filtered))
    return filtered[:30]


def get_latest_boosted_tokens() -> list[dict]:
    """Most recently boosted tokens — catches early movers."""
    data = fetch_json(f"{DEXSCREENER_BASE}/token-boosts/latest/v1")
    time.sleep(API_SLEEP)
    if not isinstance(data, list):
        return []
    filtered = [t for t in data if t.get("chainId") in ALLOWED_CHAINS]
    log.info("Latest boosted tokens on allowed chains: %d", len(filtered))
    return filtered[:20]


def get_pair_data(token_address: str) -> list[dict]:
    """All trading pairs for a given token address."""
    data = fetch_json(f"{DEXSCREENER_BASE}/latest/dex/tokens/{token_address}")
    time.sleep(API_SLEEP)
    if not data or "pairs" not in data:
        return []
    return data["pairs"] or []


def select_best_pair(pairs: list[dict]) -> Optional[dict]:
    """Pick the pair with the highest 24h volume on an allowed chain."""
    valid = [
        p for p in pairs
        if p.get("chainId") in ALLOWED_CHAINS
        and (p.get("volume") or {}).get("h24", 0) > 0
        and p.get("priceUsd")
    ]
    if not valid:
        return None
    return max(valid, key=lambda p: (p.get("volume") or {}).get("h24", 0))


# ---------------------------------------------------------------------------
# Scoring (max 100 points)
# ---------------------------------------------------------------------------

def score_coin(pair: dict, is_boosted: bool) -> dict:
    vol_24h = (pair.get("volume") or {}).get("h24", 0) or 0
    liq = (pair.get("liquidity") or {}).get("usd", 0) or 0
    chg_24h = (pair.get("priceChange") or {}).get("h24", 0) or 0
    chg_1h = (pair.get("priceChange") or {}).get("h1", 0) or 0
    h24_txns = (pair.get("txns") or {}).get("h24") or {}
    buys = h24_txns.get("buys", 0) or 0
    sells = h24_txns.get("sells", 1) or 1

    # 1. Vol / Liquidity ratio (30 pts) — high ratio = intense trading activity
    vol_liq_score = 0.0
    if liq > 0:
        ratio = vol_24h / liq
        if ratio >= 5:
            vol_liq_score = 30.0
        elif ratio >= 1:
            vol_liq_score = round((ratio - 1) / 4 * 30, 2)

    # 2. 24h price change (25 pts) — sweet spot +20% to +500%
    chg_score = 0.0
    if 20 <= chg_24h <= 500:
        chg_score = 25.0
    elif 10 <= chg_24h < 20:
        chg_score = round((chg_24h - 10) / 10 * 25, 2)
    elif 500 < chg_24h <= 2000:
        chg_score = round(max(0.0, 1 - (chg_24h - 500) / 1500) * 25, 2)

    # 3. Trending / boosted status (20 pts)
    boost_score = 20.0 if is_boosted else 0.0

    # 4. Liquidity range (15 pts) — sweet spot $50K–$5M (room to grow)
    liq_score = 0.0
    if 50_000 <= liq <= 5_000_000:
        liq_score = 15.0
    elif 10_000 <= liq < 50_000:
        liq_score = round((liq - 10_000) / 40_000 * 15, 2)
    elif 5_000_000 < liq <= 50_000_000:
        liq_score = round(max(0.0, 1 - (liq - 5_000_000) / 45_000_000) * 15, 2)

    # 5. Buy pressure (10 pts) — more buys than sells = bullish
    total_txns = buys + sells
    buy_ratio = buys / total_txns if total_txns > 0 else 0.5
    buy_score = round(buy_ratio * 10, 2) if buy_ratio > 0.5 else 0.0

    total = round(vol_liq_score + chg_score + boost_score + liq_score + buy_score, 2)
    return {
        "total": total,
        "breakdown": {
            "vol_liq_ratio": vol_liq_score,
            "price_24h": chg_score,
            "trending": boost_score,
            "liquidity_range": liq_score,
            "buy_pressure": buy_score,
        },
    }


def build_reasons(pair: dict, score: dict, is_boosted: bool) -> list[str]:
    reasons: list[str] = []
    bd = score["breakdown"]
    vol_24h = (pair.get("volume") or {}).get("h24", 0) or 0
    liq = (pair.get("liquidity") or {}).get("usd", 0) or 0
    chg_24h = (pair.get("priceChange") or {}).get("h24", 0) or 0
    h24_txns = (pair.get("txns") or {}).get("h24") or {}
    buys = h24_txns.get("buys", 0) or 0
    sells = h24_txns.get("sells", 0) or 0

    if bd["vol_liq_ratio"] > 0 and liq > 0:
        reasons.append(f"Vol/Liq={vol_24h/liq:.1f}x (extreme trading activity)")
    if bd["price_24h"] > 0:
        reasons.append(f"+{chg_24h:.1f}% in 24h (starke Momentum-Phase)")
    if bd["trending"] > 0:
        reasons.append("Trending & promoted auf DexScreener")
    if bd["liquidity_range"] > 0:
        reasons.append(f"Liquidität ${liq:,.0f} (ideale Wachstumsphase)")
    if bd["buy_pressure"] > 0 and (buys + sells) > 0:
        pct = buys / (buys + sells) * 100
        reasons.append(f"{pct:.0f}% Kaufdruck ({buys} Käufe vs {sells} Verkäufe)")
    return reasons or ["Kein starkes Signal erkannt"]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_price(p) -> str:
    try:
        p = float(p)
    except (TypeError, ValueError):
        return "N/A"
    if p < 0.000001:
        return f"${p:.10f}"
    if p < 0.01:
        return f"${p:.6f}"
    if p < 1:
        return f"${p:.4f}"
    return f"${p:.2f}"


def fmt_num(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "N/A"
    if n >= 1e9:
        return f"${n/1e9:.2f}B"
    if n >= 1e6:
        return f"${n/1e6:.2f}M"
    if n >= 1e3:
        return f"${n/1e3:.1f}K"
    return f"${n:.0f}"


# ---------------------------------------------------------------------------
# Telegram message
# ---------------------------------------------------------------------------

def generate_telegram_message(ranked: list[dict], run_at: datetime) -> str:
    date_str = run_at.strftime("%Y-%m-%d")
    time_str = run_at.strftime("%H:%M UTC")
    medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 20

    lines = [
        f"🚀 <b>Memecoin Scanner — {date_str}</b>",
        f"🕗 {time_str}  |  Quelle: DexScreener",
        "",
        "⚠️ <i>Kein Finanzrat. Nur zur Info. DYOR!</i>",
        "",
        f"🏆 <b>TOP {len(ranked)} MEMECOINS</b>",
        "",
    ]

    for i, entry in enumerate(ranked):
        pair = entry["pair"]
        score = entry["score"]
        reasons = entry["reasons"]
        medal = medals[i] if i < len(medals) else "🔹"

        name = (pair.get("baseToken") or {}).get("name", "?")
        symbol = (pair.get("baseToken") or {}).get("symbol", "?").upper()
        price = fmt_price(pair.get("priceUsd"))
        chg_24h = (pair.get("priceChange") or {}).get("h24") or 0
        chg_1h = (pair.get("priceChange") or {}).get("h1") or 0
        vol = fmt_num((pair.get("volume") or {}).get("h24"))
        liq = fmt_num((pair.get("liquidity") or {}).get("usd"))
        chain = pair.get("chainId", "?").upper()
        url = pair.get("url", "")
        arrow = "📈" if chg_24h >= 0 else "📉"

        lines.append(f"{medal} <b><a href='{url}'>{name} ({symbol})</a></b>  <code>[{chain}]</code>")
        lines.append(f"   {arrow} <b>{chg_24h:+.1f}%</b> (24h)  |  {chg_1h:+.1f}% (1h)  |  {price}")
        lines.append(f"   📊 Vol: {vol}  |  Liq: {liq}  |  Score: <b>{score['total']:.0f}/100</b>")
        lines.append(f"   ✅ {reasons[0]}")
        lines.append("")

    lines += [
        "─" * 28,
        "⚠️ <b>Haftungsausschluss:</b> Memecoins sind extrem riskant.",
        "Investiere nur, was du bereit bist zu verlieren.",
    ]

    msg = "\n".join(lines)
    if len(msg) > TELEGRAM_MAX_CHARS:
        msg = msg[:TELEGRAM_MAX_CHARS - 3] + "..."
    return msg


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def generate_markdown_report(ranked: list[dict], run_at: datetime) -> str:
    date_str = run_at.strftime("%Y-%m-%d")
    time_str = run_at.strftime("%H:%M UTC")

    lines = [
        f"# Memecoin Scanner Report — {date_str}",
        "",
        f"> Generiert: {time_str}  |  Quelle: DexScreener Free API",
        "",
        "---",
        "",
        "## ⚠️ DISCLAIMER",
        "",
        "> **KEIN FINANZRAT.** Nur für Bildungs-/Informationszwecke. "
        "Memecoins sind extrem riskant. Du könntest alles verlieren. DYOR.",
        "",
        "---",
        "",
        "## Bewertungskriterien",
        "",
        "| Kriterium | Max Pkt | Beschreibung |",
        "|-----------|---------|--------------|",
        "| Vol/Liq-Ratio | 30 | Vol > 5x Liquidität = extreme Aktivität |",
        "| 24h Preis | 25 | Sweet Spot: +20% bis +500% |",
        "| Trending/Boost | 20 | Aktiv auf DexScreener promotet |",
        "| Liquiditäts-Bereich | 15 | $50K–$5M = Wachstumsphase |",
        "| Kaufdruck | 10 | Mehr Käufe als Verkäufe |",
        "| **Gesamt** | **100** | |",
        "",
        "---",
        "",
        f"## Top {len(ranked)} Memecoins",
        "",
        "| # | Name | Symbol | Chain | Preis | 24h% | 1h% | Vol (24h) | Liq | Score |",
        "|---|------|--------|-------|-------|------|-----|-----------|-----|-------|",
    ]

    for i, entry in enumerate(ranked, 1):
        pair = entry["pair"]
        score = entry["score"]
        name = (pair.get("baseToken") or {}).get("name", "?")
        symbol = (pair.get("baseToken") or {}).get("symbol", "?").upper()
        chain = pair.get("chainId", "?")
        price = fmt_price(pair.get("priceUsd"))
        chg_24h = (pair.get("priceChange") or {}).get("h24") or 0
        chg_1h = (pair.get("priceChange") or {}).get("h1") or 0
        vol = fmt_num((pair.get("volume") or {}).get("h24"))
        liq = fmt_num((pair.get("liquidity") or {}).get("usd"))
        lines.append(
            f"| {i} | {name} | {symbol} | {chain} | {price} "
            f"| {chg_24h:+.1f}% | {chg_1h:+.1f}% | {vol} | {liq} | {score['total']:.1f}/100 |"
        )

    lines += ["", "---", ""]

    for i, entry in enumerate(ranked, 1):
        pair = entry["pair"]
        score = entry["score"]
        reasons = entry["reasons"]
        bd = score["breakdown"]
        name = (pair.get("baseToken") or {}).get("name", "?")
        symbol = (pair.get("baseToken") or {}).get("symbol", "?").upper()
        url = pair.get("url", "")
        chg_24h = (pair.get("priceChange") or {}).get("h24") or 0
        chg_1h = (pair.get("priceChange") or {}).get("h1") or 0
        h24_txns = (pair.get("txns") or {}).get("h24") or {}

        lines += [
            f"### #{i} — {name} ({symbol})",
            "",
            f"- **DEX:** [{pair.get('dexId', '?')} / {pair.get('chainId', '?')}]({url})",
            f"- **Preis:** {fmt_price(pair.get('priceUsd'))}",
            f"- **24h:** {chg_24h:+.1f}%  |  **1h:** {chg_1h:+.1f}%",
            f"- **24h Vol:** {fmt_num((pair.get('volume') or {}).get('h24'))}",
            f"- **Liquidität:** {fmt_num((pair.get('liquidity') or {}).get('usd'))}",
            f"- **Käufe/Verkäufe (24h):** {h24_txns.get('buys',0)} / {h24_txns.get('sells',0)}",
            f"- **Score:** **{score['total']:.1f} / 100**",
            "",
            "  | Komponente | Punkte |",
            "  |-----------|--------|",
            f"  | Vol/Liq-Ratio | {bd['vol_liq_ratio']:.1f} / 30 |",
            f"  | 24h Preis | {bd['price_24h']:.1f} / 25 |",
            f"  | Trending | {bd['trending']:.1f} / 20 |",
            f"  | Liquidität | {bd['liquidity_range']:.1f} / 15 |",
            f"  | Kaufdruck | {bd['buy_pressure']:.1f} / 10 |",
            "",
            "  **Signale:**",
        ]
        for r in reasons:
            lines.append(f"  - {r}")
        lines.append("")

    lines += [
        "---",
        "",
        "*Daten: [DexScreener](https://dexscreener.com) Free API  "
        "|  Tool: [memecoin_scanner.py](../memecoin_scanner.py)*",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_scanner() -> int:
    run_at = datetime.now(timezone.utc)
    date_str = run_at.strftime("%Y-%m-%d")
    log.info("=== Memecoin Scanner v2 — %s ===", date_str)

    # 1. Collect token candidates from DexScreener
    top_boosted = get_boosted_tokens()
    latest_boosted = get_latest_boosted_tokens()

    # Deduplicate by address
    seen_addresses: set[str] = set()
    all_tokens: list[dict] = []
    for t in top_boosted + latest_boosted:
        addr = (t.get("tokenAddress") or "").lower()
        if addr and addr not in seen_addresses:
            seen_addresses.add(addr)
            all_tokens.append(t)

    boosted_addresses = {(t.get("tokenAddress") or "").lower() for t in top_boosted}

    if not all_tokens:
        log.error("No token candidates retrieved. Aborting.")
        return 1

    log.info("Processing %d unique token candidates.", len(all_tokens))

    # 2. Fetch pair data and score
    all_entries: list[dict] = []
    seen_pairs: set[str] = set()

    for token in all_tokens[:35]:  # cap API calls
        addr = (token.get("tokenAddress") or "").lower()
        if not addr:
            continue

        pairs = get_pair_data(addr)
        best = select_best_pair(pairs)
        if not best:
            continue

        pair_key = best.get("pairAddress", "")
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        vol_24h = (best.get("volume") or {}).get("h24", 0) or 0
        if vol_24h < 5_000:  # skip ghost tokens
            continue

        is_boosted = addr in boosted_addresses
        score = score_coin(best, is_boosted)
        reasons = build_reasons(best, score, is_boosted)
        all_entries.append({"pair": best, "score": score, "reasons": reasons})

    if not all_entries:
        log.error("No coins passed minimum volume filter.")
        return 1

    all_entries.sort(key=lambda x: x["score"]["total"], reverse=True)
    top = all_entries[:TOP_N]
    log.info("Top %d selected (highest score: %.1f).", len(top), top[0]["score"]["total"])

    # 3. Write reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    md_content = generate_markdown_report(top, run_at)
    tg_content = generate_telegram_message(top, run_at)
    json_payload = {
        "generated_at": run_at.isoformat(),
        "disclaimer": "NOT FINANCIAL ADVICE. Educational purposes only. DYOR.",
        "data_source": "DexScreener Free API",
        "top_coins": [
            {
                "rank": i + 1,
                "name": (e["pair"].get("baseToken") or {}).get("name"),
                "symbol": (e["pair"].get("baseToken") or {}).get("symbol", "").upper(),
                "chain": e["pair"].get("chainId"),
                "dex": e["pair"].get("dexId"),
                "price_usd": e["pair"].get("priceUsd"),
                "price_change_24h": (e["pair"].get("priceChange") or {}).get("h24"),
                "price_change_1h": (e["pair"].get("priceChange") or {}).get("h1"),
                "volume_24h_usd": (e["pair"].get("volume") or {}).get("h24"),
                "liquidity_usd": (e["pair"].get("liquidity") or {}).get("usd"),
                "pair_url": e["pair"].get("url"),
                "score": e["score"],
                "reasons": e["reasons"],
            }
            for i, e in enumerate(top)
        ],
    }
    json_str = json.dumps(json_payload, indent=2)

    for fname, content in [
        (f"{date_str}.md", md_content),
        ("latest.md", md_content),
        (f"{date_str}.json", json_str),
        ("latest.json", json_str),
        ("telegram_message.txt", tg_content),
    ]:
        (REPORTS_DIR / fname).write_text(content, encoding="utf-8")
        log.info("Saved: reports/%s", fname)

    # 4. Print console summary
    print()
    print("=" * 65)
    print(f"  MEMECOIN SCANNER — {date_str}  |  {run_at.strftime('%H:%M UTC')}")
    print("=" * 65)
    print("  ⚠️  KEIN FINANZRAT — nur zur Information\n")
    print(f"  {'#':<3} {'Name':<22} {'Chain':<9} {'24h%':>7}  {'Score':>7}")
    print(f"  {'-'*3} {'-'*22} {'-'*9} {'-'*7}  {'-'*7}")
    for i, e in enumerate(top, 1):
        pair = e["pair"]
        name = (pair.get("baseToken") or {}).get("name", "?")[:22]
        chain = pair.get("chainId", "?")[:9]
        chg = (pair.get("priceChange") or {}).get("h24") or 0
        print(f"  {i:<3} {name:<22} {chain:<9} {chg:>+6.1f}%  {e['score']['total']:>6.1f}/100")
    print()
    print(f"  Reports gespeichert: {REPORTS_DIR}")
    print("=" * 65)
    print()

    log.info("=== Scanner erfolgreich abgeschlossen ===")
    return 0


if __name__ == "__main__":
    sys.exit(run_scanner())

#!/usr/bin/env python3
"""
Memecoin Scanner v2 - DexScreener Free API.
DISCLAIMER: NOT financial advice. Educational purposes only. DYOR.
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

DEXSCREENER_BASE = "https://api.dexscreener.com"
REPORTS_DIR = Path(__file__).parent / "reports"
TOP_N = 10
RETRY_COUNT = 3
API_SLEEP = 1.2
ALLOWED_CHAINS = {"solana", "ethereum", "bsc", "base", "avalanche"}
TELEGRAM_MAX_CHARS = 4000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_json(url: str, retries: int = RETRY_COUNT):
    headers = {"Accept": "application/json", "User-Agent": "memecoin-scanner/2.0"}
    for attempt in range(1, retries + 1):
        try:
            log.info("GET %s", url)
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError:
            if resp.status_code < 500:
                return None
        except Exception as exc:
            log.error("Error: %s", exc)
        if attempt < retries:
            time.sleep(2 ** attempt)
    return None


def get_boosted_tokens():
    data = fetch_json(f"{DEXSCREENER_BASE}/token-boosts/top/v1")
    time.sleep(API_SLEEP)
    if not isinstance(data, list):
        return []
    return [t for t in data if t.get("chainId") in ALLOWED_CHAINS][:30]


def get_latest_boosted_tokens():
    data = fetch_json(f"{DEXSCREENER_BASE}/token-boosts/latest/v1")
    time.sleep(API_SLEEP)
    if not isinstance(data, list):
        return []
    return [t for t in data if t.get("chainId") in ALLOWED_CHAINS][:20]


def get_pair_data(token_address: str):
    data = fetch_json(f"{DEXSCREENER_BASE}/latest/dex/tokens/{token_address}")
    time.sleep(API_SLEEP)
    if not data or "pairs" not in data:
        return []
    return data["pairs"] or []


def select_best_pair(pairs):
    valid = [
        p for p in pairs
        if p.get("chainId") in ALLOWED_CHAINS
        and (p.get("volume") or {}).get("h24", 0) > 0
        and p.get("priceUsd")
    ]
    if not valid:
        return None
    return max(valid, key=lambda p: (p.get("volume") or {}).get("h24", 0))


def score_coin(pair, is_boosted):
    vol = (pair.get("volume") or {}).get("h24", 0) or 0
    liq = (pair.get("liquidity") or {}).get("usd", 0) or 0
    chg = (pair.get("priceChange") or {}).get("h24", 0) or 0
    txns = (pair.get("txns") or {}).get("h24") or {}
    buys = txns.get("buys", 0) or 0
    sells = txns.get("sells", 1) or 1

    s_vol = 0.0
    if liq > 0:
        r = vol / liq
        s_vol = 30.0 if r >= 5 else round((r - 1) / 4 * 30, 2) if r >= 1 else 0.0

    s_chg = 0.0
    if 20 <= chg <= 500:
        s_chg = 25.0
    elif 10 <= chg < 20:
        s_chg = round((chg - 10) / 10 * 25, 2)
    elif 500 < chg <= 2000:
        s_chg = round(max(0.0, 1 - (chg - 500) / 1500) * 25, 2)

    s_boost = 20.0 if is_boosted else 0.0

    s_liq = 0.0
    if 50_000 <= liq <= 5_000_000:
        s_liq = 15.0
    elif 10_000 <= liq < 50_000:
        s_liq = round((liq - 10_000) / 40_000 * 15, 2)
    elif 5_000_000 < liq <= 50_000_000:
        s_liq = round(max(0.0, 1 - (liq - 5_000_000) / 45_000_000) * 15, 2)

    total_t = buys + sells
    buy_ratio = buys / total_t if total_t > 0 else 0.5
    s_buy = round(buy_ratio * 10, 2) if buy_ratio > 0.5 else 0.0

    total = round(s_vol + s_chg + s_boost + s_liq + s_buy, 2)
    return {"total": total, "breakdown": {
        "vol_liq": s_vol, "price_24h": s_chg,
        "trending": s_boost, "liquidity": s_liq, "buy_pressure": s_buy
    }}


def build_reasons(pair, score, is_boosted):
    reasons = []
    bd = score["breakdown"]
    vol = (pair.get("volume") or {}).get("h24", 0) or 0
    liq = (pair.get("liquidity") or {}).get("usd", 0) or 0
    chg = (pair.get("priceChange") or {}).get("h24", 0) or 0
    txns = (pair.get("txns") or {}).get("h24") or {}
    buys = txns.get("buys", 0) or 0
    sells = txns.get("sells", 0) or 0
    if bd["vol_liq"] > 0 and liq > 0:
        reasons.append(f"Vol/Liq={vol/liq:.1f}x")
    if bd["price_24h"] > 0:
        reasons.append(f"+{chg:.1f}% in 24h")
    if bd["trending"] > 0:
        reasons.append("Trending auf DexScreener")
    if bd["liquidity"] > 0:
        reasons.append(f"Liq ${liq:,.0f}")
    if bd["buy_pressure"] > 0 and (buys + sells) > 0:
        reasons.append(f"{buys/(buys+sells)*100:.0f}% Kaufdruck")
    return reasons or ["Kein starkes Signal"]


def fmt_price(p):
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


def fmt_num(n):
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


def build_telegram_message(ranked, run_at):
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"] + ["\U0001f539"] * 20
    lines = [
        f"\U0001f680 <b>Memecoin Scanner - {run_at.strftime('%Y-%m-%d')}</b>",
        f"\U0001f557 {run_at.strftime('%H:%M UTC')} | DexScreener",
        "",
        "⚠️ <i>Kein Finanzrat. Nur zur Info. DYOR!</i>",
        "",
        f"\U0001f3c6 <b>TOP {len(ranked)} MEMECOINS</b>",
        "",
    ]
    for i, entry in enumerate(ranked):
        pair = entry["pair"]
        score = entry["score"]
        reasons = entry["reasons"]
        name = (pair.get("baseToken") or {}).get("name", "?")
        symbol = (pair.get("baseToken") or {}).get("symbol", "?").upper()
        price = fmt_price(pair.get("priceUsd"))
        chg24 = (pair.get("priceChange") or {}).get("h24") or 0
        chg1 = (pair.get("priceChange") or {}).get("h1") or 0
        vol = fmt_num((pair.get("volume") or {}).get("h24"))
        liq = fmt_num((pair.get("liquidity") or {}).get("usd"))
        chain = pair.get("chainId", "?").upper()
        url = pair.get("url", "")
        arrow = "\U0001f4c8" if chg24 >= 0 else "\U0001f4c9"
        medal = medals[i] if i < len(medals) else "\U0001f539"
        lines.append(f"{medal} <b><a href='{url}'>{name} ({symbol})</a></b> <code>[{chain}]</code>")
        lines.append(f"   {arrow} <b>{chg24:+.1f}%</b> (24h) | {chg1:+.1f}% (1h) | {price}")
        lines.append(f"   \U0001f4ca Vol: {vol} | Liq: {liq} | Score: <b>{score['total']:.0f}/100</b>")
        lines.append(f"   ✅ {reasons[0]}")
        lines.append("")
    lines += [
        "─" * 25,
        "⚠️ Memecoins sind extrem riskant. DYOR!",
    ]
    msg = "\n".join(lines)
    return msg[:TELEGRAM_MAX_CHARS] if len(msg) > TELEGRAM_MAX_CHARS else msg


def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        log.info("Telegram not configured, skipping.")
        return
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        log.info("Telegram-Nachricht erfolgreich gesendet.")
    except Exception as exc:
        log.error("Telegram-Fehler: %s", exc)


def run_scanner():
    run_at = datetime.now(timezone.utc)
    date_str = run_at.strftime("%Y-%m-%d")
    log.info("=== Memecoin Scanner v2 - %s ===", date_str)

    top_boosted = get_boosted_tokens()
    latest_boosted = get_latest_boosted_tokens()
    boosted_addresses = {(t.get("tokenAddress") or "").lower() for t in top_boosted}

    seen_addr: set = set()
    all_tokens = []
    for t in top_boosted + latest_boosted:
        addr = (t.get("tokenAddress") or "").lower()
        if addr and addr not in seen_addr:
            seen_addr.add(addr)
            all_tokens.append(t)

    if not all_tokens:
        log.error("Keine Token-Daten. Abbruch.")
        return 1

    all_entries = []
    seen_pairs: set = set()
    for token in all_tokens[:35]:
        addr = (token.get("tokenAddress") or "").lower()
        if not addr:
            continue
        pairs = get_pair_data(addr)
        best = select_best_pair(pairs)
        if not best:
            continue
        pk = best.get("pairAddress", "")
        if pk in seen_pairs:
            continue
        seen_pairs.add(pk)
        if ((best.get("volume") or {}).get("h24", 0) or 0) < 5_000:
            continue
        is_boosted = addr in boosted_addresses
        score = score_coin(best, is_boosted)
        reasons = build_reasons(best, score, is_boosted)
        all_entries.append({"pair": best, "score": score, "reasons": reasons})

    if not all_entries:
        log.error("Keine Coins mit ausreichend Volumen.")
        return 1

    all_entries.sort(key=lambda x: x["score"]["total"], reverse=True)
    top = all_entries[:TOP_N]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    tg_msg = build_telegram_message(top, run_at)

    json_data = {
        "generated_at": run_at.isoformat(),
        "disclaimer": "NOT FINANCIAL ADVICE. DYOR.",
        "top_coins": [
            {
                "rank": i + 1,
                "name": (e["pair"].get("baseToken") or {}).get("name"),
                "symbol": (e["pair"].get("baseToken") or {}).get("symbol", "").upper(),
                "chain": e["pair"].get("chainId"),
                "price_usd": e["pair"].get("priceUsd"),
                "change_24h": (e["pair"].get("priceChange") or {}).get("h24"),
                "change_1h": (e["pair"].get("priceChange") or {}).get("h1"),
                "volume_24h": (e["pair"].get("volume") or {}).get("h24"),
                "liquidity": (e["pair"].get("liquidity") or {}).get("usd"),
                "url": e["pair"].get("url"),
                "score": e["score"]["total"],
                "reasons": e["reasons"],
            }
            for i, e in enumerate(top)
        ],
    }

    (REPORTS_DIR / f"{date_str}.json").write_text(json.dumps(json_data, indent=2))
    (REPORTS_DIR / "latest.json").write_text(json.dumps(json_data, indent=2))
    (REPORTS_DIR / f"{date_str}.md").write_text(tg_msg)
    (REPORTS_DIR / "latest.md").write_text(tg_msg)

    print()
    print("=" * 60)
    print(f"  MEMECOIN SCANNER - {date_str}")
    print("  Kein Finanzrat. DYOR.")
    print("=" * 60)
    for i, e in enumerate(top, 1):
        p = e["pair"]
        name = (p.get("baseToken") or {}).get("name", "?")[:20]
        chain = p.get("chainId", "?")[:8]
        chg = (p.get("priceChange") or {}).get("h24") or 0
        print(f"  {i}. {name:<20} [{chain}]  {chg:+.1f}%  Score:{e['score']['total']:.0f}")
    print()

    send_telegram(tg_msg)

    log.info("=== Fertig ===")
    return 0


if __name__ == "__main__":
    sys.exit(run_scanner())

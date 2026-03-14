# HAOUD TRADING IA - v2.0
# Ameliorations :
# 1. Backtesting automatique (60 jours)
# 2. Gestion exposition totale (max positions + budget)
# 3. Correlation crypto (blocage si BTC chute)
# 5. Vraies actualites via RSS gratuit
# 9. Alertes Telegram
# Algo technique interne (15 min) + Claude macro (1x/jour 8h UTC)

import requests
import json
import os
import time
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================

CLAUDE_KEY    = os.environ.get("CLAUDE_API_KEY", "")
BITPANDA_KEY  = os.environ.get("BITPANDA_API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "")

CRYPTO_ASSETS = {
    "BTC":  {"name": "Bitcoin"},
    "ETH":  {"name": "Ethereum"},
    "SOL":  {"name": "Solana"},
    "BNB":  {"name": "BNB"},
    "XRP":  {"name": "XRP"},
    "ADA":  {"name": "Cardano"},
    "AVAX": {"name": "Avalanche"},
    "LINK": {"name": "Chainlink"},
    "DOT":  {"name": "Polkadot"},
    "MATIC":{"name": "Polygon"},
}

COINGECKO_IDS = {
    "BTC":  "bitcoin",   "ETH":  "ethereum",
    "SOL":  "solana",    "BNB":  "binancecoin",
    "XRP":  "ripple",    "ADA":  "cardano",
    "AVAX": "avalanche-2","LINK": "chainlink",
    "DOT":  "polkadot",  "MATIC":"matic-network",
}

STOCK_ASSETS = {
    "NVDA":  {"ticker": "NVDA",  "name": "NVIDIA"},
    "AAPL":  {"ticker": "AAPL",  "name": "Apple"},
    "MSFT":  {"ticker": "MSFT",  "name": "Microsoft"},
    "GOOGL": {"ticker": "GOOGL", "name": "Alphabet"},
    "TSLA":  {"ticker": "TSLA",  "name": "Tesla"},
    "AMZN":  {"ticker": "AMZN",  "name": "Amazon"},
    "META":  {"ticker": "META",  "name": "Meta"},
}

ETF_ASSETS = {
    "SPY":  {"ticker": "SPY",     "name": "S&P 500 ETF (US)"},
    "QQQ":  {"ticker": "QQQ",     "name": "Nasdaq 100 ETF"},
    "GLD":  {"ticker": "GLD",     "name": "Gold ETF"},
    "VTI":  {"ticker": "VTI",     "name": "Total Market ETF"},
    "ARKK": {"ticker": "ARKK",    "name": "ARK Innovation ETF"},
    "CW8":  {"ticker": "CW8.PA",  "name": "Amundi MSCI World"},
    "SP5":  {"ticker": "SP5.PA",  "name": "Amundi S&P 500"},
    "C40":  {"ticker": "C40.PA",  "name": "Amundi CAC 40"},
    "PANX": {"ticker": "PANX.PA", "name": "Amundi Nasdaq-100"},
    "AEME": {"ticker": "AEME.PA", "name": "Amundi MSCI Emerging"},
}

# --- REGLES DE TRADING ---
MIN_SCORE_BUY    = 70
MAX_SCORE_SELL   = 40
STOP_LOSS_PCT    = 0.07
TAKE_PROFIT_PCT  = 0.18
MAX_TRADE_EUR    = 50
DRY_RUN          = True

# --- AMELIORATION 2 : GESTION EXPOSITION ---
MAX_POSITIONS        = 5     # Max positions ouvertes en meme temps
MAX_TOTAL_EUR        = 250   # Budget total max investi simultanement
MAX_CRYPTO_POS       = 3     # Max positions crypto
MAX_STOCK_POS        = 2     # Max positions actions/ETF

# --- AMELIORATION 3 : CORRELATION CRYPTO ---
BTC_CRASH_THRESHOLD  = -5.0  # Blocage total crypto si BTC < -5%
BTC_WARN_THRESHOLD   = -3.0  # Reduction score crypto si BTC < -3%
BTC_PENALTY_PTS      = 15    # Points retires du score crypto

# --- CLAUDE MACRO ---
CLAUDE_HOUR_UTC = 8

# --- AMELIORATION 5 : FLUX RSS ---
RSS_FEEDS = [
    {"url": "https://feeds.reuters.com/reuters/businessNews",    "source": "Reuters Business"},
    {"url": "https://feeds.reuters.com/reuters/technologyNews",  "source": "Reuters Tech"},
    {"url": "https://coindesk.com/arc/outboundfeeds/rss/",       "source": "CoinDesk"},
    {"url": "https://cointelegraph.com/rss",                     "source": "CoinTelegraph"},
]

HISTORY_FILE     = "docs/trade_history.json"
STATE_FILE       = "docs/bot_state.json"
MACRO_CACHE_FILE = "docs/macro_cache.json"
BACKTEST_FILE    = "docs/backtest.json"

# ============================================================
# AMELIORATION 9 : ALERTES TELEGRAM
# ============================================================

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
        print("  [TELEGRAM] Alerte envoyee")
    except Exception as e:
        print("  [TELEGRAM ERREUR] " + str(e))

# ============================================================
# RECUPERATION DES PRIX
# ============================================================

def get_eur_rate():
    try:
        r = requests.get(
            "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
            timeout=5
        )
        return r.json()["usd"]["eur"]
    except:
        try:
            r = requests.get("https://api.frankfurter.app/latest?from=USD&to=EUR", timeout=5)
            return r.json()["rates"]["EUR"]
        except:
            return 0.923

def get_crypto_prices():
    prices = {}
    try:
        ids = ",".join(COINGECKO_IDS.values())
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets"
            "?vs_currency=usd&ids=" + ids +
            "&order=market_cap_desc&per_page=20&page=1"
            "&sparkline=false&price_change_percentage=24h",
            headers={"Accept": "application/json"},
            timeout=15
        )
        data = r.json()
        id_to_ticker = {v: k for k, v in COINGECKO_IDS.items()}
        for coin in data:
            key = id_to_ticker.get(coin["id"])
            if not key:
                continue
            prices[key] = {
                "price_usd":  float(coin["current_price"]),
                "change_24h": float(coin.get("price_change_percentage_24h") or 0),
                "volume_usd": float(coin.get("total_volume") or 0),
                "high_24h":   float(coin.get("high_24h") or coin["current_price"]),
                "low_24h":    float(coin.get("low_24h")  or coin["current_price"]),
                "closes":     [],
                "volumes":    [],
                "name":       CRYPTO_ASSETS[key]["name"],
                "type":       "crypto",
                "source":     "CoinGecko LIVE"
            }
            print("  [OK] " + key + " = " + str(round(float(coin["current_price"]), 2)) + " USD (" + str(round(float(coin.get("price_change_percentage_24h") or 0), 2)) + "%)")
    except Exception as e:
        print("  [ERREUR CoinGecko] " + str(e))
    return prices

def get_yahoo_price(ticker, name, asset_type):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker + "?interval=1d&range=60d",
            headers=headers, timeout=10
        )
        data   = r.json()
        result = data["chart"]["result"][0]
        meta   = result["meta"]
        price  = float(meta.get("regularMarketPrice", 0))
        prev   = float(meta.get("chartPreviousClose", meta.get("previousClose", price)))
        change = ((price - prev) / prev * 100) if prev else 0
        closes  = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes  = [c for c in closes if c is not None]
        volumes = result.get("indicators", {}).get("quote", [{}])[0].get("volume", [])
        volumes = [v for v in volumes if v is not None]
        print("  [OK] " + ticker + " = " + str(round(price, 2)) + " USD (" + str(round(change, 2)) + "%)")
        return {
            "price_usd":  price,
            "change_24h": round(change, 2),
            "volume_usd": int(meta.get("regularMarketVolume", 0)) * price,
            "high_24h":   float(meta.get("regularMarketDayHigh", price)),
            "low_24h":    float(meta.get("regularMarketDayLow", price)),
            "closes":     closes,
            "volumes":    volumes,
            "name":       name,
            "type":       asset_type,
            "source":     "Yahoo Finance LIVE"
        }
    except Exception as e:
        print("  [ERREUR] " + ticker + ": " + str(e))
        return None

def get_stock_prices():
    prices = {}
    for key, info in STOCK_ASSETS.items():
        result = get_yahoo_price(info["ticker"], info["name"], "stock")
        if result:
            prices[key] = result
        time.sleep(0.3)
    return prices

def get_etf_prices():
    prices = {}
    for key, info in ETF_ASSETS.items():
        result = get_yahoo_price(info["ticker"], info["name"], "etf")
        if result:
            prices[key] = result
        time.sleep(0.3)
    return prices

# ============================================================
# AMELIORATION 5 : ACTUALITES RSS
# ============================================================

def fetch_rss_news():
    all_headlines = []
    for feed in RSS_FEEDS:
        try:
            r = requests.get(feed["url"], timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            items = root.findall(".//item")[:5]
            for item in items:
                title = item.findtext("title", "").strip()
                if title:
                    all_headlines.append(feed["source"] + ": " + title)
        except Exception as e:
            print("  [RSS ERREUR] " + feed["source"] + ": " + str(e))
    print("  [RSS] " + str(len(all_headlines)) + " actualites recuperees")
    return all_headlines[:20]

# ============================================================
# AMELIORATION 3 : CORRELATION CRYPTO
# ============================================================

def get_btc_status(all_prices):
    btc = all_prices.get("BTC")
    if not btc:
        return "unknown", 0
    chg = btc["change_24h"]
    if chg <= BTC_CRASH_THRESHOLD:
        print("  [CORRELATION] BTC en chute severe (" + str(chg) + "%) -> BLOCAGE achats crypto")
        return "crash", chg
    elif chg <= BTC_WARN_THRESHOLD:
        print("  [CORRELATION] BTC en baisse (" + str(chg) + "%) -> reduction score crypto -" + str(BTC_PENALTY_PTS) + "pts")
        return "warn", chg
    return "ok", chg

# ============================================================
# ALGORITHME TECHNIQUE INTERNE
# ============================================================

def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100
    return round(100 - (100 / (1 + ag/al)), 1)

def compute_macd(closes):
    if len(closes) < 26:
        return 0, 0
    def ema(data, p):
        k = 2 / (p + 1)
        v = data[0]
        for x in data[1:]:
            v = x * k + v * (1 - k)
        return v
    m = ema(closes[-26:], 12) - ema(closes[-26:], 26)
    s = ema(closes[-9:], 9) if len(closes) >= 9 else m
    return round(m, 4), round(s, 4)

def compute_bollinger(closes, period=20):
    if len(closes) < period:
        return 0, 0, 0
    r = closes[-period:]
    ma = sum(r) / period
    std = math.sqrt(sum((x - ma)**2 for x in r) / period)
    return round(ma + 2*std, 4), round(ma, 4), round(ma - 2*std, 4)

def compute_ma(closes, period):
    if len(closes) < period:
        return closes[-1] if closes else 0
    return round(sum(closes[-period:]) / period, 4)

def compute_momentum(closes, period=10):
    if len(closes) < period + 1:
        return 0
    return round((closes[-1] - closes[-period-1]) / closes[-period-1] * 100, 2)

def compute_volume_score(volumes):
    if len(volumes) < 10:
        return 50
    avg = sum(volumes[-10:]) / 10
    if avg == 0:
        return 50
    ratio = volumes[-1] / avg
    if ratio > 2.0:   return 80
    elif ratio > 1.5: return 65
    elif ratio > 1.0: return 55
    else:             return 40

def analyze_technical(asset, price_data):
    closes  = price_data.get("closes", [])
    volumes = price_data.get("volumes", [])
    price   = price_data["price_usd"]
    change  = price_data["change_24h"]

    rsi = compute_rsi(closes)
    if rsi < 30:   score_rsi = 80
    elif rsi < 45: score_rsi = 65
    elif rsi < 55: score_rsi = 50
    elif rsi < 70: score_rsi = 40
    else:          score_rsi = 20

    macd_line, signal_line = compute_macd(closes)
    if macd_line > signal_line and macd_line > 0:   score_macd = 75
    elif macd_line > signal_line:                   score_macd = 62
    elif macd_line < signal_line and macd_line < 0: score_macd = 25
    else:                                           score_macd = 38

    bb_upper, bb_mid, bb_lower = compute_bollinger(closes)
    if bb_upper > bb_lower and (bb_upper - bb_lower) > 0:
        pos = (price - bb_lower) / (bb_upper - bb_lower)
        if pos < 0.2:   score_bb = 78
        elif pos < 0.4: score_bb = 62
        elif pos < 0.6: score_bb = 50
        elif pos < 0.8: score_bb = 38
        else:           score_bb = 22
    else:
        score_bb = 50

    ma20 = compute_ma(closes, 20)
    ma50 = compute_ma(closes, 50)
    if price > ma20 and price > ma50 and ma20 > ma50:   score_ma = 75
    elif price > ma20 and ma20 > ma50:                  score_ma = 62
    elif price < ma20 and price < ma50:                 score_ma = 30
    elif price < ma20:                                  score_ma = 42
    else:                                               score_ma = 50

    momentum = compute_momentum(closes)
    if momentum > 10:    score_mom = 75
    elif momentum > 5:   score_mom = 65
    elif momentum > 0:   score_mom = 55
    elif momentum > -5:  score_mom = 40
    else:                score_mom = 25

    score_vol = compute_volume_score(volumes) if volumes else 50

    if change > 5:    score_chg = 30
    elif change > 2:  score_chg = 60
    elif change > 0:  score_chg = 55
    elif change > -3: score_chg = 45
    elif change > -7: score_chg = 35
    else:             score_chg = 20

    score_technique = round(
        score_rsi  * 0.25 + score_macd * 0.20 + score_bb  * 0.15 +
        score_ma   * 0.20 + score_mom  * 0.10 + score_vol * 0.05 +
        score_chg  * 0.05
    )

    if score_technique >= 65:   tendance = "HAUSSIERE"
    elif score_technique <= 40: tendance = "BAISSIERE"
    else:                       tendance = "NEUTRE"

    if score_technique >= 70:   signal_tech = "BUY"
    elif score_technique <= 35: signal_tech = "SELL"
    else:                       signal_tech = "HOLD"

    if rsi > 70:   rsi_analyse = "surachete"
    elif rsi < 30: rsi_analyse = "survendu"
    else:          rsi_analyse = "neutre"

    return {
        "score_technique": score_technique,
        "score_rsi":       score_rsi,
        "score_macd":      score_macd,
        "score_bollinger": score_bb,
        "score_ma":        score_ma,
        "score_momentum":  score_mom,
        "score_volume":    score_vol,
        "rsi":             rsi,
        "macd":            macd_line,
        "macd_signal":     signal_line,
        "bb_upper":        bb_upper,
        "bb_mid":          bb_mid,
        "bb_lower":        bb_lower,
        "ma20":            ma20,
        "ma50":            ma50,
        "momentum":        momentum,
        "tendance":        tendance,
        "signal_tech":     signal_tech,
        "rsi_analyse":     rsi_analyse,
    }

# ============================================================
# AMELIORATION 1 : BACKTESTING
# ============================================================

def run_backtest(asset, closes, eur_rate):
    if len(closes) < 30:
        return None

    trades = []
    in_position = False
    entry_price = 0
    wins = 0
    losses = 0
    total_pnl = 0

    for i in range(20, len(closes) - 1):
        window = closes[:i+1]
        rsi    = compute_rsi(window)
        ma20   = compute_ma(window, 20)
        macd_l, macd_s = compute_macd(window)
        price  = closes[i]

        # Signal achat simplifie
        buy_signal  = (rsi < 45 and price > ma20 and macd_l > macd_s)
        sell_signal = (rsi > 65 or price < ma20 * 0.93 or price > entry_price * 1.18)

        if not in_position and buy_signal:
            entry_price  = price
            in_position  = True
        elif in_position and sell_signal:
            pnl = (price - entry_price) / entry_price * 100
            total_pnl += pnl
            if pnl > 0:
                wins += 1
            else:
                losses += 1
            trades.append(round(pnl, 2))
            in_position = False

    total_trades = wins + losses
    if total_trades == 0:
        return None

    win_rate   = round(wins / total_trades * 100, 1)
    avg_pnl    = round(total_pnl / total_trades, 2)
    best_trade = round(max(trades), 2) if trades else 0
    worst      = round(min(trades), 2) if trades else 0

    return {
        "asset":        asset,
        "total_trades": total_trades,
        "wins":         wins,
        "losses":       losses,
        "win_rate":     win_rate,
        "avg_pnl_pct":  avg_pnl,
        "total_pnl_pct":round(total_pnl, 2),
        "best_trade":   best_trade,
        "worst_trade":  worst,
        "periode":      "60 jours"
    }

# ============================================================
# CLAUDE IA (1x PAR JOUR)
# ============================================================

def should_run_claude():
    now_utc = datetime.now(timezone.utc)
    macro   = load_json(MACRO_CACHE_FILE, {})
    last    = macro.get("last_claude_run", "")
    if not last:
        return True
    last_dt = datetime.fromisoformat(last)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    hours = (now_utc - last_dt).total_seconds() / 3600
    if now_utc.hour == CLAUDE_HOUR_UTC and hours >= 20:
        return True
    if hours >= 25:
        return True
    print("[CLAUDE] Cache valide (" + str(round(hours, 1)) + "h) - score macro=" + str(macro.get("score_macro", 50)))
    return False

def run_claude_macro_analysis(all_prices, eur_rate, news_headlines):
    assets_summary = ""
    for asset, data in list(all_prices.items())[:8]:
        assets_summary += asset + " " + str(round(data["price_usd"] * eur_rate, 2)) + "EUR (" + str(data["change_24h"]) + "%) | "

    news_text = ""
    if news_headlines:
        news_text = "\n\nActualites du jour :\n" + "\n".join(["- " + h for h in news_headlines[:10]])

    try:
        prompt = (
            "Tu es un analyste financier IA expert en trading algorithmique.\n"
            "Date : " + datetime.now().strftime('%d/%m/%Y %H:%M') + " UTC\n"
            "Marches : " + assets_summary +
            news_text + "\n\n"
            "Analyse le contexte macro-economique et le sentiment de marche.\n"
            "Reponds UNIQUEMENT en JSON valide sans markdown :\n"
            '{"score_macro":<0-100>,"score_sentiment":<0-100>,'
            '"tendance_marche":"<HAUSSIER|BAISSIER|NEUTRE>",'
            '"contexte":"<resume 2 phrases>",'
            '"risque_principal":"<1 phrase>",'
            '"opportunite_du_jour":"<1 phrase>",'
            '"actifs_favorables":["<t1>","<t2>"],'
            '"actifs_risques":["<t1>","<t2>"]}'
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": CLAUDE_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        text = r.json()["content"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        result["last_claude_run"] = datetime.now(timezone.utc).isoformat()
        result["news_count"]      = len(news_headlines)
        print("[CLAUDE] OK - macro=" + str(result.get("score_macro")) + " sentiment=" + str(result.get("score_sentiment")) + " news=" + str(len(news_headlines)))
        return result
    except Exception as e:
        print("[CLAUDE ERREUR] " + str(e))
        return None

# ============================================================
# SCORE FINAL HYBRIDE
# ============================================================

def compute_final_score(tech, macro_cache, asset, btc_status):
    score_tech      = tech["score_technique"]
    score_macro     = macro_cache.get("score_macro", 50)
    score_sentiment = macro_cache.get("score_sentiment", 50)
    favorables      = macro_cache.get("actifs_favorables", [])
    risques         = macro_cache.get("actifs_risques", [])
    bonus           = 5 if asset in favorables else (-5 if asset in risques else 0)

    score = round(score_tech * 0.60 + score_macro * 0.25 + score_sentiment * 0.15 + bonus)

    # Amelioration 3 : penalite BTC correlation
    asset_type = "crypto" if asset in CRYPTO_ASSETS else "other"
    if asset_type == "crypto" and btc_status == "warn":
        score = max(0, score - BTC_PENALTY_PTS)
        print("  [CORRELATION] Penalite -" + str(BTC_PENALTY_PTS) + "pts appliquee")

    return min(100, max(0, score))

# ============================================================
# AMELIORATION 2 : VERIFICATION EXPOSITION
# ============================================================

def can_open_position(asset, bot_state, asset_type):
    positions = bot_state.get("positions", {})
    total_pos = len(positions)
    total_inv = sum(p.get("amount_eur", 0) for p in positions.values())

    # Compter par type
    crypto_pos = sum(1 for k in positions if k in CRYPTO_ASSETS)
    stock_pos  = sum(1 for k in positions if k not in CRYPTO_ASSETS)

    if total_pos >= MAX_POSITIONS:
        print("  [EXPOSITION] Max positions atteint (" + str(MAX_POSITIONS) + ") - achat bloque")
        return False
    if total_inv + MAX_TRADE_EUR > MAX_TOTAL_EUR:
        print("  [EXPOSITION] Budget max atteint (" + str(MAX_TOTAL_EUR) + "EUR) - achat bloque")
        return False
    if asset_type == "crypto" and crypto_pos >= MAX_CRYPTO_POS:
        print("  [EXPOSITION] Max positions crypto atteint (" + str(MAX_CRYPTO_POS) + ") - achat bloque")
        return False
    if asset_type != "crypto" and stock_pos >= MAX_STOCK_POS:
        print("  [EXPOSITION] Max positions actions/ETF atteint (" + str(MAX_STOCK_POS) + ") - achat bloque")
        return False
    return True

# ============================================================
# ORDRE BITPANDA
# ============================================================

def place_order_bitpanda(asset, side, amount_eur):
    if DRY_RUN:
        print("  [DRY RUN] " + side + " " + asset + " " + str(amount_eur) + "EUR")
        return {"status": "simulated"}
    try:
        r = requests.get("https://api.exchange.bitpanda.com/public/v1/instruments", timeout=10)
        instrument_id = None
        for inst in r.json():
            if inst.get("base", {}).get("code") == asset and inst.get("quote", {}).get("code") == "EUR":
                instrument_id = inst["instrument_code"]
                break
        if not instrument_id:
            return None
        r = requests.post(
            "https://api.exchange.bitpanda.com/public/v1/account/orders",
            headers={"Authorization": "Bearer " + BITPANDA_KEY, "Content-Type": "application/json"},
            json={"instrument_code": instrument_id, "type": "MARKET", "side": side, "amount": str(amount_eur)},
            timeout=15
        )
        return r.json()
    except Exception as e:
        print("  [BITPANDA ERREUR] " + str(e))
        return None

# ============================================================
# UTILITAIRES
# ============================================================

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================
# BOT PRINCIPAL
# ============================================================

def run_bot():
    print("\n" + "="*60)
    print("  HAOUD TRADING IA v2.0 - " + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + " UTC")
    print("="*60 + "\n")

    eur_rate = get_eur_rate()
    print("[FX] 1 USD = " + str(round(eur_rate, 4)) + " EUR\n")

    # --- Prix ---
    print("[CRYPTO] CoinGecko...")
    all_prices = {}
    all_prices.update(get_crypto_prices())
    print("\n[ACTIONS] Yahoo Finance...")
    all_prices.update(get_stock_prices())
    print("\n[ETFs] Yahoo Finance...")
    all_prices.update(get_etf_prices())

    # --- Amelioration 3 : statut BTC ---
    btc_status, btc_chg = get_btc_status(all_prices)
    if btc_status == "crash":
        send_telegram("ALERTE HAOUD TRADING IA\nBTC en chute severe : " + str(btc_chg) + "%\nAchats crypto bloques automatiquement.")

    # --- Amelioration 5 : RSS ---
    print("\n[RSS] Recuperation actualites...")
    news_headlines = fetch_rss_news()

    # --- Amelioration 1 : Backtesting ---
    print("\n[BACKTEST] Calcul sur 60 jours...")
    backtest_results = {}
    for asset, price_data in all_prices.items():
        closes = price_data.get("closes", [])
        if len(closes) >= 30:
            bt = run_backtest(asset, closes, eur_rate)
            if bt:
                backtest_results[asset] = bt
                print("  [BT] " + asset + " | " + str(bt["total_trades"]) + " trades | Win=" + str(bt["win_rate"]) + "% | PnL=" + str(bt["total_pnl_pct"]) + "%")
    save_json(BACKTEST_FILE, {
        "last_update": datetime.now().isoformat(),
        "results": backtest_results
    })

    # --- Claude macro (1x/jour) ---
    macro_cache = load_json(MACRO_CACHE_FILE, {
        "score_macro": 50, "score_sentiment": 50,
        "tendance_marche": "NEUTRE",
        "contexte": "Analyse macro non disponible.",
        "risque_principal": "Aucun risque identifie.",
        "opportunite_du_jour": "Aucune opportunite identifiee.",
        "actifs_favorables": [], "actifs_risques": []
    })
    print("\n[MACRO] Verification Claude...")
    if should_run_claude() and CLAUDE_KEY:
        new_macro = run_claude_macro_analysis(all_prices, eur_rate, news_headlines)
        if new_macro:
            macro_cache.update(new_macro)
            save_json(MACRO_CACHE_FILE, macro_cache)
            send_telegram(
                "HAOUD TRADING IA - Analyse macro du jour\n"
                "Macro: " + str(macro_cache.get("score_macro")) + "/100 | "
                "Sentiment: " + str(macro_cache.get("score_sentiment")) + "/100\n"
                "Tendance: " + str(macro_cache.get("tendance_marche")) + "\n"
                + str(macro_cache.get("contexte", ""))
            )

    # --- Analyse et decisions ---
    history   = load_json(HISTORY_FILE, [])
    bot_state = load_json(STATE_FILE, {"positions": {}, "last_run": None, "total_pnl_eur": 0})

    print("\n[ANALYSE] " + str(len(all_prices)) + " actifs...\n")
    results = []

    for asset, price_data in all_prices.items():
        price_usd  = price_data["price_usd"]
        price_eur  = price_usd * eur_rate
        change     = price_data["change_24h"]
        name       = price_data.get("name", asset)
        atype      = price_data.get("type", "crypto")
        asset_type = "crypto" if asset in CRYPTO_ASSETS else "other"

        tech        = analyze_technical(asset, price_data)
        score_final = compute_final_score(tech, macro_cache, asset, btc_status)

        # Blocage total si BTC crash
        if asset_type == "crypto" and btc_status == "crash":
            signal = "HOLD"
            print("[" + asset + "] " + str(round(price_eur, 2)) + "EUR | RSI=" + str(tech["rsi"]) + " | Score=" + str(score_final) + " | HOLD (BTC crash)")
        else:
            if score_final >= MIN_SCORE_BUY and tech["signal_tech"] == "BUY":
                signal = "BUY"
            elif score_final <= MAX_SCORE_SELL and tech["signal_tech"] == "SELL":
                signal = "SELL"
            else:
                signal = "HOLD"
            # Securite
            if signal == "BUY"  and score_final < MIN_SCORE_BUY: signal = "HOLD"
            if signal == "SELL" and score_final > MAX_SCORE_SELL: signal = "HOLD"
            print("[" + asset + "] " + str(round(price_eur, 2)) + "EUR (" + str(change) + "%) | RSI=" + str(tech["rsi"]) + " | Score=" + str(score_final) + " | " + signal)

        action_taken = None
        position     = bot_state["positions"].get(asset)

        if position:
            entry_price = position["entry_price_eur"]
            pnl_pct     = (price_eur - entry_price) / entry_price
            if pnl_pct <= -STOP_LOSS_PCT:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                del bot_state["positions"][asset]
                action_taken = "STOP_LOSS"
                send_telegram(
                    "STOP-LOSS DECLENCHE - HAOUD TRADING IA\n"
                    "Actif: " + asset + " (" + name + ")\n"
                    "PnL: " + str(round(pnl_pct*100, 2)) + "% (" + str(round(pnl_eur, 2)) + "EUR)\n"
                    "Prix sortie: " + str(round(price_eur, 2)) + "EUR"
                )
            elif pnl_pct >= TAKE_PROFIT_PCT:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                del bot_state["positions"][asset]
                action_taken = "TAKE_PROFIT"
                send_telegram(
                    "TAKE-PROFIT DECLENCHE - HAOUD TRADING IA\n"
                    "Actif: " + asset + " (" + name + ")\n"
                    "PnL: +" + str(round(pnl_pct*100, 2)) + "% (+" + str(round(pnl_eur, 2)) + "EUR)\n"
                    "Prix sortie: " + str(round(price_eur, 2)) + "EUR"
                )

        elif signal == "BUY" and score_final >= MIN_SCORE_BUY and not position:
            # Amelioration 2 : verification exposition
            if can_open_position(asset, bot_state, asset_type):
                place_order_bitpanda(asset, "BUY", MAX_TRADE_EUR)
                bot_state["positions"][asset] = {
                    "entry_price_eur": price_eur,
                    "amount_eur":      MAX_TRADE_EUR,
                    "entry_date":      datetime.now().isoformat()
                }
                action_taken = "BUY"
                send_telegram(
                    "SIGNAL ACHAT - HAOUD TRADING IA\n"
                    "Actif: " + asset + " (" + name + ")\n"
                    "Prix: " + str(round(price_eur, 2)) + "EUR\n"
                    "Score: " + str(score_final) + "/100 | RSI: " + str(tech["rsi"]) + "\n"
                    "Montant: " + str(MAX_TRADE_EUR) + "EUR\n"
                    "Stop-loss: " + str(round(price_eur*0.93, 2)) + "EUR | TP: " + str(round(price_eur*1.18, 2)) + "EUR"
                )

        elif signal == "SELL" and score_final <= MAX_SCORE_SELL and position:
            place_order_bitpanda(asset, "SELL", position["amount_eur"])
            del bot_state["positions"][asset]
            action_taken = "SELL"

        # Backtesting disponible ?
        bt = backtest_results.get(asset, {})

        entry = {
            "timestamp":       datetime.now().isoformat(),
            "asset":           asset,
            "name":            name,
            "type":            atype,
            "price_eur":       round(price_eur, 6),
            "price_usd":       round(price_usd, 6),
            "change_24h":      round(change, 2),
            "high_24h":        round(price_data.get("high_24h", 0) * eur_rate, 6),
            "low_24h":         round(price_data.get("low_24h", 0) * eur_rate, 6),
            "volume_usd":      round(price_data.get("volume_usd", 0), 0),
            "rsi":             tech["rsi"],
            "macd":            tech["macd"],
            "bb_upper":        round(tech["bb_upper"] * eur_rate, 4),
            "bb_lower":        round(tech["bb_lower"] * eur_rate, 4),
            "ma20":            round(tech["ma20"] * eur_rate, 4),
            "ma50":            round(tech["ma50"] * eur_rate, 4),
            "momentum":        tech["momentum"],
            "score":           score_final,
            "score_technique": tech["score_technique"],
            "score_macro":     macro_cache.get("score_macro", 50),
            "score_sentiment": macro_cache.get("score_sentiment", 50),
            "score_momentum":  tech["score_momentum"],
            "score_volume":    tech["score_volume"],
            "signal":          signal,
            "confiance":       score_final,
            "tendance":        tech["tendance"],
            "rsi_analyse":     tech["rsi_analyse"],
            "action":          action_taken or "HOLD",
            "raison":          macro_cache.get("contexte", ""),
            "risque":          macro_cache.get("risque_principal", ""),
            "opportunite":     macro_cache.get("opportunite_du_jour", ""),
            "source":          price_data.get("source", ""),
            "bt_win_rate":     bt.get("win_rate", None),
            "bt_avg_pnl":      bt.get("avg_pnl_pct", None),
            "dry_run":         DRY_RUN
        }
        history.append(entry)
        results.append(entry)

    history = history[-1000:]

    bot_state["last_run"]    = datetime.now().isoformat()
    bot_state["eur_rate"]    = eur_rate
    bot_state["dry_run"]     = DRY_RUN
    bot_state["btc_status"]  = btc_status
    bot_state["btc_change"]  = btc_chg
    bot_state["macro"]       = {
        "score_macro":         macro_cache.get("score_macro", 50),
        "score_sentiment":     macro_cache.get("score_sentiment", 50),
        "tendance_marche":     macro_cache.get("tendance_marche", "NEUTRE"),
        "contexte":            macro_cache.get("contexte", ""),
        "risque_principal":    macro_cache.get("risque_principal", ""),
        "opportunite_du_jour": macro_cache.get("opportunite_du_jour", ""),
        "last_claude_run":     macro_cache.get("last_claude_run", ""),
        "news_count":          macro_cache.get("news_count", 0),
    }
    bot_state["exposition"]  = {
        "total_positions":  len(bot_state["positions"]),
        "total_investi_eur": sum(p.get("amount_eur", 0) for p in bot_state["positions"].values()),
        "max_positions":    MAX_POSITIONS,
        "max_total_eur":    MAX_TOTAL_EUR,
    }
    bot_state["last_prices"] = {
        k: {
            "price_eur":  round(v["price_usd"] * eur_rate, 6),
            "price_usd":  round(v["price_usd"], 6),
            "change_24h": round(v["change_24h"], 2),
            "high_24h":   round(v.get("high_24h", 0) * eur_rate, 6),
            "low_24h":    round(v.get("low_24h", 0) * eur_rate, 6),
            "volume_usd": round(v.get("volume_usd", 0), 0),
            "rsi":        compute_rsi(v.get("closes", [])),
            "name":       v.get("name", k),
            "type":       v.get("type", "crypto"),
            "source":     v.get("source", "")
        } for k, v in all_prices.items()
    }

    save_json(HISTORY_FILE, history)
    save_json(STATE_FILE, bot_state)

    actions = [e for e in results if e["action"] != "HOLD"]
    print("\n" + "="*60)
    print("  DONE - " + str(len(results)) + " actifs | " + str(len(actions)) + " ordres | PnL: " + str(bot_state["total_pnl_eur"]) + "EUR")
    print("  Exposition: " + str(len(bot_state["positions"])) + "/" + str(MAX_POSITIONS) + " positions | " + str(sum(p.get("amount_eur",0) for p in bot_state["positions"].values())) + "/" + str(MAX_TOTAL_EUR) + "EUR")
    print("  BTC status: " + btc_status + " (" + str(btc_chg) + "%)")
    print("  News RSS: " + str(len(news_headlines)) + " actualites")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_bot()

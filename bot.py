# HAOUD TRADING IA - v3.0 (vers 8/10)
# Ameliorations :
# 1. Donnees historiques 1 an (Yahoo Finance 1y)
# 2. Donnees on-chain crypto (blockchain.info + etherscan)
# 3. Optimisation automatique des parametres (backtesting adaptatif)
# 4. Sentiment Reddit (API gratuite sans cle)
# + tout ce qui existait en v2

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

CLAUDE_KEY     = os.environ.get("CLAUDE_API_KEY", "")
BITPANDA_KEY   = os.environ.get("BITPANDA_API_KEY", "")
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
    "BTC":  "bitcoin",    "ETH":  "ethereum",
    "SOL":  "solana",     "BNB":  "binancecoin",
    "XRP":  "ripple",     "ADA":  "cardano",
    "AVAX": "avalanche-2","LINK": "chainlink",
    "DOT":  "polkadot",   "MATIC":"matic-network",
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

# --- PARAMETRES DE BASE (seront auto-optimises) ---
DEFAULT_PARAMS = {
    "MIN_SCORE_BUY":   70,
    "MAX_SCORE_SELL":  40,
    "RSI_OVERSOLD":    35,
    "RSI_OVERBOUGHT":  65,
    "STOP_LOSS_PCT":   0.07,
    "TAKE_PROFIT_PCT": 0.18,
}

MAX_TRADE_EUR        = 50
DRY_RUN              = True
MAX_POSITIONS        = 5
MAX_TOTAL_EUR        = 250
MAX_CRYPTO_POS       = 3
MAX_STOCK_POS        = 2
BTC_CRASH_THRESHOLD  = -5.0
BTC_WARN_THRESHOLD   = -3.0
BTC_PENALTY_PTS      = 15
CLAUDE_HOUR_UTC      = 8

# --- REDDIT SUBREDDITS (amelioration 4) ---
REDDIT_SUBS = [
    {"sub": "CryptoCurrency",  "type": "crypto"},
    {"sub": "Bitcoin",         "type": "crypto"},
    {"sub": "wallstreetbets",  "type": "stock"},
    {"sub": "investing",       "type": "stock"},
    {"sub": "stocks",          "type": "stock"},
]

# --- RSS FEEDS ---
RSS_FEEDS = [
    {"url": "https://feeds.reuters.com/reuters/businessNews",   "source": "Reuters Business"},
    {"url": "https://feeds.reuters.com/reuters/technologyNews", "source": "Reuters Tech"},
    {"url": "https://coindesk.com/arc/outboundfeeds/rss/",      "source": "CoinDesk"},
    {"url": "https://cointelegraph.com/rss",                    "source": "CoinTelegraph"},
]

HISTORY_FILE      = "docs/trade_history.json"
STATE_FILE        = "docs/bot_state.json"
MACRO_CACHE_FILE  = "docs/macro_cache.json"
BACKTEST_FILE     = "docs/backtest.json"
PARAMS_FILE       = "docs/optimized_params.json"

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

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

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
            headers={"Accept": "application/json"}, timeout=15
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
                "market_cap": float(coin.get("market_cap") or 0),
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

# AMELIORATION 1 : range=1y au lieu de 60d
def get_yahoo_price(ticker, name, asset_type):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker + "?interval=1d&range=1y",
            headers=headers, timeout=12
        )
        data    = r.json()
        result  = data["chart"]["result"][0]
        meta    = result["meta"]
        price   = float(meta.get("regularMarketPrice", 0))
        prev    = float(meta.get("chartPreviousClose", meta.get("previousClose", price)))
        change  = ((price - prev) / prev * 100) if prev else 0
        closes  = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes  = [c for c in closes if c is not None]
        volumes = result.get("indicators", {}).get("quote", [{}])[0].get("volume", [])
        volumes = [v for v in volumes if v is not None]
        print("  [OK] " + ticker + " = " + str(round(price, 2)) + " USD | " + str(len(closes)) + "j historique")
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
            "source":     "Yahoo Finance 1an"
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
# AMELIORATION 2 : DONNEES ON-CHAIN CRYPTO
# ============================================================

def get_onchain_data():
    onchain = {}
    # BTC on-chain via blockchain.info (gratuit, sans cle)
    try:
        r = requests.get("https://blockchain.info/stats?format=json", timeout=8)
        d = r.json()
        btc_tx_per_day  = d.get("n_tx", 0)
        btc_hash_rate   = d.get("hash_rate", 0)
        btc_difficulty  = d.get("difficulty", 0)
        # Score on-chain BTC : transactions elevees = adoption forte
        if btc_tx_per_day > 400000:   score_btc_onchain = 75
        elif btc_tx_per_day > 300000: score_btc_onchain = 60
        elif btc_tx_per_day > 200000: score_btc_onchain = 50
        else:                         score_btc_onchain = 35
        onchain["BTC"] = {
            "tx_per_day":   btc_tx_per_day,
            "hash_rate":    btc_hash_rate,
            "difficulty":   btc_difficulty,
            "score_onchain": score_btc_onchain
        }
        print("  [ON-CHAIN] BTC tx/jour=" + str(btc_tx_per_day) + " score=" + str(score_btc_onchain))
    except Exception as e:
        print("  [ON-CHAIN] BTC erreur: " + str(e))

    # ETH on-chain via etherscan (gratuit, sans cle pour stats basiques)
    try:
        r = requests.get(
            "https://api.etherscan.io/api?module=stats&action=ethsupply",
            timeout=8
        )
        # Utiliser gastracker pour l'activite reseau
        r2 = requests.get(
            "https://api.etherscan.io/api?module=gastracker&action=gasoracle",
            timeout=8
        )
        gas = r2.json().get("result", {})
        gas_price = float(gas.get("SafeGasPrice", 20))
        # Gas eleve = reseau actif mais couteux
        if gas_price < 15:    score_eth_onchain = 70   # reseau calme = bon
        elif gas_price < 30:  score_eth_onchain = 60
        elif gas_price < 60:  score_eth_onchain = 45
        else:                 score_eth_onchain = 30   # reseau sature
        onchain["ETH"] = {
            "gas_price_gwei": gas_price,
            "score_onchain":  score_eth_onchain
        }
        print("  [ON-CHAIN] ETH gas=" + str(gas_price) + " gwei score=" + str(score_eth_onchain))
    except Exception as e:
        print("  [ON-CHAIN] ETH erreur: " + str(e))

    return onchain

# ============================================================
# AMELIORATION 4 : SENTIMENT REDDIT (sans cle API)
# ============================================================

BULLISH_WORDS = ["bull", "moon", "pump", "buy", "long", "surge", "rally", "breakout", "ath", "gain", "up", "bullish", "rocket", "hodl", "accumulate"]
BEARISH_WORDS = ["bear", "dump", "sell", "short", "crash", "drop", "down", "bearish", "fear", "panic", "correction", "loss", "red", "rekt", "capitulation"]

def get_reddit_sentiment():
    sentiment = {"crypto": 50, "stock": 50, "posts_analyzed": 0, "top_mentions": {}}
    total_bull, total_bear, total_posts = 0, 0, 0
    mentions = {}

    for sub_info in REDDIT_SUBS:
        try:
            r = requests.get(
                "https://www.reddit.com/r/" + sub_info["sub"] + "/hot.json?limit=25",
                headers={"User-Agent": "HAOUD-TradingBot/3.0"},
                timeout=10
            )
            posts = r.json().get("data", {}).get("children", [])
            for post in posts:
                d = post.get("data", {})
                text = (d.get("title", "") + " " + d.get("selftext", "")).lower()
                score_post = d.get("score", 0)

                # Compter sentiments (ponderes par le score Reddit)
                weight = min(score_post / 1000, 3) + 1
                bull_count = sum(text.count(w) for w in BULLISH_WORDS)
                bear_count = sum(text.count(w) for w in BEARISH_WORDS)
                total_bull += bull_count * weight
                total_bear += bear_count * weight
                total_posts += 1

                # Detecter mentions de tickers
                for asset in list(CRYPTO_ASSETS.keys()) + list(STOCK_ASSETS.keys()):
                    if asset.lower() in text or asset in text:
                        mentions[asset] = mentions.get(asset, 0) + 1

            time.sleep(0.5)
        except Exception as e:
            print("  [REDDIT] Erreur " + sub_info["sub"] + ": " + str(e))

    if total_bull + total_bear > 0:
        bull_ratio = total_bull / (total_bull + total_bear)
        score_reddit = round(bull_ratio * 100)
        sentiment["crypto"] = score_reddit
        sentiment["stock"]  = score_reddit
        sentiment["posts_analyzed"] = total_posts
        sentiment["top_mentions"] = dict(sorted(mentions.items(), key=lambda x: x[1], reverse=True)[:5])
        print("  [REDDIT] " + str(total_posts) + " posts | Bull=" + str(round(total_bull)) + " Bear=" + str(round(total_bear)) + " Score=" + str(score_reddit))
    else:
        print("  [REDDIT] Aucun sentiment detecte - score neutre 50")

    return sentiment

# ============================================================
# ACTUALITES RSS
# ============================================================

def fetch_rss_news():
    headlines = []
    for feed in RSS_FEEDS:
        try:
            r = requests.get(feed["url"], timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:5]:
                title = item.findtext("title", "").strip()
                if title:
                    headlines.append(feed["source"] + ": " + title)
        except Exception as e:
            print("  [RSS] " + feed["source"] + ": " + str(e))
    print("  [RSS] " + str(len(headlines)) + " actualites")
    return headlines[:20]

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
    return round(m, 6), round(s, 6)

def compute_bollinger(closes, period=20):
    if len(closes) < period:
        return 0, 0, 0
    r = closes[-period:]
    ma = sum(r) / period
    std = math.sqrt(sum((x - ma)**2 for x in r) / period)
    return round(ma + 2*std, 6), round(ma, 6), round(ma - 2*std, 6)

def compute_ma(closes, period):
    if len(closes) < period:
        return closes[-1] if closes else 0
    return round(sum(closes[-period:]) / period, 6)

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

def analyze_technical(asset, price_data, params):
    closes  = price_data.get("closes", [])
    volumes = price_data.get("volumes", [])
    price   = price_data["price_usd"]
    change  = price_data["change_24h"]

    rsi_os = params.get("RSI_OVERSOLD", 35)
    rsi_ob = params.get("RSI_OVERBOUGHT", 65)

    rsi = compute_rsi(closes)
    if rsi < rsi_os:                 score_rsi = 82
    elif rsi < rsi_os + 10:         score_rsi = 66
    elif rsi < 55:                   score_rsi = 50
    elif rsi < rsi_ob:               score_rsi = 40
    else:                            score_rsi = 18

    macd_line, signal_line = compute_macd(closes)
    if macd_line > signal_line and macd_line > 0:   score_macd = 78
    elif macd_line > signal_line:                   score_macd = 62
    elif macd_line < signal_line and macd_line < 0: score_macd = 22
    else:                                           score_macd = 38

    bb_upper, bb_mid, bb_lower = compute_bollinger(closes)
    if bb_upper > bb_lower and (bb_upper - bb_lower) > 0:
        pos = (price - bb_lower) / (bb_upper - bb_lower)
        if pos < 0.15:  score_bb = 82
        elif pos < 0.35:score_bb = 65
        elif pos < 0.65:score_bb = 50
        elif pos < 0.85:score_bb = 35
        else:           score_bb = 18
    else:
        score_bb = 50

    # MA sur 1 an : MA20, MA50, MA200
    ma20  = compute_ma(closes, 20)
    ma50  = compute_ma(closes, 50)
    ma200 = compute_ma(closes, 200)

    if price > ma20 and price > ma50 and price > ma200 and ma20 > ma50:
        score_ma = 82   # tendance long terme haussiere
    elif price > ma20 and price > ma50 and ma20 > ma50:
        score_ma = 68
    elif price > ma20:
        score_ma = 55
    elif price < ma20 and price < ma50 and price < ma200:
        score_ma = 18   # tendance long terme baissiere
    elif price < ma20 and price < ma50:
        score_ma = 32
    else:
        score_ma = 45

    momentum = compute_momentum(closes)
    if momentum > 15:    score_mom = 75
    elif momentum > 7:   score_mom = 65
    elif momentum > 2:   score_mom = 55
    elif momentum > -5:  score_mom = 42
    elif momentum > -12: score_mom = 30
    else:                score_mom = 18

    score_vol = compute_volume_score(volumes) if volumes else 50

    if change > 5:    score_chg = 28
    elif change > 2:  score_chg = 58
    elif change > 0:  score_chg = 54
    elif change > -3: score_chg = 44
    elif change > -7: score_chg = 32
    else:             score_chg = 18

    score_technique = round(
        score_rsi  * 0.22 + score_macd * 0.20 + score_bb  * 0.15 +
        score_ma   * 0.22 + score_mom  * 0.10 + score_vol * 0.06 +
        score_chg  * 0.05
    )

    if score_technique >= 65:   tendance = "HAUSSIERE"
    elif score_technique <= 40: tendance = "BAISSIERE"
    else:                       tendance = "NEUTRE"

    if score_technique >= params.get("MIN_SCORE_BUY", 70):  signal_tech = "BUY"
    elif score_technique <= params.get("MAX_SCORE_SELL", 40): signal_tech = "SELL"
    else:                                                      signal_tech = "HOLD"

    if rsi > rsi_ob:   rsi_analyse = "surachete"
    elif rsi < rsi_os: rsi_analyse = "survendu"
    else:              rsi_analyse = "neutre"

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
        "ma200":           ma200,
        "momentum":        momentum,
        "tendance":        tendance,
        "signal_tech":     signal_tech,
        "rsi_analyse":     rsi_analyse,
    }

# ============================================================
# AMELIORATION 1 : BACKTESTING SUR 1 AN
# ============================================================

def run_backtest(asset, closes, params):
    if len(closes) < 60:
        return None

    trades   = []
    position = False
    entry    = 0
    wins = losses = 0
    total_pnl = 0

    rsi_os = params.get("RSI_OVERSOLD", 35)
    rsi_ob = params.get("RSI_OVERBOUGHT", 65)
    sl     = params.get("STOP_LOSS_PCT", 0.07)
    tp     = params.get("TAKE_PROFIT_PCT", 0.18)

    for i in range(50, len(closes) - 1):
        w = closes[:i+1]
        rsi    = compute_rsi(w)
        ma20   = compute_ma(w, 20)
        ma50   = compute_ma(w, 50)
        macd_l, macd_s = compute_macd(w)
        price  = closes[i]

        buy_sig  = (rsi < rsi_os and price > ma20 and macd_l > macd_s)
        sell_sig = (rsi > rsi_ob or price < entry*(1-sl) or price > entry*(1+tp) or (price < ma20 and macd_l < macd_s))

        if not position and buy_sig:
            entry    = price
            position = True
        elif position and sell_sig:
            pnl = (price - entry) / entry * 100
            total_pnl += pnl
            if pnl > 0: wins += 1
            else:       losses += 1
            trades.append(round(pnl, 2))
            position = False

    total = wins + losses
    if total == 0:
        return None

    win_rate = round(wins / total * 100, 1)
    avg_pnl  = round(total_pnl / total, 2)
    max_dd   = round(min(trades), 2) if trades else 0

    return {
        "asset":           asset,
        "total_trades":    total,
        "wins":            wins,
        "losses":          losses,
        "win_rate":        win_rate,
        "avg_pnl_pct":     avg_pnl,
        "total_pnl_pct":   round(total_pnl, 2),
        "best_trade":      round(max(trades), 2) if trades else 0,
        "worst_trade":     max_dd,
        "periode":         str(len(closes)) + " jours",
        "params_used":     params
    }

# ============================================================
# AMELIORATION 3 : OPTIMISATION AUTOMATIQUE DES PARAMETRES
# ============================================================

def optimize_params(backtest_results):
    if not backtest_results:
        return DEFAULT_PARAMS.copy()

    # Analyser les resultats du backtest
    good_assets = [bt for bt in backtest_results.values() if bt and bt["win_rate"] >= 55 and bt["total_trades"] >= 5]
    bad_assets  = [bt for bt in backtest_results.values() if bt and bt["win_rate"] < 45 and bt["total_trades"] >= 5]

    params = DEFAULT_PARAMS.copy()

    if good_assets:
        avg_win_rate = sum(bt["win_rate"] for bt in good_assets) / len(good_assets)
        avg_pnl      = sum(bt["avg_pnl_pct"] for bt in good_assets) / len(good_assets)
        print("  [OPTIM] " + str(len(good_assets)) + " actifs rentables | Win rate moyen=" + str(round(avg_win_rate, 1)) + "%")

        # Si bon win rate global, etre un peu plus agressif
        if avg_win_rate >= 60:
            params["MIN_SCORE_BUY"]  = 68   # un peu plus permissif
            params["RSI_OVERSOLD"]   = 38
            print("  [OPTIM] Parametres assouplis (win rate eleve)")
        elif avg_win_rate >= 55:
            params["MIN_SCORE_BUY"]  = 70   # garder conservateur
            params["RSI_OVERSOLD"]   = 35
        else:
            params["MIN_SCORE_BUY"]  = 72   # plus strict
            params["RSI_OVERSOLD"]   = 32
            print("  [OPTIM] Parametres renforces (win rate faible)")

    if bad_assets:
        # Actifs qui perdent -> renforcer stop loss
        avg_worst = sum(bt["worst_trade"] for bt in bad_assets) / len(bad_assets)
        if avg_worst < -10:
            params["STOP_LOSS_PCT"] = 0.06   # stop loss plus serre
            print("  [OPTIM] Stop-loss resserre a 6% (pertes importantes detectees)")

    params["last_optimization"] = datetime.now().isoformat()
    params["assets_analyzed"]   = len(backtest_results)
    params["profitable_assets"] = len(good_assets)

    return params

# ============================================================
# CORRELATION CRYPTO
# ============================================================

def get_btc_status(all_prices):
    btc = all_prices.get("BTC")
    if not btc:
        return "unknown", 0
    chg = btc["change_24h"]
    if chg <= BTC_CRASH_THRESHOLD:
        print("  [CORRELATION] BTC crash (" + str(chg) + "%) -> blocage crypto")
        return "crash", chg
    elif chg <= BTC_WARN_THRESHOLD:
        print("  [CORRELATION] BTC baisse (" + str(chg) + "%) -> penalite -" + str(BTC_PENALTY_PTS) + "pts")
        return "warn", chg
    return "ok", chg

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
    print("[CLAUDE] Cache valide (" + str(round(hours, 1)) + "h) macro=" + str(macro.get("score_macro", 50)))
    return False

def run_claude_macro_analysis(all_prices, eur_rate, news_headlines, reddit_sentiment, backtest_results):
    assets_summary = ""
    for asset, data in list(all_prices.items())[:8]:
        assets_summary += asset + " " + str(round(data["price_usd"] * eur_rate, 2)) + "EUR (" + str(data["change_24h"]) + "%) | "

    news_text = ""
    if news_headlines:
        news_text = "\n\nActualites :\n" + "\n".join(["- " + h for h in news_headlines[:10]])

    reddit_text = ""
    if reddit_sentiment.get("posts_analyzed", 0) > 0:
        reddit_text = (
            "\n\nSentiment Reddit (" + str(reddit_sentiment["posts_analyzed"]) + " posts) : " +
            str(reddit_sentiment.get("crypto", 50)) + "/100" +
            " | Top mentions : " + str(reddit_sentiment.get("top_mentions", {}))
        )

    backtest_text = ""
    if backtest_results:
        good = [(a, bt["win_rate"]) for a, bt in backtest_results.items() if bt and bt["win_rate"] >= 55]
        bad  = [(a, bt["win_rate"]) for a, bt in backtest_results.items() if bt and bt["win_rate"] < 45]
        if good:
            backtest_text += "\nActifs rentables (backtest 1an) : " + str(good[:3])
        if bad:
            backtest_text += "\nActifs non rentables : " + str(bad[:3])

    try:
        prompt = (
            "Tu es un analyste financier IA expert en trading algorithmique.\n"
            "Date : " + datetime.now().strftime('%d/%m/%Y %H:%M') + " UTC\n"
            "Marches : " + assets_summary +
            news_text + reddit_text + backtest_text + "\n\n"
            "Analyse le contexte macro et le sentiment global.\n"
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
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        text = r.json()["content"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        result["last_claude_run"] = datetime.now(timezone.utc).isoformat()
        result["news_count"]      = len(news_headlines)
        result["reddit_score"]    = reddit_sentiment.get("crypto", 50)
        print("[CLAUDE] OK macro=" + str(result.get("score_macro")) + " sentiment=" + str(result.get("score_sentiment")))
        return result
    except Exception as e:
        print("[CLAUDE ERREUR] " + str(e))
        return None

# ============================================================
# SCORE FINAL HYBRIDE (avec on-chain)
# ============================================================

def compute_final_score(tech, macro_cache, asset, btc_status, onchain_data, params):
    score_tech      = tech["score_technique"]
    score_macro     = macro_cache.get("score_macro", 50)
    score_sentiment = macro_cache.get("score_sentiment", 50)
    favorables      = macro_cache.get("actifs_favorables", [])
    risques         = macro_cache.get("actifs_risques", [])
    bonus           = 5 if asset in favorables else (-5 if asset in risques else 0)

    # On-chain bonus pour crypto
    onchain_bonus = 0
    if asset in onchain_data:
        oc_score = onchain_data[asset].get("score_onchain", 50)
        onchain_bonus = round((oc_score - 50) * 0.1)
        if onchain_bonus != 0:
            print("  [ON-CHAIN] Bonus on-chain " + asset + ": " + str(onchain_bonus) + "pts")

    score = round(
        score_tech      * 0.55 +
        score_macro     * 0.20 +
        score_sentiment * 0.15 +
        (50 + onchain_bonus) * 0.10 +
        bonus
    )

    # Penalite BTC correlation
    if asset in CRYPTO_ASSETS and btc_status == "warn":
        score = max(0, score - BTC_PENALTY_PTS)

    return min(100, max(0, score))

# ============================================================
# GESTION EXPOSITION
# ============================================================

def can_open_position(asset, bot_state, asset_type):
    positions  = bot_state.get("positions", {})
    total_pos  = len(positions)
    total_inv  = sum(p.get("amount_eur", 0) for p in positions.values())
    crypto_pos = sum(1 for k in positions if k in CRYPTO_ASSETS)
    stock_pos  = sum(1 for k in positions if k not in CRYPTO_ASSETS)

    if total_pos >= MAX_POSITIONS:
        print("  [EXPOSITION] Max positions (" + str(MAX_POSITIONS) + ") atteint")
        return False
    if total_inv + MAX_TRADE_EUR > MAX_TOTAL_EUR:
        print("  [EXPOSITION] Budget max (" + str(MAX_TOTAL_EUR) + "EUR) atteint")
        return False
    if asset_type == "crypto" and crypto_pos >= MAX_CRYPTO_POS:
        print("  [EXPOSITION] Max crypto (" + str(MAX_CRYPTO_POS) + ") atteint")
        return False
    if asset_type != "crypto" and stock_pos >= MAX_STOCK_POS:
        print("  [EXPOSITION] Max actions/ETF (" + str(MAX_STOCK_POS) + ") atteint")
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
# BOT PRINCIPAL
# ============================================================

def run_bot():
    print("\n" + "="*60)
    print("  HAOUD TRADING IA v3.0 - " + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + " UTC")
    print("="*60 + "\n")

    eur_rate = get_eur_rate()
    print("[FX] 1 USD = " + str(round(eur_rate, 4)) + " EUR\n")

    # --- Prix (1 an historique) ---
    print("[CRYPTO] CoinGecko...")
    all_prices = {}
    all_prices.update(get_crypto_prices())
    print("\n[ACTIONS] Yahoo Finance (1 an)...")
    all_prices.update(get_stock_prices())
    print("\n[ETFs] Yahoo Finance (1 an)...")
    all_prices.update(get_etf_prices())

    # --- On-chain ---
    print("\n[ON-CHAIN] Blockchain.info + Etherscan...")
    onchain_data = get_onchain_data()

    # --- Reddit ---
    print("\n[REDDIT] Analyse sentiment...")
    reddit_sentiment = get_reddit_sentiment()

    # --- RSS ---
    print("\n[RSS] Actualites...")
    news_headlines = fetch_rss_news()

    # --- BTC correlation ---
    btc_status, btc_chg = get_btc_status(all_prices)
    if btc_status == "crash":
        send_telegram("ALERTE HAOUD TRADING IA\nBTC crash: " + str(btc_chg) + "%\nAchats crypto bloques.")

    # --- Backtest sur 1 an ---
    print("\n[BACKTEST] Calcul sur 1 an...")
    backtest_results = {}
    current_params = load_json(PARAMS_FILE, DEFAULT_PARAMS.copy())
    for asset, price_data in all_prices.items():
        closes = price_data.get("closes", [])
        if len(closes) >= 60:
            bt = run_backtest(asset, closes, current_params)
            if bt:
                backtest_results[asset] = bt
                print("  [BT] " + asset + " | " + str(bt["total_trades"]) + " trades | Win=" + str(bt["win_rate"]) + "% | Moy=" + str(bt["avg_pnl_pct"]) + "%")
    save_json(BACKTEST_FILE, {"last_update": datetime.now().isoformat(), "results": backtest_results})

    # --- Optimisation automatique des parametres ---
    print("\n[OPTIM] Optimisation des parametres...")
    optimized_params = optimize_params(backtest_results)
    save_json(PARAMS_FILE, optimized_params)
    params = optimized_params

    # --- Claude macro (1x/jour) ---
    macro_cache = load_json(MACRO_CACHE_FILE, {
        "score_macro": 50, "score_sentiment": 50,
        "tendance_marche": "NEUTRE",
        "contexte": "Analyse non disponible.",
        "risque_principal": "Aucun risque identifie.",
        "opportunite_du_jour": "Aucune opportunite.",
        "actifs_favorables": [], "actifs_risques": []
    })
    print("\n[MACRO] Verification Claude...")
    if should_run_claude() and CLAUDE_KEY:
        new_macro = run_claude_macro_analysis(all_prices, eur_rate, news_headlines, reddit_sentiment, backtest_results)
        if new_macro:
            macro_cache.update(new_macro)
            save_json(MACRO_CACHE_FILE, macro_cache)
            send_telegram(
                "HAOUD TRADING IA - Analyse macro\n"
                "Macro: " + str(macro_cache.get("score_macro")) + "/100 | "
                "Sentiment: " + str(macro_cache.get("score_sentiment")) + "/100\n"
                "Reddit: " + str(reddit_sentiment.get("crypto", 50)) + "/100\n"
                "Tendance: " + str(macro_cache.get("tendance_marche")) + "\n"
                + str(macro_cache.get("contexte", ""))
            )

    # --- Analyse et decisions ---
    history   = load_json(HISTORY_FILE, [])
    bot_state = load_json(STATE_FILE, {"positions": {}, "last_run": None, "total_pnl_eur": 0})

    print("\n[ANALYSE] " + str(len(all_prices)) + " actifs...\n")
    results = []
    min_score = params.get("MIN_SCORE_BUY", 70)
    max_score = params.get("MAX_SCORE_SELL", 40)
    sl_pct    = params.get("STOP_LOSS_PCT", 0.07)
    tp_pct    = params.get("TAKE_PROFIT_PCT", 0.18)

    for asset, price_data in all_prices.items():
        price_usd  = price_data["price_usd"]
        price_eur  = price_usd * eur_rate
        change     = price_data["change_24h"]
        name       = price_data.get("name", asset)
        atype      = price_data.get("type", "crypto")
        asset_type = "crypto" if asset in CRYPTO_ASSETS else "other"

        tech        = analyze_technical(asset, price_data, params)
        score_final = compute_final_score(tech, macro_cache, asset, btc_status, onchain_data, params)

        # Signal
        if asset_type == "crypto" and btc_status == "crash":
            signal = "HOLD"
        else:
            if score_final >= min_score and tech["signal_tech"] == "BUY":
                signal = "BUY"
            elif score_final <= max_score and tech["signal_tech"] == "SELL":
                signal = "SELL"
            else:
                signal = "HOLD"
            if signal == "BUY"  and score_final < min_score: signal = "HOLD"
            if signal == "SELL" and score_final > max_score: signal = "HOLD"

        bt = backtest_results.get(asset, {})
        bt_str = (" BT=" + str(bt.get("win_rate", "?")) + "%") if bt else ""
        print("[" + asset + "] " + str(round(price_eur, 2)) + "EUR | RSI=" + str(tech["rsi"]) + " MA200=" + str(round(tech["ma200"] * eur_rate, 2)) + " | Score=" + str(score_final) + " | " + signal + bt_str)

        action_taken = None
        position     = bot_state["positions"].get(asset)

        if position:
            entry_price = position["entry_price_eur"]
            pnl_pct     = (price_eur - entry_price) / entry_price
            if pnl_pct <= -sl_pct:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                del bot_state["positions"][asset]
                action_taken = "STOP_LOSS"
                send_telegram("STOP-LOSS " + asset + " | PnL: " + str(round(pnl_pct*100, 2)) + "% (" + str(round(pnl_eur, 2)) + "EUR)")
            elif pnl_pct >= tp_pct:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                del bot_state["positions"][asset]
                action_taken = "TAKE_PROFIT"
                send_telegram("TAKE-PROFIT " + asset + " | PnL: +" + str(round(pnl_pct*100, 2)) + "% (+" + str(round(pnl_eur, 2)) + "EUR)")

        elif signal == "BUY" and score_final >= min_score and not position:
            if can_open_position(asset, bot_state, asset_type):
                place_order_bitpanda(asset, "BUY", MAX_TRADE_EUR)
                bot_state["positions"][asset] = {
                    "entry_price_eur": price_eur,
                    "amount_eur":      MAX_TRADE_EUR,
                    "entry_date":      datetime.now().isoformat()
                }
                action_taken = "BUY"
                send_telegram(
                    "ACHAT " + asset + " (" + name + ")\n"
                    "Prix: " + str(round(price_eur, 2)) + "EUR | Score: " + str(score_final) + "/100\n"
                    "RSI: " + str(tech["rsi"]) + " | MA200: " + str(round(tech["ma200"]*eur_rate, 2)) + "EUR\n"
                    "Backtest win rate: " + str(bt.get("win_rate", "N/A")) + "%\n"
                    "SL: " + str(round(price_eur*(1-sl_pct), 2)) + " | TP: " + str(round(price_eur*(1+tp_pct), 2))
                )

        elif signal == "SELL" and score_final <= max_score and position:
            place_order_bitpanda(asset, "SELL", position["amount_eur"])
            del bot_state["positions"][asset]
            action_taken = "SELL"

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
            "ma200":           round(tech["ma200"] * eur_rate, 4),
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
            "bt_win_rate":     bt.get("win_rate") if bt else None,
            "bt_avg_pnl":      bt.get("avg_pnl_pct") if bt else None,
            "reddit_score":    reddit_sentiment.get("crypto" if asset in CRYPTO_ASSETS else "stock", 50),
            "onchain_score":   onchain_data.get(asset, {}).get("score_onchain", None),
            "params_version":  params.get("last_optimization", "default"),
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
        "reddit_score":        reddit_sentiment.get("crypto", 50),
        "posts_analyzed":      reddit_sentiment.get("posts_analyzed", 0),
        "news_count":          len(news_headlines),
    }
    bot_state["optimized_params"] = {
        "MIN_SCORE_BUY":     params.get("MIN_SCORE_BUY", 70),
        "MAX_SCORE_SELL":    params.get("MAX_SCORE_SELL", 40),
        "RSI_OVERSOLD":      params.get("RSI_OVERSOLD", 35),
        "STOP_LOSS_PCT":     params.get("STOP_LOSS_PCT", 0.07),
        "TAKE_PROFIT_PCT":   params.get("TAKE_PROFIT_PCT", 0.18),
        "profitable_assets": params.get("profitable_assets", 0),
    }
    bot_state["exposition"]  = {
        "total_positions":   len(bot_state["positions"]),
        "total_investi_eur": sum(p.get("amount_eur", 0) for p in bot_state["positions"].values()),
        "max_positions":     MAX_POSITIONS,
        "max_total_eur":     MAX_TOTAL_EUR,
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
    total_inv = sum(p.get("amount_eur", 0) for p in bot_state["positions"].values())
    print("\n" + "="*60)
    print("  DONE v3.0 - " + str(len(results)) + " actifs | " + str(len(actions)) + " ordres | PnL: " + str(bot_state["total_pnl_eur"]) + "EUR")
    print("  Exposition: " + str(len(bot_state["positions"])) + "/" + str(MAX_POSITIONS) + " | " + str(total_inv) + "/" + str(MAX_TOTAL_EUR) + "EUR")
    print("  BTC: " + btc_status + " (" + str(btc_chg) + "%) | Reddit: " + str(reddit_sentiment.get("crypto", 50)) + "/100 | News: " + str(len(news_headlines)))
    print("  Params optimises: BUY>=" + str(params.get("MIN_SCORE_BUY")) + " SL=" + str(round(params.get("STOP_LOSS_PCT", 0.07)*100, 1)) + "%")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_bot()

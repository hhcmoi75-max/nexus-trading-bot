# HAOUD TRADING IA - Agent IA autonome
# GitHub Actions cron toutes les 15 min
# Sources : CoinGecko (crypto) + Yahoo Finance (actions/ETF) + Claude AI

import requests
import json
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
CLAUDE_KEY   = os.environ.get("CLAUDE_API_KEY", "")
BITPANDA_KEY = os.environ.get("BITPANDA_API_KEY", "")

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
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "SOL":  "solana",
    "BNB":  "binancecoin",
    "XRP":  "ripple",
    "ADA":  "cardano",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "DOT":  "polkadot",
    "MATIC":"matic-network",
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

MIN_SCORE_BUY   = 70
MAX_SCORE_SELL  = 40
STOP_LOSS_PCT   = 0.07
TAKE_PROFIT_PCT = 0.18
MAX_TRADE_EUR   = 50
DRY_RUN         = True

HISTORY_FILE = "docs/trade_history.json"
STATE_FILE   = "docs/bot_state.json"

# --- TAUX EUR/USD ---
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

# --- RSI ---
def compute_rsi(closes, period=5):
    if len(closes) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i-1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

# --- PRIX COINGECKO (crypto) ---
def get_crypto_prices():
    prices = {}
    try:
        ids = ",".join(COINGECKO_IDS.values())
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets"
            "?vs_currency=usd&ids=" + ids +
            "&order=market_cap_desc&per_page=20&page=1&sparkline=false&price_change_percentage=24h",
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
                "rsi":        50,
                "name":       CRYPTO_ASSETS[key]["name"],
                "type":       "crypto",
                "source":     "CoinGecko LIVE"
            }
            print("  [OK] " + key + " = " + str(float(coin["current_price"])) + " USD")
    except Exception as e:
        print("  [ERREUR CoinGecko] " + str(e))
    return prices

# --- PRIX YAHOO FINANCE ---
def get_yahoo_price(ticker, name, asset_type):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker + "?interval=1d&range=10d",
            headers=headers, timeout=10
        )
        data   = r.json()
        result = data["chart"]["result"][0]
        meta   = result["meta"]
        price  = float(meta.get("regularMarketPrice", 0))
        prev   = float(meta.get("chartPreviousClose", meta.get("previousClose", price)))
        change = ((price - prev) / prev * 100) if prev else 0
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [c for c in closes if c is not None]
        rsi = compute_rsi(closes) if len(closes) >= 3 else 50
        print("  [OK] " + ticker + " = " + str(round(price, 2)) + " USD RSI=" + str(rsi))
        return {
            "price_usd":  price,
            "change_24h": round(change, 2),
            "volume_usd": int(meta.get("regularMarketVolume", 0)) * price,
            "high_24h":   float(meta.get("regularMarketDayHigh", price)),
            "low_24h":    float(meta.get("regularMarketDayLow", price)),
            "rsi":        rsi,
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

# --- ANALYSE CLAUDE AI ---
def analyze_with_claude(asset, info):
    type_label = {"crypto": "crypto-monnaie", "stock": "action", "etf": "ETF"}.get(info.get("type",""), "actif")
    try:
        prompt = (
            "Tu es un analyste financier IA expert en trading algorithmique.\n"
            "Analyse cette " + type_label + " : " + info['name'] + " (" + asset + ")\n"
            "- Prix : " + str(round(info['price_usd'], 4)) + " USD\n"
            "- Variation 24h : " + str(info['change_24h']) + "%\n"
            "- High 24h : " + str(round(info.get('high_24h', 0), 4)) + " | Low 24h : " + str(round(info.get('low_24h', 0), 4)) + "\n"
            "- Volume 24h : " + str(int(info.get('volume_usd', 0))) + " USD\n"
            "- RSI : " + str(info.get('rsi', 50)) + "\n"
            "- Date : " + datetime.now().strftime('%d/%m/%Y %H:%M') + " UTC\n\n"
            "Reponds UNIQUEMENT en JSON valide sans markdown :\n"
            '{"score_technique":<0-100>,"score_sentiment":<0-100>,"score_macro":<0-100>,'
            '"score_momentum":<0-100>,"score_volume":<0-100>,"signal":"<BUY|SELL|HOLD>",'
            '"confiance":<0-100>,"tendance":"<HAUSSIERE|BAISSIERE|NEUTRE>",'
            '"support":<nombre>,"resistance":<nombre>,"rsi_analyse":"<surachete|survendu|neutre>",'
            '"raison":"<analyse FR max 3 phrases>","risque_principal":"<risque FR 1 phrase>",'
            '"opportunite":"<opportunite FR 1 phrase>"}'
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
        return json.loads(text)
    except Exception as e:
        print("  [CLAUDE ERREUR] " + asset + ": " + str(e))
        return {
            "score_technique": 50, "score_sentiment": 50,
            "score_macro": 50, "score_momentum": 50, "score_volume": 50,
            "signal": "HOLD", "confiance": 50,
            "tendance": "NEUTRE", "support": 0, "resistance": 0,
            "rsi_analyse": "neutre",
            "raison": "Analyse indisponible.",
            "risque_principal": "Donnees insuffisantes.",
            "opportunite": "Donnees insuffisantes."
        }

# --- SCORE GLOBAL ---
def compute_global_score(analysis):
    weights = {
        "score_technique": 0.25,
        "score_sentiment": 0.20,
        "score_macro":     0.20,
        "score_momentum":  0.20,
        "score_volume":    0.15,
    }
    return round(min(100, max(0, sum(analysis.get(k, 50) * w for k, w in weights.items()))))

# --- ORDRE BITPANDA ---
def place_order_bitpanda(asset, side, amount_eur):
    if DRY_RUN:
        print("  [DRY RUN] " + side + " " + asset + " pour " + str(amount_eur) + "EUR")
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

# --- JSON ---
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

# --- BOT PRINCIPAL ---
def run_bot():
    print("\n" + "="*55)
    print("  HAOUD TRADING IA - " + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + " UTC")
    print("="*55 + "\n")

    eur_rate = get_eur_rate()
    print("[FX] 1 USD = " + str(round(eur_rate, 4)) + " EUR\n")

    print("[CRYPTO] CoinGecko...")
    all_prices = {}
    all_prices.update(get_crypto_prices())

    print("\n[ACTIONS] Yahoo Finance...")
    all_prices.update(get_stock_prices())

    print("\n[ETFs] Yahoo Finance...")
    all_prices.update(get_etf_prices())

    history   = load_json(HISTORY_FILE, [])
    bot_state = load_json(STATE_FILE, {"positions": {}, "last_run": None, "total_pnl_eur": 0})

    print("\n[ANALYSE IA] " + str(len(all_prices)) + " actifs...\n")
    results = []

    for asset, price_data in all_prices.items():
        price_usd = price_data["price_usd"]
        price_eur = price_usd * eur_rate
        change    = price_data["change_24h"]
        name      = price_data.get("name", asset)
        atype     = price_data.get("type", "crypto")

        print("[" + asset + "] " + name + " - " + str(round(price_eur, 4)) + "EUR (" + str(change) + "%)")

        analysis     = analyze_with_claude(asset, price_data)
        global_score = compute_global_score(analysis)
        signal       = analysis.get("signal", "HOLD")

        print("  -> Score: " + str(global_score) + " | " + signal + " | " + analysis.get("tendance", "?"))

        action_taken = None
        position     = bot_state["positions"].get(asset)

        if position:
            entry_price = position["entry_price_eur"]
            pnl_pct     = (price_eur - entry_price) / entry_price
            if pnl_pct <= -STOP_LOSS_PCT:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_pct * position["amount_eur"], 2)
                del bot_state["positions"][asset]
                action_taken = "STOP_LOSS"
            elif pnl_pct >= TAKE_PROFIT_PCT:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_pct * position["amount_eur"], 2)
                del bot_state["positions"][asset]
                action_taken = "TAKE_PROFIT"
        elif signal == "BUY" and global_score >= MIN_SCORE_BUY and not position:
            place_order_bitpanda(asset, "BUY", MAX_TRADE_EUR)
            bot_state["positions"][asset] = {
                "entry_price_eur": price_eur,
                "amount_eur":      MAX_TRADE_EUR,
                "entry_date":      datetime.now().isoformat()
            }
            action_taken = "BUY"
        elif signal == "SELL" and global_score <= MAX_SCORE_SELL and position:
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
            "rsi":             price_data.get("rsi", 50),
            "score":           global_score,
            "score_technique": analysis.get("score_technique", 50),
            "score_sentiment": analysis.get("score_sentiment", 50),
            "score_macro":     analysis.get("score_macro", 50),
            "score_momentum":  analysis.get("score_momentum", 50),
            "score_volume":    analysis.get("score_volume", 50),
            "signal":          signal,
            "confiance":       analysis.get("confiance", 50),
            "tendance":        analysis.get("tendance", "NEUTRE"),
            "support":         round(analysis.get("support", 0) * eur_rate, 4),
            "resistance":      round(analysis.get("resistance", 0) * eur_rate, 4),
            "rsi_analyse":     analysis.get("rsi_analyse", "neutre"),
            "action":          action_taken or "HOLD",
            "raison":          analysis.get("raison", ""),
            "risque":          analysis.get("risque_principal", ""),
            "opportunite":     analysis.get("opportunite", ""),
            "source":          price_data.get("source", ""),
            "dry_run":         DRY_RUN
        }
        history.append(entry)
        results.append(entry)

    history = history[-1000:]
    bot_state["last_run"]    = datetime.now().isoformat()
    bot_state["eur_rate"]    = eur_rate
    bot_state["dry_run"]     = DRY_RUN
    bot_state["last_prices"] = {
        k: {
            "price_eur":  round(v["price_usd"] * eur_rate, 6),
            "price_usd":  round(v["price_usd"], 6),
            "change_24h": round(v["change_24h"], 2),
            "high_24h":   round(v.get("high_24h", 0) * eur_rate, 6),
            "low_24h":    round(v.get("low_24h", 0) * eur_rate, 6),
            "volume_usd": round(v.get("volume_usd", 0), 0),
            "rsi":        v.get("rsi", 50),
            "name":       v.get("name", k),
            "type":       v.get("type", "crypto"),
            "source":     v.get("source", "")
        } for k, v in all_prices.items()
    }

    save_json(HISTORY_FILE, history)
    save_json(STATE_FILE, bot_state)

    actions = [e for e in results if e["action"] != "HOLD"]
    print("\n" + "="*55)
    print("  DONE - " + str(len(results)) + " actifs | " + str(len(actions)) + " ordres | PnL: " + str(bot_state['total_pnl_eur']) + "EUR")
    print("="*55 + "\n")

if __name__ == "__main__":
    run_bot()

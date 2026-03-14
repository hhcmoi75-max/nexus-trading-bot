# HAOUD TRADING IA - Agent IA autonome HYBRIDE
# Algo technique interne (toutes les 15 min) + Claude IA (1x par jour a 8h UTC)
# Sources : CoinGecko (crypto) + Yahoo Finance (actions/ETF)

import requests
import json
import os
import time
import math
from datetime import datetime, timezone

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

# --- REGLES DE TRADING ---
MIN_SCORE_BUY   = 70
MAX_SCORE_SELL  = 40
STOP_LOSS_PCT   = 0.07
TAKE_PROFIT_PCT = 0.18
MAX_TRADE_EUR   = 50
DRY_RUN         = True

# --- HEURE ANALYSE CLAUDE (UTC) ---
CLAUDE_HOUR_UTC = 8   # Claude tourne a 8h00 UTC chaque jour

HISTORY_FILE     = "docs/trade_history.json"
STATE_FILE       = "docs/bot_state.json"
MACRO_CACHE_FILE = "docs/macro_cache.json"

# ============================================================
# PARTIE 1 : RECUPERATION DES PRIX
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
                "name":       CRYPTO_ASSETS[key]["name"],
                "type":       "crypto",
                "source":     "CoinGecko LIVE"
            }
            print("  [OK] " + key + " = " + str(round(float(coin["current_price"]), 4)) + " USD (" + str(round(float(coin.get("price_change_percentage_24h") or 0), 2)) + "%)")
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
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [c for c in closes if c is not None]
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
# PARTIE 2 : ALGORITHME TECHNIQUE INTERNE (gratuit, 15 min)
# ============================================================

def compute_rsi(closes, period=14):
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

def compute_macd(closes):
    if len(closes) < 26:
        return 0, 0
    def ema(data, period):
        k = 2 / (period + 1)
        ema_val = data[0]
        for v in data[1:]:
            ema_val = v * k + ema_val * (1 - k)
        return ema_val
    ema12 = ema(closes[-26:], 12)
    ema26 = ema(closes[-26:], 26)
    macd_line = ema12 - ema26
    signal_line = ema(closes[-9:], 9) if len(closes) >= 9 else macd_line
    return round(macd_line, 4), round(signal_line, 4)

def compute_bollinger(closes, period=20):
    if len(closes) < period:
        return 0, 0, 0
    recent = closes[-period:]
    ma = sum(recent) / period
    std = math.sqrt(sum((x - ma) ** 2 for x in recent) / period)
    upper = ma + 2 * std
    lower = ma - 2 * std
    return round(upper, 4), round(ma, 4), round(lower, 4)

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
    avg_vol = sum(volumes[-10:]) / 10
    last_vol = volumes[-1]
    if avg_vol == 0:
        return 50
    ratio = last_vol / avg_vol
    if ratio > 2.0:
        return 80
    elif ratio > 1.5:
        return 65
    elif ratio > 1.0:
        return 55
    else:
        return 40

def analyze_technical(asset, price_data):
    closes  = price_data.get("closes", [])
    volumes = price_data.get("volumes", [])
    price   = price_data["price_usd"]
    change  = price_data["change_24h"]
    high    = price_data.get("high_24h", price)
    low     = price_data.get("low_24h", price)

    # RSI
    rsi = compute_rsi(closes)
    if rsi < 30:
        score_rsi = 80   # survendu = opportunite achat
    elif rsi < 45:
        score_rsi = 65
    elif rsi < 55:
        score_rsi = 50
    elif rsi < 70:
        score_rsi = 40
    else:
        score_rsi = 20   # surachete = risque

    # MACD
    macd_line, signal_line = compute_macd(closes)
    if macd_line > signal_line and macd_line > 0:
        score_macd = 75  # tendance haussiere forte
    elif macd_line > signal_line:
        score_macd = 62  # croisement haussier
    elif macd_line < signal_line and macd_line < 0:
        score_macd = 25  # tendance baissiere forte
    else:
        score_macd = 38  # croisement baissier

    # Bollinger
    bb_upper, bb_mid, bb_lower = compute_bollinger(closes)
    if bb_upper > bb_lower and (bb_upper - bb_lower) > 0:
        bb_pos = (price - bb_lower) / (bb_upper - bb_lower)
        if bb_pos < 0.2:
            score_bb = 78   # prix pres du bas = achat potentiel
        elif bb_pos < 0.4:
            score_bb = 62
        elif bb_pos < 0.6:
            score_bb = 50
        elif bb_pos < 0.8:
            score_bb = 38
        else:
            score_bb = 22   # prix pres du haut = vente potentielle
    else:
        score_bb = 50

    # Moyennes mobiles
    ma20 = compute_ma(closes, 20)
    ma50 = compute_ma(closes, 50)
    if price > ma20 and price > ma50 and ma20 > ma50:
        score_ma = 75   # prix au-dessus des 2 MA, tendance haussiere
    elif price > ma20 and ma20 > ma50:
        score_ma = 62
    elif price < ma20 and price < ma50:
        score_ma = 30   # prix sous les 2 MA, baissier
    elif price < ma20:
        score_ma = 42
    else:
        score_ma = 50

    # Momentum
    momentum = compute_momentum(closes)
    if momentum > 10:
        score_momentum = 75
    elif momentum > 5:
        score_momentum = 65
    elif momentum > 0:
        score_momentum = 55
    elif momentum > -5:
        score_momentum = 40
    else:
        score_momentum = 25

    # Volume
    score_volume = compute_volume_score(volumes) if volumes else 50

    # Variation 24h
    if change > 5:
        score_chg = 30   # trop fort = risque correction
    elif change > 2:
        score_chg = 60
    elif change > 0:
        score_chg = 55
    elif change > -3:
        score_chg = 45
    elif change > -7:
        score_chg = 35
    else:
        score_chg = 20

    # Score technique global (pondere)
    score_technique = round(
        score_rsi      * 0.25 +
        score_macd     * 0.20 +
        score_bb       * 0.15 +
        score_ma       * 0.20 +
        score_momentum * 0.10 +
        score_volume   * 0.05 +
        score_chg      * 0.05
    )

    # Tendance technique
    if score_technique >= 65:
        tendance = "HAUSSIERE"
    elif score_technique <= 40:
        tendance = "BAISSIERE"
    else:
        tendance = "NEUTRE"

    # Signal technique pur
    if score_technique >= 70:
        signal_tech = "BUY"
    elif score_technique <= 35:
        signal_tech = "SELL"
    else:
        signal_tech = "HOLD"

    # RSI analyse texte
    if rsi > 70:
        rsi_analyse = "surachete"
    elif rsi < 30:
        rsi_analyse = "survendu"
    else:
        rsi_analyse = "neutre"

    return {
        "score_technique": score_technique,
        "score_rsi":       score_rsi,
        "score_macd":      score_macd,
        "score_bollinger": score_bb,
        "score_ma":        score_ma,
        "score_momentum":  score_momentum,
        "score_volume":    score_volume,
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
# PARTIE 3 : CLAUDE IA (1x par jour a 8h UTC)
# ============================================================

def should_run_claude():
    now_utc = datetime.now(timezone.utc)
    current_hour = now_utc.hour

    # Charger le cache macro
    macro = load_json(MACRO_CACHE_FILE, {})
    last_claude = macro.get("last_claude_run", "")

    if not last_claude:
        print("[CLAUDE] Aucune analyse precedente - lancement initial")
        return True

    last_dt = datetime.fromisoformat(last_claude)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)

    hours_since = (now_utc - last_dt).total_seconds() / 3600

    # Lancer Claude si on est autour de 8h UTC ET que ca fait plus de 20h
    if current_hour == CLAUDE_HOUR_UTC and hours_since >= 20:
        print("[CLAUDE] Heure d'analyse quotidienne - lancement")
        return True

    # Ou si ca fait plus de 25h (securite)
    if hours_since >= 25:
        print("[CLAUDE] Plus de 25h sans analyse - lancement force")
        return True

    print("[CLAUDE] Analyse recente (" + str(round(hours_since, 1)) + "h ago) - utilisation du cache")
    return False

def run_claude_macro_analysis(all_prices, eur_rate):
    assets_summary = ""
    for asset, data in list(all_prices.items())[:8]:
        assets_summary += asset + " " + str(round(data["price_usd"] * eur_rate, 2)) + "EUR (" + str(data["change_24h"]) + "%) | "

    try:
        prompt = (
            "Tu es un analyste financier IA expert en trading algorithmique.\n"
            "Date : " + datetime.now().strftime('%d/%m/%Y %H:%M') + " UTC\n\n"
            "Marches surveilles : " + assets_summary + "\n\n"
            "Analyse le contexte macro-economique et le sentiment de marche ACTUEL.\n"
            "Reponds UNIQUEMENT en JSON valide sans markdown :\n"
            "{\n"
            "  \"score_macro\": <0-100>,\n"
            "  \"score_sentiment\": <0-100>,\n"
            "  \"tendance_marche\": \"<HAUSSIER|BAISSIER|NEUTRE>\",\n"
            "  \"contexte\": \"<resume macro en 2 phrases max>\",\n"
            "  \"risque_principal\": \"<risque principal du jour en 1 phrase>\",\n"
            "  \"opportunite_du_jour\": \"<opportunite principale en 1 phrase>\",\n"
            "  \"actifs_favorables\": [\"<ticker1>\", \"<ticker2>\"],\n"
            "  \"actifs_risques\": [\"<ticker1>\", \"<ticker2>\"]\n"
            "}"
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
        print("[CLAUDE] Analyse macro OK - Score macro=" + str(result.get("score_macro")) + " Sentiment=" + str(result.get("score_sentiment")))
        return result
    except Exception as e:
        print("[CLAUDE ERREUR] " + str(e))
        return None

# ============================================================
# PARTIE 4 : SCORE FINAL HYBRIDE
# ============================================================

def compute_final_score(tech_analysis, macro_cache, asset):
    score_tech = tech_analysis["score_technique"]

    # Scores macro depuis le cache Claude
    score_macro     = macro_cache.get("score_macro", 50)
    score_sentiment = macro_cache.get("score_sentiment", 50)

    # Bonus/malus si l'actif est dans les listes Claude
    favorables = macro_cache.get("actifs_favorables", [])
    risques    = macro_cache.get("actifs_risques", [])
    bonus = 5 if asset in favorables else (-5 if asset in risques else 0)

    # Ponderation : 60% technique + 25% macro + 15% sentiment
    score_final = round(
        score_tech      * 0.60 +
        score_macro     * 0.25 +
        score_sentiment * 0.15 +
        bonus
    )

    return min(100, max(0, score_final))

def compute_signal(score_final, tech_analysis):
    signal_tech = tech_analysis["signal_tech"]

    if score_final >= MIN_SCORE_BUY and signal_tech == "BUY":
        return "BUY"
    elif score_final <= MAX_SCORE_SELL and signal_tech == "SELL":
        return "SELL"
    else:
        return "HOLD"

# ============================================================
# PARTIE 5 : UTILITAIRES
# ============================================================

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
# PARTIE 6 : BOT PRINCIPAL
# ============================================================

def run_bot():
    print("\n" + "="*55)
    print("  HAOUD TRADING IA (HYBRIDE) - " + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + " UTC")
    print("="*55 + "\n")

    eur_rate = get_eur_rate()
    print("[FX] 1 USD = " + str(round(eur_rate, 4)) + " EUR\n")

    # --- Recuperation des prix ---
    print("[CRYPTO] CoinGecko...")
    all_prices = {}
    all_prices.update(get_crypto_prices())

    print("\n[ACTIONS] Yahoo Finance...")
    all_prices.update(get_stock_prices())

    print("\n[ETFs] Yahoo Finance...")
    all_prices.update(get_etf_prices())

    # --- Analyse Claude (1x par jour) ---
    macro_cache = load_json(MACRO_CACHE_FILE, {
        "score_macro": 50,
        "score_sentiment": 50,
        "tendance_marche": "NEUTRE",
        "contexte": "Analyse macro non encore disponible.",
        "risque_principal": "Aucun risque identifie.",
        "opportunite_du_jour": "Aucune opportunite identifiee.",
        "actifs_favorables": [],
        "actifs_risques": []
    })

    print("\n[MACRO] Verification analyse Claude...")
    if should_run_claude() and CLAUDE_KEY:
        new_macro = run_claude_macro_analysis(all_prices, eur_rate)
        if new_macro:
            macro_cache.update(new_macro)
            save_json(MACRO_CACHE_FILE, macro_cache)
    else:
        print("[MACRO] Cache : macro=" + str(macro_cache.get("score_macro")) + " sentiment=" + str(macro_cache.get("score_sentiment")))

    # --- Analyse technique + score final ---
    history   = load_json(HISTORY_FILE, [])
    bot_state = load_json(STATE_FILE, {"positions": {}, "last_run": None, "total_pnl_eur": 0})

    print("\n[ANALYSE TECHNIQUE] " + str(len(all_prices)) + " actifs...\n")
    results = []

    for asset, price_data in all_prices.items():
        price_usd = price_data["price_usd"]
        price_eur = price_usd * eur_rate
        change    = price_data["change_24h"]
        name      = price_data.get("name", asset)
        atype     = price_data.get("type", "crypto")

        # Analyse technique interne
        tech = analyze_technical(asset, price_data)

        # Score final hybride
        score_final = compute_final_score(tech, macro_cache, asset)
        signal      = compute_signal(score_final, tech)

        # Securite : forcer HOLD si score contredit signal
        if signal == "BUY"  and score_final < MIN_SCORE_BUY:
            signal = "HOLD"
        if signal == "SELL" and score_final > MAX_SCORE_SELL:
            signal = "HOLD"

        print("[" + asset + "] " + name + " | " + str(round(price_eur, 2)) + "EUR (" + str(change) + "%) | RSI=" + str(tech["rsi"]) + " | Score=" + str(score_final) + " | " + signal)

        # --- Decisions de trading ---
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
                print("  STOP-LOSS (" + str(round(pnl_pct*100, 1)) + "%)")
            elif pnl_pct >= TAKE_PROFIT_PCT:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_pct * position["amount_eur"], 2)
                del bot_state["positions"][asset]
                action_taken = "TAKE_PROFIT"
                print("  TAKE-PROFIT (" + str(round(pnl_pct*100, 1)) + "%)")
        elif signal == "BUY" and score_final >= MIN_SCORE_BUY and not position:
            place_order_bitpanda(asset, "BUY", MAX_TRADE_EUR)
            bot_state["positions"][asset] = {
                "entry_price_eur": price_eur,
                "amount_eur":      MAX_TRADE_EUR,
                "entry_date":      datetime.now().isoformat()
            }
            action_taken = "BUY"
            print("  ACHAT")
        elif signal == "SELL" and score_final <= MAX_SCORE_SELL and position:
            place_order_bitpanda(asset, "SELL", position["amount_eur"])
            del bot_state["positions"][asset]
            action_taken = "SELL"
            print("  VENTE")

        # Enregistrement
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
            "dry_run":         DRY_RUN
        }
        history.append(entry)
        results.append(entry)

    history = history[-1000:]
    bot_state["last_run"]    = datetime.now().isoformat()
    bot_state["eur_rate"]    = eur_rate
    bot_state["dry_run"]     = DRY_RUN
    bot_state["macro"]       = {
        "score_macro":        macro_cache.get("score_macro", 50),
        "score_sentiment":    macro_cache.get("score_sentiment", 50),
        "tendance_marche":    macro_cache.get("tendance_marche", "NEUTRE"),
        "contexte":           macro_cache.get("contexte", ""),
        "risque_principal":   macro_cache.get("risque_principal", ""),
        "opportunite_du_jour":macro_cache.get("opportunite_du_jour", ""),
        "last_claude_run":    macro_cache.get("last_claude_run", "")
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
    print("\n" + "="*55)
    print("  DONE - " + str(len(results)) + " actifs | " + str(len(actions)) + " ordres | PnL: " + str(bot_state["total_pnl_eur"]) + "EUR")
    print("  Prochaine analyse Claude : " + str(CLAUDE_HOUR_UTC) + "h00 UTC")
    print("="*55 + "\n")

if __name__ == "__main__":
    run_bot()

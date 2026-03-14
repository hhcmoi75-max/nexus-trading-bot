# HAOUD TRADING IA - v4.0
# Top 30 crypto + Top 50 S&P500 + CAC40 + DAX + ETFs monde
# Whale Alert (crypto) + SEC EDGAR 13F (stocks)
# Algo technique interne + Claude 1x/jour

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

# TOP 30 CRYPTO par market cap (CoinGecko)
CRYPTO_ASSETS = {
    "BTC":   {"name": "Bitcoin"},
    "ETH":   {"name": "Ethereum"},
    "USDT":  {"name": "Tether"},
    "BNB":   {"name": "BNB"},
    "SOL":   {"name": "Solana"},
    "XRP":   {"name": "XRP"},
    "USDC":  {"name": "USD Coin"},
    "STETH": {"name": "Lido Staked ETH"},
    "ADA":   {"name": "Cardano"},
    "AVAX":  {"name": "Avalanche"},
    "DOGE":  {"name": "Dogecoin"},
    "TRX":   {"name": "TRON"},
    "LINK":  {"name": "Chainlink"},
    "TON":   {"name": "Toncoin"},
    "SHIB":  {"name": "Shiba Inu"},
    "DOT":   {"name": "Polkadot"},
    "BCH":   {"name": "Bitcoin Cash"},
    "NEAR":  {"name": "NEAR Protocol"},
    "LTC":   {"name": "Litecoin"},
    "UNI":   {"name": "Uniswap"},
    "ICP":   {"name": "Internet Computer"},
    "MATIC": {"name": "Polygon"},
    "ETC":   {"name": "Ethereum Classic"},
    "APT":   {"name": "Aptos"},
    "ATOM":  {"name": "Cosmos"},
    "XLM":   {"name": "Stellar"},
    "FIL":   {"name": "Filecoin"},
    "ARB":   {"name": "Arbitrum"},
    "OP":    {"name": "Optimism"},
    "INJ":   {"name": "Injective"},
}

COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether",
    "BNB": "binancecoin", "SOL": "solana", "XRP": "ripple",
    "USDC": "usd-coin", "STETH": "staked-ether", "ADA": "cardano",
    "AVAX": "avalanche-2", "DOGE": "dogecoin", "TRX": "tron",
    "LINK": "chainlink", "TON": "the-open-network", "SHIB": "shiba-inu",
    "DOT": "polkadot", "BCH": "bitcoin-cash", "NEAR": "near",
    "LTC": "litecoin", "UNI": "uniswap", "ICP": "internet-computer",
    "MATIC": "matic-network", "ETC": "ethereum-classic", "APT": "aptos",
    "ATOM": "cosmos", "XLM": "stellar", "FIL": "filecoin",
    "ARB": "arbitrum", "OP": "optimism", "INJ": "injective-protocol",
}

# STABLECOINS a exclure du trading (prix fixe ~1$)
STABLECOINS = {"USDT", "USDC", "STETH"}

# TOP 50 S&P500 (les plus importantes)
STOCK_ASSETS = {
    # Tech
    "AAPL":  {"ticker": "AAPL",  "name": "Apple"},
    "MSFT":  {"ticker": "MSFT",  "name": "Microsoft"},
    "NVDA":  {"ticker": "NVDA",  "name": "NVIDIA"},
    "GOOGL": {"ticker": "GOOGL", "name": "Alphabet"},
    "AMZN":  {"ticker": "AMZN",  "name": "Amazon"},
    "META":  {"ticker": "META",  "name": "Meta"},
    "TSLA":  {"ticker": "TSLA",  "name": "Tesla"},
    "AVGO":  {"ticker": "AVGO",  "name": "Broadcom"},
    "AMD":   {"ticker": "AMD",   "name": "AMD"},
    "INTC":  {"ticker": "INTC",  "name": "Intel"},
    "CRM":   {"ticker": "CRM",   "name": "Salesforce"},
    "ORCL":  {"ticker": "ORCL",  "name": "Oracle"},
    "ADBE":  {"ticker": "ADBE",  "name": "Adobe"},
    "QCOM":  {"ticker": "QCOM",  "name": "Qualcomm"},
    "NOW":   {"ticker": "NOW",   "name": "ServiceNow"},
    # Finance
    "BRK-B": {"ticker": "BRK-B", "name": "Berkshire Hathaway"},
    "JPM":   {"ticker": "JPM",   "name": "JPMorgan Chase"},
    "V":     {"ticker": "V",     "name": "Visa"},
    "MA":    {"ticker": "MA",    "name": "Mastercard"},
    "GS":    {"ticker": "GS",    "name": "Goldman Sachs"},
    "MS":    {"ticker": "MS",    "name": "Morgan Stanley"},
    "BAC":   {"ticker": "BAC",   "name": "Bank of America"},
    # Sante
    "LLY":   {"ticker": "LLY",   "name": "Eli Lilly"},
    "UNH":   {"ticker": "UNH",   "name": "UnitedHealth"},
    "JNJ":   {"ticker": "JNJ",   "name": "Johnson & Johnson"},
    "MRK":   {"ticker": "MRK",   "name": "Merck"},
    "ABBV":  {"ticker": "ABBV",  "name": "AbbVie"},
    # Conso
    "AMGN":  {"ticker": "AMGN",  "name": "Amgen"},
    "PG":    {"ticker": "PG",    "name": "Procter & Gamble"},
    "KO":    {"ticker": "KO",    "name": "Coca-Cola"},
    "PEP":   {"ticker": "PEP",   "name": "PepsiCo"},
    "WMT":   {"ticker": "WMT",   "name": "Walmart"},
    "COST":  {"ticker": "COST",  "name": "Costco"},
    # Energie
    "XOM":   {"ticker": "XOM",   "name": "ExxonMobil"},
    "CVX":   {"ticker": "CVX",   "name": "Chevron"},
    # Divers
    "NFLX":  {"ticker": "NFLX",  "name": "Netflix"},
    "DIS":   {"ticker": "DIS",   "name": "Disney"},
    "UBER":  {"ticker": "UBER",  "name": "Uber"},
    "ABNB":  {"ticker": "ABNB",  "name": "Airbnb"},
    "PYPL":  {"ticker": "PYPL",  "name": "PayPal"},
    "SHOP":  {"ticker": "SHOP",  "name": "Shopify"},
    "COIN":  {"ticker": "COIN",  "name": "Coinbase"},
    "MSTR":  {"ticker": "MSTR",  "name": "MicroStrategy"},
}

# CAC40 + DAX (principales valeurs europeennes)
EUROPE_ASSETS = {
    # CAC40
    "MC.PA":  {"ticker": "MC.PA",  "name": "LVMH"},
    "TTE.PA": {"ticker": "TTE.PA", "name": "TotalEnergies"},
    "SAN.PA": {"ticker": "SAN.PA", "name": "Sanofi"},
    "AIR.PA": {"ticker": "AIR.PA", "name": "Airbus"},
    "BNP.PA": {"ticker": "BNP.PA", "name": "BNP Paribas"},
    "OR.PA":  {"ticker": "OR.PA",  "name": "L'Oreal"},
    "KER.PA": {"ticker": "KER.PA", "name": "Kering"},
    "SU.PA":  {"ticker": "SU.PA",  "name": "Schneider Electric"},
    "RI.PA":  {"ticker": "RI.PA",  "name": "Pernod Ricard"},
    "CAP.PA": {"ticker": "CAP.PA", "name": "Capgemini"},
    "STM.PA": {"ticker": "STM.PA", "name": "STMicroelectronics"},
    "DSY.PA": {"ticker": "DSY.PA", "name": "Dassault Systemes"},
    "ACA.PA": {"ticker": "ACA.PA", "name": "Credit Agricole"},
    "GLE.PA": {"ticker": "GLE.PA", "name": "Societe Generale"},
    "RMS.PA": {"ticker": "RMS.PA", "name": "Hermes"},
    # DAX
    "SAP.DE":  {"ticker": "SAP.DE",  "name": "SAP"},
    "SIE.DE":  {"ticker": "SIE.DE",  "name": "Siemens"},
    "ALV.DE":  {"ticker": "ALV.DE",  "name": "Allianz"},
    "MBG.DE":  {"ticker": "MBG.DE",  "name": "Mercedes-Benz"},
    "BMW.DE":  {"ticker": "BMW.DE",  "name": "BMW"},
    "BAYN.DE": {"ticker": "BAYN.DE", "name": "Bayer"},
    "VOW3.DE": {"ticker": "VOW3.DE", "name": "Volkswagen"},
    "DTE.DE":  {"ticker": "DTE.DE",  "name": "Deutsche Telekom"},
    "DBK.DE":  {"ticker": "DBK.DE",  "name": "Deutsche Bank"},
    "EOAN.DE": {"ticker": "EOAN.DE", "name": "E.ON"},
}

# ETFs MONDE ENTIER
ETF_ASSETS = {
    # US
    "SPY":  {"ticker": "SPY",     "name": "S&P 500 ETF"},
    "QQQ":  {"ticker": "QQQ",     "name": "Nasdaq 100 ETF"},
    "GLD":  {"ticker": "GLD",     "name": "Gold ETF"},
    "VTI":  {"ticker": "VTI",     "name": "Total Market ETF"},
    "ARKK": {"ticker": "ARKK",    "name": "ARK Innovation ETF"},
    "IWM":  {"ticker": "IWM",     "name": "Russell 2000 ETF"},
    "XLK":  {"ticker": "XLK",     "name": "Tech Sector ETF"},
    "XLE":  {"ticker": "XLE",     "name": "Energy Sector ETF"},
    "TLT":  {"ticker": "TLT",     "name": "20yr Treasury ETF"},
    "SLV":  {"ticker": "SLV",     "name": "Silver ETF"},
    # Amundi (Paris)
    "CW8":  {"ticker": "CW8.PA",  "name": "Amundi MSCI World"},
    "SP5":  {"ticker": "SP5.PA",  "name": "Amundi S&P 500"},
    "C40":  {"ticker": "C40.PA",  "name": "Amundi CAC 40"},
    "PANX": {"ticker": "PANX.PA", "name": "Amundi Nasdaq-100"},
    "AEME": {"ticker": "AEME.PA", "name": "Amundi MSCI Emerging"},
    "LCEU": {"ticker": "LCEU.PA", "name": "Amundi MSCI Europe"},
    "PAASI":{"ticker": "PAASI.PA","name": "Amundi MSCI Asia"},
    # iShares
    "EEM":  {"ticker": "EEM",     "name": "iShares Emerging Markets"},
    "EWJ":  {"ticker": "EWJ",     "name": "iShares Japan ETF"},
    "FXI":  {"ticker": "FXI",     "name": "iShares China ETF"},
}

# --- REGLES DE TRADING ---
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
MAX_POSITIONS        = 8
MAX_TOTAL_EUR        = 400
MAX_CRYPTO_POS       = 4
MAX_STOCK_POS        = 4
BTC_CRASH_THRESHOLD  = -5.0
BTC_WARN_THRESHOLD   = -3.0
BTC_PENALTY_PTS      = 15
CLAUDE_HOUR_UTC      = 8

# WHALE - seuils minimum (en USD)
WHALE_CRYPTO_MIN_USD = 1_000_000   # 1M$ minimum
WHALE_STOCK_MIN_USD  = 10_000_000  # 10M$ minimum

HISTORY_FILE      = "docs/trade_history.json"
STATE_FILE        = "docs/bot_state.json"
MACRO_CACHE_FILE  = "docs/macro_cache.json"
BACKTEST_FILE     = "docs/backtest.json"
PARAMS_FILE       = "docs/optimized_params.json"
WHALE_FILE        = "docs/whale_alerts.json"

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
# WHALE TRACKING
# ============================================================

def get_crypto_whale_alerts():
    whales = []
    try:
        # Whale Alert RSS (transactions massives on-chain)
        r = requests.get(
            "https://whale-alert.io/rss",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        root = ET.fromstring(r.content)
        for item in root.findall(".//item")[:20]:
            title = item.findtext("title", "").strip()
            desc  = item.findtext("description", "").strip()
            date  = item.findtext("pubDate", "").strip()
            if not title:
                continue
            # Detecter montant et crypto
            amount_usd = 0
            asset      = "UNKNOWN"
            title_low  = title.lower()
            # Extraire montant
            import re
            amounts = re.findall(r'\$([0-9,]+)', title)
            if amounts:
                try:
                    amount_usd = int(amounts[0].replace(",", ""))
                except:
                    pass
            # Detecter l'actif
            for ticker in COINGECKO_IDS.keys():
                if ticker.lower() in title_low or CRYPTO_ASSETS[ticker]["name"].lower() in title_low:
                    asset = ticker
                    break
            if amount_usd >= WHALE_CRYPTO_MIN_USD:
                # Determiner direction (achat/vente/transfert)
                direction = "TRANSFER"
                if "exchange" in title_low and ("to" in title_low):
                    direction = "SELL"  # vers exchange = vente probable
                elif "exchange" in title_low and ("from" in title_low):
                    direction = "BUY"   # depuis exchange = achat probable
                elif "unknown wallet" in title_low:
                    direction = "TRANSFER"

                whales.append({
                    "type":       "crypto",
                    "asset":      asset,
                    "amount_usd": amount_usd,
                    "direction":  direction,
                    "title":      title,
                    "date":       date,
                    "source":     "Whale Alert"
                })
        print("  [WHALE CRYPTO] " + str(len(whales)) + " transactions detectees")
    except Exception as e:
        print("  [WHALE CRYPTO] Erreur: " + str(e))
        # Fallback : simuler des donnees whale basiques
        whales = get_crypto_whale_fallback()
    return whales

def get_crypto_whale_fallback():
    # Si Whale Alert inaccessible, utiliser CoinGecko pour detecter
    # les mouvements de baleines via variation volume anormale
    whales = []
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets"
            "?vs_currency=usd&order=volume_desc&per_page=10&page=1"
            "&price_change_percentage=1h",
            headers={"Accept": "application/json"}, timeout=10
        )
        data = r.json()
        id_to_ticker = {v: k for k, v in COINGECKO_IDS.items()}
        for coin in data:
            key = id_to_ticker.get(coin["id"])
            if not key or key in STABLECOINS:
                continue
            chg_1h = float(coin.get("price_change_percentage_1h_in_currency") or 0)
            vol    = float(coin.get("total_volume") or 0)
            # Mouvement fort en 1h avec gros volume = potentielle activite whale
            if abs(chg_1h) > 3 and vol > 500_000_000:
                direction = "BUY" if chg_1h > 0 else "SELL"
                whales.append({
                    "type":       "crypto",
                    "asset":      key,
                    "amount_usd": int(vol * 0.1),
                    "direction":  direction,
                    "title":      key + " variation 1h: " + str(round(chg_1h, 2)) + "% avec volume $" + str(int(vol/1e6)) + "M",
                    "date":       datetime.now().isoformat(),
                    "source":     "CoinGecko Volume Alert"
                })
        print("  [WHALE FALLBACK] " + str(len(whales)) + " signaux volume detectes")
    except Exception as e:
        print("  [WHALE FALLBACK] Erreur: " + str(e))
    return whales

def get_stock_whale_alerts():
    whales = []
    try:
        # SEC EDGAR : derniers filings 13F (achats institutionnels)
        # Chercher les Form 4 (insider transactions) recents
        r = requests.get(
            "https://efts.sec.gov/LATEST/search-index?q=%22form+4%22&dateRange=custom"
            "&startdt=" + datetime.now().strftime('%Y-%m-%d') + "&enddt=" + datetime.now().strftime('%Y-%m-%d') +
            "&hits.hits._source=period_of_report,display_names,file_date,form_type",
            headers={"User-Agent": "HAOUD-TradingBot contact@haoud.fr"},
            timeout=10
        )
        # Utiliser l'API EDGAR full-text search plus simple
        r2 = requests.get(
            "https://efts.sec.gov/LATEST/search-index?q=%22acquisition%22+%22common+stock%22"
            "&forms=4&dateRange=custom"
            "&startdt=" + datetime.now().strftime('%Y-%m-%d'),
            headers={"User-Agent": "HAOUD-TradingBot contact@haoud.fr"},
            timeout=10
        )
        filings = r2.json().get("hits", {}).get("hits", [])
        seen = set()
        for f in filings[:10]:
            src = f.get("_source", {})
            names = src.get("display_names", [])
            ticker = None
            for name in names:
                # Tenter de matcher avec nos actifs
                for t, info in STOCK_ASSETS.items():
                    if info["name"].lower() in str(name).lower():
                        ticker = t
                        break
                if ticker:
                    break
            if ticker and ticker not in seen:
                seen.add(ticker)
                whales.append({
                    "type":       "stock",
                    "asset":      ticker,
                    "amount_usd": WHALE_STOCK_MIN_USD,
                    "direction":  "BUY",
                    "title":      "Insider acquisition declaree : " + str(names)[:80],
                    "date":       src.get("file_date", datetime.now().isoformat()),
                    "source":     "SEC EDGAR Form 4"
                })
        print("  [WHALE STOCK] " + str(len(whales)) + " insider transactions detectees")
    except Exception as e:
        print("  [WHALE STOCK] Erreur: " + str(e))
        whales = get_stock_whale_fallback()
    return whales

def get_stock_whale_fallback():
    # Fallback : utiliser Yahoo Finance pour detecter volumes anormaux
    whales = []
    high_volume_assets = ["NVDA", "TSLA", "AAPL", "MSFT", "META", "AMZN", "GOOGL"]
    for ticker in high_volume_assets:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker + "?interval=1d&range=5d",
                headers=headers, timeout=8
            )
            data   = r.json()
            result = data["chart"]["result"][0]
            vols   = result.get("indicators", {}).get("quote", [{}])[0].get("volume", [])
            vols   = [v for v in vols if v is not None]
            if len(vols) >= 3:
                avg_vol  = sum(vols[:-1]) / len(vols[:-1])
                last_vol = vols[-1]
                if avg_vol > 0 and last_vol > avg_vol * 2:
                    price = float(result["meta"].get("regularMarketPrice", 0))
                    amount = int(last_vol * price)
                    if amount >= WHALE_STOCK_MIN_USD:
                        whales.append({
                            "type":       "stock",
                            "asset":      ticker,
                            "amount_usd": amount,
                            "direction":  "BUY",
                            "title":      ticker + " volume x" + str(round(last_vol/avg_vol, 1)) + " la moyenne",
                            "date":       datetime.now().isoformat(),
                            "source":     "Yahoo Volume Alert"
                        })
            time.sleep(0.2)
        except:
            pass
    print("  [WHALE STOCK FALLBACK] " + str(len(whales)) + " volumes anormaux")
    return whales

def process_whale_alerts(crypto_whales, stock_whales, all_prices, eur_rate):
    all_whales = crypto_whales + stock_whales
    # Enrichir avec prix actuel
    for w in all_whales:
        asset = w["asset"]
        if asset in all_prices:
            w["current_price_eur"] = round(all_prices[asset]["price_usd"] * eur_rate, 2)
            w["change_24h"]        = all_prices[asset]["change_24h"]
        else:
            w["current_price_eur"] = None
            w["change_24h"]        = None
        w["validated"]    = False
        w["alert_id"]     = asset + "_" + str(int(time.time()))
        w["amount_eur"]   = round(w["amount_usd"] * eur_rate / 1e6, 1)  # en millions EUR

    # Garder uniquement les BUY significatifs pour alertes
    buy_alerts = [w for w in all_whales if w["direction"] == "BUY"]
    if buy_alerts:
        msg = "WHALES DETECTEES - HAOUD TRADING IA\n"
        for w in buy_alerts[:5]:
            msg += w["asset"] + " | " + w["direction"] + " | $" + str(int(w["amount_usd"]/1e6)) + "M | " + w["source"] + "\n"
        msg += "Voir dashboard pour validation"
        send_telegram(msg)

    return all_whales

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
        # Recuperer top 30 en une seule requete
        ids = ",".join(COINGECKO_IDS.values())
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets"
            "?vs_currency=usd&ids=" + ids +
            "&order=market_cap_desc&per_page=50&page=1"
            "&sparkline=false&price_change_percentage=24h",
            headers={"Accept": "application/json"}, timeout=20
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
        print("  [OK] " + str(len(prices)) + " cryptos recuperees")
    except Exception as e:
        print("  [ERREUR CoinGecko] " + str(e))
    return prices

def get_yahoo_price_single(ticker, name, asset_type):
    """Recupere 1 an d historique pour un seul actif (pour le calcul technique)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker + "?interval=1d&range=1y",
            headers=headers, timeout=10
        )
        data    = r.json()
        result  = data["chart"]["result"][0]
        meta    = result["meta"]
        closes  = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes  = [c for c in closes if c is not None]
        volumes = result.get("indicators", {}).get("quote", [{}])[0].get("volume", [])
        volumes = [v for v in volumes if v is not None]
        return closes, volumes
    except:
        return [], []

def get_yahoo_batch_quotes(tickers_map, asset_type):
    """
    Recupere les prix en temps reel pour TOUS les tickers en 1 seule requete.
    tickers_map = {key: {"ticker": t, "name": n}}
    """
    prices = {}
    # Yahoo Finance v7 supporte les requetes batch
    all_tickers = [info["ticker"] for info in tickers_map.values()]
    # Splitter en chunks de 20 pour eviter les timeouts
    chunk_size = 20
    chunks = [all_tickers[i:i+chunk_size] for i in range(0, len(all_tickers), chunk_size)]
    ticker_to_key = {info["ticker"]: key for key, info in tickers_map.items()}

    for chunk in chunks:
        try:
            symbols = ",".join(chunk)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(
                "https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + symbols,
                headers=headers, timeout=15
            )
            data = r.json()
            quotes = data.get("quoteResponse", {}).get("result", [])
            for q in quotes:
                ticker = q.get("symbol", "")
                key    = ticker_to_key.get(ticker)
                if not key:
                    continue
                price  = float(q.get("regularMarketPrice", 0))
                prev   = float(q.get("regularMarketPreviousClose", price))
                change = ((price - prev) / prev * 100) if prev else 0
                prices[key] = {
                    "price_usd":  price,
                    "change_24h": round(change, 2),
                    "volume_usd": float(q.get("regularMarketVolume", 0)) * price,
                    "high_24h":   float(q.get("regularMarketDayHigh", price)),
                    "low_24h":    float(q.get("regularMarketDayLow", price)),
                    "closes":     [],
                    "volumes":    [],
                    "name":       tickers_map[key]["name"],
                    "type":       asset_type,
                    "source":     "Yahoo Finance LIVE"
                }
            print("  [BATCH] " + str(len(quotes)) + "/" + str(len(chunk)) + " quotes OK")
            time.sleep(0.3)
        except Exception as e:
            print("  [BATCH ERREUR] " + str(e))
            time.sleep(1)

    # Recuperer historique 1 an en parallele (uniquement pour les actifs obtenus)
    print("  [HISTORIQUE] Recuperation 1 an pour " + str(len(prices)) + " actifs...")
    for key, data in prices.items():
        ticker = tickers_map[key]["ticker"]
        closes, volumes = get_yahoo_price_single(ticker, data["name"], asset_type)
        if closes:
            data["closes"]  = closes
            data["volumes"] = volumes
        time.sleep(0.1)

    return prices

def get_all_stock_prices():
    prices = {}
    print("  Actions US (" + str(len(STOCK_ASSETS)) + " actifs en batch)...")
    us = get_yahoo_batch_quotes(STOCK_ASSETS, "stock")
    prices.update(us)
    print("  Actions Europe (" + str(len(EUROPE_ASSETS)) + " actifs en batch)...")
    eu = get_yahoo_batch_quotes(EUROPE_ASSETS, "stock_eu")
    prices.update(eu)
    print("  [STOCKS] " + str(len(prices)) + " actifs recuperes")
    return prices

def get_all_etf_prices():
    print("  ETFs (" + str(len(ETF_ASSETS)) + " actifs en batch)...")
    prices = get_yahoo_batch_quotes(ETF_ASSETS, "etf")
    print("  [ETFs] " + str(len(prices)) + " actifs recuperes")
    return prices

# ============================================================
# ON-CHAIN DATA
# ============================================================

def get_onchain_data():
    onchain = {}
    try:
        r = requests.get("https://blockchain.info/stats?format=json", timeout=8)
        d = r.json()
        tx = d.get("n_tx", 0)
        if tx > 400000:   s = 75
        elif tx > 300000: s = 60
        elif tx > 200000: s = 50
        else:             s = 35
        onchain["BTC"] = {"tx_per_day": tx, "score_onchain": s}
        print("  [ON-CHAIN] BTC tx=" + str(tx) + " score=" + str(s))
    except Exception as e:
        print("  [ON-CHAIN] BTC: " + str(e))
    try:
        r = requests.get(
            "https://api.etherscan.io/api?module=gastracker&action=gasoracle",
            timeout=8
        )
        gas = float(r.json().get("result", {}).get("SafeGasPrice", 20))
        s = 70 if gas < 15 else (60 if gas < 30 else (45 if gas < 60 else 30))
        onchain["ETH"] = {"gas_price_gwei": gas, "score_onchain": s}
        print("  [ON-CHAIN] ETH gas=" + str(gas) + " score=" + str(s))
    except Exception as e:
        print("  [ON-CHAIN] ETH: " + str(e))
    return onchain

# ============================================================
# ALGORITHME TECHNIQUE
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
    r = volumes[-1] / avg
    if r > 2.0:   return 80
    elif r > 1.5: return 65
    elif r > 1.0: return 55
    else:         return 40

def analyze_technical(asset, price_data, params):
    closes  = price_data.get("closes", [])
    volumes = price_data.get("volumes", [])
    price   = price_data["price_usd"]
    change  = price_data["change_24h"]
    rsi_os  = params.get("RSI_OVERSOLD", 35)
    rsi_ob  = params.get("RSI_OVERBOUGHT", 65)

    rsi = compute_rsi(closes)
    score_rsi = 82 if rsi < rsi_os else (66 if rsi < rsi_os+10 else (50 if rsi < 55 else (40 if rsi < rsi_ob else 18)))

    ml, sl = compute_macd(closes)
    score_macd = 78 if (ml > sl and ml > 0) else (62 if ml > sl else (22 if (ml < sl and ml < 0) else 38))

    bbu, bbm, bbl = compute_bollinger(closes)
    if bbu > bbl and (bbu - bbl) > 0:
        pos = (price - bbl) / (bbu - bbl)
        score_bb = 82 if pos < 0.15 else (65 if pos < 0.35 else (50 if pos < 0.65 else (35 if pos < 0.85 else 18)))
    else:
        score_bb = 50

    ma20  = compute_ma(closes, 20)
    ma50  = compute_ma(closes, 50)
    ma200 = compute_ma(closes, 200)
    if price > ma20 and price > ma50 and price > ma200 and ma20 > ma50:    score_ma = 82
    elif price > ma20 and price > ma50 and ma20 > ma50:                    score_ma = 68
    elif price > ma20:                                                      score_ma = 55
    elif price < ma20 and price < ma50 and price < ma200:                  score_ma = 18
    elif price < ma20 and price < ma50:                                    score_ma = 32
    else:                                                                   score_ma = 45

    mom = compute_momentum(closes)
    score_mom = 75 if mom > 15 else (65 if mom > 7 else (55 if mom > 2 else (42 if mom > -5 else (30 if mom > -12 else 18))))
    score_vol = compute_volume_score(volumes) if volumes else 50
    score_chg = 28 if change > 5 else (58 if change > 2 else (54 if change > 0 else (44 if change > -3 else (32 if change > -7 else 18))))

    score_tech = round(
        score_rsi  * 0.22 + score_macd * 0.20 + score_bb  * 0.15 +
        score_ma   * 0.22 + score_mom  * 0.10 + score_vol * 0.06 + score_chg * 0.05
    )

    tendance    = "HAUSSIERE" if score_tech >= 65 else ("BAISSIERE" if score_tech <= 40 else "NEUTRE")
    signal_tech = "BUY" if score_tech >= params.get("MIN_SCORE_BUY", 70) else ("SELL" if score_tech <= params.get("MAX_SCORE_SELL", 40) else "HOLD")
    rsi_analyse = "surachete" if rsi > rsi_ob else ("survendu" if rsi < rsi_os else "neutre")

    return {
        "score_technique": score_tech, "rsi": rsi, "macd": ml,
        "macd_signal": sl, "bb_upper": bbu, "bb_mid": bbm, "bb_lower": bbl,
        "ma20": ma20, "ma50": ma50, "ma200": ma200, "momentum": mom,
        "score_rsi": score_rsi, "score_macd": score_macd,
        "score_bollinger": score_bb, "score_ma": score_ma,
        "score_momentum": score_mom, "score_volume": score_vol,
        "tendance": tendance, "signal_tech": signal_tech, "rsi_analyse": rsi_analyse,
    }

# ============================================================
# BACKTESTING + OPTIMISATION
# ============================================================

def run_backtest(asset, closes, params):
    if len(closes) < 60:
        return None
    trades = []
    position = False
    entry = 0
    wins = losses = 0
    total_pnl = 0
    sl = params.get("STOP_LOSS_PCT", 0.07)
    tp = params.get("TAKE_PROFIT_PCT", 0.18)
    rsi_os = params.get("RSI_OVERSOLD", 35)
    rsi_ob = params.get("RSI_OVERBOUGHT", 65)

    for i in range(50, len(closes) - 1):
        w = closes[:i+1]
        rsi = compute_rsi(w)
        ma20 = compute_ma(w, 20)
        ml, ms = compute_macd(w)
        price = closes[i]
        buy_sig  = (rsi < rsi_os and price > ma20 and ml > ms)
        sell_sig = (rsi > rsi_ob or (position and price < entry*(1-sl)) or (position and price > entry*(1+tp)))
        if not position and buy_sig:
            entry = price
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
    return {
        "asset": asset, "total_trades": total, "wins": wins, "losses": losses,
        "win_rate": round(wins / total * 100, 1),
        "avg_pnl_pct": round(total_pnl / total, 2),
        "total_pnl_pct": round(total_pnl, 2),
        "best_trade": round(max(trades), 2) if trades else 0,
        "worst_trade": round(min(trades), 2) if trades else 0,
        "periode": str(len(closes)) + " jours"
    }

def optimize_params(backtest_results):
    if not backtest_results:
        return DEFAULT_PARAMS.copy()
    good = [bt for bt in backtest_results.values() if bt and bt["win_rate"] >= 55 and bt["total_trades"] >= 5]
    bad  = [bt for bt in backtest_results.values() if bt and bt["win_rate"] < 45 and bt["total_trades"] >= 5]
    params = DEFAULT_PARAMS.copy()
    if good:
        avg_wr = sum(bt["win_rate"] for bt in good) / len(good)
        if avg_wr >= 60:   params["MIN_SCORE_BUY"] = 68
        elif avg_wr >= 55: params["MIN_SCORE_BUY"] = 70
        else:              params["MIN_SCORE_BUY"] = 72
        print("  [OPTIM] " + str(len(good)) + " actifs rentables | Seuil BUY=" + str(params["MIN_SCORE_BUY"]))
    if bad:
        avg_worst = sum(bt["worst_trade"] for bt in bad) / len(bad)
        if avg_worst < -10:
            params["STOP_LOSS_PCT"] = 0.06
            print("  [OPTIM] Stop-loss resserre a 6%")
    params["last_optimization"] = datetime.now().isoformat()
    params["assets_analyzed"]   = len(backtest_results)
    params["profitable_assets"] = len(good)
    return params

# ============================================================
# CORRELATION BTC
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
        print("  [CORRELATION] BTC warn (" + str(chg) + "%) -> penalite -" + str(BTC_PENALTY_PTS) + "pts")
        return "warn", chg
    return "ok", chg

# ============================================================
# REDDIT + RSS
# ============================================================

BULLISH = ["bull","moon","pump","buy","long","surge","rally","breakout","ath","gain","up","bullish","rocket","hodl"]
BEARISH = ["bear","dump","sell","short","crash","drop","down","bearish","fear","panic","correction","loss","red","rekt"]

def get_reddit_sentiment():
    total_bull = total_bear = total_posts = 0
    mentions = {}
    subs = ["CryptoCurrency", "wallstreetbets", "investing", "stocks", "Bitcoin"]
    for sub in subs:
        try:
            r = requests.get(
                "https://www.reddit.com/r/" + sub + "/hot.json?limit=25",
                headers={"User-Agent": "HAOUD-Bot/4.0"}, timeout=10
            )
            posts = r.json().get("data", {}).get("children", [])
            for post in posts:
                d    = post.get("data", {})
                text = (d.get("title","") + " " + d.get("selftext","")).lower()
                w    = min(d.get("score", 0) / 1000, 3) + 1
                total_bull  += sum(text.count(x) for x in BULLISH) * w
                total_bear  += sum(text.count(x) for x in BEARISH) * w
                total_posts += 1
                all_assets = list(CRYPTO_ASSETS.keys()) + list(STOCK_ASSETS.keys()) + list(EUROPE_ASSETS.keys())
                for asset in all_assets:
                    if asset.lower() in text:
                        mentions[asset] = mentions.get(asset, 0) + 1
            time.sleep(0.5)
        except:
            pass
    score = round(total_bull / (total_bull + total_bear) * 100) if (total_bull + total_bear) > 0 else 50
    print("  [REDDIT] " + str(total_posts) + " posts | Score=" + str(score))
    return {"crypto": score, "stock": score, "posts_analyzed": total_posts,
            "top_mentions": dict(sorted(mentions.items(), key=lambda x: x[1], reverse=True)[:10])}

def fetch_rss_news():
    headlines = []
    feeds = [
        ("https://feeds.reuters.com/reuters/businessNews",   "Reuters"),
        ("https://coindesk.com/arc/outboundfeeds/rss/",      "CoinDesk"),
        ("https://cointelegraph.com/rss",                    "CoinTelegraph"),
        ("https://feeds.reuters.com/reuters/technologyNews", "Reuters Tech"),
    ]
    for url, source in feeds:
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:5]:
                t = item.findtext("title", "").strip()
                if t:
                    headlines.append(source + ": " + t)
        except:
            pass
    print("  [RSS] " + str(len(headlines)) + " actualites")
    return headlines[:20]

# ============================================================
# CLAUDE IA (1x PAR JOUR)
# ============================================================

def should_run_claude():
    now = datetime.now(timezone.utc)
    m   = load_json(MACRO_CACHE_FILE, {})
    last = m.get("last_claude_run", "")
    if not last:
        return True
    ld = datetime.fromisoformat(last)
    if ld.tzinfo is None:
        ld = ld.replace(tzinfo=timezone.utc)
    hours = (now - ld).total_seconds() / 3600
    if now.hour == CLAUDE_HOUR_UTC and hours >= 20:
        return True
    if hours >= 25:
        return True
    print("[CLAUDE] Cache valide (" + str(round(hours,1)) + "h) macro=" + str(m.get("score_macro",50)))
    return False

def run_claude_macro_analysis(all_prices, eur_rate, news, reddit, backtest_results, whale_alerts):
    summary = ""
    for asset, d in list(all_prices.items())[:10]:
        summary += asset + " " + str(round(d["price_usd"]*eur_rate,2)) + "EUR (" + str(d["change_24h"]) + "%) | "

    news_text = "\n\nActualites:\n" + "\n".join(["- " + h for h in news[:8]]) if news else ""
    reddit_text = "\n\nReddit sentiment: " + str(reddit.get("crypto",50)) + "/100 (" + str(reddit.get("posts_analyzed",0)) + " posts)" if reddit else ""

    bt_text = ""
    if backtest_results:
        good = [(a, bt["win_rate"]) for a,bt in backtest_results.items() if bt and bt["win_rate"]>=55][:3]
        bad  = [(a, bt["win_rate"]) for a,bt in backtest_results.items() if bt and bt["win_rate"]<45][:3]
        if good: bt_text += "\nActifs rentables backtest: " + str(good)
        if bad:  bt_text += "\nActifs non rentables: " + str(bad)

    whale_text = ""
    buy_whales = [w for w in whale_alerts if w["direction"] == "BUY"][:3]
    if buy_whales:
        whale_text = "\n\nWhales BUY detectees: " + ", ".join([w["asset"] + " $" + str(int(w["amount_usd"]/1e6)) + "M" for w in buy_whales])

    try:
        prompt = (
            "Tu es un analyste financier IA expert en trading algorithmique.\n"
            "Date: " + datetime.now().strftime('%d/%m/%Y %H:%M') + " UTC\n"
            "Marches: " + summary +
            news_text + reddit_text + bt_text + whale_text + "\n\n"
            "Analyse le contexte macro et le sentiment global.\n"
            "Reponds UNIQUEMENT en JSON valide sans markdown:\n"
            '{"score_macro":<0-100>,"score_sentiment":<0-100>,'
            '"tendance_marche":"<HAUSSIER|BAISSIER|NEUTRE>",'
            '"contexte":"<2 phrases>",'
            '"risque_principal":"<1 phrase>",'
            '"opportunite_du_jour":"<1 phrase>",'
            '"actifs_favorables":["<t1>","<t2>","<t3>"],'
            '"actifs_risques":["<t1>","<t2>"]}'
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 600, "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        text = r.json()["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
        result = json.loads(text)
        result["last_claude_run"] = datetime.now(timezone.utc).isoformat()
        result["news_count"]      = len(news)
        result["reddit_score"]    = reddit.get("crypto", 50)
        print("[CLAUDE] OK macro=" + str(result.get("score_macro")) + " sentiment=" + str(result.get("score_sentiment")))
        return result
    except Exception as e:
        print("[CLAUDE ERREUR] " + str(e))
        return None

# ============================================================
# SCORE FINAL + GESTION EXPOSITION + ORDRE
# ============================================================

def compute_final_score(tech, macro_cache, asset, btc_status, onchain_data, params):
    st  = tech["score_technique"]
    sm  = macro_cache.get("score_macro", 50)
    ss  = macro_cache.get("score_sentiment", 50)
    fav = macro_cache.get("actifs_favorables", [])
    ris = macro_cache.get("actifs_risques", [])
    bonus = 5 if asset in fav else (-5 if asset in ris else 0)
    oc_bonus = 0
    if asset in onchain_data:
        oc_bonus = round((onchain_data[asset].get("score_onchain", 50) - 50) * 0.1)
    score = round(st * 0.55 + sm * 0.20 + ss * 0.15 + (50 + oc_bonus) * 0.10 + bonus)
    if asset in CRYPTO_ASSETS and btc_status == "warn":
        score = max(0, score - BTC_PENALTY_PTS)
    return min(100, max(0, score))

def can_open_position(asset, bot_state, asset_type):
    pos  = bot_state.get("positions", {})
    t    = len(pos)
    inv  = sum(p.get("amount_eur", 0) for p in pos.values())
    crp  = sum(1 for k in pos if k in CRYPTO_ASSETS)
    stk  = sum(1 for k in pos if k not in CRYPTO_ASSETS)
    if t >= MAX_POSITIONS:
        print("  [EXPOSITION] Max " + str(MAX_POSITIONS) + " atteint")
        return False
    if inv + MAX_TRADE_EUR > MAX_TOTAL_EUR:
        print("  [EXPOSITION] Budget " + str(MAX_TOTAL_EUR) + "EUR atteint")
        return False
    if asset_type == "crypto" and crp >= MAX_CRYPTO_POS:
        print("  [EXPOSITION] Max crypto " + str(MAX_CRYPTO_POS) + " atteint")
        return False
    if asset_type != "crypto" and stk >= MAX_STOCK_POS:
        print("  [EXPOSITION] Max stock " + str(MAX_STOCK_POS) + " atteint")
        return False
    return True

def place_order_bitpanda(asset, side, amount_eur):
    if DRY_RUN:
        print("  [DRY RUN] " + side + " " + asset + " " + str(amount_eur) + "EUR")
        return {"status": "simulated"}
    try:
        r = requests.get("https://api.exchange.bitpanda.com/public/v1/instruments", timeout=10)
        iid = None
        for inst in r.json():
            if inst.get("base", {}).get("code") == asset and inst.get("quote", {}).get("code") == "EUR":
                iid = inst["instrument_code"]
                break
        if not iid:
            return None
        r = requests.post(
            "https://api.exchange.bitpanda.com/public/v1/account/orders",
            headers={"Authorization": "Bearer " + BITPANDA_KEY, "Content-Type": "application/json"},
            json={"instrument_code": iid, "type": "MARKET", "side": side, "amount": str(amount_eur)},
            timeout=15
        )
        return r.json()
    except Exception as e:
        print("  [BITPANDA] " + str(e))
        return None

# ============================================================
# BOT PRINCIPAL
# ============================================================

def run_bot():
    print("\n" + "="*65)
    print("  HAOUD TRADING IA v4.0 - " + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + " UTC")
    print("  " + str(len(CRYPTO_ASSETS)) + " crypto | " + str(len(STOCK_ASSETS)) + " US | " + str(len(EUROPE_ASSETS)) + " EU | " + str(len(ETF_ASSETS)) + " ETF")
    print("="*65 + "\n")

    eur_rate = get_eur_rate()
    print("[FX] 1 USD = " + str(round(eur_rate, 4)) + " EUR\n")

    # Prix
    print("[CRYPTO] Top 30 CoinGecko...")
    all_prices = {}
    all_prices.update(get_crypto_prices())
    print("\n[ACTIONS] Yahoo Finance (US + Europe)...")
    all_prices.update(get_all_stock_prices())
    print("\n[ETFs] Yahoo Finance...")
    all_prices.update(get_all_etf_prices())

    # On-chain
    print("\n[ON-CHAIN] Blockchain.info + Etherscan...")
    onchain_data = get_onchain_data()

    # Whales
    print("\n[WHALES] Crypto + Stocks...")
    crypto_whales = get_crypto_whale_alerts()
    stock_whales  = get_stock_whale_alerts()
    whale_alerts  = process_whale_alerts(crypto_whales, stock_whales, all_prices, eur_rate)
    # Garder 50 alertes max, triees par montant
    whale_alerts.sort(key=lambda x: x["amount_usd"], reverse=True)
    existing_whales = load_json(WHALE_FILE, {"alerts": [], "last_update": ""})
    save_json(WHALE_FILE, {
        "last_update": datetime.now().isoformat(),
        "alerts":      whale_alerts[:50]
    })
    print("  [WHALES] " + str(len(whale_alerts)) + " alertes sauvegardees")

    # Reddit + RSS
    print("\n[REDDIT] Sentiment...")
    reddit = get_reddit_sentiment()
    print("\n[RSS] Actualites...")
    news = fetch_rss_news()

    # BTC correlation
    btc_status, btc_chg = get_btc_status(all_prices)
    if btc_status == "crash":
        send_telegram("ALERTE BTC crash " + str(btc_chg) + "% - achats crypto bloques")

    # Backtest
    print("\n[BACKTEST] " + str(len(all_prices)) + " actifs...")
    current_params  = load_json(PARAMS_FILE, DEFAULT_PARAMS.copy())
    backtest_results = {}
    for asset, pd in all_prices.items():
        if asset in STABLECOINS:
            continue
        closes = pd.get("closes", [])
        if len(closes) >= 60:
            bt = run_backtest(asset, closes, current_params)
            if bt:
                backtest_results[asset] = bt
    print("  [BACKTEST] " + str(len(backtest_results)) + " actifs analyses")
    save_json(BACKTEST_FILE, {"last_update": datetime.now().isoformat(), "results": backtest_results})

    # Optimisation
    print("\n[OPTIM] Parametres...")
    optimized = optimize_params(backtest_results)
    save_json(PARAMS_FILE, optimized)
    params = optimized

    # Claude macro
    macro_cache = load_json(MACRO_CACHE_FILE, {
        "score_macro": 50, "score_sentiment": 50, "tendance_marche": "NEUTRE",
        "contexte": "Analyse non disponible.", "risque_principal": "Aucun.",
        "opportunite_du_jour": "Aucune.", "actifs_favorables": [], "actifs_risques": []
    })
    print("\n[MACRO] Claude...")
    if should_run_claude() and CLAUDE_KEY:
        new_macro = run_claude_macro_analysis(all_prices, eur_rate, news, reddit, backtest_results, whale_alerts)
        if new_macro:
            macro_cache.update(new_macro)
            save_json(MACRO_CACHE_FILE, macro_cache)

    # Analyse et decisions
    history   = load_json(HISTORY_FILE, [])
    bot_state = load_json(STATE_FILE, {"positions": {}, "last_run": None, "total_pnl_eur": 0})
    min_score = params.get("MIN_SCORE_BUY", 70)
    max_score = params.get("MAX_SCORE_SELL", 40)
    sl_pct    = params.get("STOP_LOSS_PCT", 0.07)
    tp_pct    = params.get("TAKE_PROFIT_PCT", 0.18)

    print("\n[ANALYSE] " + str(len(all_prices)) + " actifs...\n")
    results = []

    for asset, price_data in all_prices.items():
        if asset in STABLECOINS:
            continue

        price_usd  = price_data["price_usd"]
        price_eur  = price_usd * eur_rate
        change     = price_data["change_24h"]
        name       = price_data.get("name", asset)
        atype      = price_data.get("type", "crypto")
        asset_type = "crypto" if asset in CRYPTO_ASSETS else "other"

        tech        = analyze_technical(asset, price_data, params)
        score_final = compute_final_score(tech, macro_cache, asset, btc_status, onchain_data, params)

        if asset_type == "crypto" and btc_status == "crash":
            signal = "HOLD"
        else:
            if score_final >= min_score and tech["signal_tech"] == "BUY":   signal = "BUY"
            elif score_final <= max_score and tech["signal_tech"] == "SELL": signal = "SELL"
            else:                                                             signal = "HOLD"
            if signal == "BUY"  and score_final < min_score: signal = "HOLD"
            if signal == "SELL" and score_final > max_score: signal = "HOLD"

        bt = backtest_results.get(asset, {})

        action_taken = None
        position     = bot_state["positions"].get(asset)

        if position:
            ep      = position["entry_price_eur"]
            pnl_pct = (price_eur - ep) / ep
            if pnl_pct <= -sl_pct:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                del bot_state["positions"][asset]
                action_taken = "STOP_LOSS"
                send_telegram("STOP-LOSS " + asset + " PnL: " + str(round(pnl_pct*100,2)) + "% (" + str(round(pnl_eur,2)) + "EUR)")
            elif pnl_pct >= tp_pct:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                del bot_state["positions"][asset]
                action_taken = "TAKE_PROFIT"
                send_telegram("TAKE-PROFIT " + asset + " PnL: +" + str(round(pnl_pct*100,2)) + "% (+" + str(round(pnl_eur,2)) + "EUR)")
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
                    "Prix: " + str(round(price_eur,2)) + "EUR | Score: " + str(score_final) + "/100\n"
                    "RSI: " + str(tech["rsi"]) + " | BT win: " + str(bt.get("win_rate","N/A")) + "%\n"
                    "SL: " + str(round(price_eur*(1-sl_pct),2)) + " TP: " + str(round(price_eur*(1+tp_pct),2))
                )
        elif signal == "SELL" and score_final <= max_score and position:
            place_order_bitpanda(asset, "SELL", position["amount_eur"])
            del bot_state["positions"][asset]
            action_taken = "SELL"

        entry = {
            "timestamp":       datetime.now().isoformat(),
            "asset":           asset, "name": name, "type": atype,
            "price_eur":       round(price_eur, 6),
            "price_usd":       round(price_usd, 6),
            "change_24h":      round(change, 2),
            "high_24h":        round(price_data.get("high_24h", 0) * eur_rate, 6),
            "low_24h":         round(price_data.get("low_24h", 0) * eur_rate, 6),
            "volume_usd":      round(price_data.get("volume_usd", 0), 0),
            "rsi":             tech["rsi"], "macd": tech["macd"],
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
            "signal":          signal, "confiance": score_final,
            "tendance":        tech["tendance"], "rsi_analyse": tech["rsi_analyse"],
            "action":          action_taken or "HOLD",
            "raison":          macro_cache.get("contexte", ""),
            "risque":          macro_cache.get("risque_principal", ""),
            "opportunite":     macro_cache.get("opportunite_du_jour", ""),
            "source":          price_data.get("source", ""),
            "bt_win_rate":     bt.get("win_rate") if bt else None,
            "bt_avg_pnl":      bt.get("avg_pnl_pct") if bt else None,
            "reddit_score":    reddit.get("crypto" if asset in CRYPTO_ASSETS else "stock", 50),
            "onchain_score":   onchain_data.get(asset, {}).get("score_onchain"),
            "dry_run":         DRY_RUN
        }
        history.append(entry)
        results.append(entry)
        print("[" + asset + "] " + str(round(price_eur,2)) + "EUR | RSI=" + str(tech["rsi"]) + " | Score=" + str(score_final) + " | " + signal + (" BT=" + str(bt.get("win_rate","?")) + "%" if bt else ""))

    history = history[-2000:]
    actions = [e for e in results if e["action"] != "HOLD"]
    total_inv = sum(p.get("amount_eur", 0) for p in bot_state["positions"].values())

    bot_state["last_run"]         = datetime.now().isoformat()
    bot_state["eur_rate"]         = eur_rate
    bot_state["dry_run"]          = DRY_RUN
    bot_state["btc_status"]       = btc_status
    bot_state["btc_change"]       = btc_chg
    bot_state["total_assets"]     = len(results)
    bot_state["macro"]            = {
        "score_macro":         macro_cache.get("score_macro", 50),
        "score_sentiment":     macro_cache.get("score_sentiment", 50),
        "tendance_marche":     macro_cache.get("tendance_marche", "NEUTRE"),
        "contexte":            macro_cache.get("contexte", ""),
        "risque_principal":    macro_cache.get("risque_principal", ""),
        "opportunite_du_jour": macro_cache.get("opportunite_du_jour", ""),
        "last_claude_run":     macro_cache.get("last_claude_run", ""),
        "reddit_score":        reddit.get("crypto", 50),
        "posts_analyzed":      reddit.get("posts_analyzed", 0),
        "news_count":          len(news),
        "whale_alerts":        len(whale_alerts),
    }
    bot_state["optimized_params"] = {
        "MIN_SCORE_BUY":     params.get("MIN_SCORE_BUY", 70),
        "STOP_LOSS_PCT":     params.get("STOP_LOSS_PCT", 0.07),
        "TAKE_PROFIT_PCT":   params.get("TAKE_PROFIT_PCT", 0.18),
        "profitable_assets": params.get("profitable_assets", 0),
    }
    bot_state["exposition"]       = {
        "total_positions":   len(bot_state["positions"]),
        "total_investi_eur": total_inv,
        "max_positions":     MAX_POSITIONS,
        "max_total_eur":     MAX_TOTAL_EUR,
    }
    bot_state["last_prices"]      = {
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
        } for k, v in all_prices.items() if k not in STABLECOINS
    }

    save_json(HISTORY_FILE, history)
    save_json(STATE_FILE, bot_state)

    print("\n" + "="*65)
    print("  DONE v4.0 - " + str(len(results)) + " actifs | " + str(len(actions)) + " ordres | PnL: " + str(bot_state["total_pnl_eur"]) + "EUR")
    print("  Exposition: " + str(len(bot_state["positions"])) + "/" + str(MAX_POSITIONS) + " | " + str(total_inv) + "/" + str(MAX_TOTAL_EUR) + "EUR")
    print("  Whales: " + str(len(whale_alerts)) + " | Reddit: " + str(reddit.get("crypto",50)) + "/100 | News: " + str(len(news)))
    print("  BTC: " + btc_status + " (" + str(btc_chg) + "%) | Params BUY>=" + str(params.get("MIN_SCORE_BUY",70)))
    print("="*65 + "\n")

if __name__ == "__main__":
    run_bot()

"""
NEXUS TRADING BOT — Agent IA autonome
Fonctionne via GitHub Actions (cron toutes les 15 min)
"""

import requests
import json
import os
from datetime import datetime

# ─── CONFIGURATION ───────────────────────────────────────────────
AV_KEY        = os.environ.get("ALPHA_VANTAGE_KEY", "")
CLAUDE_KEY    = os.environ.get("CLAUDE_API_KEY", "")
BITPANDA_KEY  = os.environ.get("BITPANDA_API_KEY", "")

# Actifs à surveiller
CRYPTO_ASSETS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT"
}
STOCK_ASSETS = {
    "NVDA": "NVDA",
    "AAPL": "AAPL"
}

# Règles de trading
MIN_SCORE_BUY    = 70    # Score minimum pour acheter
MAX_SCORE_SELL   = 40    # Score maximum pour vendre
STOP_LOSS_PCT    = 0.07  # -7%
TAKE_PROFIT_PCT  = 0.18  # +18%
MAX_TRADE_EUR    = 50    # Montant max par trade en euros
DRY_RUN          = True  # True = simulation, False = vrais ordres

HISTORY_FILE = "docs/trade_history.json"
STATE_FILE   = "docs/bot_state.json"

# ─── TAUX EUR/USD ─────────────────────────────────────────────────
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

# ─── PRIX BINANCE ─────────────────────────────────────────────────
def get_binance_prices():
    prices = {}
    try:
        symbols = json.dumps(list(CRYPTO_ASSETS.values()))
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/24hr?symbols={symbols}",
            timeout=10
        )
        for t in r.json():
            key = next((k for k, v in CRYPTO_ASSETS.items() if v == t["symbol"]), None)
            if key:
                prices[key] = {
                    "price_usd": float(t["lastPrice"]),
                    "change_24h": float(t["priceChangePercent"]),
                    "volume": float(t["quoteVolume"]),
                    "source": "Binance LIVE"
                }
    except Exception as e:
        print(f"[BINANCE] Erreur: {e}")
    return prices

# ─── PRIX ALPHA VANTAGE ───────────────────────────────────────────
def get_stock_prices():
    prices = {}
    for key, symbol in STOCK_ASSETS.items():
        try:
            r = requests.get(
                f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={AV_KEY}",
                timeout=10
            )
            q = r.json().get("Global Quote", {})
            if q.get("05. price"):
                prices[key] = {
                    "price_usd": float(q["05. price"]),
                    "change_24h": float(q["10. change percent"].replace("%", "")),
                    "volume": int(q.get("06. volume", 0)),
                    "source": "Alpha Vantage LIVE"
                }
        except Exception as e:
            print(f"[AV] Erreur {key}: {e}")
    return prices

# ─── ANALYSE CLAUDE AI ────────────────────────────────────────────
def analyze_with_claude(asset, name, price_eur, change, eur_rate):
    try:
        prompt = f"""Tu es un analyste financier IA expert en trading algorithmique.
Analyse {name} ({asset}) :
- Prix actuel : {price_eur:.2f}€ (taux 1 USD = {eur_rate:.4f}€)
- Variation 24h : {change:+.2f}%
- Date : {datetime.now().strftime('%d/%m/%Y %H:%M')} UTC

Réponds UNIQUEMENT en JSON valide sans markdown :
{{
  "score_technique": <0-100>,
  "score_sentiment": <0-100>,
  "score_macro": <0-100>,
  "score_momentum": <0-100>,
  "signal": "<BUY|SELL|HOLD>",
  "confiance": <0-100>,
  "raison": "<explication courte en français, max 2 phrases>",
  "risque_principal": "<risque principal en français, max 1 phrase>"
}}"""

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
        return json.loads(text)
    except Exception as e:
        print(f"[CLAUDE] Erreur analyse {asset}: {e}")
        return {
            "score_technique": 50, "score_sentiment": 50,
            "score_macro": 50, "score_momentum": 50,
            "signal": "HOLD", "confiance": 50,
            "raison": "Analyse indisponible.", "risque_principal": "Données insuffisantes."
        }

# ─── CALCUL SCORE GLOBAL ─────────────────────────────────────────
def compute_global_score(analysis):
    weights = {
        "score_technique": 0.25,
        "score_sentiment": 0.20,
        "score_macro":     0.20,
        "score_momentum":  0.15,
    }
    score = sum(analysis.get(k, 50) * w for k, w in weights.items())
    # Bonus RSI selon variation
    return round(min(100, max(0, score)))

# ─── EXÉCUTION ORDRE BITPANDA ────────────────────────────────────
def place_order_bitpanda(asset, side, amount_eur):
    if DRY_RUN:
        print(f"[DRY RUN] {side} {asset} pour {amount_eur}€ — ordre simulé")
        return {"status": "simulated", "side": side, "amount_eur": amount_eur}

    try:
        # Récupérer l'instrument ID Bitpanda pour l'actif
        r = requests.get(
            "https://api.exchange.bitpanda.com/public/v1/instruments",
            timeout=10
        )
        instruments = r.json()
        instrument_id = None
        for inst in instruments:
            if inst.get("base", {}).get("code") == asset and inst.get("quote", {}).get("code") == "EUR":
                instrument_id = inst["instrument_code"]
                break

        if not instrument_id:
            print(f"[BITPANDA] Instrument {asset}/EUR introuvable")
            return None

        # Passer l'ordre
        order = {
            "instrument_code": instrument_id,
            "type": "MARKET",
            "side": side,
            "amount": str(amount_eur)
        }
        r = requests.post(
            "https://api.exchange.bitpanda.com/public/v1/account/orders",
            headers={
                "Authorization": f"Bearer {BITPANDA_KEY}",
                "Content-Type": "application/json"
            },
            json=order,
            timeout=15
        )
        result = r.json()
        print(f"[BITPANDA] Ordre {side} {asset} : {result}")
        return result
    except Exception as e:
        print(f"[BITPANDA] Erreur ordre: {e}")
        return None

# ─── CHARGEMENT / SAUVEGARDE ÉTAT ────────────────────────────────
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

# ─── BOT PRINCIPAL ───────────────────────────────────────────────
def run_bot():
    print(f"\n{'='*50}")
    print(f"NEXUS TRADING BOT — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} UTC")
    print(f"{'='*50}\n")

    eur_rate = get_eur_rate()
    print(f"[FX] 1 USD = {eur_rate:.4f} EUR")

    # Récupérer tous les prix
    all_prices = {}
    all_prices.update(get_binance_prices())
    all_prices.update(get_stock_prices())

    history   = load_json(HISTORY_FILE, [])
    bot_state = load_json(STATE_FILE, {"positions": {}, "last_run": None, "total_pnl_eur": 0})

    results = []

    for asset, price_data in all_prices.items():
        price_usd = price_data["price_usd"]
        price_eur = price_usd * eur_rate
        change    = price_data["change_24h"]
        name      = {"BTC":"Bitcoin","ETH":"Ethereum","SOL":"Solana","NVDA":"NVIDIA","AAPL":"Apple"}.get(asset, asset)

        print(f"\n[{asset}] {name} — {price_eur:.2f}€ ({change:+.2f}%)")

        # Analyse IA
        analysis     = analyze_with_claude(asset, name, price_eur, change, eur_rate)
        global_score = compute_global_score(analysis)
        signal       = analysis.get("signal", "HOLD")
        confiance    = analysis.get("confiance", 50)

        print(f"  Score global : {global_score}/100 | Signal : {signal} | Confiance : {confiance}%")
        print(f"  Raison : {analysis.get('raison', 'N/A')}")

        action_taken = None
        position     = bot_state["positions"].get(asset)

        # ── Vérifier stop-loss / take-profit sur position ouverte ──
        if position:
            entry_price = position["entry_price_eur"]
            pnl_pct     = (price_eur - entry_price) / entry_price

            if pnl_pct <= -STOP_LOSS_PCT:
                print(f"  STOP-LOSS déclenché ! PnL: {pnl_pct*100:.1f}%")
                result = place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = (price_eur - entry_price) / entry_price * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                del bot_state["positions"][asset]
                action_taken = "STOP_LOSS"

            elif pnl_pct >= TAKE_PROFIT_PCT:
                print(f"  TAKE-PROFIT déclenché ! PnL: {pnl_pct*100:.1f}%")
                result = place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                del bot_state["positions"][asset]
                action_taken = "TAKE_PROFIT"

        # ── Signal d'achat ──
        elif signal == "BUY" and global_score >= MIN_SCORE_BUY and not position:
            print(f"  SIGNAL ACHAT — score {global_score} >= {MIN_SCORE_BUY}")
            result = place_order_bitpanda(asset, "BUY", MAX_TRADE_EUR)
            bot_state["positions"][asset] = {
                "entry_price_eur": price_eur,
                "amount_eur": MAX_TRADE_EUR,
                "entry_date": datetime.now().isoformat()
            }
            action_taken = "BUY"

        # ── Signal de vente sans position ──
        elif signal == "SELL" and global_score <= MAX_SCORE_SELL and position:
            print(f"  SIGNAL VENTE — score {global_score} <= {MAX_SCORE_SELL}")
            result = place_order_bitpanda(asset, "SELL", position["amount_eur"])
            del bot_state["positions"][asset]
            action_taken = "SELL"

        # ── Enregistrer dans l'historique ──
        entry = {
            "timestamp":    datetime.now().isoformat(),
            "asset":        asset,
            "name":         name,
            "price_eur":    round(price_eur, 2),
            "change_24h":   round(change, 2),
            "score":        global_score,
            "signal":       signal,
            "confiance":    confiance,
            "action":       action_taken or "HOLD",
            "raison":       analysis.get("raison", ""),
            "risque":       analysis.get("risque_principal", ""),
            "dry_run":      DRY_RUN
        }
        history.append(entry)
        results.append(entry)

    # Garder les 500 dernières entrées
    history = history[-500:]

    bot_state["last_run"]   = datetime.now().isoformat()
    bot_state["eur_rate"]   = eur_rate
    bot_state["last_prices"] = {k: {"price_eur": round(v["price_usd"]*eur_rate,2), "change_24h": round(v["change_24h"],2)} for k,v in all_prices.items()}

    save_json(HISTORY_FILE, history)
    save_json(STATE_FILE, bot_state)

    print(f"\n[DONE] {len(results)} actifs analysés | PnL total : {bot_state['total_pnl_eur']:.2f}€")
    print(f"[DONE] Fichiers mis à jour : {HISTORY_FILE}, {STATE_FILE}")

if __name__ == "__main__":
    run_bot()

# HAOUD TRADING IA - v5.0 (vers 8.5/10)
# Nouveautes :
# 1. Deep Learning allege (scikit-learn RandomForest)
# 2. Cycle 5 minutes (au lieu de 15)
# 3. Memoire infinie compressee (Claude distille 1x/semaine)
# + Tout de v4 : top 30 crypto, 50 US, CAC40, DAX, 20 ETFs, whales

import requests
import json
import os
import time
import math
import xml.etree.ElementTree as ET
import pickle
import hashlib
from datetime import datetime, timezone, timedelta

# ML imports (leger)
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[ML] scikit-learn non disponible - mode algo classique")

# ============================================================
# CONFIGURATION
# ============================================================

CLAUDE_KEY     = os.environ.get("CLAUDE_API_KEY", "")
BITPANDA_KEY   = os.environ.get("BITPANDA_API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "")

CRYPTO_ASSETS = {
    "BTC":   {"name": "Bitcoin"},     "ETH":   {"name": "Ethereum"},
    "BNB":   {"name": "BNB"},         "SOL":   {"name": "Solana"},
    "XRP":   {"name": "XRP"},         "ADA":   {"name": "Cardano"},
    "AVAX":  {"name": "Avalanche"},   "LINK":  {"name": "Chainlink"},
    "DOT":   {"name": "Polkadot"},    "MATIC": {"name": "Polygon"},
    "DOGE":  {"name": "Dogecoin"},    "TRX":   {"name": "TRON"},
    "TON":   {"name": "Toncoin"},     "SHIB":  {"name": "Shiba Inu"},
    "BCH":   {"name": "Bitcoin Cash"},"NEAR":  {"name": "NEAR Protocol"},
    "LTC":   {"name": "Litecoin"},    "UNI":   {"name": "Uniswap"},
    "ICP":   {"name": "Internet Computer"}, "MATIC": {"name": "Polygon"},
    "ETC":   {"name": "Ethereum Classic"},  "APT":   {"name": "Aptos"},
    "ATOM":  {"name": "Cosmos"},      "XLM":   {"name": "Stellar"},
    "FIL":   {"name": "Filecoin"},    "ARB":   {"name": "Arbitrum"},
    "OP":    {"name": "Optimism"},    "INJ":   {"name": "Injective"},
}

COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "XRP": "ripple", "ADA": "cardano",
    "AVAX": "avalanche-2", "LINK": "chainlink", "DOT": "polkadot",
    "MATIC": "matic-network", "DOGE": "dogecoin", "TRX": "tron",
    "TON": "the-open-network", "SHIB": "shiba-inu", "BCH": "bitcoin-cash",
    "NEAR": "near", "LTC": "litecoin", "UNI": "uniswap",
    "ICP": "internet-computer", "ETC": "ethereum-classic", "APT": "aptos",
    "ATOM": "cosmos", "XLM": "stellar", "FIL": "filecoin",
    "ARB": "arbitrum", "OP": "optimism", "INJ": "injective-protocol",
}

STABLECOINS = {"USDT", "USDC", "STETH", "BUSD"}

STOCK_ASSETS = {
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
    "BRK-B": {"ticker": "BRK-B", "name": "Berkshire Hathaway"},
    "JPM":   {"ticker": "JPM",   "name": "JPMorgan"},
    "V":     {"ticker": "V",     "name": "Visa"},
    "MA":    {"ticker": "MA",    "name": "Mastercard"},
    "GS":    {"ticker": "GS",    "name": "Goldman Sachs"},
    "LLY":   {"ticker": "LLY",   "name": "Eli Lilly"},
    "UNH":   {"ticker": "UNH",   "name": "UnitedHealth"},
    "JNJ":   {"ticker": "JNJ",   "name": "Johnson & Johnson"},
    "PG":    {"ticker": "PG",    "name": "Procter & Gamble"},
    "KO":    {"ticker": "KO",    "name": "Coca-Cola"},
    "WMT":   {"ticker": "WMT",   "name": "Walmart"},
    "XOM":   {"ticker": "XOM",   "name": "ExxonMobil"},
    "NFLX":  {"ticker": "NFLX",  "name": "Netflix"},
    "COIN":  {"ticker": "COIN",  "name": "Coinbase"},
    "MSTR":  {"ticker": "MSTR",  "name": "MicroStrategy"},
}

EUROPE_ASSETS = {
    "MC.PA":  {"ticker": "MC.PA",  "name": "LVMH"},
    "TTE.PA": {"ticker": "TTE.PA", "name": "TotalEnergies"},
    "SAN.PA": {"ticker": "SAN.PA", "name": "Sanofi"},
    "AIR.PA": {"ticker": "AIR.PA", "name": "Airbus"},
    "BNP.PA": {"ticker": "BNP.PA", "name": "BNP Paribas"},
    "OR.PA":  {"ticker": "OR.PA",  "name": "L'Oreal"},
    "RMS.PA": {"ticker": "RMS.PA", "name": "Hermes"},
    "SAP.DE": {"ticker": "SAP.DE", "name": "SAP"},
    "SIE.DE": {"ticker": "SIE.DE", "name": "Siemens"},
    "ALV.DE": {"ticker": "ALV.DE", "name": "Allianz"},
    "MBG.DE": {"ticker": "MBG.DE", "name": "Mercedes-Benz"},
    "BMW.DE": {"ticker": "BMW.DE", "name": "BMW"},
}

ETF_ASSETS = {
    "SPY":  {"ticker": "SPY",     "name": "S&P 500 ETF"},
    "QQQ":  {"ticker": "QQQ",     "name": "Nasdaq 100 ETF"},
    "GLD":  {"ticker": "GLD",     "name": "Gold ETF"},
    "VTI":  {"ticker": "VTI",     "name": "Total Market ETF"},
    "ARKK": {"ticker": "ARKK",    "name": "ARK Innovation ETF"},
    "IWM":  {"ticker": "IWM",     "name": "Russell 2000 ETF"},
    "TLT":  {"ticker": "TLT",     "name": "20yr Treasury ETF"},
    "CW8":  {"ticker": "CW8.PA",  "name": "Amundi MSCI World"},
    "SP5":  {"ticker": "SP5.PA",  "name": "Amundi S&P 500"},
    "C40":  {"ticker": "C40.PA",  "name": "Amundi CAC 40"},
    "PANX": {"ticker": "PANX.PA", "name": "Amundi Nasdaq-100"},
    "AEME": {"ticker": "AEME.PA", "name": "Amundi MSCI Emerging"},
}

# --- PARAMETRES DE BASE (overrides par le learning) ---
BASE_PARAMS = {
    "MIN_SCORE_BUY":   70,
    "MAX_SCORE_SELL":  40,
    "RSI_OVERSOLD":    35,
    "RSI_OVERBOUGHT":  65,
    "STOP_LOSS_PCT":   0.07,
    "TAKE_PROFIT_PCT": 0.18,
}

BASE_WEIGHTS = {
    "technique":  0.55,
    "macro":      0.20,
    "sentiment":  0.15,
    "onchain":    0.10,
}

MAX_TRADE_EUR       = 50
DRY_RUN             = True
MAX_POSITIONS       = 8
MAX_TOTAL_EUR       = 400
MAX_CRYPTO_POS      = 4
MAX_STOCK_POS       = 4
BTC_CRASH_THRESHOLD = -5.0
BTC_WARN_THRESHOLD  = -3.0
BTC_PENALTY_PTS     = 15
CLAUDE_HOUR_UTC     = 8
WISDOM_DAY_OF_WEEK  = 0   # Lundi = distillation hebdo

# Nombre minimum de trades avant d'activer le ML
ML_MIN_TRADES = 20

# ============================================================
# AMELIORATION 1 : TRAILING STOP + TAKE-PROFIT PAR PALIERS
# ============================================================
TRAILING_STOP_ENABLED  = True
TRAILING_STOP_PCT      = 0.04    # Stop remonte si gain > 4% (garde 4% de gain mini)

# Take-profit par paliers (vente partielle)
TP_PALIERS = [
    (0.08,  0.30),   # +8%  -> vendre 30% de la position
    (0.15,  0.40),   # +15% -> vendre 40% supplementaires
    (0.25,  1.00),   # +25% -> vendre le reste
]

# ============================================================
# AMELIORATION 2 : HEURES DE TRADING OPTIMALES
# ============================================================
TRADING_HOURS_ENABLED = True
# Plages horaires UTC ou le trading est autorise
TRADING_WINDOWS = [
    (7, 10),    # Ouverture Europe (7h-10h UTC)
    (13, 17),   # Ouverture US + chevauchement (13h-17h UTC)
    (19, 22),   # Session asiatique debut (19h-22h UTC)
]
# Exception : les cryptos tradent 24h/24 (toujours autorises)
CRYPTO_24H = True

# ============================================================
# AMELIORATION 3 : CORRELATION INTER-ACTIFS
# ============================================================
# Secteurs pour diversification forcee
SECTEURS = {
    "crypto_major":   ["BTC", "ETH", "BNB"],
    "crypto_alt":     ["SOL", "ADA", "AVAX", "LINK", "DOT", "MATIC"],
    "crypto_meme":    ["DOGE", "SHIB"],
    "tech_us":        ["NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMD"],
    "finance_us":     ["JPM", "GS", "V", "MA"],
    "etf_us":         ["SPY", "QQQ", "VTI"],
    "etf_or":         ["GLD"],
    "europe":         ["MC.PA", "TTE.PA", "SAP.DE", "SIE.DE"],
}
MAX_PER_SECTEUR = 1   # Max 1 position par secteur

# ============================================================
# AMELIORATION 4 : REINVESTISSEMENT AUTOMATIQUE
# ============================================================
REINVEST_ENABLED    = True
REINVEST_RATE       = 0.20   # 20% des gains reinvestis dans MAX_TRADE_EUR
MAX_TRADE_HARD_CAP  = 200    # Plafond absolu par trade (securite)


HISTORY_FILE   = "docs/trade_history.json"
STATE_FILE     = "docs/bot_state.json"
MACRO_FILE     = "docs/macro_cache.json"
BACKTEST_FILE  = "docs/backtest.json"
PARAMS_FILE    = "docs/optimized_params.json"
WHALE_FILE     = "docs/whale_alerts.json"
LEARNING_FILE  = "docs/learning.json"
WISDOM_FILE    = "docs/wisdom.json"
MODEL_FILE     = "docs/ml_model.pkl"

# ============================================================
# UTILITAIRES
# ============================================================

# ============================================================
# AMELIORATION 1 : TRAILING STOP + TP PALIERS
# ============================================================

def update_trailing_stop(position, price_eur):
    """Met a jour le trailing stop si le prix monte"""
    if not TRAILING_STOP_ENABLED:
        return position
    ep = position["entry_price_eur"]
    pnl_pct = (price_eur - ep) / ep
    # Activer le trailing seulement apres +4% de gain
    if pnl_pct >= 0.04:
        # Le stop ne peut que monter, jamais descendre
        new_stop = price_eur * (1 - TRAILING_STOP_PCT)
        current_stop = position.get("trailing_stop_eur", ep * (1 - 0.07))
        if new_stop > current_stop:
            position["trailing_stop_eur"] = round(new_stop, 4)
            position["trailing_activated"] = True
            print("  [TRAILING] " + str(round(new_stop, 2)) + "EUR (prix=" + str(round(price_eur,2)) + " gain=" + str(round(pnl_pct*100,1)) + "%)")
    return position

def check_tp_paliers(position, price_eur, asset, learning_data):
    """
    Verifie les paliers de take-profit et vend partiellement.
    Retourne (action, montant_vendu, reste_position)
    """
    ep          = position["entry_price_eur"]
    pnl_pct     = (price_eur - ep) / ep
    total_amount = position["amount_eur"]
    paliers_done = position.get("paliers_done", [])

    for palier_pct, fraction in TP_PALIERS:
        palier_key = str(palier_pct)
        if pnl_pct >= palier_pct and palier_key not in paliers_done:
            montant_vente = round(total_amount * fraction, 2)
            if montant_vente < 1:
                continue
            place_order_bitpanda(asset, "SELL", montant_vente)
            pnl_eur = pnl_pct * montant_vente
            paliers_done.append(palier_key)
            # Reduire la position
            position["amount_eur"]    = round(total_amount - montant_vente, 2)
            position["paliers_done"]  = paliers_done
            position["amount_eur"]    = max(0, position["amount_eur"])
            print("  [TP PALIER] +" + str(round(palier_pct*100)) + "% -> vente " + str(round(fraction*100)) + "% = " + str(montant_vente) + "EUR | PnL=" + str(round(pnl_eur,2)) + "EUR")
            send_telegram("TP PALIER +" + str(round(palier_pct*100)) + "% - " + asset + "\nVendu: " + str(montant_vente) + "EUR | Gain: +" + str(round(pnl_eur,2)) + "EUR\nReste: " + str(position["amount_eur"]) + "EUR")
            return "TP_PALIER_" + str(round(palier_pct*100)), pnl_eur, position

    return None, 0, position

# ============================================================
# AMELIORATION 2 : FILTRE HEURES DE TRADING
# ============================================================

def is_trading_allowed(asset_type):
    """Verifie si on est dans une fenetre de trading optimale"""
    if not TRADING_HOURS_ENABLED:
        return True
    if asset_type == "crypto" and CRYPTO_24H:
        return True   # Les cryptos tradent toujours
    hour_utc = datetime.now(timezone.utc).hour
    for start, end in TRADING_WINDOWS:
        if start <= hour_utc < end:
            return True
    return False

def get_momentum_exit_signal(tech):
    """Detecte si le momentum indique une sortie imminente"""
    rsi      = tech.get("rsi", 50)
    macd     = tech.get("macd", 0)
    macd_sig = tech.get("macd_signal", 0)
    momentum = tech.get("momentum", 0)
    # Signal de sortie : RSI suracheté + MACD qui croise à la baisse + momentum negatif
    rsi_overbought = rsi >= 72
    macd_bearish   = macd < macd_sig and macd > 0   # Croisement baissier depuis le haut
    mom_fading     = momentum < -3
    exit_signals   = sum([rsi_overbought, macd_bearish, mom_fading])
    if exit_signals >= 2:
        print("  [MOMENTUM EXIT] RSI=" + str(rsi) + " MACD cross=" + str(macd_bearish) + " Mom=" + str(momentum))
        return True
    return False

# ============================================================
# AMELIORATION 3 : CORRELATION INTER-ACTIFS
# ============================================================

def get_asset_secteur(asset):
    for secteur, assets in SECTEURS.items():
        if asset in assets:
            return secteur
    return "other"

def is_secteur_full(asset, bot_state):
    """Verifie si le secteur de l actif est deja maximalise"""
    secteur = get_asset_secteur(asset)
    if secteur == "other":
        return False
    positions = bot_state.get("positions", {})
    same_secteur = [k for k in positions if get_asset_secteur(k) == secteur]
    if len(same_secteur) >= MAX_PER_SECTEUR:
        print("  [SECTEUR] " + secteur + " plein (" + str(same_secteur) + ") -> achat bloque")
        return True
    return False

def get_diversification_bonus(asset, bot_state):
    """Bonus si l actif diversifie le portefeuille"""
    if not bot_state.get("positions"):
        return 0
    secteur = get_asset_secteur(asset)
    positions_secteurs = [get_asset_secteur(k) for k in bot_state["positions"]]
    # Bonus si secteur pas encore represente
    if secteur not in positions_secteurs:
        return 3   # +3pts pour la diversification
    return 0

# ============================================================
# AMELIORATION 4 : REINVESTISSEMENT AUTOMATIQUE
# ============================================================

def compute_dynamic_trade_amount(bot_state):
    """Calcule le montant du prochain trade selon les gains accumules"""
    if not REINVEST_ENABLED:
        return MAX_TRADE_EUR
    total_pnl = bot_state.get("total_pnl_eur", 0)
    if total_pnl <= 0:
        return MAX_TRADE_EUR
    # Augmenter le montant de 20% des gains cumules
    bonus = total_pnl * REINVEST_RATE
    new_amount = round(min(MAX_TRADE_EUR + bonus, MAX_TRADE_HARD_CAP), 2)
    if new_amount > MAX_TRADE_EUR:
        print("  [REINVEST] Montant trade augmente: " + str(MAX_TRADE_EUR) + " -> " + str(new_amount) + "EUR (PnL cumul=" + str(total_pnl) + "EUR)")
    return new_amount

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

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

# ============================================================
# NIVEAU 3 : DEEP LEARNING - MODELE ML
# ============================================================

def extract_features(entry):
    """Extrait un vecteur de features depuis un trade historique"""
    return [
        float(entry.get("rsi", 50)),
        float(entry.get("score_technique", 50)),
        float(entry.get("score_macro", 50)),
        float(entry.get("score_sentiment", 50)),
        float(entry.get("score_momentum", 50)),
        float(entry.get("score_volume", 50)),
        float(entry.get("change_24h", 0)),
        float(entry.get("score", 50)),
        1.0 if entry.get("type") == "crypto" else 0.0,
        1.0 if entry.get("type") == "stock" else 0.0,
        1.0 if entry.get("type") == "etf" else 0.0,
        float(entry.get("momentum", 0)),
        float(entry.get("reddit_score", 50)),
        float(entry.get("bt_win_rate", 50) or 50),
    ]

def train_ml_model(history):
    """Entraine le modele sur les trades clotures (avec resultat connu)"""
    if not ML_AVAILABLE:
        return None, None

    # Construire dataset : uniquement les trades avec resultats
    closed = load_json(LEARNING_FILE, {}).get("trade_log", [])
    if len(closed) < ML_MIN_TRADES:
        print("  [ML] Pas assez de trades clotures (" + str(len(closed)) + "/" + str(ML_MIN_TRADES) + ") - entrainement reporte")
        return None, None

    X, y = [], []
    for trade in closed:
        entry_h = next((h for h in history if h.get("asset") == trade.get("asset") and
                        h.get("timestamp", "")[:16] == trade.get("entry_time", "")[:16]), None)
        if not entry_h:
            continue
        features = extract_features(entry_h)
        label    = 1 if trade.get("pnl_pct", 0) > 0 else 0
        X.append(features)
        y.append(label)

    if len(X) < ML_MIN_TRADES:
        print("  [ML] Features insuffisantes (" + str(len(X)) + ") - skip")
        return None, None

    try:
        X_arr = np.array(X)
        y_arr = np.array(y)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_arr)

        # RandomForest leger
        model = RandomForestClassifier(
            n_estimators=50,
            max_depth=5,
            min_samples_split=4,
            random_state=42,
            n_jobs=1
        )
        model.fit(X_scaled, y_arr)

        # Cross-validation pour evaluer la fiabilite
        if len(X) >= 10:
            cv_scores = cross_val_score(model, X_scaled, y_arr, cv=min(5, len(X)//4), scoring='accuracy')
            accuracy = round(cv_scores.mean() * 100, 1)
            print("  [ML] Modele entraine sur " + str(len(X)) + " trades | Precision CV: " + str(accuracy) + "%")
        else:
            accuracy = 50
            print("  [ML] Modele entraine sur " + str(len(X)) + " trades")

        # Sauvegarder le modele
        with open(MODEL_FILE, 'wb') as f:
            pickle.dump({"model": model, "scaler": scaler, "accuracy": accuracy, "n_trades": len(X)}, f)

        return model, scaler
    except Exception as e:
        print("  [ML] Erreur entrainement: " + str(e))
        return None, None

def load_ml_model():
    """Charge le modele ML existant"""
    if not ML_AVAILABLE:
        return None, None
    try:
        with open(MODEL_FILE, 'rb') as f:
            data = pickle.load(f)
        print("  [ML] Modele charge | Precision: " + str(data.get("accuracy", "?")) + "% | Trades: " + str(data.get("n_trades", "?")))
        return data["model"], data["scaler"]
    except:
        return None, None

def get_ml_score(asset_entry, model, scaler):
    """Obtient le score de confiance du modele ML (0-100)"""
    if model is None or scaler is None:
        return None
    try:
        features = np.array([extract_features(asset_entry)])
        features_scaled = scaler.transform(features)
        proba = model.predict_proba(features_scaled)[0]
        win_proba = float(proba[1]) if len(proba) > 1 else 0.5
        return round(win_proba * 100, 1)
    except:
        return None

# ============================================================
# NIVEAU 2 : AJUSTEMENT DES POIDS ADAPTATIFS
# ============================================================

def update_adaptive_weights(learning_data, closed_trade):
    """Ajuste les poids des composantes selon les resultats"""
    weights  = learning_data.get("weights", BASE_WEIGHTS.copy())
    pnl      = closed_trade.get("pnl_pct", 0)
    entry    = closed_trade.get("entry_snapshot", {})

    if not entry:
        return weights

    # Identifier quelle composante etait la plus differente de la moyenne
    tech_score = entry.get("score_technique", 50)
    macro_score = entry.get("score_macro", 50)
    sent_score  = entry.get("score_sentiment", 50)
    oc_score    = entry.get("onchain_score", 50) or 50

    # Si trade gagnant : renforcer la composante la plus haute
    # Si trade perdant : reduire la composante qui avait induit en erreur
    lr = 0.02  # taux d'apprentissage conservateur

    if pnl > 0:
        # Identifier composante la plus predictive du succes
        top_comp = max([("technique", tech_score), ("macro", macro_score),
                       ("sentiment", sent_score), ("onchain", oc_score)], key=lambda x: x[1])
        weights[top_comp[0]] = min(0.75, weights[top_comp[0]] + lr)
    else:
        # Identifier composante qui avait un score eleve mais trade raté
        global_score = entry.get("score", 50)
        if tech_score > global_score + 5:
            weights["technique"] = max(0.30, weights["technique"] - lr)
        if macro_score > global_score + 10:
            weights["macro"] = max(0.10, weights["macro"] - lr)

    # Renormaliser pour que la somme = 1
    total = sum(weights.values())
    weights = {k: round(v / total, 3) for k, v in weights.items()}

    print("  [LEARN] Poids mis a jour: tech=" + str(weights.get("technique")) +
          " macro=" + str(weights.get("macro")) + " sent=" + str(weights.get("sentiment")))
    return weights

# ============================================================
# NIVEAU 1 : AJUSTEMENT DES SEUILS
# ============================================================

def update_adaptive_thresholds(learning_data):
    """Ajuste MIN_SCORE_BUY, RSI seuils selon les stats reelles"""
    trade_log = learning_data.get("trade_log", [])
    params    = learning_data.get("thresholds", BASE_PARAMS.copy())

    if len(trade_log) < 10:
        return params

    # Analyser les 30 derniers trades
    recent = trade_log[-30:]
    wins   = [t for t in recent if t.get("pnl_pct", 0) > 0]
    losses = [t for t in recent if t.get("pnl_pct", 0) <= 0]
    win_rate = len(wins) / len(recent) if recent else 0.5

    print("  [LEARN] Win rate recent: " + str(round(win_rate*100, 1)) + "% sur " + str(len(recent)) + " trades")

    # Niveau 1 : Ajuster seuil BUY
    if win_rate >= 0.65:
        params["MIN_SCORE_BUY"] = max(65, params.get("MIN_SCORE_BUY", 70) - 1)
        print("  [LEARN] Seuil BUY assoupli -> " + str(params["MIN_SCORE_BUY"]))
    elif win_rate <= 0.40:
        params["MIN_SCORE_BUY"] = min(80, params.get("MIN_SCORE_BUY", 70) + 2)
        print("  [LEARN] Seuil BUY renforce -> " + str(params["MIN_SCORE_BUY"]))

    # Analyser les stop-loss : si trop frequents, serrer
    stop_losses = [t for t in recent if t.get("action") == "STOP_LOSS"]
    if len(stop_losses) > len(recent) * 0.3:
        params["STOP_LOSS_PCT"] = max(0.05, params.get("STOP_LOSS_PCT", 0.07) - 0.005)
        print("  [LEARN] Stop-loss resserre -> " + str(round(params["STOP_LOSS_PCT"]*100, 1)) + "%")

    # Analyser RSI des trades gagnants vs perdants
    if wins and losses:
        avg_rsi_wins   = sum(t.get("entry_rsi", 50) for t in wins) / len(wins)
        avg_rsi_losses = sum(t.get("entry_rsi", 50) for t in losses) / len(losses)
        if avg_rsi_wins < avg_rsi_losses - 5:
            params["RSI_OVERSOLD"] = max(25, params.get("RSI_OVERSOLD", 35) - 1)
            print("  [LEARN] RSI oversold ajuste -> " + str(params["RSI_OVERSOLD"]))

    params["last_update"]  = datetime.now().isoformat()
    params["win_rate_recent"] = round(win_rate * 100, 1)
    return params

# ============================================================
# NIVEAU 3 : PATTERNS PAR ACTIF
# ============================================================

def update_asset_patterns(learning_data, asset, closed_trade):
    """Detecte et memorise les patterns gagnants/perdants par actif"""
    patterns = learning_data.get("asset_patterns", {})
    if asset not in patterns:
        patterns[asset] = {
            "trades":        0,
            "wins":          0,
            "losses":        0,
            "win_rate":      0,
            "avg_pnl":       0,
            "best_rsi_range": None,
            "avoid_conditions": [],
            "favorable_conditions": [],
            "last_trades":   []
        }

    p   = patterns[asset]
    pnl = closed_trade.get("pnl_pct", 0)
    rsi = closed_trade.get("entry_rsi", 50)
    chg = closed_trade.get("entry_change_24h", 0)

    p["trades"] += 1
    if pnl > 0:
        p["wins"] += 1
    else:
        p["losses"] += 1

    p["win_rate"] = round(p["wins"] / p["trades"] * 100, 1)
    all_pnls     = [t.get("pnl_pct", 0) for t in p["last_trades"]] + [pnl]
    p["avg_pnl"] = round(sum(all_pnls) / len(all_pnls), 2)

    # Detecter conditions favorables / a eviter
    condition = {
        "rsi": rsi,
        "change_24h": chg,
        "pnl": pnl,
        "result": "win" if pnl > 0 else "loss"
    }

    # Garder les 10 derniers trades
    p["last_trades"].append(condition)
    p["last_trades"] = p["last_trades"][-10:]

    # Identifier les meilleures conditions RSI
    win_rsi  = [t["rsi"] for t in p["last_trades"] if t["result"] == "win"]
    lose_rsi = [t["rsi"] for t in p["last_trades"] if t["result"] == "loss"]
    if len(win_rsi) >= 3:
        p["best_rsi_range"] = [round(min(win_rsi), 1), round(max(win_rsi), 1)]

    # Conditions a eviter (pertes repetees)
    if pnl < -5:
        cond_avoid = "RSI=" + str(round(rsi)) + " change=" + str(round(chg, 1)) + "%"
        if cond_avoid not in p["avoid_conditions"]:
            p["avoid_conditions"].append(cond_avoid)
            p["avoid_conditions"] = p["avoid_conditions"][-5:]

    # Conditions favorables (gains repetees)
    if pnl > 5:
        cond_fav = "RSI=" + str(round(rsi)) + " change=" + str(round(chg, 1)) + "%"
        if cond_fav not in p["favorable_conditions"]:
            p["favorable_conditions"].append(cond_fav)
            p["favorable_conditions"] = p["favorable_conditions"][-5:]

    patterns[asset] = p
    print("  [PATTERN] " + asset + " | " + str(p["wins"]) + "W/" + str(p["losses"]) + "L | Win=" + str(p["win_rate"]) + "%")
    return patterns

def get_pattern_bonus(asset, rsi, learning_data):
    """Retourne un bonus/malus de score selon les patterns appris"""
    patterns = learning_data.get("asset_patterns", {})
    p = patterns.get(asset)
    if not p or p.get("trades", 0) < 5:
        return 0

    bonus = 0
    win_rate = p.get("win_rate", 50)

    # Bonus si l'actif a un bon historique global
    if win_rate >= 65:   bonus += 5
    elif win_rate <= 35: bonus -= 8

    # Bonus si RSI dans la plage gagnante
    best_rsi = p.get("best_rsi_range")
    if best_rsi and best_rsi[0] <= rsi <= best_rsi[1]:
        bonus += 4
        print("  [PATTERN] " + asset + " RSI dans zone favorable -> +" + str(bonus) + "pts")

    return bonus

# ============================================================
# MEMOIRE INFINIE COMPRESSEE (distillation Claude 1x/semaine)
# ============================================================

def should_distill_wisdom():
    wisdom = load_json(WISDOM_FILE, {})
    last   = wisdom.get("last_distillation", "")
    if not last:
        return True
    ld = datetime.fromisoformat(last)
    if ld.tzinfo is None:
        ld = ld.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - ld).days
    return days >= 7 and datetime.now(timezone.utc).weekday() == WISDOM_DAY_OF_WEEK

def distill_wisdom(history, learning_data):
    """Claude distille les lecons des trades en sagesse compressee"""
    if not CLAUDE_KEY:
        return None

    trade_log    = learning_data.get("trade_log", [])
    asset_patt   = learning_data.get("asset_patterns", {})
    stats        = learning_data.get("stats", {})

    if len(trade_log) < 10:
        return None

    # Preparer un resume compact
    recent_trades = trade_log[-50:]
    best_trades   = sorted(recent_trades, key=lambda x: x.get("pnl_pct", 0), reverse=True)[:5]
    worst_trades  = sorted(recent_trades, key=lambda x: x.get("pnl_pct", 0))[:5]
    best_assets   = sorted(asset_patt.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True)[:5]
    worst_assets  = sorted(asset_patt.items(), key=lambda x: x[1].get("win_rate", 0))[:5]

    summary = (
        "RAPPORT BOT HAOUD TRADING IA\n"
        "Periode analysee: " + str(len(trade_log)) + " trades\n"
        "Win rate global: " + str(stats.get("win_rate", 0)) + "%\n"
        "PnL moyen: " + str(stats.get("avg_pnl", 0)) + "%\n\n"
        "5 meilleurs trades: " + str([t.get("asset") + " +" + str(round(t.get("pnl_pct",0),1)) + "%" for t in best_trades]) + "\n"
        "5 pires trades: " + str([t.get("asset") + " " + str(round(t.get("pnl_pct",0),1)) + "%" for t in worst_trades]) + "\n"
        "Actifs performants: " + str([(a, str(p.get("win_rate","?")) + "%") for a,p in best_assets]) + "\n"
        "Actifs a eviter: " + str([(a, str(p.get("win_rate","?")) + "%") for a,p in worst_assets]) + "\n"
    )

    try:
        prompt = (
            "Tu es un expert en trading algorithmique.\n"
            "Analyse ces resultats de mon bot de trading et distille les lecons cles.\n\n"
            + summary + "\n\n"
            "Reponds UNIQUEMENT en JSON valide sans markdown:\n"
            "{\n"
            '  "lecons_cles": ["<lecon1>", "<lecon2>", "<lecon3>"],\n'
            '  "actifs_a_privilegier": ["<ticker1>", "<ticker2>"],\n'
            '  "actifs_a_eviter": ["<ticker1>", "<ticker2>"],\n'
            '  "conditions_favorables": "<description des conditions de marche gagnantes>",\n'
            '  "erreurs_recurrentes": "<description des erreurs a corriger>",\n'
            '  "recommandation_seuil_buy": <nombre entre 65 et 80>,\n'
            '  "recommandation_stop_loss": <nombre entre 0.04 et 0.10>,\n'
            '  "strategie_recommandee": "<conseil strategique en 2 phrases>"\n'
            "}"
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 800,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        text = r.json()["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
        wisdom = json.loads(text)
        wisdom["last_distillation"] = datetime.now(timezone.utc).isoformat()
        wisdom["trades_analyzed"]   = len(trade_log)
        wisdom["win_rate_at_distill"] = stats.get("win_rate", 0)
        print("[WISDOM] Distillation OK - " + str(len(wisdom.get("lecons_cles", []))) + " lecons extraites")

        # Appliquer les recommandations dans les params
        current_params = load_json(PARAMS_FILE, BASE_PARAMS.copy())
        rec_buy = wisdom.get("recommandation_seuil_buy")
        rec_sl  = wisdom.get("recommandation_stop_loss")
        if rec_buy and 65 <= rec_buy <= 80:
            current_params["MIN_SCORE_BUY"] = int(rec_buy)
        if rec_sl and 0.04 <= rec_sl <= 0.10:
            current_params["STOP_LOSS_PCT"] = float(rec_sl)
        current_params["wisdom_applied"] = datetime.now().isoformat()
        save_json(PARAMS_FILE, current_params)

        send_telegram(
            "HAOUD TRADING IA - Distillation hebdo\n"
            "Win rate: " + str(stats.get("win_rate", 0)) + "%\n"
            "Lecon principale: " + str(wisdom.get("lecons_cles", ["N/A"])[0]) + "\n"
            "Actifs favoris: " + str(wisdom.get("actifs_a_privilegier", []))
        )
        return wisdom
    except Exception as e:
        print("[WISDOM] Erreur: " + str(e))
        return None

def record_closed_trade(asset, entry_snapshot, exit_price_eur, action, learning_data):
    """Enregistre un trade cloture et declenche l'apprentissage"""
    entry_price = entry_snapshot.get("entry_price_eur", exit_price_eur)
    pnl_pct     = round((exit_price_eur - entry_price) / entry_price * 100, 2) if entry_price > 0 else 0

    trade_record = {
        "asset":             asset,
        "action":            action,
        "entry_price_eur":   entry_price,
        "exit_price_eur":    round(exit_price_eur, 4),
        "pnl_pct":           pnl_pct,
        "entry_time":        entry_snapshot.get("entry_date", ""),
        "exit_time":         datetime.now().isoformat(),
        "entry_rsi":         entry_snapshot.get("rsi", 50),
        "entry_score":       entry_snapshot.get("score", 50),
        "entry_change_24h":  entry_snapshot.get("change_24h", 0),
        "entry_snapshot":    {
            "score_technique": entry_snapshot.get("score_technique", 50),
            "score_macro":     entry_snapshot.get("score_macro", 50),
            "score_sentiment": entry_snapshot.get("score_sentiment", 50),
            "onchain_score":   entry_snapshot.get("onchain_score"),
            "score":           entry_snapshot.get("score", 50),
        }
    }

    trade_log = learning_data.get("trade_log", [])
    trade_log.append(trade_record)
    trade_log = trade_log[-200:]  # Garder 200 trades en memoire chaude

    # Mettre a jour les stats
    wins   = len([t for t in trade_log if t.get("pnl_pct", 0) > 0])
    losses = len([t for t in trade_log if t.get("pnl_pct", 0) <= 0])
    total  = wins + losses
    all_pnl = [t.get("pnl_pct", 0) for t in trade_log]

    learning_data["trade_log"] = trade_log
    learning_data["stats"]     = {
        "total_closed": total,
        "wins":         wins,
        "losses":       losses,
        "win_rate":     round(wins / total * 100, 1) if total > 0 else 0,
        "avg_pnl":      round(sum(all_pnl) / len(all_pnl), 2) if all_pnl else 0,
        "total_pnl":    round(sum(all_pnl), 2),
        "best_trade":   round(max(all_pnl), 2) if all_pnl else 0,
        "worst_trade":  round(min(all_pnl), 2) if all_pnl else 0,
    }

    print("  [LEARN] Trade enregistre " + asset + " PnL=" + str(pnl_pct) + "% | Win rate=" + str(learning_data["stats"]["win_rate"]) + "%")
    return trade_record

# ============================================================
# RECUPERATION DES PRIX (batch optimise)
# ============================================================

def get_eur_rate():
    try:
        r = requests.get(
            "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json", timeout=5)
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
            "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=" + ids +
            "&order=market_cap_desc&per_page=50&page=1&sparkline=false&price_change_percentage=24h",
            headers={"Accept": "application/json"}, timeout=20)
        id_to_ticker = {v: k for k, v in COINGECKO_IDS.items()}
        for coin in r.json():
            key = id_to_ticker.get(coin["id"])
            if not key or key in STABLECOINS:
                continue
            prices[key] = {
                "price_usd":  float(coin["current_price"]),
                "change_24h": float(coin.get("price_change_percentage_24h") or 0),
                "volume_usd": float(coin.get("total_volume") or 0),
                "high_24h":   float(coin.get("high_24h") or coin["current_price"]),
                "low_24h":    float(coin.get("low_24h")  or coin["current_price"]),
                "closes":     [], "volumes": [],
                "name":       CRYPTO_ASSETS[key]["name"],
                "type":       "crypto", "source": "CoinGecko LIVE"
            }
        print("  [OK] " + str(len(prices)) + " cryptos")
    except Exception as e:
        print("  [ERREUR CoinGecko] " + str(e))
    return prices

def get_yahoo_price_single(ticker):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker + "?interval=1d&range=1y",
            headers=headers, timeout=10)
        result  = r.json()["chart"]["result"][0]
        closes  = [c for c in result.get("indicators",{}).get("quote",[{}])[0].get("close",[]) if c]
        volumes = [v for v in result.get("indicators",{}).get("quote",[{}])[0].get("volume",[]) if v]
        return closes, volumes
    except:
        return [], []

def get_yahoo_batch_quotes(tickers_map, asset_type):
    prices = {}
    all_tickers = [info["ticker"] for info in tickers_map.values()]
    ticker_to_key = {info["ticker"]: key for key, info in tickers_map.items()}
    chunks = [all_tickers[i:i+20] for i in range(0, len(all_tickers), 20)]

    for chunk in chunks:
        try:
            symbols = ",".join(chunk)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = requests.get(
                "https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + symbols,
                headers=headers, timeout=15)
            for q in r.json().get("quoteResponse",{}).get("result",[]):
                ticker = q.get("symbol","")
                key    = ticker_to_key.get(ticker)
                if not key:
                    continue
                price  = float(q.get("regularMarketPrice", 0))
                prev   = float(q.get("regularMarketPreviousClose", price))
                change = ((price - prev) / prev * 100) if prev else 0
                prices[key] = {
                    "price_usd":  price, "change_24h": round(change, 2),
                    "volume_usd": float(q.get("regularMarketVolume", 0)) * price,
                    "high_24h":   float(q.get("regularMarketDayHigh", price)),
                    "low_24h":    float(q.get("regularMarketDayLow", price)),
                    "closes":     [], "volumes":    [],
                    "name":       tickers_map[key]["name"],
                    "type":       asset_type, "source": "Yahoo Finance LIVE"
                }
            time.sleep(0.3)
        except Exception as e:
            print("  [BATCH] " + str(e))

    # Historique 1 an
    for key, data in prices.items():
        ticker = tickers_map[key]["ticker"]
        closes, volumes = get_yahoo_price_single(ticker)
        if closes:
            data["closes"]  = closes
            data["volumes"] = volumes
        time.sleep(0.08)

    print("  [OK] " + str(len(prices)) + " " + asset_type)
    return prices

# ============================================================
# INDICATEURS TECHNIQUES
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

def analyze_technical(asset, price_data, params):
    closes  = price_data.get("closes", [])
    volumes = price_data.get("volumes", [])
    price   = price_data["price_usd"]
    change  = price_data["change_24h"]
    rsi_os  = params.get("RSI_OVERSOLD", 35)
    rsi_ob  = params.get("RSI_OVERBOUGHT", 65)

    rsi = compute_rsi(closes)
    sr  = 82 if rsi < rsi_os else (66 if rsi < rsi_os+10 else (50 if rsi < 55 else (40 if rsi < rsi_ob else 18)))
    ml, sl_macd = compute_macd(closes)
    sm  = 78 if (ml > sl_macd and ml > 0) else (62 if ml > sl_macd else (22 if (ml < sl_macd and ml < 0) else 38))
    bbu, bbm, bbl = compute_bollinger(closes)
    if bbu > bbl and (bbu-bbl) > 0:
        pos = (price - bbl) / (bbu - bbl)
        sb = 82 if pos<0.15 else (65 if pos<0.35 else (50 if pos<0.65 else (35 if pos<0.85 else 18)))
    else:
        sb = 50
    ma20, ma50, ma200 = compute_ma(closes,20), compute_ma(closes,50), compute_ma(closes,200)
    if price>ma20 and price>ma50 and price>ma200 and ma20>ma50:   sma=82
    elif price>ma20 and price>ma50 and ma20>ma50:                 sma=68
    elif price>ma20:                                               sma=55
    elif price<ma20 and price<ma50 and price<ma200:               sma=18
    elif price<ma20 and price<ma50:                               sma=32
    else:                                                          sma=45
    mom = compute_momentum(closes)
    smom = 75 if mom>15 else (65 if mom>7 else (55 if mom>2 else (42 if mom>-5 else (30 if mom>-12 else 18))))
    vols = price_data.get("volumes", [])
    if len(vols) >= 10:
        avg = sum(vols[-10:]) / 10
        rat = vols[-1] / avg if avg > 0 else 1
        svol = 80 if rat>2 else (65 if rat>1.5 else (55 if rat>1 else 40))
    else:
        svol = 50
    schg = 28 if change>5 else (58 if change>2 else (54 if change>0 else (44 if change>-3 else (32 if change>-7 else 18))))

    score_tech = round(sr*0.22 + sm*0.20 + sb*0.15 + sma*0.22 + smom*0.10 + svol*0.06 + schg*0.05)
    tendance   = "HAUSSIERE" if score_tech>=65 else ("BAISSIERE" if score_tech<=40 else "NEUTRE")
    sig_tech   = "BUY" if score_tech>=params.get("MIN_SCORE_BUY",70) else ("SELL" if score_tech<=params.get("MAX_SCORE_SELL",40) else "HOLD")
    rsi_lbl    = "surachete" if rsi>rsi_ob else ("survendu" if rsi<rsi_os else "neutre")

    return {
        "score_technique": score_tech, "rsi": rsi, "macd": ml, "macd_signal": sl_macd,
        "bb_upper": bbu, "bb_mid": bbm, "bb_lower": bbl,
        "ma20": ma20, "ma50": ma50, "ma200": ma200, "momentum": mom,
        "score_rsi": sr, "score_macd": sm, "score_bollinger": sb,
        "score_ma": sma, "score_momentum": smom, "score_volume": svol,
        "tendance": tendance, "signal_tech": sig_tech, "rsi_analyse": rsi_lbl,
    }

# ============================================================
# ON-CHAIN, RSS, REDDIT, WHALE, CLAUDE (identiques v4)
# ============================================================

def get_onchain_data():
    onchain = {}
    try:
        r = requests.get("https://blockchain.info/stats?format=json", timeout=8)
        d = r.json()
        tx = d.get("n_tx", 0)
        s  = 75 if tx>400000 else (60 if tx>300000 else (50 if tx>200000 else 35))
        onchain["BTC"] = {"tx_per_day": tx, "score_onchain": s}
    except: pass
    try:
        r  = requests.get("https://api.etherscan.io/api?module=gastracker&action=gasoracle", timeout=8)
        gas = float(r.json().get("result",{}).get("SafeGasPrice", 20))
        s   = 70 if gas<15 else (60 if gas<30 else (45 if gas<60 else 30))
        onchain["ETH"] = {"gas_price_gwei": gas, "score_onchain": s}
    except: pass
    return onchain

BULLISH = ["bull","moon","pump","buy","long","surge","rally","breakout","ath","gain","bullish","rocket","hodl"]
BEARISH = ["bear","dump","sell","short","crash","drop","bearish","fear","panic","correction","loss","rekt"]

def get_reddit_sentiment():
    total_bull = total_bear = total_posts = 0
    subs = ["CryptoCurrency","wallstreetbets","investing","stocks","Bitcoin"]
    for sub in subs:
        try:
            r = requests.get("https://www.reddit.com/r/"+sub+"/hot.json?limit=15",
                headers={"User-Agent":"HAOUD-Bot/5.0"}, timeout=8)
            for post in r.json().get("data",{}).get("children",[]):
                d = post.get("data",{})
                text = (d.get("title","")+" "+d.get("selftext","")).lower()
                w = min(d.get("score",0)/1000,3)+1
                total_bull += sum(text.count(x) for x in BULLISH)*w
                total_bear += sum(text.count(x) for x in BEARISH)*w
                total_posts += 1
            time.sleep(0.3)
        except: pass
    score = round(total_bull/(total_bull+total_bear)*100) if (total_bull+total_bear)>0 else 50
    return {"crypto": score, "stock": score, "posts_analyzed": total_posts}

def fetch_rss_news():
    headlines = []
    feeds = [
        ("https://feeds.reuters.com/reuters/businessNews","Reuters"),
        ("https://coindesk.com/arc/outboundfeeds/rss/","CoinDesk"),
        ("https://cointelegraph.com/rss","CoinTelegraph"),
    ]
    for url, source in feeds:
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:4]:
                t = item.findtext("title","").strip()
                if t: headlines.append(source+": "+t)
        except: pass
    return headlines[:15]

def get_btc_status(all_prices):
    btc = all_prices.get("BTC")
    if not btc: return "unknown", 0
    chg = btc["change_24h"]
    if chg <= BTC_CRASH_THRESHOLD: return "crash", chg
    elif chg <= BTC_WARN_THRESHOLD: return "warn", chg
    return "ok", chg

def should_run_claude():
    m = load_json(MACRO_FILE, {})
    last = m.get("last_claude_run","")
    if not last: return True
    ld = datetime.fromisoformat(last)
    if ld.tzinfo is None: ld = ld.replace(tzinfo=timezone.utc)
    hours = (datetime.now(timezone.utc)-ld).total_seconds()/3600
    if datetime.now(timezone.utc).hour==CLAUDE_HOUR_UTC and hours>=20: return True
    if hours>=25: return True
    return False

def run_claude_macro(all_prices, eur_rate, news, reddit, backtest, whales, learning_data):
    summary = "".join([k+" "+str(round(d["price_usd"]*eur_rate,2))+"EUR ("+str(d["change_24h"])+"%) | " for k,d in list(all_prices.items())[:8]])
    news_txt  = "\nNews:\n"+"\n".join(["- "+h for h in news[:6]]) if news else ""
    reddit_txt = "\nReddit: "+str(reddit.get("crypto",50))+"/100" if reddit else ""
    stats_txt = "\nStats bot: win_rate="+str(learning_data.get("stats",{}).get("win_rate",0))+"% avg_pnl="+str(learning_data.get("stats",{}).get("avg_pnl",0))+"%"
    wisdom_txt = ""
    wisdom = load_json(WISDOM_FILE, {})
    if wisdom.get("lecons_cles"):
        wisdom_txt = "\nSagesse accumulee: "+str(wisdom["lecons_cles"][:2])

    try:
        prompt = (
            "Tu es un analyste financier IA expert en trading algorithmique.\n"
            "Date: "+datetime.now().strftime('%d/%m/%Y %H:%M')+" UTC\n"
            "Marches: "+summary+news_txt+reddit_txt+stats_txt+wisdom_txt+"\n\n"
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
            headers={"Content-Type":"application/json","x-api-key":CLAUDE_KEY,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":500,"messages":[{"role":"user","content":prompt}]},
            timeout=30)
        text = r.json()["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
        result = json.loads(text)
        result["last_claude_run"] = datetime.now(timezone.utc).isoformat()
        print("[CLAUDE] macro="+str(result.get("score_macro"))+" sentiment="+str(result.get("score_sentiment")))
        return result
    except Exception as e:
        print("[CLAUDE ERREUR] "+str(e))
        return None

# ============================================================
# SCORE FINAL V5 (avec ML + learning)
# ============================================================

def compute_final_score_v5(tech, macro_cache, asset, btc_status, onchain_data,
                            params, weights, learning_data, ml_model, ml_scaler,
                            asset_entry_for_ml):
    st  = tech["score_technique"]
    sm  = macro_cache.get("score_macro", 50)
    ss  = macro_cache.get("score_sentiment", 50)
    fav = macro_cache.get("actifs_favorables", [])
    ris = macro_cache.get("actifs_risques", [])
    bonus_claude = 5 if asset in fav else (-5 if asset in ris else 0)
    oc_score = onchain_data.get(asset, {}).get("score_onchain", 50)

    # Score hybride avec poids adaptatifs (niveau 2)
    score = round(
        st       * weights.get("technique", 0.55) +
        sm       * weights.get("macro", 0.20) +
        ss       * weights.get("sentiment", 0.15) +
        oc_score * weights.get("onchain", 0.10) +
        bonus_claude
    )

    # Bonus patterns par actif (niveau 3)
    rsi = tech.get("rsi", 50)
    pattern_bonus = get_pattern_bonus(asset, rsi, learning_data)
    score += pattern_bonus

    # Bonus ML (si modele disponible)
    ml_score = get_ml_score(asset_entry_for_ml, ml_model, ml_scaler)
    if ml_score is not None:
        # Le ML vote : si confiance > 65%, bonus de 5pts; si < 35%, malus
        ml_bonus = 5 if ml_score >= 65 else (-5 if ml_score <= 35 else 0)
        score += ml_bonus
        if ml_bonus != 0:
            print("  [ML] Score confiance="+str(ml_score)+"% -> bonus="+str(ml_bonus)+"pts")

    # Correlation BTC
    if asset in CRYPTO_ASSETS and btc_status == "warn":
        score = max(0, score - BTC_PENALTY_PTS)

    return min(100, max(0, score)), ml_score

def can_open_position(asset, bot_state, asset_type):
    pos = bot_state.get("positions", {})
    if len(pos) >= MAX_POSITIONS: return False
    if sum(p.get("amount_eur",0) for p in pos.values()) + MAX_TRADE_EUR > MAX_TOTAL_EUR: return False
    if asset_type=="crypto" and sum(1 for k in pos if k in CRYPTO_ASSETS) >= MAX_CRYPTO_POS: return False
    if asset_type!="crypto" and sum(1 for k in pos if k not in CRYPTO_ASSETS) >= MAX_STOCK_POS: return False
    return True

def place_order_bitpanda(asset, side, amount_eur):
    if DRY_RUN:
        print("  [DRY RUN] "+side+" "+asset+" "+str(amount_eur)+"EUR")
        return {"status":"simulated"}
    try:
        r = requests.get("https://api.exchange.bitpanda.com/public/v1/instruments", timeout=10)
        iid = None
        for inst in r.json():
            if inst.get("base",{}).get("code")==asset and inst.get("quote",{}).get("code")=="EUR":
                iid = inst["instrument_code"]; break
        if not iid: return None
        r = requests.post(
            "https://api.exchange.bitpanda.com/public/v1/account/orders",
            headers={"Authorization":"Bearer "+BITPANDA_KEY,"Content-Type":"application/json"},
            json={"instrument_code":iid,"type":"MARKET","side":side,"amount":str(amount_eur)},
            timeout=15)
        return r.json()
    except Exception as e:
        print("  [BITPANDA] "+str(e)); return None

# ============================================================
# BOT PRINCIPAL v5.0
# ============================================================

def run_bot():
    print("\n"+"="*65)
    print("  HAOUD TRADING IA v5.0 - "+datetime.now().strftime('%d/%m/%Y %H:%M:%S')+" UTC")
    print("  Deep Learning + 5min + Memoire infinie")
    print("="*65+"\n")

    eur_rate = get_eur_rate()
    print("[FX] 1 USD = "+str(round(eur_rate,4))+" EUR\n")

    # --- Chargement des systemes d'apprentissage ---
    learning_data = load_json(LEARNING_FILE, {
        "version": 2, "weights": BASE_WEIGHTS.copy(),
        "thresholds": BASE_PARAMS.copy(),
        "asset_patterns": {}, "trade_log": [],
        "stats": {"total_closed":0,"wins":0,"losses":0,"win_rate":0,"avg_pnl":0},
        "last_update": None
    })

    # --- Distillation hebdo de sagesse ---
    if should_distill_wisdom():
        print("[WISDOM] Distillation hebdomadaire...")
        history_for_wisdom = load_json(HISTORY_FILE, [])
        new_wisdom = distill_wisdom(history_for_wisdom, learning_data)
        if new_wisdom:
            save_json(WISDOM_FILE, new_wisdom)

    # --- Prix (batch optimise) ---
    print("[CRYPTO] CoinGecko...")
    all_prices = {}
    all_prices.update(get_crypto_prices())
    print("\n[ACTIONS] Yahoo Finance batch...")
    all_prices.update(get_yahoo_batch_quotes(STOCK_ASSETS, "stock"))
    all_prices.update(get_yahoo_batch_quotes(EUROPE_ASSETS, "stock_eu"))
    print("\n[ETFs] Yahoo Finance batch...")
    all_prices.update(get_yahoo_batch_quotes(ETF_ASSETS, "etf"))

    # --- On-chain ---
    print("\n[ON-CHAIN]...")
    onchain_data = get_onchain_data()

    # --- BTC correlation ---
    btc_status, btc_chg = get_btc_status(all_prices)
    if btc_status == "crash":
        send_telegram("ALERTE BTC crash "+str(btc_chg)+"% - achats crypto bloques")

    # --- Reddit + RSS ---
    print("\n[REDDIT]...")
    reddit = get_reddit_sentiment()
    print("\n[RSS]...")
    news = fetch_rss_news()
    print("  [RSS] "+str(len(news))+" actualites")

    # --- Backtest ---
    print("\n[BACKTEST]...")
    current_params = load_json(PARAMS_FILE, BASE_PARAMS.copy())
    backtest_results = {}
    for asset, pd in all_prices.items():
        if asset in STABLECOINS: continue
        closes = pd.get("closes", [])
        if len(closes) >= 60:
            wins = losses = total_pnl = 0
            trades = []
            position = False
            entry = 0
            sl = current_params.get("STOP_LOSS_PCT", 0.07)
            tp = current_params.get("TAKE_PROFIT_PCT", 0.18)
            rsi_os = current_params.get("RSI_OVERSOLD", 35)
            for i in range(50, len(closes)-1):
                w = closes[:i+1]
                rsi = compute_rsi(w)
                ma20 = compute_ma(w, 20)
                ml2, ms2 = compute_macd(w)
                price = closes[i]
                if not position and rsi < rsi_os and price > ma20 and ml2 > ms2:
                    entry = price; position = True
                elif position and (rsi > 65 or price < entry*(1-sl) or price > entry*(1+tp)):
                    pnl = (price-entry)/entry*100
                    total_pnl += pnl
                    if pnl > 0: wins += 1
                    else: losses += 1
                    trades.append(round(pnl,2))
                    position = False
            total = wins + losses
            if total > 0:
                backtest_results[asset] = {
                    "win_rate": round(wins/total*100,1),
                    "avg_pnl_pct": round(total_pnl/total,2),
                    "total_trades": total
                }
    save_json(BACKTEST_FILE, {"last_update": datetime.now().isoformat(), "results": backtest_results})
    print("  [BACKTEST] "+str(len(backtest_results))+" actifs")

    # --- NIVEAU 1+2+3 : Apprentissage adaptatif ---
    print("\n[LEARNING] Mise a jour parametres adaptatifs...")
    updated_params  = update_adaptive_thresholds(learning_data)
    updated_weights = learning_data.get("weights", BASE_WEIGHTS.copy())
    params  = updated_params
    weights = updated_weights
    save_json(PARAMS_FILE, params)

    # --- DEEP LEARNING : Entrainement ML ---
    print("\n[ML] Deep Learning...")
    history_all = load_json(HISTORY_FILE, [])
    ml_model, ml_scaler = train_ml_model(history_all)
    if ml_model is None:
        ml_model, ml_scaler = load_ml_model()

    # --- Claude macro (1x/jour) ---
    macro_cache = load_json(MACRO_FILE, {
        "score_macro":50,"score_sentiment":50,"tendance_marche":"NEUTRE",
        "contexte":"Analyse non disponible.","risque_principal":"Aucun.",
        "opportunite_du_jour":"Aucune.","actifs_favorables":[],"actifs_risques":[]
    })
    print("\n[MACRO] Claude...")
    if should_run_claude() and CLAUDE_KEY:
        new_macro = run_claude_macro(all_prices, eur_rate, news, reddit, backtest_results, [], learning_data)
        if new_macro:
            macro_cache.update(new_macro)
            save_json(MACRO_FILE, macro_cache)

    # --- Analyse et decisions ---
    history   = load_json(HISTORY_FILE, [])
    bot_state = load_json(STATE_FILE, {"positions":{}, "last_run":None, "total_pnl_eur":0})
    min_score = params.get("MIN_SCORE_BUY", 70)
    max_score = params.get("MAX_SCORE_SELL", 40)
    sl_pct    = params.get("STOP_LOSS_PCT", 0.07)
    tp_pct    = params.get("TAKE_PROFIT_PCT", 0.18)

    print("\n[ANALYSE] "+str(len(all_prices))+" actifs...\n")
    results = []

    for asset, price_data in all_prices.items():
        if asset in STABLECOINS: continue

        price_usd  = price_data["price_usd"]
        price_eur  = price_usd * eur_rate
        change     = price_data["change_24h"]
        name       = price_data.get("name", asset)
        atype      = price_data.get("type", "crypto")
        asset_type = "crypto" if asset in CRYPTO_ASSETS else "other"

        tech = analyze_technical(asset, price_data, params)
        bt   = backtest_results.get(asset, {})

        # Preparer entry pour ML
        ml_entry = {
            "rsi": tech["rsi"], "score_technique": tech["score_technique"],
            "score_macro": macro_cache.get("score_macro", 50),
            "score_sentiment": macro_cache.get("score_sentiment", 50),
            "score_momentum": tech["score_momentum"], "score_volume": tech["score_volume"],
            "change_24h": change, "score": 50, "type": atype,
            "momentum": tech["momentum"], "reddit_score": reddit.get("crypto" if asset in CRYPTO_ASSETS else "stock", 50),
            "bt_win_rate": bt.get("win_rate", 50),
        }

        score_final, ml_confidence = compute_final_score_v5(
            tech, macro_cache, asset, btc_status, onchain_data,
            params, weights, learning_data, ml_model, ml_scaler, ml_entry
        )
        ml_entry["score"] = score_final

        # Signal
        if asset_type == "crypto" and btc_status == "crash":
            signal = "HOLD"
        else:
            if score_final >= min_score and tech["signal_tech"] == "BUY":   signal = "BUY"
            elif score_final <= max_score and tech["signal_tech"] == "SELL": signal = "SELL"
            else:                                                             signal = "HOLD"
            if signal=="BUY"  and score_final < min_score: signal = "HOLD"
            if signal=="SELL" and score_final > max_score: signal = "HOLD"

        action_taken = None
        position     = bot_state["positions"].get(asset)

        # Amelioration 3 : bonus diversification
        div_bonus = get_diversification_bonus(asset, bot_state)
        if div_bonus:
            score_final = min(100, score_final + div_bonus)

        if position:
            ep      = position["entry_price_eur"]
            pnl_pct = (price_eur - ep) / ep

            # Amelioration 1A : Trailing stop update
            position = update_trailing_stop(position, price_eur)
            bot_state["positions"][asset] = position

            # Amelioration 1B : Take-profit par paliers
            if not action_taken:
                palier_action, palier_pnl, position = check_tp_paliers(position, price_eur, asset, learning_data)
                if palier_action:
                    bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + palier_pnl, 2)
                    bot_state["positions"][asset] = position
                    action_taken = palier_action
                    if position.get("amount_eur", 0) <= 1:
                        trade_rec = record_closed_trade(asset, position, price_eur, "TAKE_PROFIT", learning_data)
                        learning_data["weights"]        = update_adaptive_weights(learning_data, trade_rec)
                        learning_data["asset_patterns"] = update_asset_patterns(learning_data, asset, trade_rec)
                        del bot_state["positions"][asset]

            # Stop loss (trailing ou fixe)
            if not action_taken and asset in bot_state["positions"]:
                trailing_stop = position.get("trailing_stop_eur", ep * (1 - sl_pct))
                if price_eur <= trailing_stop:
                    stop_label = "TRAILING_STOP" if position.get("trailing_activated") else "STOP_LOSS"
                    place_order_bitpanda(asset, "SELL", position["amount_eur"])
                    pnl_eur = pnl_pct * position["amount_eur"]
                    bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                    trade_rec = record_closed_trade(asset, position, price_eur, stop_label, learning_data)
                    learning_data["weights"]        = update_adaptive_weights(learning_data, trade_rec)
                    learning_data["asset_patterns"] = update_asset_patterns(learning_data, asset, trade_rec)
                    del bot_state["positions"][asset]
                    action_taken = stop_label
                    send_telegram(stop_label+" "+asset+" PnL: "+str(round(pnl_pct*100,2))+"% ("+str(round(pnl_eur,2))+"EUR)")

            # Take-profit classique
            elif not action_taken and asset in bot_state["positions"] and pnl_pct >= tp_pct:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                trade_rec = record_closed_trade(asset, position, price_eur, "TAKE_PROFIT", learning_data)
                learning_data["weights"]        = update_adaptive_weights(learning_data, trade_rec)
                learning_data["asset_patterns"] = update_asset_patterns(learning_data, asset, trade_rec)
                del bot_state["positions"][asset]
                action_taken = "TAKE_PROFIT"
                send_telegram("TAKE-PROFIT "+asset+" PnL: +"+str(round(pnl_pct*100,2))+"% (+"+str(round(pnl_eur,2))+"EUR)")

            # Amelioration 2 : Sortie sur momentum (si gain > 3%)
            elif not action_taken and asset in bot_state["positions"] and get_momentum_exit_signal(tech) and pnl_pct > 0.03:
                place_order_bitpanda(asset, "SELL", position["amount_eur"])
                pnl_eur = pnl_pct * position["amount_eur"]
                bot_state["total_pnl_eur"] = round(bot_state["total_pnl_eur"] + pnl_eur, 2)
                trade_rec = record_closed_trade(asset, position, price_eur, "MOMENTUM_EXIT", learning_data)
                learning_data["weights"]        = update_adaptive_weights(learning_data, trade_rec)
                learning_data["asset_patterns"] = update_asset_patterns(learning_data, asset, trade_rec)
                del bot_state["positions"][asset]
                action_taken = "MOMENTUM_EXIT"
                send_telegram("SORTIE MOMENTUM "+asset+" +"+str(round(pnl_pct*100,2))+"% (+"+str(round(pnl_eur,2))+"EUR)")

        elif signal == "BUY" and score_final >= min_score and not position:
            # Amelioration 2 : Filtre heures de trading
            if not is_trading_allowed(asset_type):
                print("  [HEURES] Bloque heure="+str(datetime.now(timezone.utc).hour)+"h UTC")
            # Amelioration 3 : Filtre secteur
            elif is_secteur_full(asset, bot_state):
                pass
            elif can_open_position(asset, bot_state, asset_type):
                # Amelioration 4 : Montant dynamique
                trade_amount = compute_dynamic_trade_amount(bot_state)
                place_order_bitpanda(asset, "BUY", trade_amount)
                position_record = {
                    "entry_price_eur":    price_eur,
                    "amount_eur":         trade_amount,
                    "entry_date":         datetime.now().isoformat(),
                    "rsi":                tech["rsi"],
                    "score":              score_final,
                    "change_24h":         change,
                    "score_technique":    tech["score_technique"],
                    "score_macro":        macro_cache.get("score_macro", 50),
                    "score_sentiment":    macro_cache.get("score_sentiment", 50),
                    "onchain_score":      onchain_data.get(asset, {}).get("score_onchain"),
                    "trailing_stop_eur":  round(price_eur * (1 - sl_pct), 4),
                    "trailing_activated": False,
                    "paliers_done":       [],
                    "secteur":            get_asset_secteur(asset),
                }
                bot_state["positions"][asset] = position_record
                action_taken = "BUY"
                ml_str = " | ML="+str(ml_confidence)+"%" if ml_confidence else ""
                send_telegram(
                    "ACHAT "+asset+" ("+name+")\nPrix: "+str(round(price_eur,2))+"EUR | Score: "+str(score_final)+"/100"+ml_str+"\nSecteur: "+get_asset_secteur(asset)+" | Montant: "+str(trade_amount)+"EUR\nSL: "+str(round(price_eur*(1-sl_pct),2))+" | TP: +8%/+15%/+25%"
                )

        elif signal == "SELL" and score_final <= max_score and position:
            place_order_bitpanda(asset, "SELL", position["amount_eur"])
            trade_rec = record_closed_trade(asset, position, price_eur, "SELL", learning_data)
            learning_data["weights"]        = update_adaptive_weights(learning_data, trade_rec)
            learning_data["asset_patterns"] = update_asset_patterns(learning_data, asset, trade_rec)
            del bot_state["positions"][asset]
            action_taken = "SELL"

        ml_str = " ML="+str(ml_confidence)+"%" if ml_confidence else ""
        print("["+asset+"] "+str(round(price_eur,2))+"EUR | RSI="+str(tech["rsi"])+" | Score="+str(score_final)+" | "+signal+ml_str)

        entry = {
            "timestamp": datetime.now().isoformat(), "asset": asset, "name": name, "type": atype,
            "price_eur": round(price_eur,6), "price_usd": round(price_usd,6),
            "change_24h": round(change,2),
            "high_24h": round(price_data.get("high_24h",0)*eur_rate,6),
            "low_24h":  round(price_data.get("low_24h",0)*eur_rate,6),
            "volume_usd": round(price_data.get("volume_usd",0),0),
            "rsi": tech["rsi"], "macd": tech["macd"],
            "bb_upper": round(tech["bb_upper"]*eur_rate,4),
            "bb_lower": round(tech["bb_lower"]*eur_rate,4),
            "ma20":  round(tech["ma20"]*eur_rate,4),
            "ma50":  round(tech["ma50"]*eur_rate,4),
            "ma200": round(tech["ma200"]*eur_rate,4),
            "momentum": tech["momentum"],
            "score": score_final,
            "score_technique": tech["score_technique"],
            "score_macro":     macro_cache.get("score_macro",50),
            "score_sentiment": macro_cache.get("score_sentiment",50),
            "score_momentum":  tech["score_momentum"],
            "score_volume":    tech["score_volume"],
            "signal": signal, "confiance": score_final,
            "tendance": tech["tendance"], "rsi_analyse": tech["rsi_analyse"],
            "action": action_taken or "HOLD",
            "raison":       macro_cache.get("contexte",""),
            "risque":       macro_cache.get("risque_principal",""),
            "opportunite":  macro_cache.get("opportunite_du_jour",""),
            "source":       price_data.get("source",""),
            "bt_win_rate":  bt.get("win_rate"),
            "bt_avg_pnl":   bt.get("avg_pnl_pct"),
            "reddit_score": reddit.get("crypto" if asset in CRYPTO_ASSETS else "stock",50),
            "onchain_score":onchain_data.get(asset,{}).get("score_onchain"),
            "ml_confidence":ml_confidence,
            "dry_run": DRY_RUN
        }
        history.append(entry)
        results.append(entry)

    # --- Sauvegarder learning ---
    learning_data["last_update"] = datetime.now().isoformat()
    save_json(LEARNING_FILE, learning_data)

    history = history[-2000:]
    actions = [e for e in results if e["action"] != "HOLD"]
    total_inv = sum(p.get("amount_eur",0) for p in bot_state["positions"].values())
    stats = learning_data.get("stats", {})

    bot_state["last_run"]    = datetime.now().isoformat()
    bot_state["eur_rate"]    = eur_rate
    bot_state["dry_run"]     = DRY_RUN
    bot_state["btc_status"]  = btc_status
    bot_state["btc_change"]  = btc_chg
    bot_state["total_assets"]= len(results)
    bot_state["learning"]    = {
        "win_rate":          stats.get("win_rate",0),
        "avg_pnl":           stats.get("avg_pnl",0),
        "total_closed":      stats.get("total_closed",0),
        "current_min_score": params.get("MIN_SCORE_BUY",70),
        "current_sl":        round(params.get("STOP_LOSS_PCT",0.07)*100,1),
        "current_weights":   weights,
        "ml_active":         ml_model is not None,
        "ml_accuracy":       None,
    }
    # Recuperer accuracy ML si dispo
    try:
        with open(MODEL_FILE,'rb') as f:
            mdata = pickle.load(f)
            bot_state["learning"]["ml_accuracy"] = mdata.get("accuracy")
    except: pass

    bot_state["macro"] = {
        "score_macro":         macro_cache.get("score_macro",50),
        "score_sentiment":     macro_cache.get("score_sentiment",50),
        "tendance_marche":     macro_cache.get("tendance_marche","NEUTRE"),
        "contexte":            macro_cache.get("contexte",""),
        "risque_principal":    macro_cache.get("risque_principal",""),
        "opportunite_du_jour": macro_cache.get("opportunite_du_jour",""),
        "last_claude_run":     macro_cache.get("last_claude_run",""),
        "reddit_score":        reddit.get("crypto",50),
        "news_count":          len(news),
    }
    bot_state["exposition"] = {
        "total_positions":   len(bot_state["positions"]),
        "total_investi_eur": total_inv,
        "max_positions":     MAX_POSITIONS,
        "max_total_eur":     MAX_TOTAL_EUR,
    }
    bot_state["last_prices"] = {
        k: {
            "price_eur":  round(v["price_usd"]*eur_rate,6),
            "price_usd":  round(v["price_usd"],6),
            "change_24h": round(v["change_24h"],2),
            "high_24h":   round(v.get("high_24h",0)*eur_rate,6),
            "low_24h":    round(v.get("low_24h",0)*eur_rate,6),
            "volume_usd": round(v.get("volume_usd",0),0),
            "rsi":        compute_rsi(v.get("closes",[])),
            "name":       v.get("name",k),
            "type":       v.get("type","crypto"),
            "source":     v.get("source","")
        } for k,v in all_prices.items() if k not in STABLECOINS
    }

    save_json(HISTORY_FILE, history)
    save_json(STATE_FILE, bot_state)

    print("\n"+"="*65)
    print("  DONE v5.0 - "+str(len(results))+" actifs | "+str(len(actions))+" ordres | PnL: "+str(bot_state["total_pnl_eur"])+"EUR")
    print("  Exposition: "+str(len(bot_state["positions"]))+"/"+str(MAX_POSITIONS)+" | "+str(total_inv)+"/"+str(MAX_TOTAL_EUR)+"EUR")
    print("  Learning: WR="+str(stats.get("win_rate",0))+"% | ML="+str(ml_model is not None)+" | Trades="+str(stats.get("total_closed",0)))
    print("  Seuil BUY="+str(params.get("MIN_SCORE_BUY",70))+" | SL="+str(round(params.get("STOP_LOSS_PCT",0.07)*100,1))+"% | Reddit="+str(reddit.get("crypto",50)))
    print("="*65+"\n")

if __name__ == "__main__":
    run_bot()

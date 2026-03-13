# NEXUS TRADING BOT 🤖

Agent IA autonome de trading — GitHub Actions + Page Free.fr

---

## Architecture

```
GitHub Actions (gratuit)          Page Free.fr (gratuit)
┌──────────────────────┐         ┌─────────────────────┐
│  bot.py              │         │  docs/index.html    │
│  Toutes les 15 min : │──JSON──▶│  Dashboard live     │
│  1. Prix Binance     │         │  Surveillance       │
│  2. Prix AV (stocks) │         │  Historique trades  │
│  3. Analyse Claude   │         └─────────────────────┘
│  4. Score BUY/SELL   │
│  5. Ordre Bitpanda   │
│  6. Commit JSON      │
└──────────────────────┘
```

---

## Installation — Étape par étape

### Étape 1 — Créer le repo GitHub

1. Va sur https://github.com/new
2. Nom du repo : `nexus-trading-bot`
3. Coche **Private** (pour protéger tes clés)
4. Clique **Create repository**

### Étape 2 — Uploader les fichiers

Upload tous ces fichiers dans ton repo :
```
nexus-trading-bot/
├── bot.py
├── .github/
│   └── workflows/
│       └── trading-bot.yml
├── docs/
│   ├── index.html
│   ├── trade_history.json
│   └── bot_state.json
└── README.md
```

### Étape 3 — Configurer les secrets GitHub

Dans ton repo GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Ajoute ces 3 secrets :

| Nom du secret       | Valeur                          |
|---------------------|---------------------------------|
| `ALPHA_VANTAGE_KEY` | `4LFYZ34RRNSSD3H9`              |
| `CLAUDE_API_KEY`    | Ta clé API Claude (Anthropic)   |
| `BITPANDA_API_KEY`  | Ta clé API Bitpanda Fusion      |

### Étape 4 — Obtenir ta clé Claude API

1. Va sur https://console.anthropic.com
2. Clique **API Keys** → **Create Key**
3. Copie la clé et ajoute-la dans les secrets GitHub

### Étape 5 — Obtenir ta clé Bitpanda API

1. Connecte-toi sur https://web.bitpanda.com/fusion (sur PC)
2. Va dans **Paramètres** → **API Keys**
3. Crée une clé avec les droits **Trading**
4. Copie-la dans les secrets GitHub

### Étape 6 — Activer GitHub Actions

1. Dans ton repo → onglet **Actions**
2. Clique **Enable Actions** si demandé
3. Le bot tournera automatiquement toutes les 15 minutes

### Étape 7 — Configurer le dashboard sur Free.fr

1. Ouvre `docs/index.html`
2. Remplace `TON_PSEUDO` par ton pseudo GitHub dans ces lignes :
   ```
   const STATE_URL   = 'https://raw.githubusercontent.com/TON_PSEUDO/nexus-trading-bot/main/docs/bot_state.json';
   const HISTORY_URL = 'https://raw.githubusercontent.com/TON_PSEUDO/nexus-trading-bot/main/docs/trade_history.json';
   ```
3. Upload `index.html` sur ta page Free.fr via FTP

### Étape 8 — Passer en mode réel (quand tu es prêt)

Dans `bot.py`, ligne 22, change :
```python
DRY_RUN = True   # simulation
```
en :
```python
DRY_RUN = False  # vrais ordres !
```

⚠️ **ATTENTION** : Ne passe en mode réel qu'après avoir vérifié que la simulation fonctionne correctement pendant plusieurs jours.

---

## Paramètres configurables (bot.py)

| Paramètre         | Valeur par défaut | Description                        |
|-------------------|-------------------|------------------------------------|
| `MIN_SCORE_BUY`   | 70                | Score min pour acheter (0-100)     |
| `MAX_SCORE_SELL`  | 40                | Score max pour vendre (0-100)      |
| `STOP_LOSS_PCT`   | 0.07              | Stop-loss à -7%                    |
| `TAKE_PROFIT_PCT` | 0.18              | Take-profit à +18%                 |
| `MAX_TRADE_EUR`   | 50                | Montant max par trade en euros     |
| `DRY_RUN`         | True              | True = simulation, False = réel    |

---

## Actifs surveillés

**Cryptos (via Binance, gratuit)** : BTC, ETH, SOL
**Actions (via Alpha Vantage)** : NVDA, AAPL

Pour ajouter un actif, modifie les dictionnaires `CRYPTO_ASSETS` ou `STOCK_ASSETS` dans `bot.py`.

---

## Logs et surveillance

- Les logs de chaque exécution sont visibles dans **GitHub → Actions → dernière exécution**
- L'historique complet est dans `docs/trade_history.json`
- Le dashboard sur ta page Free.fr se rafraîchit automatiquement toutes les 60 secondes

---

## ⚠️ Avertissement

Le trading automatisé comporte des **risques financiers réels**. Ce bot est fourni à titre éducatif. Les performances passées ne garantissent pas les résultats futurs. Commence toujours en mode simulation (`DRY_RUN = True`) avant de risquer de l'argent réel.

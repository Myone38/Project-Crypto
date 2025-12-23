# Project-Crypto

[![CI](https://github.com/Myone38/Project-Crypto/actions/workflows/ci.yml/badge.svg)](https://github.com/Myone38/Project-Crypto/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/Myone38/Project-Crypto/branch/main/graph/badge.svg?token=)](https://codecov.io/gh/Myone38/Project-Crypto)

Brief: Dashboard et moteur de trading pour Bitvavo (Dash + background engine).

---

## Branch protection (recommended)

To require passing CI before merging to `main`:

1. Go to your GitHub repository → Settings → Branches → Branch protection rules.
2. Click **Add rule** and set **Branch name pattern** to `main`.
3. Enable **Require status checks to pass before merging** and select the checks to require (e.g., `test` and `lint` from the CI workflow).
4. Optionally enable **Require linear history** and **Include administrators**.

This ensures PRs cannot be merged unless CI is green.

## Installation rapide

1. Créer un environnement virtuel et activer :

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Configurer les variables d'environnement (recommandé) :

   - `BITVAVO_API_KEY` : votre clé API Bitvavo
   - `BITVAVO_API_SECRET` : votre secret Bitvavo
   - `TELEGRAM_BOT_TOKEN` : token du bot Telegram (optionnel)
   - `TELEGRAM_CHAT_ID` : id du chat Telegram (optionnel)
   - `APP_DEBUG` : `True`/`False` (optionnel, default False)

   Pour développement local, vous pouvez créer un fichier `.env` (non versionné) contenant ces variables.

3. Lancer :

   ```powershell
   python main.py
   ```

## Git hooks (optionnel)

Pour exécuter des vérifications locales avant chaque commit, installez `pre-commit` et activez le hook :

```powershell
pip install -r requirements.txt
pre-commit install
# Pour exécuter sur tous les fichiers (exécution initiale)
pre-commit run --all-files
```

Le projet inclut un fichier `.pre-commit-config.yaml` qui exécute `ruff --fix` (automatique) ainsi que quelques hooks utiles (`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`).

## Sécurité

- **Ne commitez jamais** vos clés dans le repo. Le fichier `config/credentials.json` est listé dans `.gitignore` mais il est préférable d'utiliser des variables d'environnement.
- Si des clés ont été partagées, **révoquez-les et régénérez-les** immédiatement.

## Notes techniques

- Le projet utilise `python-bitvavo-api` pour communiquer avec Bitvavo.
- Le bot lit d'abord les variables d'environnement; si elles sont absentes, il tente un fallback sur `config/credentials.json`.

---

## Continuous Integration (CI) ✅

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs the pre-commit checks, linting and test suite on every push and pull request targeting `main`.

A new **auto-fix** job runs `ruff --fix` on pull requests and will open a pull request with the formatting/lint fixes when changes are made automatically (labelled `autofix`).

CI runs `pre-commit` on changed files for pull requests (fast feedback) and executes `pre-commit run --all-files` on pushes to `main` to ensure repository-wide consistency (or on scheduled runs if configured).

---

## Candles backfill & realtime updater 🔁

You can backfill historical candles and start a resilient realtime updater (performs an initial backfill, polls the latest candles periodically, and detects internal gaps).

Runner script: `scripts/update_candles.py`

Usage examples:

- Backfill only (no realtime):

```powershell
python scripts/update_candles.py --interval 1h
```

- Backfill + start realtime (blocking):

```powershell
python scripts/update_candles.py --realtime --interval 1m
```

- Backfill + start realtime (non-blocking useful for tests or supervisory processes):

```powershell
python scripts/update_candles.py --realtime --interval 1m --no-block
```

### Metrics (in-process)

- The updater emits simple in-process metrics via `app.metrics`:
  - `backfill_inserted_<MARKET>` — number of candles inserted during backfill
  - `latest_inserted_<MARKET>` — number of latest candles inserted during realtime polling

Access metrics programmatically:

```python
from app.metrics import get_metrics
print(get_metrics())
```

---



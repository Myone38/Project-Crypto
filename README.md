# Project-Crypto

Brief: Dashboard et moteur de trading pour Bitvavo (Dash + background engine).

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

## Sécurité

- **Ne commitez jamais** vos clés dans le repo. Le fichier `config/credentials.json` est listé dans `.gitignore` mais il est préférable d'utiliser des variables d'environnement.
- Si des clés ont été partagées, **révoquez-les et régénérez-les** immédiatement.

## Notes techniques

- Le projet utilise `python-bitvavo-api` pour communiquer avec Bitvavo.
- Le bot lit d'abord les variables d'environnement; si elles sont absentes, il tente un fallback sur `config/credentials.json`.

---

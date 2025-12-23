import json
import threading
import time
import requests
import os

# Optional dotenv support (local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class TelegramThread(threading.Thread):
    """
    Thread d'envoi Telegram :
      - lit les credentials depuis app/credentials.json
      - fournit .send(msg) pour push un message dans la file
      - sécurise l'envoi (aucune exception ne stoppe le thread)
    """

    def __init__(self, engine, credential_path=None):
        super().__init__()
        self.daemon = True
        self.engine = engine

        # -----------------------------------------------------
        # 1) Chemin fichier credentials
        # -----------------------------------------------------
        if credential_path is None:
            credential_path = os.path.join("config", "credentials.json")

        self.token, self.chat_id = self._load_credentials(credential_path)

        if not self.token or not self.chat_id:
            raise ValueError(
                "TelegramThread : credentials.json doit contenir telegram.bot_token et telegram.chat_id"
            )

        # File FIFO des messages
        self.queue = []

        # Flag pour arrêt propre
        self.running = True

    # ---------------------------------------------------------
    # LECTURE CREDENTIALS.JSON
    # ---------------------------------------------------------
    def _load_credentials(self, path):
        # Prefer environment variables for credentials
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if token and chat_id:
            return token, chat_id

        try:
            with open(path, "r") as f:
                data = json.load(f)

            t = data.get("telegram", {})
            return t.get("bot_token"), t.get("chat_id")

        except Exception as e:
            print(f"[Telegram] Erreur lecture {path} : {e}")
            return None, None

    # ---------------------------------------------------------
    # API TELEGRAM
    # ---------------------------------------------------------
    def send(self, msg):
        """Ajoute un message à envoyer (thread-safe simple)."""
        if isinstance(msg, str) and msg.strip():
            self.queue.append(msg)

    def _send_now(self, msg):
        """Envoi direct Telegram (interne)."""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": msg
        }

        try:
            r = requests.post(url, json=payload, timeout=5)
            r.raise_for_status()
        except Exception as e:
            print(f"[Telegram] Envoi erreur : {e}")

    # ---------------------------------------------------------
    # BOUCLE THREAD
    # ---------------------------------------------------------
    def run(self):
        while self.running:
            try:
                while self.queue:
                    msg = self.queue.pop(0)
                    self._send_now(msg)

            except Exception as ex:
                # Pour éviter l'arrêt total du thread
                print(f"[Telegram] Erreur interne dans loop : {ex}")

            time.sleep(1)

    # ---------------------------------------------------------
    # FERMETURE
    # ---------------------------------------------------------
    def stop(self):
        self.running = False

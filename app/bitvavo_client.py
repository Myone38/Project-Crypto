import json
import os
import requests
from python_bitvavo_api.bitvavo import Bitvavo


class BitvavoClient:
    """
    Wrapper REST Bitvavo avec fonctionnalités étendues :
      - get_wallet()
      - get_orders(status)
      - get_price_eur(asset)
      - Récupération automatique du rate-limit API

    Les infos de rate-limit sont récupérées via une requête REST brute
    (la librairie officielle ne renvoie pas les headers).
    """

    BASE_URL = "https://api.bitvavo.com/v2"

    def __init__(self):
        # ------------------------------------------------------
        # CHARGER LES CREDENTIALS
        # ------------------------------------------------------
        creds_path = os.path.join("config", "credentials.json")

        try:
            with open(creds_path, "r") as f:
                data = json.load(f)

            creds = data.get("bitvavo", {})
            api_key = creds.get("api_key")
            api_secret = creds.get("api_secret")

        except Exception as e:
            raise ValueError(f"[BitvavoClient] Impossible de lire {creds_path} : {e}")

        if not api_key or not api_secret:
            raise ValueError("[BitvavoClient] api_key/api_secret absents dans credentials.json")

        # ------------------------------------------------------
        # INITIALISER LE CLIENT OFFICIEL BITVAVO
        # ------------------------------------------------------
        self.client = Bitvavo({
            'APIKEY': api_key,
            'APISECRET': api_secret,
            'RESTURL': self.BASE_URL,
            'ACCESSWINDOW': 10000,
            'DEBUGGING': False
        })

        # ------------------------------------------------------
        # STOCKAGE RATE LIMIT
        # ------------------------------------------------------
        self.rate_limit_limit = None
        self.rate_limit_remaining = None
        self.rate_limit_resetat = None

    # ----------------------------------------------------------
    # MÉTHODE UTILITAIRE : récupérer rate-limit via une requête brute
    # ----------------------------------------------------------
    def _refresh_rate_limit(self):
        """Effectue un /time pour récupérer les headers de rate-limit."""
        try:
            url = f"{self.BASE_URL}/time"
            response = requests.get(url)
            self._update_rate_limit(response)
        except Exception:
            pass  # On ignore si erreur réseau ponctuelle

    def _update_rate_limit(self, response):
        """Extraction des headers rate-limit."""
        self.rate_limit_limit = response.headers.get("bitvavo-ratelimit-limit")
        self.rate_limit_remaining = response.headers.get("bitvavo-ratelimit-remaining")
        self.rate_limit_resetat = response.headers.get("bitvavo-ratelimit-resetat")

    # ----------------------------------------------------------
    # PUBLIC : obtenir rate-limit
    # ----------------------------------------------------------
    def get_rate_limit(self):
        """Retourne un dict lisible avec les infos de rate limiting."""
        # On rafraîchit à chaque appel
        self._refresh_rate_limit()

        print("RATE LIMIT →",
        "limit:", self.rate_limit_limit,
        "remaining:", self.rate_limit_remaining,
        "reset:", self.rate_limit_resetat)

        return {
            "limit": self.rate_limit_limit,
            "remaining": self.rate_limit_remaining,
            "reset_at": self.rate_limit_resetat
        }

    # ----------------------------------------------------------
    # WALLET
    # ----------------------------------------------------------
    def get_wallet(self):
        """Retourne [{symbol, available, inOrder}, ...]."""
        try:
            data = self.client.balance()
            self._refresh_rate_limit()  # On met aussi à jour après un appel officiel
            return data
        except Exception as e:
            print(f"[BitvavoClient] Erreur get_wallet : {e}")
            return None

    # ----------------------------------------------------------
    # ORDERS
    # ----------------------------------------------------------
    def get_orders(self, status="open"):
        """
        status = open | closed | all
        """
        try:
            if status == "open":
                data = self.client.ordersOpen()
            else:
                data = self.client.getOrders()

            self._refresh_rate_limit()
            return data
        except Exception as e:
            print(f"[BitvavoClient] Erreur get_orders : {e}")
            return None

    # ----------------------------------------------------------
    # PRIX EUR
    # ----------------------------------------------------------
    def get_price_eur(self, asset):
        """
        Renvoie le prix EUR du marché {asset}-EUR.
        """
        if asset == "EUR":
            return 1.0

        try:
            market = f"{asset}-EUR"
            data = self.client.tickerPrice({"market": market})

            self._refresh_rate_limit()

            if isinstance(data, dict) and "price" in data:
                return float(data["price"])

            return None

        except Exception as e:
            print(f"[BitvavoClient] Erreur get_price_eur : {e}")
            return None

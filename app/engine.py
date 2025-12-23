import threading
import time
from datetime import datetime

from app.telegram_thread import TelegramThread
from app.bitvavo_client import BitvavoClient


# ============================================================
#  STATE : stockage des données du moteur
# ============================================================
class EngineState:
    def __init__(self):
        self.running = False
        self.logs = []
        self.portfolio = []
        self.orders = []
        self.equity_history = []
        self.rate_limit = None

    def add_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.logs.append(entry)

        # On limite la taille
        if len(self.logs) > 500:
            self.logs.pop(0)


# ============================================================
#  ENGINE PRINCIPAL
# ============================================================
class Engine:
    def __init__(self):
        print(">>> ENGINE INSTANCE CREATED <<<")

        self.state = EngineState()
        self.lock = threading.Lock()

        # Init Bitvavo
        print(">>> INIT BITVAVO <<<")
        self.bitvavo = BitvavoClient()

        # Thread Telegram
        self.telegram = TelegramThread(self)
        self.telegram.start()

        self.thread = None

    # --------------------------------------------------------
    # START / STOP
    # --------------------------------------------------------
    def start(self):
        print(">>> ENGINE START CALLED <<<")

        if self.state.running:
            return

        self.state.running = True

        self.thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )

        print(">>> THREAD CREATED :", self.thread)
        self.thread.start()

        self.state.add_log("Moteur démarré.")
        self.telegram.send("🚀 Bot crypto démarré.")

    def stop(self):
        self.state.running = False
        self.state.add_log("Arrêt demandé.")
        self.telegram.send("🟥 Bot crypto arrêté.")
        time.sleep(0.5)

    # --------------------------------------------------------
    #  CALCUL EQUITY
    # --------------------------------------------------------
    def compute_real_equity(self):
        try:
            wallet = self.bitvavo.get_wallet()
            if not wallet:
                return None

            total = 0.0

            for item in wallet:
                symbol = item.get("symbol")
                available = float(item.get("available", 0))
                in_order = float(item.get("inOrder", 0))
                qty = available + in_order

                if symbol == "EUR":
                    total += qty
                    continue

                price = self.bitvavo.get_price_eur(symbol)
                if price:
                    total += qty * price

            return total

        except Exception as e:
            self.state.add_log(f"Erreur compute_real_equity : {e}")
            return None

    # --------------------------------------------------------
    #  BOUCLE PRINCIPALE
    # --------------------------------------------------------
    def _run_loop(self):
        print(">>> ENTERED RUN LOOP <<<")

        while self.state.running:
            try:
            # WALLET avec enrichissement
                wallet = self.bitvavo.get_wallet()
                print("WALLET:", wallet)

                if wallet:
                    # ✅ Enrichir chaque item avec la valeur en EUR
                    enriched_wallet = []
                    for item in wallet:
                        symbol = item.get("symbol")
                        available = float(item.get("available", 0))
                        in_order = float(item.get("inOrder", 0))
                        total_qty = available + in_order

                    # Calculer la valeur en EUR
                        if symbol == "EUR":
                            value_eur = total_qty
                        else:
                            try:
                                price = self.bitvavo.get_price_eur(symbol)
                                value_eur = total_qty * price if price else 0
                            except Exception as e:
                                print(f"Erreur prix {symbol}: {e}")
                                value_eur = 0

                    # Créer un nouvel item enrichi
                        enriched_item = item.copy()
                        enriched_item['total_qty'] = total_qty
                        enriched_item['value_eur'] = value_eur
                        enriched_wallet.append(enriched_item)

                    self.state.portfolio = enriched_wallet

                # ORDERS
                orders = self.bitvavo.get_orders("open")
                print("ORDERS:", orders)
                if orders:
                    self.state.orders = orders

                # EQUITY
                eq = self.compute_real_equity()
                print("EQ:", eq)

                if eq is not None:
                    self.state.equity_history.append(eq)
                    if len(self.state.equity_history) > 2000:
                        self.state.equity_history.pop(0)

                # RATE LIMITE
                try:
                    rate = self.bitvavo.get_rate_limit()
                    self.state.rate_limit = rate
                    print("RATE LIMIT:", rate)
                except Exception as e:
                    print(f"Erreur rate limit: {e}")

                self.state.add_log("Données mises à jour.")

            except Exception as e:
                self.state.add_log(f"Erreur moteur : {e}")

            time.sleep(3)

        self.state.add_log("Moteur stoppé proprement.")

# ============================================================
#  SINGLETON
# ============================================================
_engine_instance = None

def get_engine():
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = Engine()
    return _engine_instance

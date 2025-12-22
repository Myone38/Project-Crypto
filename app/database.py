"""
Database Manager pour Crypto Bot
Gestion centralisée de toutes les données persistantes
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import threading


class Database:
    """Gestionnaire de base de données SQLite pour le bot crypto"""
    
    def __init__(self, db_path="data/crypto_bot.db"):
        """Initialise la connexion et crée les tables"""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.lock = threading.Lock()
        self._create_tables()
        print(f"✅ Database initialisée : {db_path}")
    
    def _get_connection(self):
        """Crée une nouvelle connexion (thread-safe)"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def _create_tables(self):
        """Crée toutes les tables nécessaires"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # ============================================================
        # 1. HISTORIQUE EQUITY
        # ============================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                value REAL NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_equity_timestamp 
            ON equity_history(timestamp)
        ''')
        
        # ============================================================
        # 2. HISTORIQUE ORDRES
        # ============================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL,
                status TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME,
                filled_at DATETIME
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_market 
            ON orders_history(market)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_created 
            ON orders_history(created_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_status 
            ON orders_history(status)
        ''')
        
        # ============================================================
        # 3. BOUGIES (CANDLES)
        # ============================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(market, interval, timestamp)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_candles_market_interval 
            ON market_candles(market, interval)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_candles_timestamp 
            ON market_candles(timestamp)
        ''')
        
        # ============================================================
        # 4. INDICATEURS
        # ============================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                indicator_name TEXT NOT NULL,
                value REAL,
                value_json TEXT,
                UNIQUE(market, interval, timestamp, indicator_name)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_indicators_market 
            ON market_indicators(market, indicator_name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_indicators_timestamp 
            ON market_indicators(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    # ================================================================
    # MÉTHODES EQUITY
    # ================================================================
    
    def save_equity(self, value: float) -> bool:
        """Enregistre une valeur d'equity"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO equity_history (value) VALUES (?)",
                    (value,)
                )
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"❌ Erreur save_equity: {e}")
            return False
    
    def get_equity_history(self, hours: int = 24) -> List[Tuple[str, float]]:
        """Récupère l'historique equity sur X heures"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, value 
                FROM equity_history 
                WHERE timestamp >= datetime('now', ?)
                ORDER BY timestamp
            ''', (f'-{hours} hours',))
            
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            print(f"❌ Erreur get_equity_history: {e}")
            return []
    
    def get_equity_all(self) -> List[Tuple[str, float]]:
        """Récupère TOUT l'historique equity"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, value 
                FROM equity_history 
                ORDER BY timestamp
            ''')
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            print(f"❌ Erreur get_equity_all: {e}")
            return []
    
    # ================================================================
    # MÉTHODES ORDRES
    # ================================================================
    
    def save_order(self, order: Dict) -> bool:
        """Enregistre ou met à jour un ordre"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO orders_history 
                    (order_id, market, side, order_type, amount, price, status, 
                     created_at, updated_at, filled_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order.get('orderId'),
                    order.get('market'),
                    order.get('side'),
                    order.get('orderType'),
                    float(order.get('amount', 0)),
                    float(order.get('price', 0)) if order.get('price') else None,
                    order.get('status'),
                    order.get('created', datetime.now().isoformat()),
                    datetime.now().isoformat(),
                    order.get('filledAt')
                ))
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"❌ Erreur save_order: {e}")
            return False
    
    def get_orders_history(self, market: Optional[str] = None, 
                          status: Optional[str] = None,
                          days: int = 30) -> List[Dict]:
        """Récupère l'historique des ordres"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM orders_history 
                WHERE created_at >= datetime('now', ?)
            '''
            params = [f'-{days} days']
            
            if market:
                query += ' AND market = ?'
                params.append(market)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            
            cursor.execute(query, params)
            
            columns = [desc[0] for desc in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return result
        except Exception as e:
            print(f"❌ Erreur get_orders_history: {e}")
            return []
    
    # ================================================================
    # MÉTHODES CANDLES
    # ================================================================
    
    def save_candles(self, market: str, interval: str, candles: List[List]) -> int:
        """
        Enregistre des bougies (format Bitvavo)
        candles = [[timestamp, open, high, low, close, volume], ...]
        Retourne le nombre de bougies insérées
        """
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                inserted = 0
                for candle in candles:
                    try:
                        timestamp = datetime.fromtimestamp(candle[0] / 1000)
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO market_candles 
                            (market, interval, timestamp, open, high, low, close, volume)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            market,
                            interval,
                            timestamp,
                            float(candle[1]),  # open
                            float(candle[2]),  # high
                            float(candle[3]),  # low
                            float(candle[4]),  # close
                            float(candle[5])   # volume
                        ))
                        
                        if cursor.rowcount > 0:
                            inserted += 1
                            
                    except Exception as e:
                        print(f"⚠️ Erreur candle individuelle: {e}")
                        continue
                
                conn.commit()
                conn.close()
                return inserted
        except Exception as e:
            print(f"❌ Erreur save_candles: {e}")
            return 0
    
    def get_candles(self, market: str, interval: str, 
                   limit: int = 100) -> List[Dict]:
        """Récupère les dernières bougies"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume
                FROM market_candles
                WHERE market = ? AND interval = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (market, interval, limit))
            
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return list(reversed(result))  # Ordre chronologique
        except Exception as e:
            print(f"❌ Erreur get_candles: {e}")
            return []
    
    # ================================================================
    # MÉTHODES INDICATEURS
    # ================================================================
    
    def save_indicator(self, market: str, interval: str, 
                      timestamp: datetime, indicator_name: str,
                      value: Optional[float] = None,
                      value_dict: Optional[Dict] = None) -> bool:
        """Enregistre un indicateur calculé"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                value_json = json.dumps(value_dict) if value_dict else None
                
                cursor.execute('''
                    INSERT OR REPLACE INTO market_indicators 
                    (market, interval, timestamp, indicator_name, value, value_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (market, interval, timestamp, indicator_name, value, value_json))
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"❌ Erreur save_indicator: {e}")
            return False
    
    def get_indicators(self, market: str, interval: str,
                      indicator_name: str, limit: int = 100) -> List[Dict]:
        """Récupère les valeurs d'un indicateur"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, value, value_json
                FROM market_indicators
                WHERE market = ? AND interval = ? AND indicator_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (market, interval, indicator_name, limit))
            
            result = []
            for row in cursor.fetchall():
                item = {
                    'timestamp': row[0],
                    'value': row[1]
                }
                if row[2]:
                    item['data'] = json.loads(row[2])
                result.append(item)
            
            conn.close()
            return list(reversed(result))
        except Exception as e:
            print(f"❌ Erreur get_indicators: {e}")
            return []
    
    # ================================================================
    # MÉTHODES UTILITAIRES
    # ================================================================
    
    def get_stats(self) -> Dict:
        """Retourne des statistiques sur la DB"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            # Nombre d'equity points
            cursor.execute("SELECT COUNT(*) FROM equity_history")
            stats['equity_points'] = cursor.fetchone()[0]
            
            # Nombre d'ordres
            cursor.execute("SELECT COUNT(*) FROM orders_history")
            stats['orders_total'] = cursor.fetchone()[0]
            
            # Nombre de bougies par marché
            cursor.execute('''
                SELECT market, interval, COUNT(*) 
                FROM market_candles 
                GROUP BY market, interval
            ''')
            stats['candles'] = {f"{row[0]}_{row[1]}": row[2] 
                               for row in cursor.fetchall()}
            
            # Nombre d'indicateurs
            cursor.execute("SELECT COUNT(*) FROM market_indicators")
            stats['indicators_total'] = cursor.fetchone()[0]
            
            # Taille de la DB
            stats['db_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
            
            conn.close()
            return stats
        except Exception as e:
            print(f"❌ Erreur get_stats: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Nettoie les données anciennes"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cutoff = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
                
                # Nettoyer equity
                cursor.execute(
                    "DELETE FROM equity_history WHERE timestamp < ?",
                    (cutoff,)
                )
                equity_deleted = cursor.rowcount
                
                # Nettoyer bougies
                cursor.execute(
                    "DELETE FROM market_candles WHERE timestamp < ?",
                    (cutoff,)
                )
                candles_deleted = cursor.rowcount
                
                # Nettoyer indicateurs
                cursor.execute(
                    "DELETE FROM market_indicators WHERE timestamp < ?",
                    (cutoff,)
                )
                indicators_deleted = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                print(f"🗑️ Nettoyage effectué:")
                print(f"   • Equity: {equity_deleted} lignes")
                print(f"   • Candles: {candles_deleted} lignes")
                print(f"   • Indicators: {indicators_deleted} lignes")
                
                return True
        except Exception as e:
            print(f"❌ Erreur cleanup_old_data: {e}")
            return False


# ================================================================
# SINGLETON POUR USAGE GLOBAL
# ================================================================
_db_instance = None

def get_database() -> Database:
    """Retourne l'instance unique de la database"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
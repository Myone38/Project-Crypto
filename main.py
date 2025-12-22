# main.py - DASHBOARD CRYPTO BOT - Version finale corrigée
import dash
from dash import Dash, html, dcc, Input, Output, callback, dash_table, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import time
import sys
import traceback

# -------------------------------------------------------------------
# CONFIGURATION ET INITIALISATION
# -------------------------------------------------------------------
print("=" * 60)
print("🤖 CRYPTO BOT DASHBOARD - DASH VERSION")
print("=" * 60)

# Initialisation du moteur
ENGINE_INSTANCE = None
try:
    # Ajout du chemin courant pour l'import
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from app.engine import get_engine
    ENGINE_INSTANCE = get_engine()
    print(f"✅ Moteur initialisé avec succès")
    
    # Test des données initiales
    if hasattr(ENGINE_INSTANCE, 'state'):
        print(f"   • Points equity: {len(ENGINE_INSTANCE.state.equity_history)}")
        print(f"   • Items portfolio: {len(ENGINE_INSTANCE.state.portfolio)}")
        print(f"   • Ordres ouverts: {len(ENGINE_INSTANCE.state.orders)}")
        print(f"   • Statut: {'🟢 Actif' if ENGINE_INSTANCE.state.running else '🔴 Arrêté'}")
    else:
        print("   ⚠️ Structure 'state' non trouvée")
        
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("   Vérifiez que le fichier app/engine.py existe")
except Exception as e:
    print(f"❌ Erreur d'initialisation: {e}")
    traceback.print_exc()

print("-" * 60)

# -------------------------------------------------------------------
# FONCTIONS HELPER
# -------------------------------------------------------------------
def calculate_24h_variation(equity_history):
    """Calcule la variation sur 24h"""
    if not equity_history or len(equity_history) < 2:
        return None, None
    
    points_24h = 28800  # 24h à 3 secondes d'intervalle
    
    if len(equity_history) > points_24h:
        equity_24h_ago = equity_history[-points_24h]
    else:
        equity_24h_ago = equity_history[0]
    
    equity_now = equity_history[-1]
    change = equity_now - equity_24h_ago
    pct = (change / equity_24h_ago) * 100 if equity_24h_ago != 0 else 0
    
    return change, pct

def safe_float(value, default=0.0):
    """Convertit en float de manière sécurisée"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# -------------------------------------------------------------------
# APPLICATION DASH
# -------------------------------------------------------------------
app = Dash(__name__, suppress_callback_exceptions=True)

# -------------------------------------------------------------------
# STYLE CSS
# -------------------------------------------------------------------
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Crypto Bot Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            body {
                background-color: #f8f9fa;
                color: #333;
            }
            
            .main-container {
                display: flex;
                min-height: 100vh;
            }
            
            /* Sidebar */
            .sidebar {
                width: 280px;
                background: linear-gradient(180deg, #1a237e 0%, #283593 100%);
                color: white;
                padding: 25px 20px;
                box-shadow: 3px 0 15px rgba(0,0,0,0.1);
                position: fixed;
                height: 100vh;
                overflow-y: auto;
                z-index: 1000;
            }
            
            .sidebar h3 {
                color: #fff;
                margin-bottom: 10px;
                font-size: 1.4rem;
            }
            
            .sidebar h4 {
                color: #bbdefb;
                margin-top: 25px;
                margin-bottom: 15px;
                font-size: 1.1rem;
            }
            
            .sidebar hr {
                border-color: #3949ab;
                margin: 20px 0;
            }
            
            /* Contenu principal */
            .content {
                flex: 1;
                margin-left: 280px;
                padding: 25px;
            }
            
            /* Métriques */
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                margin: 25px 0;
            }
            
            .metric-card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                border-left: 5px solid #1f77b4;
                transition: transform 0.2s;
            }
            
            .metric-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 15px rgba(0,0,0,0.1);
            }
            
            .metric-card h4 {
                color: #555;
                margin-bottom: 10px;
                font-size: 1rem;
                font-weight: 600;
            }
            
            .metric-value {
                font-size: 2rem;
                font-weight: 700;
                color: #1a237e;
            }
            
            /* Boutons */
            .btn {
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                width: 100%;
                margin-bottom: 10px;
            }
            
            .btn-start {
                background: linear-gradient(135deg, #00c853 0%, #64dd17 100%);
                color: white;
            }
            
            .btn-stop {
                background: linear-gradient(135deg, #ff3d00 0%, #ff9100 100%);
                color: white;
            }
            
            .btn:hover {
                opacity: 0.9;
                transform: scale(1.02);
            }
            
            /* Graphique */
            .chart-container {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                margin: 20px 0;
            }
            
            /* Tableaux */
            .table-container {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                margin: 20px 0;
                overflow-x: auto;
            }
            
            /* Logs */
            .logs-container {
                background: #1e1e1e;
                color: #00ff00;
                border-radius: 8px;
                padding: 15px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                height: 300px;
                overflow-y: auto;
                white-space: pre-wrap;
                margin-top: 10px;
            }
            
            /* Statut */
            .status-running {
                color: #00e676;
                font-weight: bold;
                background: rgba(0, 230, 118, 0.1);
                padding: 8px 15px;
                border-radius: 20px;
                display: inline-block;
            }
            
            .status-stopped {
                color: #ff5252;
                font-weight: bold;
                background: rgba(255, 82, 82, 0.1);
                padding: 8px 15px;
                border-radius: 20px;
                display: inline-block;
            }
            
            /* Responsive */
            @media (max-width: 1200px) {
                .metrics-grid {
                    grid-template-columns: repeat(2, 1fr);
                }
            }
            
            @media (max-width: 768px) {
                .sidebar {
                    width: 100%;
                    position: relative;
                    height: auto;
                }
                
                .content {
                    margin-left: 0;
                }
                
                .metrics-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# -------------------------------------------------------------------
# LAYOUT DE L'APPLICATION
# -------------------------------------------------------------------
app.layout = html.Div([
    # Stockage des données moteur
    dcc.Store(
        id='engine-data-store',
        data={
            'equity_history': [],
            'portfolio': [],
            'orders': [],
            'logs': [],
            'running': False,
            'last_update': None
        }
    ),
    
    # Intervalle de rafraîchissement
    dcc.Interval(
        id='refresh-interval',
        interval=3000,  # 3 secondes
        n_intervals=0
    ),
    
    # Intervalle lent pour les logs (10 secondes)
    dcc.Interval(
        id='slow-refresh',
        interval=10000,
        n_intervals=0
    ),
    
    # Conteneur principal
    html.Div([
        # -----------------------------------------------------------
        # SIDEBAR
        # -----------------------------------------------------------
        html.Div([
            # Logo et titre
            html.Div([
                html.H3("🤖 Crypto Bot", style={'marginBottom': '5px'}),
                html.P("Dashboard de trading", style={'color': '#bbdefb', 'fontSize': '14px'})
            ]),
            
            html.Hr(),
            
            # Contrôles
            html.H4("🎮 Contrôles"),
            html.Div(id='status-display', style={'margin': '15px 0'}),
            
            html.Div([
                html.Button("▶️ Démarrer le Bot", 
                          id='start-btn', 
                          n_clicks=0,
                          className='btn btn-start'),
                html.Button("⏹️ Arrêter le Bot", 
                          id='stop-btn', 
                          n_clicks=0,
                          className='btn btn-stop')
            ]),
            
            html.Hr(),
            
            # Stats rapides
            html.H4("📊 Statistiques"),
            html.Div(id='sidebar-stats', style={'marginTop': '10px'}),
            
            html.Hr(),
            
            # Dernière mise à jour
            html.Div([
                html.P("Dernière actualisation:", style={'color': '#bbdefb', 'fontSize': '12px'}),
                html.Div(id='last-update', style={'fontSize': '14px', 'fontWeight': 'bold'})
            ]),
            
            html.Hr(),
            
            # Informations système
            html.Div([
                html.P("Système", style={'color': '#bbdefb', 'fontSize': '12px'}),
                html.Div(id='system-info', style={'fontSize': '11px', 'color': '#90caf9'})
            ])
            
        ], className='sidebar'),
        
        # -----------------------------------------------------------
        # CONTENU PRINCIPAL
        # -----------------------------------------------------------
        html.Div([
            # Header
            html.Div([
                html.H1("📊 Tableau de Bord Crypto Bot", 
                       style={'color': '#1a237e', 'marginBottom': '10px'}),
                html.P("Surveillance en temps réel de votre bot de trading",
                      style={'color': '#666', 'fontSize': '16px'})
            ]),
            
            # Métriques principales
            html.Div([
                html.Div([
                    html.H4("💰 Equity Total"),
                    html.Div(id='equity-metric', className='metric-value',
                            children="Chargement...")
                ], className='metric-card'),
                
                html.Div([
                    html.H4("📈 Variation 24h"),
                    html.Div(id='variation-metric', className='metric-value',
                            children="N/A")
                ], className='metric-card'),
                
                html.Div([
                    html.H4("📋 Ordres Actifs"),
                    html.Div(id='orders-metric', className='metric-value',
                            children="0")
                ], className='metric-card'),
                
                html.Div([
                    html.H4("🪙 Actifs Détenus"),
                    html.Div(id='assets-metric', className='metric-value',
                            children="0")
                ], className='metric-card')
            ], className='metrics-grid'),
            
            # Graphique et stats
            html.Div([
                html.Div([
                    html.H3("📈 Évolution de l'Equity"),
                    dcc.Graph(id='equity-chart', style={'height': '400px'})
                ], className='chart-container'),
                
                html.Div(id='equity-stats', style={'marginTop': '20px'})
            ]),
            
            # Portfolio et Ordres (côte à côte)
            html.Div([
                html.Div([
                    html.H3("💰 Portfolio Bitvavo"),
                    html.Div(id='portfolio-container',
                            style={'marginTop': '15px'})
                ], className='table-container', style={'flex': 2, 'marginRight': '20px'}),
                
                html.Div([
                    html.H3("📄 Ordres Ouverts"),
                    html.Div(id='orders-container',
                            style={'marginTop': '15px'})
                ], className='table-container', style={'flex': 1})
            ], style={'display': 'flex', 'marginTop': '30px'}),
            
            # Logs
            html.Div([
                html.H3("📜 Journal d'activité"),
                html.Div(id='logs-container', className='logs-container')
            ], style={'marginTop': '30px'}),
            
            # Footer
            html.Div([
                html.Hr(),
                html.Div(id='footer', style={
                    'textAlign': 'center',
                    'color': '#666',
                    'fontSize': '12px',
                    'marginTop': '20px'
                })
            ])
            
        ], className='content')
    ], className='main-container')
])

# -------------------------------------------------------------------
# CALLBACK 1: Mise à jour des données du moteur
# -------------------------------------------------------------------
@app.callback(
    [Output('engine-data-store', 'data'),
     Output('status-display', 'children'),
     Output('last-update', 'children'),
     Output('system-info', 'children')],
    [Input('refresh-interval', 'n_intervals'),
     Input('start-btn', 'n_clicks'),
     Input('stop-btn', 'n_clicks')],
    [State('engine-data-store', 'data')]
)
def update_engine_state(n_intervals, start_clicks, stop_clicks, stored_data):
    """Récupère les données du moteur et gère les contrôles"""
    
    # Initialiser les données si nécessaire
    if stored_data is None:
        stored_data = {
            'equity_history': [],
            'portfolio': [],
            'orders': [],
            'logs': [],
            'running': False,
            'last_update': None
        }
    
    # Vérifier quel bouton a été cliqué
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # Gérer les actions Start/Stop
    if triggered_id == 'start-btn' and ENGINE_INSTANCE:
        try:
            ENGINE_INSTANCE.start()
            print("▶️ Bouton Start cliqué")
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Erreur Start: {e}")
    
    elif triggered_id == 'stop-btn' and ENGINE_INSTANCE:
        try:
            ENGINE_INSTANCE.stop()
            print("⏹️ Bouton Stop cliqué")
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Erreur Stop: {e}")
    
    # Récupérer les données du moteur
    new_data = stored_data.copy()
    
    try:
        if ENGINE_INSTANCE and hasattr(ENGINE_INSTANCE, 'state'):
            # Récupération sécurisée des données
            state = ENGINE_INSTANCE.state
            
            # Equity history
            if hasattr(state, 'equity_history'):
                try:
                    # Convertir en floats pour sécurité
                    equity_vals = []
                    for val in state.equity_history:
                        try:
                            equity_vals.append(float(val))
                        except:
                            equity_vals.append(0.0)
                    new_data['equity_history'] = equity_vals
                except:
                    new_data['equity_history'] = []
            
            # Portfolio
            if hasattr(state, 'portfolio'):
                new_data['portfolio'] = state.portfolio.copy() if state.portfolio else []
            
            # Orders
            if hasattr(state, 'orders'):
                new_data['orders'] = state.orders.copy() if state.orders else []
            
            # Logs
            if hasattr(state, 'logs'):
                new_data['logs'] = state.logs.copy() if state.logs else []
            
            # Running status
            if hasattr(state, 'running'):
                new_data['running'] = state.running

            #  Rate limit
            if hasattr(state, 'rate_limit'):
                new_data['rate_limit'] = state.rate_limit    
            
            new_data['last_update'] = datetime.now().isoformat()
            
    except Exception as e:
        print(f"⚠️ Erreur récupération données: {e}")
    
    # Afficher le statut
    if new_data.get('running', False):
        status_display = html.Span("🟢 BOT ACTIF", className='status-running')
    else:
        status_display = html.Span("🔴 BOT ARRÊTÉ", className='status-stopped')
    
    # Dernière mise à jour
    last_update = datetime.now().strftime('%H:%M:%S')
    last_update_display = f"{last_update} (auto-refresh 3s)"
    
    # Info système
    system_info = [
        f"Python {sys.version.split()[0]}",
        html.Br(),
        f"Dash {dash.__version__}",
        html.Br(),
        f"Equity points: {len(new_data['equity_history'])}",
        html.Br(),
        f"Log entries: {len(new_data['logs'])}"
    ]
    
    return new_data, status_display, last_update_display, system_info

# -------------------------------------------------------------------
# CALLBACK 2: Mise à jour de l'interface
# -------------------------------------------------------------------
@app.callback(
    [Output('equity-metric', 'children'),
     Output('variation-metric', 'children'),
     Output('orders-metric', 'children'),
     Output('assets-metric', 'children'),
     Output('equity-chart', 'figure'),
     Output('equity-stats', 'children'),
     Output('portfolio-container', 'children'),
     Output('orders-container', 'children'),
     Output('logs-container', 'children'),
     Output('sidebar-stats', 'children'),
     Output('footer', 'children')],
    [Input('engine-data-store', 'data'),
     Input('slow-refresh', 'n_intervals')]
)
def update_dashboard_ui(engine_data, slow_refresh):
    """Met à jour tous les éléments de l'interface"""
    
    # Données par défaut en cas d'erreur
    default_values = {
        'equity': "Chargement...",
        'variation': "N/A",
        'orders': "0",
        'assets': "0",
        'figure': go.Figure(),
        'stats': html.P("En attente de données..."),
        'portfolio': html.P("⏳ Chargement du portfolio..."),
        'orders_display': html.P("✅ Aucun ordre ouvert"),
        'logs': html.P("📭 Aucun log disponible"),
        'sidebar_stats': html.Div(),
        'footer': "Crypto Bot Dashboard v1.0 • Dash"
    }
    
    try:
        # Vérification des données d'entrée
        if not engine_data or not isinstance(engine_data, dict):
            print("⚠️ engine_data invalide")
            return list(default_values.values())
        
        # Extraction sécurisée des données
        equity_history = engine_data.get('equity_history', [])
        portfolio = engine_data.get('portfolio', [])
        orders = engine_data.get('orders', [])
        logs = engine_data.get('logs', [])
        rate_limit = engine_data.get('rate_limit')
        
        # -------------------------------------------------------------------
        # 1. MÉTRIQUES PRINCIPALES
        # -------------------------------------------------------------------
        
        # Equity total
        if equity_history and len(equity_history) > 0:
            try:
                last_equity = safe_float(equity_history[-1])
                equity_display = f"{last_equity:,.2f} €"
            except:
                equity_display = "Erreur"
        else:
            equity_display = "En attente..."
        
        # Variation 24h
        variation_display = "N/A"
        if len(equity_history) >= 2:
            try:
                change, pct = calculate_24h_variation(equity_history)
                if change is not None and pct is not None:
                    color = "green" if change >= 0 else "red"
                    variation_display = html.Span([
                        f"{change:+,.2f} € ",
                        html.Span(f"({pct:+.2f}%)", style={'color': color, 'fontSize': '14px'})
                    ])
                else:
                    # Variation depuis le début
                    if equity_history[0] != 0:
                        change_total = equity_history[-1] - equity_history[0]
                        pct_total = (change_total / equity_history[0]) * 100
                        color = "green" if change_total >= 0 else "red"
                        variation_display = html.Span([
                            f"{change_total:+,.2f} € ",
                            html.Span(f"({pct_total:+.2f}%)", style={'color': color, 'fontSize': '14px'})
                        ])
            except Exception as e:
                variation_display = "Calcul erreur"
        
        # Nombre d'ordres et d'actifs
        nb_orders = len(orders) if isinstance(orders, list) else 0
        nb_assets = len(portfolio) if isinstance(portfolio, list) else 0
        
        # -------------------------------------------------------------------
        # 2. GRAPHIQUE
        # -------------------------------------------------------------------
        fig = go.Figure()
        
        if equity_history and len(equity_history) > 0:
            try:
                # Créer les timestamps
                nb_points = len(equity_history)
                now = datetime.now()
                timestamps = [now - timedelta(seconds=3 * (nb_points - i - 1)) 
                            for i in range(nb_points)]
                
                # Créer la trace
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=equity_history,
                    mode='lines',
                    line=dict(color='#1f77b4', width=3),
                    name='Equity',
                    fill='tozeroy',
                    fillcolor='rgba(31, 119, 180, 0.1)'
                ))
                
                # Ligne de tendance (optionnelle)
                if len(equity_history) > 10:
                    try:
                        import numpy as np
                        x_vals = np.arange(len(equity_history))
                        z = np.polyfit(x_vals, equity_history, 1)
                        p = np.poly1d(z)
                        fig.add_trace(go.Scatter(
                            x=timestamps,
                            y=p(x_vals),
                            mode='lines',
                            line=dict(color='red', width=2, dash='dash'),
                            name='Tendance'
                        ))
                    except:
                        pass
                
                # Configuration
                fig.update_layout(
                    height=400,
                    showlegend=True,
                    legend=dict(x=0.02, y=0.98),
                    margin=dict(l=40, r=40, t=40, b=40),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    xaxis=dict(
                        title='Heure',
                        tickformat='%H:%M',
                        gridcolor='#f0f0f0',
                        showline=True,
                        linecolor='#ddd'
                    ),
                    yaxis=dict(
                        title='Equity (€)',
                        gridcolor='#f0f0f0',
                        showline=True,
                        linecolor='#ddd'
                    )
                )
                
            except Exception as e:
                print(f"⚠️ Erreur création graphique: {e}")
                fig.update_layout(title="Erreur d'affichage")
        
        else:
            # Graphique vide
            fig.update_layout(
                height=400,
                title="En attente de données...",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                annotations=[dict(
                    text="Aucune donnée disponible",
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=16)
                )]
            )
        
        # -------------------------------------------------------------------
        # 3. STATISTIQUES EQUITY
        # -------------------------------------------------------------------
        stats_content = None  # ✅ Initialisation

        if equity_history and len(equity_history) > 0:
            try:
                # Utiliser les mêmes données que le graphique (24h glissantes)
                points_24h = 28800  # 24h à 3 secondes d'intervalle
                if len(equity_history) > points_24h:
                    equity_24h = equity_history[-points_24h:]
                else:
                    equity_24h = equity_history
                
                equity_floats = [safe_float(x) for x in equity_24h]
                min_eq = min(equity_floats)
                max_eq = max(equity_floats)
                avg_eq = sum(equity_floats) / len(equity_floats)
                last_eq = equity_floats[-1]
                
                stats_content = html.Div([
                    html.Div([
                        html.P("Minimum 24h", style={'color': '#666', 'fontSize': '12px'}),
                        html.H4(f"{min_eq:,.2f} €", style={'color': '#ff3d00'})
                    ], style={'textAlign': 'center', 'padding': '10px', 'background': '#fff3e0', 'borderRadius': '8px', 'flex': 1}),
                    
                    html.Div([
                        html.P("Maximum 24h", style={'color': '#666', 'fontSize': '12px'}),
                        html.H4(f"{max_eq:,.2f} €", style={'color': '#00c853'})
                    ], style={'textAlign': 'center', 'padding': '10px', 'background': '#e8f5e8', 'borderRadius': '8px', 'flex': 1}),
                    
                    html.Div([
                        html.P("Moyenne 24h", style={'color': '#666', 'fontSize': '12px'}),
                        html.H4(f"{avg_eq:,.2f} €", style={'color': '#1a237e'})
                    ], style={'textAlign': 'center', 'padding': '10px', 'background': '#e8eaf6', 'borderRadius': '8px', 'flex': 1}),
                    
                    html.Div([
                        html.P("Actuel", style={'color': '#666', 'fontSize': '12px'}),
                        html.H4(f"{last_eq:,.2f} €", style={'color': '#ff9800'})
                    ], style={'textAlign': 'center', 'padding': '10px', 'background': '#fff8e1', 'borderRadius': '8px', 'flex': 1})
                ], style={'display': 'flex', 'gap': '15px', 'marginTop': '15px'})
                
            except Exception as e:
                print(f"⚠️ Erreur calcul stats equity: {e}")
                stats_content = html.P(f"Erreur calcul stats: {str(e)[:50]}", style={'color': 'red'})
        else:
            stats_content = html.P("En attente de données pour les statistiques", 
                                style={'color': '#666', 'fontStyle': 'italic'})
                            
        # -------------------------------------------------------------------
        # 4. TABLEAU DU PORTFOLIO
        # -------------------------------------------------------------------
        if portfolio and isinstance(portfolio, list) and len(portfolio) > 0:
            try:
                portfolio_data = []
                for item in portfolio:
                    if isinstance(item, dict):
                        symbol = item.get('symbol', 'N/A')
                        available = safe_float(item.get('available', 0))
                        in_order = safe_float(item.get('inOrder', 0))
                        total = safe_float(item.get('total_qty', available + in_order))

                        # ✅ Récupérer directement la valeur calculée par l'engine
                        value_eur = safe_float(item.get('value_eur', 0))


                        portfolio_data.append({
                            'Asset': symbol,
                            'Disponible': f"{available:.8f}",
                            'En ordre': f"{in_order:.8f}",
                            'Total': f"{total:.8f}",
                            'Valeur €': f"{value_eur:.2f} €"
                        })
                
                if portfolio_data:
                    portfolio_table = dash_table.DataTable(
                        data=portfolio_data,
                        columns=[
                            {'name': 'Asset', 'id': 'Asset'},
                            {'name': 'Disponible', 'id': 'Disponible'},
                            {'name': 'En ordre', 'id': 'En ordre'},
                            {'name': 'Total', 'id': 'Total'},
                            {'name': 'Valeur €', 'id': 'Valeur €'}
                        ],
                        style_table={'overflowX': 'auto'},
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px',
                            'fontSize': '13px',
                            'minWidth': '100px'
                        },
                        style_cell_conditional=[  # ✅ AJOUTER CECI
                            {
                            'if': {'column_id': 'Asset'},
                            'width': '100px',
                            'maxWidth': '100px'
                            }
                        ],
                        style_header={
                            'fontWeight': 'bold',
                            'backgroundColor': '#f5f5f5',
                            'borderBottom': '2px solid #ddd'
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': '#f9f9f9'
                            }
                        ]
                    )
                else:
                    portfolio_table = html.P("Format de données invalide")
                    
            except Exception as e:
                portfolio_table = html.P(f"Erreur portfolio: {str(e)[:50]}")
        else:
            portfolio_table = html.P("⏳ Aucun actif dans le portfolio", 
                                   style={'color': '#666', 'fontStyle': 'italic'})
        
        # -------------------------------------------------------------------
        # 5. ORDRES OUVERTES
        # -------------------------------------------------------------------
        if orders and isinstance(orders, list) and len(orders) > 0:
            try:
                orders_data = []
                for order in orders:
                    if isinstance(order, dict):
                        orders_data.append({
                            'Market': order.get('market', 'N/A'),
                            'Side': order.get('side', 'N/A'),
                            'Type': order.get('orderType', 'N/A'),
                            'Amount': order.get('amount', 'N/A'),
                            'Price': order.get('price', 'N/A'),
                            'Status': order.get('status', 'N/A')
                        })
                
                if orders_data:
                    orders_table = dash_table.DataTable(
                        data=orders_data,
                        columns=[{'name': col, 'id': col} for col in 
                                ['Market', 'Side', 'Type', 'Amount', 'Price', 'Status']],
                        style_table={'overflowX': 'auto'},
                        style_cell={
                            'padding': '8px',
                            'fontSize': '12px',
                            'minWidth': '80px'
                        },
                        style_header={
                            'fontWeight': 'bold',
                            'backgroundColor': '#f0f7ff'
                        },
                        style_data_conditional=[
                            {
                                'if': {'column_id': 'Side', 'filter_query': '{Side} eq "buy"'},
                                'color': 'green',
                                'fontWeight': 'bold'
                            },
                            {
                                'if': {'column_id': 'Side', 'filter_query': '{Side} eq "sell"'},
                                'color': 'red',
                                'fontWeight': 'bold'
                            }
                        ]
                    )
                else:
                    orders_table = html.P("Format de données invalide")
                    
            except Exception as e:
                orders_table = html.P(f"Erreur orders: {str(e)[:50]}")
        else:
            orders_table = html.P("✅ Aucun ordre ouvert", 
                                style={'color': 'green', 'fontStyle': 'italic'})
        
        # -------------------------------------------------------------------
        # 6. LOGS
        # -------------------------------------------------------------------
        if logs and isinstance(logs, list) and len(logs) > 0:
            try:
                # Prendre les 15 derniers logs
                recent_logs = logs[-15:] if len(logs) > 15 else logs
                logs_content = []
                
                for i, log in enumerate(recent_logs):
                    if isinstance(log, str):
                        # Colorisation basique
                        log_lower = log.lower()
                        if 'error' in log_lower or 'failed' in log_lower:
                            color = '#ff5252'
                        elif 'success' in log_lower or 'executed' in log_lower:
                            color = '#00e676'
                        elif 'buy' in log_lower:
                            color = '#00c853'
                        elif 'sell' in log_lower:
                            color = '#ff3d00'
                        elif 'warning' in log_lower:
                            color = '#ff9800'
                        else:
                            color = '#ffffff'
                        
                        logs_content.append(
                            html.Div([
                                html.Span(f"[{len(logs)-len(recent_logs)+i+1:04d}] ", 
                                         style={'color': '#90caf9'}),
                                html.Span(log, style={'color': color})
                            ], style={'marginBottom': '3px', 'fontFamily': 'monospace'})
                        )
                
                if logs_content:
                    logs_display = html.Div(logs_content)
                else:
                    logs_display = html.P("Aucun log valide")
                    
            except Exception as e:
                logs_display = html.P(f"Erreur logs: {str(e)[:50]}")
        else:
            logs_display = html.P("📭 Aucun log disponible", 
                                style={'color': '#666', 'fontStyle': 'italic'})
        
        # -------------------------------------------------------------------
        # 7. STATS SIDEBAR
        # -------------------------------------------------------------------
        sidebar_stats = html.Div([
            html.Div([
                html.Span("📊 Points Equity: ", 
                         style={'fontWeight': 'bold', 'color': '#bbdefb'}),
                html.Span(str(len(equity_history)))
            ], style={'marginBottom': '10px'}),
            
            html.Div([
                html.Span("🪙 Actifs différents: ", 
                         style={'fontWeight': 'bold', 'color': '#bbdefb'}),
                html.Span(str(nb_assets))
            ], style={'marginBottom': '10px'}),
            
            html.Div([
                html.Span("📋 Ordres actifs: ", 
                         style={'fontWeight': 'bold', 'color': '#bbdefb'}),
                html.Span(str(nb_orders))
            ], style={'marginBottom': '10px'}),
            
            html.Div([
                html.Span("📝 Entrées logs: ", 
                         style={'fontWeight': 'bold', 'color': '#bbdefb'}),
                html.Span(str(len(logs)))
            ])
        ])

        # Dans la section "7. STATS SIDEBAR", remplacer par :

        # -------------------------------------------------------------------
        # 7. STATS SIDEBAR avec RATE LIMIT
        # -------------------------------------------------------------------
        # Calcul du rate limit
        rate_limit_display = None
        if rate_limit and isinstance(rate_limit, dict):
            try:
                limit = rate_limit.get('limit')
                remaining = rate_limit.get('remaining')
        
                if limit and remaining:
                    limit_int = int(limit)
                    remaining_int = int(remaining)
                    used = limit_int - remaining_int
                    percentage = (used / limit_int) * 100 if limit_int > 0 else 0
            
                # Déterminer la couleur selon le niveau
                if percentage < 70:
                    color = '#00e676'  # Vert
                    status = '✅'
                elif percentage < 90:
                    color = '#ff9800'  # Orange
                    status = '⚠️'
                else:
                    color = '#ff5252'  # Rouge
                    status = '🚨'
            
                rate_limit_display = html.Div([
                    html.Div([
                        html.Span(f"{status} Rate Limit API: ", 
                                 style={'fontWeight': 'bold', 'color': '#bbdefb'}),
                        html.Span(f"{remaining}/{limit}", 
                                 style={'color': color, 'fontWeight': 'bold'})
                    ], style={'marginBottom': '5px'}),
                    html.Div([
                        html.Div(
                            style={
                                'width': f'{percentage}%',
                                'height': '8px',
                                'backgroundColor': color,
                                'borderRadius': '4px',
                                'transition': 'width 0.3s'
                            }
                        )
                    ], style={
                        'width': '100%',
                        'height': '8px',
                        'backgroundColor': '#3949ab',
                        'borderRadius': '4px',
                        'marginBottom': '10px'
                    })
                ])
            except Exception as e:
                print(f"Erreur rate limit display: {e}")

        sidebar_stats = html.Div([
        html.Div([
            html.Span("📊 Points Equity: ", 
                     style={'fontWeight': 'bold', 'color': '#bbdefb'}),
            html.Span(str(len(equity_history)))
        ], style={'marginBottom': '10px'}),
    
        html.Div([
            html.Span("🪙 Actifs différents: ", 
                     style={'fontWeight': 'bold', 'color': '#bbdefb'}),
            html.Span(str(nb_assets))
        ], style={'marginBottom': '10px'}),
    
        html.Div([
            html.Span("📋 Ordres actifs: ", 
                     style={'fontWeight': 'bold', 'color': '#bbdefb'}),
            html.Span(str(nb_orders))
        ], style={'marginBottom': '10px'}),
    
        html.Div([
            html.Span("📝 Entrées logs: ", 
                     style={'fontWeight': 'bold', 'color': '#bbdefb'}),
            html.Span(str(len(logs)))
        ], style={'marginBottom': '15px'}),  # ✅ Plus d'espace avant rate limit
    
        html.Hr(style={'borderColor': '#3949ab', 'margin': '10px 0'}),  # ✅ Séparateur
    
    # ✅ AJOUTER LE RATE LIMIT ICI
    rate_limit_display if rate_limit_display else html.Div([
        html.Span("⚡ Rate Limit API: ", 
                 style={'fontWeight': 'bold', 'color': '#bbdefb'}),
        html.Span("N/A", style={'color': '#90caf9'})
    ])
])
        
        # -------------------------------------------------------------------
        # 8. FOOTER
        # -------------------------------------------------------------------
        now = datetime.now()
        footer_text = [
            f"Crypto Bot Dashboard v1.0 • ",
            html.Span("Dash ", style={'color': '#1f77b4', 'fontWeight': 'bold'}),
            f"• {now.strftime('%d/%m/%Y %H:%M:%S')} • ",
            html.Span("🟢 Connecté" if ENGINE_INSTANCE else "🔴 Déconnecté", 
                     style={'color': 'green' if ENGINE_INSTANCE else 'red'})
        ]
        
        # -------------------------------------------------------------------
        # RETOUR DES VALEURS
        # -------------------------------------------------------------------
        return [
            equity_display,      # 1 - equity-metric
            variation_display,   # 2 - variation-metric
            str(nb_orders),      # 3 - orders-metric
            str(nb_assets),      # 4 - assets-metric
            fig,                 # 5 - equity-chart
            stats_content,       # 6 - equity-stats
            portfolio_table,     # 7 - portfolio-container
            orders_table,        # 8 - orders-container
            logs_display,        # 9 - logs-container
            sidebar_stats,       # 10 - sidebar-stats
            footer_text          # 11 - footer
        ]
        
    except Exception as e:
        print(f"❌ ERREUR dans update_dashboard_ui: {e}")
        import traceback
        traceback.print_exc()
        
        # Retourner des valeurs par défaut en cas d'erreur
        error_fig = go.Figure()
        error_fig.update_layout(
            height=400,
            title="Erreur de chargement",
            annotations=[dict(
                text=f"Erreur: {str(e)[:100]}",
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14, color="red")
            )]
        )
        
        return [
            "Erreur",           # 1 - equity-metric
            "Erreur",           # 2 - variation-metric
            "0",                # 3 - orders-metric
            "0",                # 4 - assets-metric
            error_fig,          # 5 - equity-chart
            html.P(f"Erreur: {str(e)[:50]}"),  # 6 - equity-stats
            html.P("Erreur chargement portfolio"),  # 7 - portfolio-container
            html.P("Erreur chargement ordres"),     # 8 - orders-container
            html.P(f"Erreur: {str(e)[:50]}"),       # 9 - logs-container
            html.Div("Erreur stats"),               # 10 - sidebar-stats
            "Dashboard en erreur - Vérifiez les logs"  # 11 - footer
        ]

# -------------------------------------------------------------------
# LANCEMENT DE L'APPLICATION
# -------------------------------------------------------------------
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 LANCEMENT DU DASHBOARD CRYPTO BOT")
    print("=" * 60)
    
    if ENGINE_INSTANCE:
        print("✅ Moteur de trading initialisé")
        print(f"   • Type: {type(ENGINE_INSTANCE).__name__}")
        
        # Test des données initiales
        try:
            if hasattr(ENGINE_INSTANCE, 'state'):
                state = ENGINE_INSTANCE.state
                print(f"   • Statut: {'🟢 RUNNING' if getattr(state, 'running', False) else '🔴 STOPPED'}")
                print(f"   • Historique equity: {len(getattr(state, 'equity_history', []))} points")
                print(f"   • Portfolio: {len(getattr(state, 'portfolio', []))} actifs")
                print(f"   • Ordres: {len(getattr(state, 'orders', []))} ouverts")
        except Exception as e:
            print(f"   ⚠️ Erreur vérification: {e}")
    else:
        print("⚠️  Moteur non initialisé - Mode démo activé")
        print("   Le dashboard fonctionnera avec des données simulées")
    
    print("\n📊 Accès au dashboard:")
    print("   ► http://localhost:8050")
    print("\n⚙️  Configuration:")
    print("   • Rafraîchissement: 3 secondes")
    print("   • Port: 8050")
    print("   • Debug: Activé")
    print("=" * 60 + "\n")
    
    # Lancement avec app.run() comme demandé
    app.run(
        debug=True,
        host='127.0.0.1',
        port=8050,
        dev_tools_ui=True,
        dev_tools_hot_reload=True,
        dev_tools_hot_reload_interval=1,
        dev_tools_silence_routes_logging=False
    )
import os

class AlpacaTrader:
    def __init__(self):
        self.api_key = os.environ.get("ALPACA_API_KEY", "MOCK_KEY")
        self.api_secret = os.environ.get("ALPACA_SECRET_KEY", "MOCK_SECRET")
        self.base_url = "https://paper-api.alpaca.markets"

    def process_alert(self, alert_data):
        print(f"[TRADING BOT] 📊 Réception de l'alerte OSINT : Niveau {alert_data.get('risk_level')}")
        if alert_data.get('impacted_sector') == "Semi-conducteurs" and alert_data.get('risk_level') == "Critique":
            print("[TRADING BOT] 📉 Signal de crise détecté. VENTE à découvert de l'ETF Semi-conducteurs (SOXX).")
            self.place_order("SOXX", 10, "sell", "market")
            print("[TRADING BOT] 📈 Signal d'opportunité. ACHAT de couverture sur la logistique maritime (ZIM).")
            self.place_order("ZIM", 50, "buy", "market")
        else:
            print("[TRADING BOT] 💤 Pas de signal de trading asymétrique. Standby.")

    def place_order(self, symbol, qty, side, order_type):
        print(f"[TRADING BOT] ⚡ EXÉCUTION (PAPER TRADING) -> {side.upper()} {qty} actions de {symbol} au prix {order_type}")
        # Code réel commenté : self.api.submit_order(symbol=symbol, qty=qty, side=side, type=order_type, time_in_force='gtc')

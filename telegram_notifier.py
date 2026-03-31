# notifications/telegram_notifier.py

import requests
import json

PRICE_THRESHOLDS = [150000, 100000, 90000]  # ₹1.5L, ₹1L, ₹90K

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        return response.json()

    def check_threshold_alerts(self, laptop: dict, current_price: float):
        """
        Fire an alert when a laptop's price crosses below
        any of the defined thresholds (₹1.5L, ₹1L, ₹90K).
        """
        alerts = []
        for threshold in PRICE_THRESHOLDS:
            if current_price <= threshold:
                label = self._format_price(threshold)
                alerts.append((threshold, label))

        if not alerts:
            return

        # Alert for the lowest threshold crossed
        lowest_threshold, label = min(alerts, key=lambda x: x[0])

        message = (
            f"🚨 <b>Price Alert — Under {label}!</b>\n\n"
            f"💻 <b>{laptop['brand']} {laptop['series']}</b>\n"
            f"📋 {laptop.get('model_name', 'N/A')}\n"
            f"💰 Current Price: <b>{self._format_price(current_price)}</b>\n"
            f"🏷️ Threshold Crossed: {label}\n"
            f"🔗 {laptop.get('url', '')}"
        )
        self.send_message(message)

    def check_price_drop(self, laptop: dict, old_price: float, new_price: float):
        """Alert on any price drop (existing logic)."""
        if new_price >= old_price:
            return

        drop_amount = old_price - new_price
        drop_pct = (drop_amount / old_price) * 100

        message = (
            f"📉 <b>Price Drop!</b>\n\n"
            f"💻 <b>{laptop['brand']} {laptop['series']}</b>\n"
            f"📋 {laptop.get('model_name', 'N/A')}\n"
            f"💰 {self._format_price(old_price)} → <b>{self._format_price(new_price)}</b>\n"
            f"📊 Drop: ₹{drop_amount:,.0f} ({drop_pct:.1f}% off)\n"
            f"🔗 {laptop.get('url', '')}"
        )
        self.send_message(message)

    def check_back_in_stock(self, laptop: dict, price: float):
        """Alert when a previously out-of-stock laptop is available."""
        message = (
            f"✅ <b>Back in Stock!</b>\n\n"
            f"💻 <b>{laptop['brand']} {laptop['series']}</b>\n"
            f"📋 {laptop.get('model_name', 'N/A')}\n"
            f"💰 Price: <b>{self._format_price(price)}</b>\n"
            f"🔗 {laptop.get('url', '')}"
        )
        self.send_message(message)

    @staticmethod
    def _format_price(price: float) -> str:
        if price >= 100000:
            return f"₹{price/100000:.1f}L"
        return f"₹{price/1000:.0f}K"

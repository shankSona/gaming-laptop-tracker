import os
import requests

class TelegramNotifier:
    def __init__(self):
        self.token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.chat_id = os.environ["TELEGRAM_CHAT_ID"]

    def send(self, message: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        requests.post(url, json={
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })

    def send_price_drops(self, drops: list):
        if not drops: return
        lines = ["🔥 <b>Gaming Laptop Price Drops!</b>\n"]
        for d in drops:
            lines.append(
                f"💸 <b>{d['name']}</b>\n"
                f"   ₹{d['old_price']:,.0f} → ₹{d['new_price']:,.0f}  "
                f"(▼₹{d['drop_amt']:,.0f} / {d['drop_pct']}% off)\n"
                f"   📌 {d['source']}\n"
                f"   🔗 {d['url']}\n"
            )
        lines.append("\n🕐 Auto-tracked every hour")
        self.send("\n".join(lines))

    def send_back_in_stock(self, laptop_name, price, url):
        self.send(
            f"✅ <b>Back in Stock!</b>\n\n"
            f"<b>{laptop_name}</b>\n"
            f"Price: ₹{price:,.0f}\n"
            f"🔗 {url}"
        )

    def send_new_laptop_alert(self, brand, name, price, source):
        self.send(
            f"🆕 <b>New Laptop Detected!</b>\n\n"
            f"Brand: {brand}\n"
            f"<b>{name}</b>\n"
            f"₹{price:,.0f} on {source}\n"
            f"Added to tracker automatically!"
        )

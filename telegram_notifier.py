import os
import requests

class TelegramNotifier:
    def __init__(self):
        self.token   = os.environ["TELEGRAM_BOT_TOKEN"]
        self.chat_id = os.environ["TELEGRAM_CHAT_ID"]

    def _send(self, text: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        requests.post(url, json={
            "chat_id":                  self.chat_id,
            "text":                     text,
            "parse_mode":               "HTML",
            "disable_web_page_preview": True,
        })

    def _top3_block(self, top3: list) -> str:
        """Formats the top 3 cheapest qualifying laptops block."""
        if not top3:
            return "\n\n📊 <b>Top 3 Best Value Right Now</b>\nNo qualifying laptops found yet."

        lines = ["\n\n📊 <b>Top 3 Cheapest With Best Config Right Now</b>"]
        medals = ["🥇", "🥈", "🥉"]
        for i, lp in enumerate(top3):
            office_str  = f" | 💼 {lp['office']}" if lp['office'] not in ("None","Unknown") else ""
            upgrade_str = " | 🔧 Upgradable" if lp['upgradable'] else ""
            lines.append(
                f"\n{medals[i]} <b>{lp['name']}</b>\n"
                f"   💰 <b>₹{lp['price']:,.0f}</b> on {lp['vendor']}\n"
                f"   🖥 {lp['cpu']}\n"
                f"   🎮 {lp['gpu']}\n"
                f"   💾 {lp['ram']} | 📀 {lp['storage']}\n"
                f"   🪟 {lp['windows']}{office_str}{upgrade_str}\n"
                f"   ⭐ Score: {lp['score']}/100\n"
                f"   🔗 {lp['url']}"
            )
        return "\n".join(lines)

    def send_price_drops(self, drops: list, top3: list):
        if not drops:
            return
        lines = [f"🔥 <b>Price Drop Alert! ({len(drops)} laptop{'s' if len(drops)>1 else ''})</b>\n"]
        for d in drops:
            qual = " ✅ Meets your spec" if d.get("qualifies") else " ⚠️ Below your min spec"
            lines.append(
                f"💸 <b>{d['name']}</b>{qual}\n"
                f"   ₹{d['old_price']:,.0f} → <b>₹{d['new_price']:,.0f}</b>  "
                f"(▼ ₹{d['change_inr']:,.0f} / {d['change_pct']}% off)\n"
                f"   🖥 {d['cpu']} | 🎮 {d['gpu']}\n"
                f"   💾 {d['ram']} | 📀 {d['storage']}\n"
                f"   🪟 {d['windows']} | 💼 Office: {d['office']}\n"
                f"   📌 {d['vendor']}\n"
                f"   🔗 {d['url']}\n"
            )
        self._send("\n".join(lines) + self._top3_block(top3))

    def send_price_rises(self, rises: list, top3: list):
        if not rises:
            return
        lines = [f"📈 <b>Price Increase Alert! ({len(rises)} laptop{'s' if len(rises)>1 else ''})</b>\n"]
        for r in rises:
            lines.append(
                f"📈 <b>{r['name']}</b>\n"
                f"   ₹{r['old_price']:,.0f} → <b>₹{r['new_price']:,.0f}</b>  "
                f"(▲ ₹{r['change_inr']:,.0f} / {r['change_pct']}% rise)\n"
                f"   📌 {r['vendor']}\n"
                f"   🔗 {r['url']}\n"
            )
        self._send("\n".join(lines) + self._top3_block(top3))

    def send_new_laptops(self, new_laptops: list, top3: list):
        if not new_laptops:
            return
        lines = [f"🆕 <b>New Laptop{'s' if len(new_laptops)>1 else ''} Detected!</b>\n"]
        for lp in new_laptops:
            lines.append(
                f"✨ <b>{lp['name']}</b>\n"
                f"   Brand: {lp['brand']} | ₹{lp['price']:,.0f}\n"
                f"   📌 {lp['vendor']}\n"
                f"   🔗 {lp['url']}\n"
            )
        self._send("\n".join(lines) + self._top3_block(top3))

    def send_back_in_stock(self, laptop: dict, top3: list):
        msg = (
            f"✅ <b>Back in Stock!</b>\n\n"
            f"<b>{laptop['name']}</b>\n"
            f"₹{laptop['price']:,.0f} on {laptop['vendor']}\n"
            f"🔗 {laptop['url']}"
        )
        self._send(msg + self._top3_block(top3))

    def send_hourly_digest(self, top3: list):
        """
        Optional: send top 3 every morning at 9am
        even if no price changes occurred.
        """
        msg = "☀️ <b>Good Morning! Daily Best Value Picks</b>"
        self._send(msg + self._top3_block(top3))

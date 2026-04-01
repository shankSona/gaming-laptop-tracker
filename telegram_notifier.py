import os
import requests

# ── PRICE THRESHOLD ALERTS ───────────────────────────────────
# Alert fires when ANY laptop's price drops AT or BELOW these levels.
# Checks all laptops regardless of brand/series.
PRICE_THRESHOLDS = [
    (150000, "₹1.5L"),
    (100000, "₹1L"),
    (90000,  "₹90K"),
]


class TelegramNotifier:
    def __init__(self):
        self.token   = os.environ["TELEGRAM_BOT_TOKEN"]
        self.chat_id = os.environ["TELEGRAM_CHAT_ID"]

    def _send(self, text: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            requests.post(url, json={
                "chat_id":                  self.chat_id,
                "text":                     text,
                "parse_mode":               "HTML",
                "disable_web_page_preview": True,
            }, timeout=15)
        except Exception as e:
            print(f"Telegram send error: {e}")

    # ── THRESHOLD ALERTS ─────────────────────────────────────

    def check_threshold_alerts(self, laptops_with_prices: list):
        """
        Call once per run with ALL scraped laptops.
        Fires a Telegram alert for each laptop whose price is
        at or below any of the defined thresholds.

        laptops_with_prices: list of dicts with keys:
          name, brand, series, price_inr, vendor_name, source_url
        """
        for lp in laptops_with_prices:
            price = lp.get("price_inr", 0)
            crossed = [label for amount, label in PRICE_THRESHOLDS if price <= amount]
            if not crossed:
                continue

            # Report the most restrictive (lowest) threshold crossed
            best_label = crossed[-1]  # last = lowest threshold

            msg = (
                f"🚨 <b>Price Alert — Under {best_label}!</b>\n\n"
                f"💻 <b>{lp['brand']} {lp['series']}</b>\n"
                f"📋 {lp['name']}\n"
                f"💰 Current Price: <b>₹{price:,.0f}</b>\n"
                f"🏷️ Thresholds crossed: {', '.join(crossed)}\n"
                f"🏪 {lp.get('vendor_name', '')}\n"
                f"🔗 {lp.get('source_url', '')}"
            )
            self._send(msg)

    # ── EXISTING NOTIFICATION METHODS ────────────────────────

    def _top3_block(self, top3: list) -> str:
        if not top3:
            return "\n\n📊 <b>Top 3 Best Value Right Now</b>\nNo qualifying laptops found yet."

        lines = ["\n\n📊 <b>Top 3 Cheapest With Best Config Right Now</b>"]
        medals = ["🥇", "🥈", "🥉"]
        for i, lp in enumerate(top3):
            office_str  = f" | 💼 {lp['office']}" if lp['office'] not in ("None", "Unknown") else ""
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
        msg = "☀️ <b>Good Morning! Daily Best Value Picks</b>"
        self._send(msg + self._top3_block(top3))

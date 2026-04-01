import os

from scrapers.amazon_in     import AmazonIndiaScraper
from scrapers.flipkart_in   import FlipkartScraper
from scrapers.hp_in         import HPIndiaScraper
from scrapers.dell_in       import DellIndiaScraper
from scrapers.lenovo_in     import LenovoIndiaScraper
from scrapers.asus_in       import ASUSIndiaScraper
from scrapers.croma_in      import CromaScraper
from scrapers.vijaysales_in import VijaysSalesScraper
from scrapers.poorvika_in   import PoorvikaScraper
from databricks_writer      import DatabricksWriter
from telegram_notifier      import TelegramNotifier


def main():
    scrapers = [
        AmazonIndiaScraper(),
        FlipkartScraper(),
        HPIndiaScraper(),
        DellIndiaScraper(),
        LenovoIndiaScraper(),
        ASUSIndiaScraper(),
        CromaScraper(),
        VijaysSalesScraper(),
        PoorvikaScraper(),
    ]

    all_laptops = []
    for scraper in scrapers:
        try:
            items = scraper.scrape()
            all_laptops.extend(items)
            print(f"✅ {scraper.name}: {len(items)} listings scraped")
        except Exception as e:
            print(f"❌ {scraper.name} failed: {e}")

    if not all_laptops:
        print("⚠️ No data collected. Exiting.")
        return

    print(f"\n📦 Total listings collected: {len(all_laptops)}")
    qualifying = [lp for lp in all_laptops if lp.meets_requirement]
    print(f"✅ Meets your min spec: {len(qualifying)}")

    writer   = DatabricksWriter()
    results  = writer.write(all_laptops)
    notifier = TelegramNotifier()
    top3     = results["top3"]

    print(f"\n📊 Results:")
    print(f"   Price Drops  : {len(results['price_drops'])}")
    print(f"   Price Rises  : {len(results['price_rises'])}")
    print(f"   New Laptops  : {len(results['new_laptops'])}")

    # ── THRESHOLD ALERTS (₹1.5L / ₹1L / ₹90K) ──────────────
    # Build list of all laptops with prices for threshold checking
    threshold_payload = [
        {
            "name":        lp.model_name,
            "brand":       lp.brand,
            "series":      lp.series,
            "price_inr":   lp.price_inr,
            "vendor_name": lp.vendor_name,
            "source_url":  lp.source_url,
        }
        for lp in all_laptops if lp.price_inr > 0
    ]
    notifier.check_threshold_alerts(threshold_payload)

    # ── STANDARD NOTIFICATIONS ───────────────────────────────
    if results["price_drops"]:
        notifier.send_price_drops(results["price_drops"], top3)
        print("📲 Drop notification sent!")

    if results["price_rises"]:
        notifier.send_price_rises(results["price_rises"], top3)
        print("📲 Rise notification sent!")

    if results["new_laptops"]:
        notifier.send_new_laptops(results["new_laptops"], top3)
        print("📲 New laptop notification sent!")


if __name__ == "__main__":
    main()

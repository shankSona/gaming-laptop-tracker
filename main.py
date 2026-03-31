import os

from databricks_writer import DatabricksWriter
from telegram_notifier import TelegramNotifier

from scrapers.amazon_in import AmazonIndiaScraper
from scrapers.hp_in import HPIndiaScraper
from scrapers.dell_in import DellIndiaScraper
from scrapers.lenovo_in import LenovoIndiaScraper
from scrapers.asus_in import ASUSIndiaScraper
from scrapers.flipkart_in import FlipkartScraper
from scrapers.croma_in import CromaScraper
from scrapers.vijaysales_in import VijaysSalesScraper
from scrapers.poorvika_in import PoorvikaScraper

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
            print(f"✅ {scraper.name}: {len(items)} listings")
        except Exception as e:
            print(f"❌ {scraper.name} failed: {e}")

    if not all_laptops:
        print("No data collected. Exiting.")
        return

    writer = DatabricksWriter()
    drops = writer.write(all_laptops)
    print(f"📊 Written {len(all_laptops)} entries. {len(drops)} price drops found.")

    if drops:
        TelegramNotifier().send_price_drops(drops)
        print("📲 Telegram notification sent!")

if __name__ == "__main__":
    main()

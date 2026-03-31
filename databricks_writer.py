import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from datetime import datetime

class DatabricksWriter:
    def __init__(self):
        self.client = WorkspaceClient(
            host=os.environ["DATABRICKS_HOST"],
            token=os.environ["DATABRICKS_TOKEN"],
        )
        self.warehouse_id = os.environ["DATABRICKS_WAREHOUSE_ID"]

    def _run_sql(self, sql):
        resp = self.client.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=sql,
            wait_timeout="50s"
        )
        return resp

    def write(self, laptops: list) -> list:
        """Upsert laptops, insert prices, return list of price drops."""
        price_drops = []
        for laptop in laptops:
            # UPSERT dim_laptops
            self._run_sql(f"""
                MERGE INTO laptop_tracker.dim_laptops AS t
                USING (SELECT '{laptop.model_id}' model_id) AS s ON t.model_id = s.model_id
                WHEN MATCHED THEN UPDATE SET
                    is_active=true, updated_at=current_timestamp()
                WHEN NOT MATCHED THEN INSERT (
                    model_id, brand, series, model_name, cpu, gpu,
                    ram_gb, storage_gb, display_inches, refresh_hz,
                    weight_kg, spec_score, is_active, first_seen_at, updated_at
                ) VALUES (
                    '{laptop.model_id}','{laptop.brand}','{laptop.series}',
                    '{laptop.model_name.replace("'","''")}',
                    '{laptop.cpu}','{laptop.gpu}',
                    {laptop.ram_gb},{laptop.storage_gb},
                    {laptop.display_inches},{laptop.refresh_hz},
                    {laptop.weight_kg},0,true,
                    current_timestamp(),current_timestamp()
                )
            """)

            # Check previous price for drop detection
            prev = self._run_sql(f"""
                SELECT price_inr FROM laptop_tracker.fact_prices
                WHERE model_id='{laptop.model_id}'
                ORDER BY recorded_at DESC LIMIT 1
            """)

            prev_price = None
            if prev.result and prev.result.data_array:
                prev_price = float(prev.result.data_array[0][0])

            # INSERT new price row
            self._run_sql(f"""
                INSERT INTO laptop_tracker.fact_prices
                (model_id, recorded_at, price_inr, in_stock, source_site, source_url)
                VALUES (
                    '{laptop.model_id}', current_timestamp(),
                    {laptop.price_inr}, {str(laptop.in_stock).lower()},
                    '{laptop.source_site}', '{laptop.source_url}'
                )
            """)

            # Detect price drop
            if prev_price and laptop.price_inr < prev_price:
                drop_amt = prev_price - laptop.price_inr
                drop_pct = (drop_amt / prev_price) * 100
                price_drops.append({
                    "name": laptop.model_name,
                    "brand": laptop.brand,
                    "old_price": prev_price,
                    "new_price": laptop.price_inr,
                    "drop_amt": drop_amt,
                    "drop_pct": round(drop_pct, 1),
                    "source": laptop.source_site,
                    "url": laptop.source_url,
                })

        return price_drops

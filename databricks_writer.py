import os
from databricks.sdk import WorkspaceClient
from datetime import datetime

class DatabricksWriter:
    def __init__(self):
        self.client = WorkspaceClient(
            host=os.environ["DATABRICKS_HOST"],
            token=os.environ["DATABRICKS_TOKEN"],
        )
        self.warehouse_id = os.environ["DATABRICKS_WAREHOUSE_ID"]

    def _sql(self, sql):
        resp = self.client.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=sql,
            wait_timeout="50s"
        )
        return resp

    def _escape(self, s):
        return str(s).replace("'", "''") if s else ""

    def write(self, laptops: list) -> dict:
        """
        Upsert all laptops. Returns dict with:
          - price_drops: list
          - price_rises: list
          - new_laptops: list
          - top3: list (top 3 cheapest qualifying laptops right now)
        """
        price_drops  = []
        price_rises  = []
        new_laptops  = []

        for lp in laptops:
            # ── 1. UPSERT dim_laptops ─────────────────────────
            self._sql(f"""
                MERGE INTO laptop_tracker.dim_laptops AS t
                USING (SELECT '{self._escape(lp.model_id)}' AS model_id) AS s
                ON t.model_id = s.model_id
                WHEN MATCHED THEN UPDATE SET
                    is_active         = true,
                    ms_office         = '{self._escape(lp.ms_office)}',
                    windows_version   = '{self._escape(lp.windows_version)}',
                    meets_requirement = {str(lp.meets_requirement).lower()},
                    spec_score        = {lp.spec_score},
                    updated_at        = current_timestamp()
                WHEN NOT MATCHED THEN INSERT (
                    model_id, brand, series, model_name,
                    cpu, cpu_brand, cpu_gen, cpu_tier,
                    gpu, gpu_vram_gb, gpu_tier,
                    ram_gb, ram_type, ram_slots,
                    storage_gb, storage_slots,
                    display_inches, refresh_hz,
                    is_upgradable, ms_office, windows_version,
                    weight_kg, spec_score, meets_requirement,
                    primary_vendor, is_active,
                    first_seen_at, updated_at
                ) VALUES (
                    '{self._escape(lp.model_id)}',
                    '{self._escape(lp.brand)}',
                    '{self._escape(lp.series)}',
                    '{self._escape(lp.model_name)}',
                    '{self._escape(lp.cpu)}',
                    '{self._escape(lp.cpu_brand)}',
                    {lp.cpu_gen},
                    '{self._escape(lp.cpu_tier)}',
                    '{self._escape(lp.gpu)}',
                    {lp.gpu_vram_gb},
                    '{self._escape(lp.gpu_tier)}',
                    {lp.ram_gb},
                    '{self._escape(lp.ram_type)}',
                    {lp.ram_slots},
                    {lp.storage_gb},
                    {lp.storage_slots},
                    {lp.display_inches},
                    {lp.refresh_hz},
                    {str(lp.is_upgradable).lower()},
                    '{self._escape(lp.ms_office)}',
                    '{self._escape(lp.windows_version)}',
                    {lp.weight_kg},
                    {lp.spec_score},
                    {str(lp.meets_requirement).lower()},
                    '{self._escape(lp.vendor_name)}',
                    true,
                    current_timestamp(),
                    current_timestamp()
                )
            """)

            # ── 2. Check if this is a genuinely new laptop ────
            check = self._sql(f"""
                SELECT COUNT(*) FROM laptop_tracker.fact_prices
                WHERE model_id = '{self._escape(lp.model_id)}'
                AND vendor_name = '{self._escape(lp.vendor_name)}'
            """)
            is_new = True
            if check.result and check.result.data_array:
                is_new = int(check.result.data_array[0][0]) == 0

            if is_new:
                new_laptops.append({
                    "name": lp.model_name, "brand": lp.brand,
                    "price": lp.price_inr, "vendor": lp.vendor_name,
                    "url": lp.source_url,
                })

            # ── 3. Fetch previous price for this model+vendor ─
            prev_resp = self._sql(f"""
                SELECT price_inr FROM laptop_tracker.fact_prices
                WHERE model_id    = '{self._escape(lp.model_id)}'
                AND   vendor_name = '{self._escape(lp.vendor_name)}'
                ORDER BY recorded_at DESC LIMIT 1
            """)
            prev_price = None
            if prev_resp.result and prev_resp.result.data_array:
                prev_price = float(prev_resp.result.data_array[0][0])

            # ── 4. Compute change ─────────────────────────────
            change_inr = 0.0
            change_pct = 0.0
            direction  = "NEW" if is_new else "UNCHANGED"

            if prev_price is not None:
                change_inr = lp.price_inr - prev_price
                change_pct = round((change_inr / prev_price) * 100, 2)
                if change_inr < -1:        # drop > ₹1
                    direction = "DROP"
                elif change_inr > 1:       # rise > ₹1
                    direction = "RISE"
                else:
                    direction = "UNCHANGED"

            # ── 5. INSERT into fact_prices ────────────────────
            self._sql(f"""
                INSERT INTO laptop_tracker.fact_prices
                (model_id, vendor_name, recorded_at, price_inr,
                 prev_price_inr, price_change_inr, price_change_pct,
                 change_direction, in_stock, source_url)
                VALUES (
                    '{self._escape(lp.model_id)}',
                    '{self._escape(lp.vendor_name)}',
                    current_timestamp(),
                    {lp.price_inr},
                    {'NULL' if prev_price is None else prev_price},
                    {change_inr},
                    {change_pct},
                    '{direction}',
                    {str(lp.in_stock).lower()},
                    '{self._escape(lp.source_url)}'
                )
            """)

            # ── 6. Log in price_changes table if moved ────────
            if direction in ("DROP", "RISE"):
                self._sql(f"""
                    INSERT INTO laptop_tracker.price_changes
                    (model_id, vendor_name, changed_at,
                     old_price_inr, new_price_inr,
                     change_inr, change_pct, direction)
                    VALUES (
                        '{self._escape(lp.model_id)}',
                        '{self._escape(lp.vendor_name)}',
                        current_timestamp(),
                        {prev_price},
                        {lp.price_inr},
                        {change_inr},
                        {change_pct},
                        '{direction}'
                    )
                """)
                payload = {
                    "name":       lp.model_name,
                    "brand":      lp.brand,
                    "old_price":  prev_price,
                    "new_price":  lp.price_inr,
                    "change_inr": abs(change_inr),
                    "change_pct": abs(change_pct),
                    "vendor":     lp.vendor_name,
                    "url":        lp.source_url,
                    # spec summary for notification
                    "cpu":        lp.cpu,
                    "gpu":        lp.gpu,
                    "ram":        f"{lp.ram_gb}GB {lp.ram_type}",
                    "storage":    f"{lp.storage_gb}GB SSD",
                    "windows":    lp.windows_version,
                    "office":     lp.ms_office,
                    "qualifies":  lp.meets_requirement,
                }
                if direction == "DROP":
                    price_drops.append(payload)
                else:
                    price_rises.append(payload)

        # ── 7. Fetch top 3 cheapest qualifying laptops ────────
        top3 = self.get_top3()

        return {
            "price_drops":  price_drops,
            "price_rises":  price_rises,
            "new_laptops":  new_laptops,
            "top3":         top3,
        }

    def get_top3(self) -> list:
        """
        Top 3 cheapest laptops that meet minimum requirements,
        picking the lowest current price across all vendors per model.
        """
        resp = self._sql("""
            SELECT
                d.brand,
                d.model_name,
                d.cpu,
                d.gpu,
                d.ram_gb,
                d.ram_type,
                d.storage_gb,
                d.windows_version,
                d.ms_office,
                d.is_upgradable,
                d.spec_score,
                f.vendor_name,
                f.price_inr,
                f.source_url
            FROM laptop_tracker.dim_laptops d
            JOIN (
                SELECT model_id, vendor_name, price_inr, source_url,
                       ROW_NUMBER() OVER (
                           PARTITION BY model_id
                           ORDER BY price_inr ASC, recorded_at DESC
                       ) AS rn
                FROM laptop_tracker.fact_prices
                WHERE in_stock = true
            ) f ON d.model_id = f.model_id AND f.rn = 1
            WHERE d.meets_requirement = true
            AND   d.is_active = true
            ORDER BY f.price_inr ASC
            LIMIT 3
        """)

        top3 = []
        if resp.result and resp.result.data_array:
            for row in resp.result.data_array:
                top3.append({
                    "brand":    row[0], "name":    row[1],
                    "cpu":      row[2], "gpu":     row[3],
                    "ram":      f"{row[4]}GB {row[5]}",
                    "storage":  f"{row[6]}GB SSD",
                    "windows":  row[7], "office":  row[8],
                    "upgradable": row[9], "score": row[10],
                    "vendor":   row[11], "price":  float(row[12]),
                    "url":      row[13],
                })
        return top3

import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

class PriceBook:
    """
    Maintain an Excel sheet of fertilizer products.
    Primary key is `url`.
    """

    DEFAULT_FILENAME = "price_of_fertilizers.xlsx"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, file_path: str | None = None):
        self.file_path = file_path or self.DEFAULT_FILENAME

        if os.path.exists(self.file_path):
            self.df = pd.read_excel(self.file_path, engine="openpyxl", dtype=str)
        else:
            # create an empty DataFrame with expected columns
            self.df = pd.DataFrame(
                columns=[
                    "url",
                    "name",
                    "category",
                    "price",
                    "price_per_kg",
                    "created_at",
                    "last_updated",
                ]
            )

    def upsert(self, row: Dict[str, Any]) -> None:
        """
        Add or update a single product row.
        All values are coerced to string to preserve formatting.
        """

        # Convert all values to strings (especially price fields)
        row = {k: str(v) for k, v in row.items()}

        pk = row["url"]
        now = datetime.now().strftime(self.DATE_FMT)

        mask = self.df["url"] == pk
        if mask.any():
            # ---- update existing row ----
            idx = self.df.index[mask][0]
            for k, v in row.items():
                self.df.at[idx, k] = v
            self.df.at[idx, "last_updated"] = now
        else:
            # ---- insert new row ----
            row["created_at"] = now
            row["last_updated"] = now
            self.df.loc[len(self.df)] = row

    def bulk_upsert(self, rows: List[Dict[str, Any]]) -> None:
        """Convenience: upsert a list of product dicts."""
        for r in rows:
            self.upsert(r)

    def save(self, excel_path: str | None = None) -> None:
        """Write DataFrame to disk, preserving price as text."""
        path = excel_path or self.file_path

        # Ensure price columns are saved as string
        self.df["price"] = self.df["price"].astype(str)
        self.df["price_per_kg"] = self.df["price_per_kg"].astype(str)

        self.df.to_excel(path, index=False)
        print(f"✅ Saved {len(self.df)} rows → {path}")

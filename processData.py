import pandas as pd
import numpy as np
import re
import datetime
import os
import statistics
import unicodedata
from persianNumberNormalizer import PersianNumberNormalizer


class ProcessData:
    """A class to process and analyze fertilizer price data from Excel files."""

    def __init__(self):
        """Initialize with an empty DataFrame."""
        self.df = None

    def load_and_concatenate_data(self, file_path):
        """
        Load Excel file with multiple sheets and concatenate into a single DataFrame.

        Args:
            file_path (str): Path to the Excel file.

        Returns:
            pd.DataFrame: Concatenated DataFrame.
        """
        sheets = pd.read_excel(file_path, sheet_name=None)
        self.df = pd.concat([sheet for sheet in sheets.values()], ignore_index=True)
        return self.df

    def clean_initial_data(self, keywords):
        """
        Clean the DataFrame by dropping unnecessary columns and filtering irrelevant keywords.

        Args:
            keywords (list): List of keywords to exclude from the 'name' column.

        Returns:
            pd.DataFrame: Cleaned DataFrame.
        """
        self.df.dropna(subset=["price_per_kg"], inplace=True)
        columns_to_drop = [
            "created_at",
            "last_updated",
            "url",
            "last_price_update",
            "_pk",
        ]
        self.df.drop(
            columns=[col for col in columns_to_drop if col in self.df.columns],
            inplace=True,
        )

        pattern = "|".join(keywords)
        self.df = self.df[~self.df["name"].astype(str).str.contains(pattern, na=False)]

        # Normalize names and convert prices to float
        normalizer = PersianNumberNormalizer()
        self.df["name"] = normalizer.convert(self.df["name"])
        self.df["price_per_kg"] = pd.to_numeric(
            self.df["price_per_kg"], errors="coerce"
        ).astype(float)
        self.df = self.df[self.df["price_per_kg"] > 12000]

        return self.df

    def filter_npk_fertilizers(self, include_pattern, exclude_pattern):
        """
        Filter DataFrame for NPK fertilizers based on inclusion and exclusion patterns.

        Args:
            include_pattern (str): Regex pattern for including NPK fertilizers.
            exclude_pattern (str): Regex pattern for excluding non-NPK fertilizers.

        Returns:
            pd.DataFrame: Filtered DataFrame for NPK fertilizers.
        """
        return self.df[
            self.df["name"]
            .str.lower()
            .str.contains(include_pattern, regex=True, na=False)
            & ~self.df["name"].str.contains(exclude_pattern, regex=True, na=False)
        ]

    def process_npk_fertilizers(self, filtered_df_npk, raw_source_df):
        """
        Process NPK fertilizers and compute statistics for each fertilizer type.

        Args:
            filtered_df_npk (pd.DataFrame): Filtered DataFrame for NPK fertilizers.
            raw_source_df (pd.DataFrame): Raw source DataFrame containing fertilizer metadata.

        Returns:
            pd.DataFrame: DataFrame with processed NPK fertilizer statistics.
        """
        raw_source_df_npk = raw_source_df[raw_source_df["input_code"] == 17]
        all_raw_npk_names = (
            raw_source_df_npk.iloc[:, 4]
            .astype(str)
            .str.replace("-", " ", regex=False)
            .str.replace(r"\+TE", " TE", case=False, regex=True)
            .str.replace(r"\+Ca", " Ca", case=False, regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .tolist()
        )

        rows = []
        for idx, name in enumerate(all_raw_npk_names):
            name_norm = name.lower().strip()
            m = re.match(r"(\d+)\D+(\d+)\D+(\d+)", name_norm)
            pattern = (
                f"{m.group(1)}\\D*{m.group(2)}\\D*{m.group(3)}"
                if m
                else re.escape(name_norm)
            )
            pattern = re.sub(
                r"(\\\+\s*(?:te|ca|me))$", r"(?:\1)?", pattern, flags=re.IGNORECASE
            )

            filtered = filtered_df_npk[
                filtered_df_npk["name"]
                .str.lower()
                .str.contains(pattern, regex=True, na=False)
            ]
            filtered_df_npk = filtered_df_npk[~filtered_df_npk.isin(filtered)].dropna(
                how="all"
            )

            if filtered.empty:
                continue

            rows.append(
                {
                    "code": raw_source_df_npk.iloc[idx, 2],
                    "name": name,
                    "med": filtered["price_per_kg"].mean(),
                    "min": filtered["price_per_kg"].min(),
                    "max": filtered["price_per_kg"].max(),
                    "std": filtered["price_per_kg"].std(),
                    "listOfNames": filtered["name"].tolist(),
                    "listOfPrices": filtered["price_per_kg"].tolist(),
                }
            )

        return pd.DataFrame(rows)

    def process_non_npk_fertilizers(self, raw_source_df, result_df):
        """
        Process non-NPK fertilizers and append to result DataFrame.

        Args:
            raw_source_df (pd.DataFrame): Raw source DataFrame containing fertilizer metadata.
            result_df (pd.DataFrame): Existing result DataFrame to append to.

        Returns:
            pd.DataFrame: Updated result DataFrame with non-NPK fertilizers.
        """
        npk_excluded_raw_source = raw_source_df[raw_source_df["input_code"] != 17]
        cleaned_col = (
            npk_excluded_raw_source.iloc[:, 4]
            .str.replace("+", " ", regex=False)
            .str.replace("\xad\u200c", " ", regex=False)
            .str.replace(r"[()]", " ", regex=True)
            .str.replace("های", " ", regex=False)
            .str.replace("کودهای", "کود", regex=False)
            .str.replace("باکتریهای", "باکتری", regex=False)
            .str.replace("...)", " ", regex=False)
            .str.replace("+TE", " TE", regex=False)
            .str.replace("+Ca", " Ca", regex=False)
            .str.replace("اسیدهای", "اسید", regex=False)
            .str.strip()
        )
        npk_excluded_raw_source.iloc[:, 4] = cleaned_col

        def contains_all_words(text, words):
            """Check if all words are present in text (case-insensitive)."""
            text_lower = str(text).lower()
            return all(word in text_lower for word in words)

        rows = result_df.to_dict("records")
        for counter, full_name in enumerate(
            npk_excluded_raw_source.iloc[:, 4].tolist()
        ):
            words = full_name.split()
            filtered = self.df[
                self.df["name"].apply(lambda x: contains_all_words(x, words))
            ]
            self.df = self.df[~self.df.isin(filtered)].dropna(how="all")

            if filtered.empty:
                continue

            rows.append(
                {
                    "code": npk_excluded_raw_source.iloc[counter, 2],
                    "name": full_name,
                    "med": filtered["price_per_kg"].mean(),
                    "min": filtered["price_per_kg"].min(),
                    "max": filtered["price_per_kg"].max(),
                    "std": filtered["price_per_kg"].std(),
                    "listOfNames": filtered["name"].tolist(),
                    "listOfPrices": filtered["price_per_kg"].tolist(),
                }
            )

        return pd.DataFrame(rows)

    def normalize_text(self, text):
        """
        Normalize Persian/Arabic text by replacing characters and removing unwanted spaces.

        Args:
            text (str): Input text to normalize.

        Returns:
            str: Normalized text.
        """
        if pd.isna(text):
            return ""
        text = text.replace("ي", "ی").replace("ك", "ک")
        text = re.sub(r"[\u200c\u200f\u00a0]", "", text)
        return text

    def filter_irrelevant_fertilizers(self, result_df):
        """
        Filter out irrelevant fertilizers based on predefined keyword mappings.

        Args:
            result_df (pd.DataFrame): DataFrame containing fertilizer data.

        Returns:
            pd.DataFrame: Filtered DataFrame.
        """
        irrelevant_map = {
            "اوره": [
                "سولفات",
                "فسفات",
                "گوگرد",
                "منیزیم",
                "آهن",
                "پتاس",
                "روی",
                "کلسیم",
                "گوگردی",
            ],
            "مرغی": ["اوره", "فسفات", "سولفات", "پتاس", "گوگرد", "پلیت", "پلت"],
            "کمپوست": ["اوره", "فسفات", "سولفات", "پتاس", "گوگرد"],
            "کود سبز": ["فسفات", "سولفات", "گوگرد", "نیتروژن", "پتاس", "روی", "کلسیم"],
            "کلر": ["جلبک", "کلروفیل"],
            "کلات مس": ["کلات آهن"],
            "10 52 10": ["فسفات", "فسفر"],
        }

        def filter_irrelevant_for_fertilizer(row):
            fert = self.normalize_text(row["name"])
            prices = row["listOfPrices"]
            names = [self.normalize_text(n) for n in row["listOfNames"]]
            irrelevant = irrelevant_map.get(fert, [])
            patterns = [
                re.compile(rf"\b{re.escape(bad_kw)}\b", flags=re.IGNORECASE)
                for bad_kw in irrelevant
            ]

            new_prices, new_names = [], []
            for price, name in zip(prices, names):
                if not any(p.search(name) for p in patterns):
                    new_prices.append(price)
                    new_names.append(name)

            row["listOfPrices"] = new_prices
            row["listOfNames"] = new_names
            return row

        return result_df.apply(filter_irrelevant_for_fertilizer, axis=1)

    def handle_potassium_silicate(self, result_df):
        """
        Separate potassium silicate and silicate potassium entries.

        Args:
            result_df (pd.DataFrame): DataFrame containing fertilizer data.

        Returns:
            pd.DataFrame: Updated DataFrame with separated entries.
        """
        both_potassium_df = result_df[result_df["code"] == "13-119"]
        if both_potassium_df.empty:
            return result_df

        both_potassium_index = both_potassium_df.index[0]
        both_names = both_potassium_df["listOfNames"].tolist()[0]
        both_prices = both_potassium_df["listOfPrices"].tolist()[0]

        pattern = re.compile(r"سیلیکات\s*پتاسیم")
        silicate_potassium_names = [n for n in both_names if pattern.search(n)]
        potassium_silicate_names = [n for n in both_names if not pattern.search(n)]

        potassium_silicate_prices = [
            both_prices[i]
            for i, n in enumerate(both_names)
            if n in potassium_silicate_names
        ]
        silicate_potassium_prices = [
            both_prices[i]
            for i, n in enumerate(both_names)
            if n in silicate_potassium_names
        ]

        result_df.at[both_potassium_index, "listOfNames"] = potassium_silicate_names
        result_df.at[both_potassium_index, "listOfPrices"] = potassium_silicate_prices

        silicate_potassium_df = pd.DataFrame(
            {
                "code": ["19-145"],
                "name": ["سیلیکات پتاسیم"],
                "med": [np.nan],
                "min": [np.nan],
                "max": [np.nan],
                "std": [np.nan],
                "listOfPrices": [silicate_potassium_prices],
                "listOfNames": [silicate_potassium_names],
            }
        )

        return pd.concat([result_df, silicate_potassium_df], ignore_index=True)

    def normalize_number_string(self, s):
        """
        Convert Persian/Arabic digits to English and remove thousands separators.

        Args:
            s (str): Input string containing numbers.

        Returns:
            str: Normalized number string.
        """
        if not isinstance(s, str):
            return s
        s = unicodedata.normalize("NFKC", s)
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        arabic_digits = "٠١٢٣٤٥٦٧٨٩"
        english_digits = "0123456789"
        s = s.translate(str.maketrans(persian_digits, english_digits))
        s = s.translate(str.maketrans(arabic_digits, english_digits))
        s = s.replace("٬", "").replace("،", "").replace(",", "")
        return s

    def remove_outliers_iqr(self, names, prices):
        """
        Remove outliers from prices using the IQR method, ensuring at least two items remain.

        Args:
            names (list): List of fertilizer names.
            prices (list): List of corresponding prices.

        Returns:
            tuple: Filtered lists of names and prices.
        """
        if not prices:
            return names, prices

        RATE = 1.5
        clean_data = []
        for name, price in zip(names, prices):
            if isinstance(price, (int, float)):
                clean_data.append((float(price), name))
            elif isinstance(price, str):
                normalized = self.normalize_number_string(price)
                match = re.search(r"[-+]?\d*\.?\d+", normalized)
                if match:
                    clean_data.append((float(match.group()), name))

        if len(clean_data) < 2:
            return names, prices

        clean_data.sort(key=lambda x: x[0])
        clean_prices = [p for p, _ in clean_data]
        clean_names = [n for _, n in clean_data]

        q1 = statistics.quantiles(clean_prices, n=4)[0]
        q3 = statistics.quantiles(clean_prices, n=4)[2]
        iqr = q3 - q1
        lower_limit = q1 - RATE * iqr
        upper_limit = q3 + RATE * iqr

        filtered_data = [
            (p, n) for p, n in clean_data if lower_limit <= p <= upper_limit
        ]
        if len(filtered_data) < 2:
            return names, prices

        return [n for _, n in filtered_data], [p for p, _ in filtered_data]

    def process_outliers(self, result_df):
        """
        Process outliers in the result DataFrame using the IQR method.

        Args:
            result_df (pd.DataFrame): DataFrame containing fertilizer data.

        Returns:
            pd.DataFrame: DataFrame with outliers removed and statistics updated.
        """
        rows = []
        for _, row in result_df.iterrows():
            filtered_names, filtered_prices = self.remove_outliers_iqr(
                row["listOfNames"], row["listOfPrices"]
            )
            filtered_prices = [
                p
                for p in filtered_prices
                if p is not None and not (isinstance(p, float) and np.isnan(p))
            ]

            if filtered_prices:
                median = statistics.median(filtered_prices)
                minimum = min(filtered_prices)
                maximum = max(filtered_prices)
                std = (
                    statistics.stdev(filtered_prices)
                    if len(filtered_prices) >= 2
                    else None
                )
            else:
                median, minimum, maximum, std = None, None, None, None

            rows.append(
                {
                    "code": row["code"],
                    "name": row["name"],
                    "med": median,
                    "min": minimum,
                    "max": maximum,
                    "std": std,
                    "listOfPrices": filtered_prices,
                    "listOfNames": filtered_names,
                }
            )

        return pd.DataFrame(rows)

    def save_absent_fertilizers(self, result_df, raw_source_df):
        """
        Identify and save fertilizers absent from the result DataFrame.

        Args:
            result_df (pd.DataFrame): Processed DataFrame with fertilizer data.
            raw_source_df (pd.DataFrame): Raw source DataFrame with all fertilizers.
        """
        result_list = result_df["name"].str.replace("-", " ", regex=False).tolist()
        complete_list = (
            raw_source_df.iloc[:, 4].str.replace("-", " ", regex=False).tolist()
        )
        absent_fertilizers = [x for x in complete_list if x not in result_list]

        absent_df = pd.DataFrame({"absents": absent_fertilizers})
        os.makedirs("absents", exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"absents/fertilizer_absent_{now_str}.xlsx"
        absent_df.to_excel(
            filename, sheet_name="Fertilizer_Absent_Estimations", index=False
        )

    def save_results(self, result_df):
        """
        Save the processed DataFrame to an Excel file with frozen headers.

        Args:
            result_df (pd.DataFrame): DataFrame to save.
        """
        os.makedirs("estimation_output", exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"estimation_output/fertilizer_price_estimations_{now_str}.xlsx"
        sheet_name = "Fertilizer_Price_Estimations"

        with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)

    def run(self, input_file, raw_source_file):
        """
        Execute the complete data processing pipeline.

        Args:
            input_file (str): Path to the input Excel file with fertilizer data.
            raw_source_file (str): Path to the raw source Excel file with fertilizer metadata.
        """
        # Load and concatenate data
        self.load_and_concatenate_data(input_file)

        # Clean initial data
        keywords = ["خاک", "سم", "قارچ", "حشره", "علف", "صمغ"]
        self.clean_initial_data(keywords)

        # Save cleaned data to CSV
        self.df.to_csv("concatenated_excel/fullRawExcel.csv", index=False)

        # Filter NPK fertilizers
        include_pattern = r"(npk|n\s*p\s*k|کامل)"
        exclude_pattern = r"(خاک)"
        filtered_df_npk = self.filter_npk_fertilizers(include_pattern, exclude_pattern)

        # Load raw source data
        raw_source_df = pd.read_excel(raw_source_file)

        # Process NPK fertilizers
        result_df = self.process_npk_fertilizers(filtered_df_npk, raw_source_df)

        # Process non-NPK fertilizers
        result_df = self.process_non_npk_fertilizers(raw_source_df, result_df)

        # Filter irrelevant fertilizers
        result_df = self.filter_irrelevant_fertilizers(result_df)

        # Handle potassium silicate issue
        result_df = self.handle_potassium_silicate(result_df)

        # Remove outliers
        result_df = self.process_outliers(result_df)

        # Save absent fertilizers
        self.save_absent_fertilizers(result_df, raw_source_df)

        # Save final results
        self.save_results(result_df)


if __name__ == "__main__":
    processor = ProcessData()
    processor.run(
        input_file="output/price_of_fertilizers - Copy (10).xlsx",
        raw_source_file="source/raw_source_of_fertilizer.xlsx",
    )

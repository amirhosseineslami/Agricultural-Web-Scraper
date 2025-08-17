# %%
from persianNumberNormalizer import PersianNumberNormalizer
import re, pandas as pd, numpy as np, datetime


class processData:
    """
    Process Data in Excel
    """

    df = None

    # %%


df = pd.read_excel("output/price_of_fertilizers - Copy (10).xlsx", sheet_name=None)
df

# %%
# Concatenate all the data in the
dataFrame = pd.DataFrame()
for data in df.values():
    dataFrame = pd.concat([data, dataFrame], ignore_index=True)

dataFrame

# %%
# DATAAAAAAAAAAAAAAAAAAAAAAA SILICATTTTTTTTTTTTTTTTTTTTT
# DATAAAAAAAAAAAAAAAAAAAAAAA SILICATTTTTTTTTTTTTTTTTTTTT


dataFrame[dataFrame["name"].str.contains("سیلیکات")]

# %%
df = dataFrame

df.dropna(subset=["price_per_kg"], inplace=True)
df = df.drop(labels="created_at", axis=1)
df = df.drop(labels="last_updated", axis=1)
df.to_csv("concatenated_excel/fullRawExcel.csv")

df.drop("url", axis=1, inplace=True)

# Filter some irrelevent keywords
keywords = ["خاک", "سم", "قارچ", "حشره", "علف", "صمغ"]
pattern = "|".join(keywords)

df = df[~df.iloc[:, 0].astype(str).str.contains(pattern)]


# %%
# DATAAAAAAAAAAAAAAAAAAAAAAA SILICATTTTTTTTTTTTTTTTTTTTT
# DATAAAAAAAAAAAAAAAAAAAAAAA SILICATTTTTTTTTTTTTTTTTTTTT


df[df["name"].str.contains("سیلیکات")]

# %%
df = df.drop(labels="last_price_update", axis=1)
df

# %%
df.drop("_pk", axis=1, inplace=True)
df

# %%
normalizer = PersianNumberNormalizer()
df["name"] = normalizer.convert(df["name"])

# %%
# convert all of the prices to float
df["price_per_kg"] = pd.to_numeric(df["price_per_kg"], errors="coerce").astype(float)

# %%
df

# %%
raw_source_df = pd.read_excel(io="source/raw_source_of_fertilizer.xlsx")

# %% [markdown]
# **Filter specific fertilizer**

# %% [markdown]
# npk

# %%
# Compile all positive patterns into one regex
include_pattern = r"(npk|n\s*p\s*k|کامل)"
exclude_pattern = r"(خاک)"

filtered_df_npk = df[
    df["name"].str.lower().str.contains(include_pattern, regex=True, na=False)
    & ~df["name"].str.contains(exclude_pattern, regex=True, na=False)
]

# %%
raw_source_df.columns

# %%
raw_source_df_npk_filtered = raw_source_df[raw_source_df["input_code"] == 17]
raw_source_df_npk_filtered

# %%
allRawNpkRealNamesList = (
    raw_source_df_npk_filtered.iloc[:, 4]
    .astype(str)
    # Replace "-" with space
    .str.replace("-", " ", regex=False)
    # Replace +TE (case-insensitive) with " TE"
    .str.replace(r"\+TE", " TE", case=False, regex=True)
    # Replace +Ca (case-insensitive) with " Ca"
    .str.replace(r"\+Ca", " Ca", case=False, regex=True)
    # Collapse multiple spaces to one
    .str.replace(r"\s+", " ", regex=True)
    # Strip extra spaces at start/end
    .str.strip()
    .tolist()
)
allRawNpkRealNamesList

# %%
filtered_df_npk


# %%
import re
import pandas as pd

rows = []

for idx, name in enumerate(allRawNpkRealNamesList):
    name_norm = name.lower().strip()

    # Flexible matching between numbers (any non-digit chars allowed)
    m = re.match(r"(\d+)\D+(\d+)\D+(\d+)", name_norm)
    if m:
        pattern = f"{m.group(1)}\\D*{m.group(2)}\\D*{m.group(3)}"
    else:
        pattern = re.escape(name_norm)

    # Make +TE / +Ca / +ME optional at the end (case-insensitive)
    pattern = re.sub(
        r"(\\\+\s*(?:te|ca|me))$", r"(?:\1)?", pattern, flags=re.IGNORECASE
    )

    filtered = filtered_df_npk[
        filtered_df_npk["name"].str.lower().str.contains(pattern, regex=True, na=False)
    ]

    # Eliminate this row from the dataframe to have unique data
    filtered_df_npk = filtered_df_npk[~filtered_df_npk.isin(filtered)].dropna(how="all")

    if filtered.empty:
        continue

    row = {
        "code": raw_source_df_npk_filtered.iloc[idx, 2],
        "name": name,
        "med": filtered["price_per_kg"].mean(),
        "min": filtered["price_per_kg"].min(),
        "max": filtered["price_per_kg"].max(),
        "std": filtered["price_per_kg"].std(),
        "listOfNames": filtered["name"].tolist(),
        "listOfPrices": filtered["price_per_kg"].tolist(),
    }
    rows.append(row)

result_df = pd.DataFrame(rows)
print(result_df)


# %%
npk_excluded_raw_source = raw_source_df[raw_source_df["input_code"] != 17]
npk_excluded_raw_source

# %%
npk_excluded_raw_source.iloc[:, 4].tolist()
cleaned_col = (
    npk_excluded_raw_source.iloc[:, 4]
    .str.replace("+", " ", regex=False)
    .str.replace("\xad\u200c", " ", regex=False)
    .str.replace(")", " ")
    .replace("(", " ")
    .replace("های", " ")
    .replace("کودهای", "کود")
    .replace("باکتریهای", "باکتری")
    .replace("...)", " ")
    .replace("+TE", " TE")
    .replace("+Ca", " Ca")
    .replace("اسیدهای", "اسید")
)
npk_excluded_raw_source.iloc[:, 4] = cleaned_col
npk_excluded_raw_source

# %%
# Find "سیلیکات پتاسیم"


def normalize_text(s):
    if pd.isna(s):
        return ""
    # Replace Arabic forms with Persian
    s = s.replace("ي", "ی").replace("ك", "ک")
    # Remove zero-width and non-breaking spaces
    s = re.sub(r"[\u200c\u200f\u00a0]", "", s)
    return s


df["name_clean"] = df["name"].apply(normalize_text)

# Now search
df[df["name_clean"].str.contains("سیلیکات", na=False)]


# %%
df["name"].tolist()

# %%
df[df["name"].str.contains("سیلیکات", na=False)]

# %%
import pandas as pd


def contains_all_words(text, words):
    """Check if all words are present in text (any order). Case insensitive."""
    text_lower = str(text).lower()
    return all(word in text_lower for word in words)


for counter, full_name in enumerate(npk_excluded_raw_source.iloc[:, 4].tolist()):
    words = full_name.split()

    # Filter rows where 'name' column contains all words (in any order)
    filtered = df[df["name"].apply(lambda x: contains_all_words(x, words))]

    if filtered.empty:
        continue  # skip if no matches
    else:
        # Eliminate this row from the dataframe to have unique data
        df = df[~df.isin(filtered)].dropna(how="all")

    row = {
        "code": npk_excluded_raw_source.iloc[counter, 2],
        "name": full_name,
        "med": filtered["price_per_kg"].mean(),
        "min": filtered["price_per_kg"].min(),
        "max": filtered["price_per_kg"].max(),
        "std": filtered["price_per_kg"].std(),
        "listOfNames": filtered["name"].tolist(),
        "listOfPrices": filtered["price_per_kg"].tolist(),
    }
    rows.append(row)

result_df = pd.DataFrame(rows)
print(result_df)


# %%
result_df

# %%
result_df

# %% [markdown]
# **Correct EXCEPTIONS**

# %%
result_df

# %%
import pandas as pd
import re

# Irrelevant keywords per fertilizer
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


def normalize_text(text):
    """Normalize Persian/Arabic text and remove unwanted spaces."""
    text = str(text)
    # Replace Arabic characters with Persian ones
    text = text.replace("ي", "ی").replace("ك", "ک")
    # Remove diacritics
    text = re.sub(r"[\u064B-\u065F]", "", text)
    # Remove zero-width and multiple spaces
    text = re.sub(r"[\u200c\u200f]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def filter_irrelevant_for_fertilizer(row):
    fert = normalize_text(row["name"])
    prices = row["listOfPrices"]
    names = [normalize_text(n) for n in row["listOfNames"]]

    irrelevant = irrelevant_map.get(fert, [])
    # Compile regex patterns for speed and accuracy
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


result_df = result_df.apply(filter_irrelevant_for_fertilizer, axis=1)


# %% [markdown]
# **Handle Potasium Silicat Problem**

# %%
result_df

# %%
bothPotasiomSilicatsDf = result_df[result_df["code"] == "13-119"]
bothPotasiomIndex = result_df[result_df["code"] == "13-119"].index[0]

bothPotasiomSilicatsNames = bothPotasiomSilicatsDf.listOfNames.tolist()[0]
bothPotasiomSilicatsPrices = bothPotasiomSilicatsDf.listOfPrices.tolist()[0]

pattern = re.compile(r"سیلیکات\s*پتاسیم")
silicatPotasiumNames = [
    n for n in list(bothPotasiomSilicatsDf.listOfNames.tolist()[0]) if pattern.search(n)
]
potasium_silicatNames = [
    n
    for n in list(bothPotasiomSilicatsDf.listOfNames.tolist()[0])
    if n not in silicatPotasiumNames
]
potasium_silicatNames

potasium_silicatPrices = []
silicat_potasiumPrices = []
for index in range(len(bothPotasiomSilicatsNames)):
    name = bothPotasiomSilicatsNames[index]
    if name in potasium_silicatNames:
        # It's Potasium Silicat
        potasium_silicatPrices.append(bothPotasiomSilicatsPrices[index])

    else:
        # It's Silicat Potasium
        silicat_potasiumPrices.append(bothPotasiomSilicatsPrices[index])

# Now we have both names and prices devided
result_df.at[bothPotasiomIndex, "listOfNames"] = potasium_silicatNames
result_df.at[bothPotasiomIndex, "listOfPrices"] = potasium_silicatPrices
silicatPotasiumDf = pd.DataFrame(
    {
        "code": "19-145",
        "name": "سیلیکات پتاسیم",
        "med": "Nan",
        "min": "Nan",
        "max": "Nan",
        "std": "Nan",
        "listOfPrices": [silicat_potasiumPrices],
        "listOfNames": [silicatPotasiumNames],
    }
)
result_df = pd.concat([result_df, silicatPotasiumDf], ignore_index=True)
result_df

# %% [markdown]
# **Remove any Price outlier via IQR**

# %% [markdown]
# write the function for removing outliers by median of the prices

# %%
import statistics
import re
import unicodedata


def normalize_number_string(s: str) -> str:
    """Convert Persian/Arabic digits to English and remove thousands separators."""
    if not isinstance(s, str):
        return s
    # Normalize Unicode
    s = unicodedata.normalize("NFKC", s)
    # Convert Persian digits
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"
    s = s.translate(str.maketrans(persian_digits, english_digits))
    s = s.translate(str.maketrans(arabic_digits, english_digits))
    # Remove Persian/Arabic/English commas
    s = s.replace("٬", "").replace("،", "").replace(",", "")
    return s


def remove_outliers_iqr(names, prices):
    """
    Removes outliers using the IQR method,
    ensures at least 2 items remain.
    Automatically handles Persian/Arabic digits and sorts by price.
    """
    if not prices:
        return names, prices

    # How much robust if smaller become more aggresive
    RATE = 1.5

    # Extract numeric values and sort them by price
    clean_data = []
    for name, price in zip(names, prices):
        if isinstance(price, (int, float)):
            clean_data.append((float(price), name))
        elif isinstance(price, str):
            normalized = normalize_number_string(price)
            match = re.search(r"[-+]?\d*\.?\d+", normalized)
            if match:
                clean_data.append((float(match.group()), name))

    # If fewer than 2 numeric prices, skip filtering
    if len(clean_data) < 2:
        return names, prices

    # Sort by price
    clean_data.sort(key=lambda x: x[0])
    clean_prices = [p for p, _ in clean_data]
    clean_names = [n for _, n in clean_data]

    # Calculate Q1, Q3, and IQR
    q1 = statistics.quantiles(clean_prices, n=4)[0]
    q3 = statistics.quantiles(clean_prices, n=4)[2]
    iqr = q3 - q1
    lower_limit = q1 - RATE * iqr
    upper_limit = q3 + RATE * iqr

    # Filter values within bounds
    filtered_data = [(p, n) for p, n in clean_data if lower_limit <= p <= upper_limit]

    # Ensure at least 2 prices remain
    if len(filtered_data) < 2:
        return names, prices

    # Return sorted filtered results
    filtered_prices = [p for p, _ in filtered_data]
    filtered_names = [n for _, n in filtered_data]
    return filtered_names, filtered_prices


# %%
import math
import statistics

listOfRemovedOutliersByMedian = []

for index, row in result_df.iterrows():
    filtered_outliers_names, filtered_outliers_prices = remove_outliers_iqr(
        row["listOfNames"], row["listOfPrices"]
    )

    # Remove NaN or non-numeric values from prices list
    filtered_outliers_prices = [
        p
        for p in filtered_outliers_prices
        if p is not None and not (isinstance(p, float) and math.isnan(p))
    ]

    if filtered_outliers_prices:
        median = statistics.median(filtered_outliers_prices)
        minimum = min(filtered_outliers_prices)
        maximum = max(filtered_outliers_prices)
        if len(filtered_outliers_prices) >= 2:
            std = statistics.stdev(filtered_outliers_prices)
        else:
            std = None
    else:
        median, minimum, maximum, std = None, None, None, None

    listOfRemovedOutliersByMedian.append(
        {
            "code": row["code"],
            "name": row["name"],
            "med": median,
            "min": minimum,
            "max": maximum,
            "std": std,
            "listOfPrices": filtered_outliers_prices,
            "listOfNames": filtered_outliers_names,
        }
    )

dfOfRemovedOutliersByMedian = pd.DataFrame(listOfRemovedOutliersByMedian)
result_df = dfOfRemovedOutliersByMedian
dfOfRemovedOutliersByMedian


# %% [markdown]
# ***Checking Fertilizers Which Aren't In The List***

# %%
resultList = result_df.iloc[:, 1].str.replace("-", " ", regex=False).tolist()
completeList = raw_source_df.iloc[:, 4].str.replace("-", " ", regex=False).tolist()
absentFertilizers = [x for x in completeList if x not in resultList]
absentdf = pd.DataFrame({"absents": absentFertilizers})
import datetime
import os

os.makedirs("absents", exist_ok=True)

now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"absents/fertilizer_absent_{now_str}.xlsx"

absentdf.to_excel(filename, sheet_name="Fertilizer_Absent_Estimations", index=False)


# %%
result_df[result_df["name"] == "سولفات پتاسیم"].listOfNames.tolist()

# %% [markdown]
# save the result

# %%
import datetime
import os

os.makedirs("estimation_output", exist_ok=True)

now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"estimation_output/fertilizer_price_estimations_{now_str}.xlsx"
sheetName = "Fertilizer_Price_Estimations"

with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
    result_df.to_excel(writer, sheet_name=sheetName, index=False)

    # Get the sheet then freez the first row
    work_sheet = writer.sheets[sheetName]
    work_sheet.freeze_panes(1, 0)

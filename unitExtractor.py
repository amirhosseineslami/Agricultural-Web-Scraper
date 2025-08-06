import re
import unicodedata
import logging
from typing import Tuple, Optional, List, Dict
from decimal import Decimal, InvalidOperation
from collections import OrderedDict
import asyncio

import logging

# configure only a file handler
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("unit_extractor.log", encoding="utf-8")],
)

# Use logger as usual
logger = logging.getLogger(__name__)

# Comprehensive mapping of units to kilogram conversion factors
UNIT_KEYWORDS = {
    # Weight units
    "کیلوگرم": 1.0,
    "کیلو": 1.0,
    "کیلویی": 1.0,
    "کیلوئی": 1.0,
    "کیلوگرمی": 1.0,
    "kg": 1.0,
    "KG": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "kilo": 1.0,
    "kilos": 1.0,
    "k": 1.0,
    "گرم": 0.001,
    "گرمی": 0.001,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "gms": 0.001,
    "gm": 0.001,
    "milligram": 0.000001,
    "milligrams": 0.000001,
    "mg": 0.000001,
    "میلی‌گرم": 0.000001,
    "میلی گرم": 0.000001,
    "میکروگرم": 0.000000001,
    "میکرو گرم": 0.000000001,
    "microgram": 0.000000001,
    "micrograms": 0.000000001,
    "μg": 0.000000001,
    "تن": 1000.0,
    "t": 1000.0,
    "ton": 1000.0,
    "tons": 1000.0,
    "tonne": 1000.0,
    "tonnes": 1000.0,
    "metric ton": 1000.0,
    "metric tons": 1000.0,
    "ounce": 0.0283495,
    "ounces": 0.0283495,
    "oz": 0.0283495,
    "pound": 0.453592,
    "pounds": 0.453592,
    "lb": 0.453592,
    "lbs": 0.453592,
    # Volume units (assuming water density: 1L = 1kg for liquids)
    "لیتر": 1.0,
    "لیتری": 1.0,
    "l": 1.0,
    "L": 1.0,
    "liter": 1.0,
    "liters": 1.0,
    "litre": 1.0,
    "litres": 1.0,
    "میلی‌لیتر": 0.001,
    "میلی لیتر": 0.001,
    "ml": 0.001,
    "ML": 0.001,
    "milliliter": 0.001,
    "milliliters": 0.001,
    "millilitre": 0.001,
    "millilitres": 0.001,
    "سی‌سی": 0.001,
    "سی سی": 0.001,
    "cc": 0.001,
    "cubic centimeter": 0.001,
    "cubic centimeters": 0.001,
    "gallon": 3.78541,
    "gallons": 3.78541,
    "gal": 3.78541,
    "quart": 0.946353,
    "quarts": 0.946353,
    "qt": 0.946353,
    "pint": 0.473176,
    "pints": 0.473176,
    "pt": 0.473176,
    # Traditional Persian units
    "من": 3.0,
    "مَن": 3.0,
    "چارک": 0.75,
    "سیر": 0.075,
    "وکا": 0.0013,
    # Additional colloquial or shorthand units
    "کیلو گرمی": 1.0,
    "گرمي": 0.001,
    "كيلو": 1.0,
    "ليتر": 1.0,
    "ميلي ليتر": 0.001,
    "سي‌سي": 0.001,
}

# Character mappings for normalization
PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫٬", "0123456789.,")
ARABIC_TO_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
SUPERSCRIPT_TO_NORMAL = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

# Comprehensive number pattern
NUMBER_PATTERN = r"""
    (?:
        (?:
            \d+(?:[.,]\d{0,10})?(?:[eE][-+]?\d+)?  # Decimal or scientific notation
            |
            [۰-۹]+(?:[٫.][۰-۹]{0,10})?              # Persian numerals
            |
            [٠-٩]+(?:[٫.][٠-٩]{0,10})?              # Arabic numerals
            |
            \d+\s*/\s*\d+                           # Fraction
            |
            [۰-۹]+\s*/\s*[۰-۹]+                     # Persian fraction
            |
            [٠-٩]+\s*/\s*[٠-٩]+                     # Arabic fraction
        )
        (?!\d)                                      # No trailing digits
    )
"""

# Unit pattern, sorted by length
UNIT_PATTERN = "|".join(
    sorted(map(re.escape, UNIT_KEYWORDS.keys()), key=len, reverse=True)
)

# Primary pattern for number + unit or unit + number
FLEXIBLE_PATTERN = rf"""
    (?:
        (?P<amount1>{NUMBER_PATTERN})[\s\-\u200c\u200d\u200e\u200f\u202f\u00a0]*?(?P<unit1>{UNIT_PATTERN})(?!\w)
        |
        (?P<unit2>{UNIT_PATTERN})[\s\-\u200c\u200d\u200e\u200f\u202f\u00a0]*?(?P<amount2>{NUMBER_PATTERN})(?!\w)
    )
"""

# Fallback pattern for looser matching
FALLBACK_PATTERN = rf"""
    (?P<amount>{NUMBER_PATTERN})\s*(?P<unit>{UNIT_PATTERN})(?!\w)
"""

# Separate patterns for package counts to avoid group name conflicts
PACKAGE_PATTERNS = [
    re.compile(
        r"بسته\s*(?P<persian_count>\d+|[۰-۹]+)\s*عددی", flags=re.IGNORECASE | re.UNICODE
    ),
    re.compile(r"pack\s*(?P<english_pack_count>\d+)", flags=re.IGNORECASE | re.UNICODE),
    re.compile(
        r"package\s*(?P<english_package_count>\d+)", flags=re.IGNORECASE | re.UNICODE
    ),
]


class UnitExtractor:
    def __init__(self):
        """
        Initialize the UnitExtractor with compiled regex patterns and unit mappings.
        """
        self.unit_keywords = OrderedDict(UNIT_KEYWORDS)
        self.pattern = re.compile(
            FLEXIBLE_PATTERN, flags=re.IGNORECASE | re.VERBOSE | re.UNICODE
        )
        self.fallback_pattern = re.compile(
            FALLBACK_PATTERN, flags=re.IGNORECASE | re.VERBOSE | re.UNICODE
        )
        self.package_patterns = PACKAGE_PATTERNS
        self.default_package_weights = {
            "خاک ژله ای": 0.004,  # Default weight for gel soil packages (4g)
            "خاک رس": 0.2,  # Default weight for clay soil packages (200g)
            "default": 0.001,  # Fallback weight for unknown packages
        }
        logger.debug(
            "UnitExtractor initialized with %d unit mappings and %d package patterns",
            len(self.unit_keywords),
            len(self.package_patterns),
        )

    def normalize_text(self, text: str) -> str:
        """
        Normalize input text by converting numerals and handling Unicode variations.
        """
        if not isinstance(text, str):
            logger.error("Input text must be a string, received: %s", type(text))
            return ""

        try:
            # Unicode normalization
            text = unicodedata.normalize("NFKC", text)
            # Convert numerals
            text = text.translate(PERSIAN_TO_LATIN)
            text = text.translate(ARABIC_TO_LATIN)
            text = text.translate(SUPERSCRIPT_TO_NORMAL)
            # Normalize separators
            text = re.sub(r"[\u200c\u200d\u200e\u200f\u202f\u00a0]+", " ", text)
            text = text.replace("٫", ".")
            text = text.replace(",", ".")
            # Normalize spaces
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        except Exception as e:
            logger.error("Error normalizing text: %s", str(e))
            return text

    def parse_number(self, amount_str: str) -> Optional[Decimal]:
        """
        Parse a string representing a number into a Decimal.
        """
        if not amount_str:
            logger.warning("Empty amount string provided")
            return None

        try:
            # Handle fractions
            if "/" in amount_str:
                numerator, denominator = map(str.strip, amount_str.split("/"))
                num = Decimal(numerator.replace(",", "."))
                denom = Decimal(denominator.replace(",", "."))
                if denom == 0:
                    logger.error("Division by zero in fraction: %s", amount_str)
                    return None
                return num / denom

            # Handle scientific notation or decimal
            cleaned_amount = amount_str.replace(",", ".")
            return Decimal(cleaned_amount)
        except (InvalidOperation, ValueError, ZeroDivisionError) as e:
            logger.error("Failed to parse number '%s': %s", amount_str, str(e))
            return None

    def convert_to_kg(self, amount: Decimal, unit: str) -> Optional[Decimal]:
        """
        Convert the given amount and unit to kilograms.
        """
        factor = self.unit_keywords.get(unit.strip(), None)
        if factor is None:
            logger.warning("Unknown unit: %s", unit)
            return None
        try:
            return amount * Decimal(str(factor))
        except InvalidOperation as e:
            logger.error("Error converting %s %s to kg: %s", amount, unit, str(e))
            return None

    def estimate_package_weight(self, text: str, count: int) -> Optional[Decimal]:
        """
        Estimate total weight for packages based on context.
        """
        try:
            for key, weight in self.default_package_weights.items():
                if key in text:
                    return Decimal(str(count)) * Decimal(str(weight))
            return Decimal(str(count)) * Decimal(
                str(self.default_package_weights["default"])
            )
        except InvalidOperation as e:
            logger.error("Error estimating package weight for '%s': %s", text, str(e))
            return None

    def token_based_extraction(
        self, text: str
    ) -> Tuple[Optional[Decimal], Optional[str]]:
        """
        Fallback token-based extraction for complex cases.
        """
        tokens = text.split()
        for i, token in enumerate(tokens):
            # Try to parse token as a number
            num = self.parse_number(token)
            if num is not None:
                # Check next and previous tokens for units
                for offset in [1, -1]:
                    if 0 <= i + offset < len(tokens):
                        next_token = tokens[i + offset]
                        if next_token in self.unit_keywords:
                            amount_in_kg = self.convert_to_kg(num, next_token)
                            if amount_in_kg is not None:
                                return amount_in_kg, next_token
        return None, None

    async def extract_amount_and_unit(
        self, text: str
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract the first valid amount and unit from text and convert to kilograms.
        """
        if not text:
            logger.warning("Empty input text provided")
            return None, None

        normalized = self.normalize_text(text)
        if not normalized:
            logger.warning("Normalized text is empty")
            return None, None

        try:
            # Try primary pattern
            match = self.pattern.search(normalized)
            if match:
                amount_str = match.group("amount1") or match.group("amount2")
                unit = match.group("unit1") or match.group("unit2")

                if amount_str and unit:
                    amount = self.parse_number(amount_str)
                    if amount is not None:
                        amount_in_kg = self.convert_to_kg(amount, unit)
                        if amount_in_kg is not None:
                            logger.debug(
                                "Extracted %s %s -> %s kg", amount, unit, amount_in_kg
                            )
                            return float(round(amount_in_kg, 6)), unit

            # Try fallback pattern
            match = self.fallback_pattern.search(normalized)
            if match:
                amount_str = match.group("amount")
                unit = match.group("unit")

                if amount_str and unit:
                    amount = self.parse_number(amount_str)
                    if amount is not None:
                        amount_in_kg = self.convert_to_kg(amount, unit)
                        if amount_in_kg is not None:
                            logger.debug(
                                "Fallback extracted %s %s -> %s kg",
                                amount,
                                unit,
                                amount_in_kg,
                            )
                            return float(round(amount_in_kg, 6)), unit

            # Try package patterns
            for pattern in self.package_patterns:
                match = pattern.search(normalized)
                if match:
                    count_str = (
                        match.group("persian_count")
                        or match.group("english_pack_count")
                        or match.group("english_package_count")
                    )
                    count = self.parse_number(count_str)
                    if count is not None:
                        amount_in_kg = self.estimate_package_weight(
                            normalized, int(count)
                        )
                        if amount_in_kg is not None:
                            logger.debug(
                                "Package extracted %s units -> %s kg",
                                count,
                                amount_in_kg,
                            )
                            return float(round(amount_in_kg, 6)), "estimated_package"

            # Try token-based extraction
            amount_in_kg, unit = self.token_based_extraction(normalized)
            if amount_in_kg is not None:
                logger.debug("Token-based extracted %s %s", amount_in_kg, unit)
                return float(round(amount_in_kg, 6)), unit

            logger.info("No amount-unit match found in text: %s", normalized)
            return None, None
        except Exception as e:
            logger.error("Error extracting amount and unit from '%s': %s", text, str(e))
            return None, None

    async def extract_all_amounts_and_units(
        self, text: str
    ) -> List[Tuple[Optional[float], Optional[str]]]:
        """
        Extract all amount-unit pairs from the text and convert to kilograms.
        """
        if not text:
            logger.warning("Empty input text provided for multi-extraction")
            return []

        normalized = self.normalize_text(text)
        if not normalized:
            logger.warning("Normalized text is empty for multi-extraction")
            return []

        results = []
        try:
            # Try primary pattern
            matches = self.pattern.finditer(normalized)
            for match in matches:
                amount_str = match.group("amount1") or match.group("amount2")
                unit = match.group("unit1") or match.group("unit2")

                if amount_str and unit:
                    amount = self.parse_number(amount_str)
                    if amount is not None:
                        amount_in_kg = self.convert_to_kg(amount, unit)
                        if amount_in_kg is not None:
                            results.append((float(round(amount_in_kg, 6)), unit))

            # Try fallback pattern
            if not results:
                matches = self.fallback_pattern.finditer(normalized)
                for match in matches:
                    amount_str = match.group("amount")
                    unit = match.group("unit")

                    if amount_str and unit:
                        amount = self.parse_number(amount_str)
                        if amount is not None:
                            amount_in_kg = self.convert_to_kg(amount, unit)
                            if amount_in_kg is not None:
                                results.append((float(round(amount_in_kg, 6)), unit))

            # Try package patterns
            for pattern in self.package_patterns:
                matches = pattern.finditer(normalized)
                for match in matches:
                    count_str = (
                        match.group("persian_count")
                        or match.group("english_pack_count")
                        or match.group("english_package_count")
                    )
                    count = self.parse_number(count_str)
                    if count is not None:
                        amount_in_kg = self.estimate_package_weight(
                            normalized, int(count)
                        )
                        if amount_in_kg is not None:
                            results.append(
                                (float(round(amount_in_kg, 6)), "estimated_package")
                            )

            # Try token-based extraction
            amount_in_kg, unit = self.token_based_extraction(normalized)
            if amount_in_kg is not None:
                results.append((float(round(amount_in_kg, 6)), unit))

        except Exception as e:
            logger.error(
                "Error extracting all amounts and units from '%s': %s", text, str(e)
            )
            return []

        if not results:
            logger.info("No valid amount-unit pairs found in text: %s", normalized)
        return results

    async def process_product_data(self, product_data: Dict) -> Dict:
        """
        Process a product dictionary to extract and convert weight to kilograms.
        """
        if not isinstance(product_data, dict):
            logger.error(
                "Product data must be a dictionary, received: %s", type(product_data)
            )
            return product_data

        name = product_data.get("name", "")
        price_str = product_data.get("price", "")

        if not name:
            logger.warning("No product name provided")
            product_data["kg"] = "nan"
            product_data["price/kg"] = "nan"
            return product_data

        try:
            amount_in_kg, unit = await self.extract_amount_and_unit(name)
            if amount_in_kg is None:
                logger.info("No valid weight found in product name: %s", name)
                product_data["kg"] = "nan"
                product_data["price/kg"] = "nan"
                return product_data

            product_data["kg"] = amount_in_kg

            if price_str:
                try:
                    price_normalized = self.normalize_text(price_str)
                    price = float(price_normalized.replace(",", ""))
                    if amount_in_kg > 0:
                        price_per_kg = price / amount_in_kg
                        product_data["price/kg"] = round(price_per_kg, 2)
                    else:
                        product_data["price/kg"] = "nan"
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(
                        "Failed to calculate price/kg for price '%s': %s",
                        price_str,
                        str(e),
                    )
                    product_data["price/kg"] = "nan"
            else:
                product_data["price/kg"] = "nan"

        except Exception as e:
            logger.error("Error processing product data for '%s': %s", name, str(e))
            product_data["kg"] = "nan"
            product_data["price/kg"] = "nan"

        return product_data

    async def batch_process_products(self, products: List[Dict]) -> List[Dict]:
        """
        Process a list of product dictionaries in batch.
        """
        tasks = [self.process_product_data(product) for product in products]
        return await asyncio.gather(*tasks, return_exceptions=True)

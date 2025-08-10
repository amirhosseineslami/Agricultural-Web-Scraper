import re
import unicodedata
import logging
from typing import Tuple, Optional, List, Dict
from decimal import Decimal, InvalidOperation
from collections import OrderedDict
import asyncio
import os
from logging.handlers import RotatingFileHandler

# Configure a custom logger for PriceExtractor
logger = logging.getLogger("price_extractor")
logger.setLevel(logging.DEBUG)

# Clear any existing handlers to prevent terminal output
logger.handlers.clear()

# Create logs directory and set up file logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "price_extractor.log")

# Set up RotatingFileHandler
handler = RotatingFileHandler(
    log_file, maxBytes=10 * 1024 * 1024, backupCount=5
)  # 10MB per file, 5 backups
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# Verify handler setup
logger.debug(
    "Logging configured with %d handlers: %s",
    len(logger.handlers),
    [h.__class__.__name__ for h in logger.handlers],
)

# Comprehensive mapping of currencies to IRR conversion factors (approximate rates as of August 2025)
CURRENCY_KEYWORDS = {
    # Iranian currencies
    "ریال": 1.0,
    "ریالی": 1.0,
    "IRR": 1.0,
    "rial": 1.0,
    "rials": 1.0,
    "تومان": 10.0,
    "تومن": 10.0,
    "TMT": 10.0,
    "toman": 10.0,
    "tomans": 10.0,
    "هزار تومان": 10_000.0,
    "هزار تومن": 10_000.0,
    "میلیون تومان": 10_000_000.0,
    "میلیون تومن": 10_000_000.0,
    "میلیارد تومان": 10_000_000_000.0,
    "میلیارد تومن": 10_000_000_000.0,
    # International currencies
    "USD": 420_000.0,
    "$": 420_000.0,
    "dollar": 420_000.0,
    "dollars": 420_000.0,
    "EUR": 460_000.0,
    "€": 460_000.0,
    "euro": 460_000.0,
    "euros": 460_000.0,
    "GBP": 530_000.0,
    "£": 530_000.0,
    "pound": 530_000.0,
    "pounds": 530_000.0,
    "JPY": 2_800.0,
    "¥": 2_800.0,
    "yen": 2_800.0,
    "AED": 114_000.0,
    "درهم": 114_000.0,
    "dirham": 114_000.0,
    "dirhams": 114_000.0,
    "CNY": 58_000.0,
    "yuan": 58_000.0,
    # Additional colloquial forms
    "هزار": 1_000.0,  # Assumes rial if standalone
    "میلیون": 1_000_000.0,  # Assumes rial if standalone
    "میلیارد": 1_000_000_000.0,  # Assumes rial if standalone
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

# Currency pattern, sorted by length
CURRENCY_PATTERN = "|".join(
    sorted(map(re.escape, CURRENCY_KEYWORDS.keys()), key=len, reverse=True)
)

# Primary pattern for price + currency or currency + price
FLEXIBLE_PATTERN = rf"""
    (?:
        (?P<amount1>{NUMBER_PATTERN})[\s\-\u200c\u200d\u200e\u200f\u202f\u00a0]*?(?P<currency1>{CURRENCY_PATTERN})(?!\w)
        |
        (?P<currency2>{CURRENCY_PATTERN})[\s\-\u200c\u200d\u200e\u200f\u202f\u00a0]*?(?P<amount2>{NUMBER_PATTERN})(?!\w)
    )
"""

# Fallback pattern for looser matching
FALLBACK_PATTERN = rf"""
    (?P<amount>{NUMBER_PATTERN})\s*(?P<currency>{CURRENCY_PATTERN})(?!\w)
"""

# Pattern for standalone large numbers (e.g., "2 میلیون" assuming rial)
STANDALONE_PATTERN = rf"""
    (?P<amount>{NUMBER_PATTERN})\s*(?P<currency>هزار|میلیون|میلیارد)(?!\w)
"""


class PriceExtractor:
    def __init__(self):
        """
        Initialize the PriceExtractor with compiled regex patterns and currency mappings.
        """
        self.currency_keywords = OrderedDict(CURRENCY_KEYWORDS)
        self.pattern = re.compile(
            FLEXIBLE_PATTERN, flags=re.IGNORECASE | re.VERBOSE | re.UNICODE
        )
        self.fallback_pattern = re.compile(
            FALLBACK_PATTERN, flags=re.IGNORECASE | re.VERBOSE | re.UNICODE
        )
        self.standalone_pattern = re.compile(
            STANDALONE_PATTERN, flags=re.IGNORECASE | re.VERBOSE | re.UNICODE
        )
        logger.debug(
            "PriceExtractor initialized with %d currency mappings",
            len(self.currency_keywords),
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

    def convert_to_irr(self, amount: Decimal, currency: str) -> Optional[Decimal]:
        """
        Convert the given amount and currency to Iranian rial (IRR).
        """
        factor = self.currency_keywords.get(currency.strip(), None)
        if factor is None:
            logger.warning("Unknown currency: %s", currency)
            return None
        try:
            return amount * Decimal(str(factor))
        except InvalidOperation as e:
            logger.error("Error converting %s %s to IRR: %s", amount, currency, str(e))
            return None

    def token_based_extraction(
        self, text: str
    ) -> Tuple[Optional[Decimal], Optional[str]]:
        """
        Fallback token-based extraction for complex price formats.
        """
        tokens = text.split()
        for i, token in enumerate(tokens):
            # Try to parse token as a number
            num = self.parse_number(token)
            if num is not None:
                # Check next and previous tokens for currencies
                for offset in [1, -1]:
                    if 0 <= i + offset < len(tokens):
                        next_token = tokens[i + offset]
                        if next_token in self.currency_keywords:
                            amount_in_irr = self.convert_to_irr(num, next_token)
                            if amount_in_irr is not None:
                                return amount_in_irr, next_token
        return None, None

    async def extract_price_and_currency(
        self, text: str
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract the first valid price and currency from text and convert to IRR.
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
                currency = match.group("currency1") or match.group("currency2")

                if amount_str and currency:
                    amount = self.parse_number(amount_str)
                    if amount is not None:
                        amount_in_irr = self.convert_to_irr(amount, currency)
                        if amount_in_irr is not None:
                            logger.debug(
                                "Extracted %s %s -> %s IRR",
                                amount,
                                currency,
                                amount_in_irr,
                            )
                            return float(round(amount_in_irr, 2)), currency

            # Try fallback pattern
            match = self.fallback_pattern.search(normalized)
            if match:
                amount_str = match.group("amount")
                currency = match.group("currency")

                if amount_str and currency:
                    amount = self.parse_number(amount_str)
                    if amount is not None:
                        amount_in_irr = self.convert_to_irr(amount, currency)
                        if amount_in_irr is not None:
                            logger.debug(
                                "Fallback extracted %s %s -> %s IRR",
                                amount,
                                currency,
                                amount_in_irr,
                            )
                            return float(round(amount_in_irr, 2)), currency

            # Try standalone pattern (e.g., "2 میلیون" assuming rial)
            match = self.standalone_pattern.search(normalized)
            if match:
                amount_str = match.group("amount")
                currency = match.group("currency")

                if amount_str and currency:
                    amount = self.parse_number(amount_str)
                    if amount is not None:
                        amount_in_irr = self.convert_to_irr(amount, currency)
                        if amount_in_irr is not None:
                            logger.debug(
                                "Standalone extracted %s %s -> %s IRR",
                                amount,
                                currency,
                                amount_in_irr,
                            )
                            return float(round(amount_in_irr, 2)), currency

            # Try token-based extraction
            amount_in_irr, currency = self.token_based_extraction(normalized)
            if amount_in_irr is not None:
                logger.debug("Token-based extracted %s %s", amount_in_irr, currency)
                return float(round(amount_in_irr, 2)), currency

            logger.info("No price-currency match found in text: %s", normalized)
            return None, None
        except Exception as e:
            logger.error(
                "Error extracting price and currency from '%s': %s", text, str(e)
            )
            return None, None

    async def extract_all_prices_and_currencies(
        self, text: str
    ) -> List[Tuple[Optional[float], Optional[str]]]:
        """
        Extract all price-currency pairs from the text and convert to IRR.
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
                currency = match.group("currency1") or match.group("currency2")

                if amount_str and currency:
                    amount = self.parse_number(amount_str)
                    if amount is not None:
                        amount_in_irr = self.convert_to_irr(amount, currency)
                        if amount_in_irr is not None:
                            results.append((float(round(amount_in_irr, 2)), currency))

            # Try fallback pattern
            if not results:
                matches = self.fallback_pattern.finditer(normalized)
                for match in matches:
                    amount_str = match.group("amount")
                    currency = match.group("currency")

                    if amount_str and currency:
                        amount = self.parse_number(amount_str)
                        if amount is not None:
                            amount_in_irr = self.convert_to_irr(amount, currency)
                            if amount_in_irr is not None:
                                results.append(
                                    (float(round(amount_in_irr, 2)), currency)
                                )

            # Try standalone pattern
            matches = self.standalone_pattern.finditer(normalized)
            for match in matches:
                amount_str = match.group("amount")
                currency = match.group("currency")

                if amount_str and currency:
                    amount = self.parse_number(amount_str)
                    if amount is not None:
                        amount_in_irr = self.convert_to_irr(amount, currency)
                        if amount_in_irr is not None:
                            results.append((float(round(amount_in_irr, 2)), currency))

            # Try token-based extraction
            amount_in_irr, currency = self.token_based_extraction(normalized)
            if amount_in_irr is not None:
                results.append((float(round(amount_in_irr, 2)), currency))

        except Exception as e:
            logger.error(
                "Error extracting all prices and currencies from '%s': %s", text, str(e)
            )
            return []

        if not results:
            logger.info("No valid price-currency pairs found in text: %s", normalized)
        return results

    async def process_product_data(self, product_data: Dict) -> Dict:
        """
        Process a product dictionary to extract and convert price to IRR.
        """
        if not isinstance(product_data, dict):
            logger.error(
                "Product data must be a dictionary, received: %s", type(product_data)
            )
            return product_data

        price_str = product_data.get("price", "")
        name = product_data.get("name", "")

        if not price_str:
            logger.warning("No price provided for product: %s", name or "unknown")
            product_data["price_irr"] = "nan"
            return product_data

        try:
            price_in_irr, currency = await self.extract_price_and_currency(price_str)
            if price_in_irr is None:
                logger.info("No valid price found in price string: %s", price_str)
                product_data["price_irr"] = "nan"
                return product_data

            product_data["price_irr"] = price_in_irr
            product_data["currency"] = currency

        except Exception as e:
            logger.error(
                "Error processing product data for '%s': %s", price_str, str(e)
            )
            product_data["price_irr"] = "nan"
            product_data["currency"] = None

        return product_data

    async def batch_process_products(self, products: List[Dict]) -> List[Dict]:
        """
        Process a list of product dictionaries in batch.
        """
        tasks = [self.process_product_data(product) for product in products]
        return await asyncio.gather(*tasks, return_exceptions=True)

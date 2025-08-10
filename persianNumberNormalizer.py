import unicodedata
import pandas as pd
from typing import Union


class PersianNumberNormalizer:
    """
    Normalize Persian and Arabic digits in text to English digits.
    Can process single strings or pandas Series.
    """

    # Persian and Arabic digits mapping to English digits
    PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
    ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
    ENGLISH_DIGITS = "0123456789"

    def __init__(self):
        # Create translation tables for Persian and Arabic digits
        self.persian_trans_table = str.maketrans(
            self.PERSIAN_DIGITS, self.ENGLISH_DIGITS
        )
        self.arabic_trans_table = str.maketrans(self.ARABIC_DIGITS, self.ENGLISH_DIGITS)

    def normalize_text(self, text: str) -> str:
        """
        Normalize Unicode text to NFKC form to unify representation.
        """
        if not isinstance(text, str):
            return text
        return unicodedata.normalize("NFKC", text)

    def convert_numbers(self, text: str) -> str:
        """
        Convert all Persian and Arabic digits in the input text to English digits.
        """
        if not isinstance(text, str):
            return text

        # Normalize Unicode forms
        text = self.normalize_text(text)

        # Translate Persian digits
        text = text.translate(self.persian_trans_table)
        # Translate Arabic digits
        text = text.translate(self.arabic_trans_table)

        return text

    def convert_series(self, series: pd.Series) -> pd.Series:
        """
        Convert Persian and Arabic digits in a pandas Series of strings to English digits.
        Non-string values are left unchanged.
        """
        return series.apply(self.convert_numbers)

    def convert(self, data: Union[str, pd.Series]) -> Union[str, pd.Series]:
        """
        Convert Persian and Arabic digits in a string or pandas Series.
        """
        if isinstance(data, pd.Series):
            return self.convert_series(data)
        elif isinstance(data, str):
            return self.convert_numbers(data)
        else:
            # Return data unchanged if not str or Series
            return data

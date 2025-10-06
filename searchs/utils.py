import unicodedata
import re

def preprocess_query(query: str) -> str:
    """
    حذف فاصله‌ها، حروف بزرگ/کوچک و نرمال‌سازی کاراکترها.
    """
    query = query.strip().lower()
    # حذف نمادهای غیر ضروری
    query = re.sub(r"[^\w\s]", "", query)
    # نرمال‌سازی حروف (مثلاً فارسی)
    query = unicodedata.normalize("NFKC", query)
    return query
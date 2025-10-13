import re

PERSIAN_NUM_MAP = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹",
    "0123456789"
)

ARABIC_CHAR_MAP = str.maketrans(
    "يك",
    "یک"
)

def preprocess_query(query: str) -> str:
    """
    پاکسازی و نرمال‌سازی عبارت جستجو برای فارسی و انگلیسی.
    - تبدیل اعداد فارسی به انگلیسی
    - تبدیل ی و ك عربی به ی و ک فارسی
    - lowercase کردن
    - حذف فاصله‌های اضافی و کاراکترهای خاص
    """
    if not isinstance(query, str):
        return ""
    
    query = query.strip()
    query = query.translate(PERSIAN_NUM_MAP)      # اعداد فارسی → انگلیسی
    query = query.translate(ARABIC_CHAR_MAP)     # حروف عربی → فارسی
    query = query.lower()
    query = re.sub(r'\s+', ' ', query)           # حذف فاصله‌های اضافی
    query = re.sub(r'[^\w\s]', '', query)        # حذف کاراکترهای خاص (به جز underscore و فاصله)
    return query
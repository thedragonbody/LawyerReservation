import re

def preprocess_query(query: str) -> str:
    """
    پاکسازی و نرمال‌سازی عبارت جستجو.
    - حذف فاصله‌های اضافی
    - lowercase
    - حذف کاراکترهای خاص
    """
    if not isinstance(query, str):
        return ""
    query = query.strip().lower()
    query = re.sub(r'\s+', ' ', query)
    # اجازه می‌دیم underscore و حروف/اعداد/فاصله بمونن
    query = re.sub(r'[^\w\s]', '', query)
    return query
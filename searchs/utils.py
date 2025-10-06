import re

def preprocess_query(query: str) -> str:
    """
    پاکسازی و نرمال‌سازی عبارت جستجو.
    - حذف فاصله‌های اضافی
    - lowercase
    - حذف کاراکترهای خاص
    """
    query = query.strip().lower()
    query = re.sub(r'\s+', ' ', query)
    query = re.sub(r'[^\w\s]', '', query)
    return query
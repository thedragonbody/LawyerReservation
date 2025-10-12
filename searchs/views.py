import json
import hashlib
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_redis import get_redis_connection
from elasticsearch_dsl import Q
from django.db.models import Count

from searchs.models import SearchHistory
from searchs.utils import preprocess_query
from users.documents import UserDocument, LawyerProfileDocument, ClientProfileDocument
from appointments.documents import AppointmentDocument
from payments.documents import PaymentDocument
from cases.documents import CaseDocument

# تنظیمات کش و محدودیت
CACHE_TIMEOUT_RESULTS = 60 * 5  # 5 دقیقه
CACHE_TIMEOUT_SUGGEST = 60 * 3   # 3 دقیقه
RATE_LIMIT = 50                  # 50 درخواست در دقیقه


# ---------------------- Helper Functions ----------------------

def _safe_redis_get(cache_conn, key):
    """دریافت امن از Redis با json.loads و جلوگیری از eval"""
    try:
        val = cache_conn.get(key)
        if val is None:
            return None
        if isinstance(val, bytes):
            val = val.decode("utf-8")
        return json.loads(val)
    except Exception:
        return None


def _safe_redis_set(cache_conn, key, value, ex=None):
    """ذخیره امن در Redis با json.dumps"""
    try:
        cache_conn.set(key, json.dumps(value, default=str), ex=ex)
    except Exception:
        pass


def _client_ip(request):
    """برگرداندن IP واقعی کاربر"""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "anon")


# ---------------------- Views ----------------------

# 🌐 Global Search
class GlobalSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raw_query = request.query_params.get("q", "").strip()
        if not raw_query:
            return Response({"detail": "لطفاً عبارت جستجو را وارد کنید."}, status=400)

        entity_type = request.query_params.get("type")  # users, lawyers, clients, appointments, payments, cases
        status_filter = request.query_params.get("status")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        normalized_q = preprocess_query(raw_query)
        cache_conn = get_redis_connection()

        # هش کلید کش
        key_base = f"{normalized_q}:{entity_type or 'all'}:{status_filter or ''}:{from_date or ''}:{to_date or ''}"
        cache_key = "search_global:" + hashlib.md5(key_base.encode()).hexdigest()

        # 🔹 Rate-limit
        user_id = f"user:{request.user.id}" if request.user.is_authenticated else f"ip:{_client_ip(request)}"
        rate_key = f"search_rate:{user_id}"

        try:
            pipe = cache_conn.pipeline()
            pipe.incr(rate_key)
            pipe.expire(rate_key, 60)
            res = pipe.execute()
            current = int(res[0]) if res and res[0] else 0
        except Exception:
            current = 0

        if current and current > RATE_LIMIT:
            return Response({"detail": "تعداد درخواست‌ها بیش از حد است. لطفاً بعداً تلاش کنید."}, status=429)

        # 🔹 کش نتایج
        cached = _safe_redis_get(cache_conn, cache_key)
        if cached is not None:
            return Response({"query": raw_query, "results": cached}, status=200)

        results = {}

        # ثبت تاریخچه
        if request.user.is_authenticated:
            try:
                SearchHistory.objects.update_or_create(
                    user=request.user,
                    normalized_query=normalized_q,
                    defaults={"query": raw_query}
                )
            except Exception:
                pass

        # تابع ساخت query در Elasticsearch
        def build_search(doc_class, fields, status=None, from_date=None, to_date=None):
            q_text = normalized_q if normalized_q else raw_query
            fuzziness = "AUTO" if len(q_text) >= 3 else 0
            q = Q("multi_match", query=q_text, fields=fields, fuzziness=fuzziness)

            if status:
                q &= Q("match", status=status)

            if from_date or to_date:
                date_range = {}
                if from_date:
                    date_range["gte"] = from_date
                if to_date:
                    date_range["lte"] = to_date
                q &= Q("range", date=date_range)

            try:
                hits = doc_class.search().query(q).execute()
                return [hit.to_dict() for hit in hits]
            except Exception:
                return []

        # مدل‌های قابل جستجو
        all_searches = {
            "users": lambda: build_search(UserDocument, ["first_name", "last_name", "email", "full_name"]),
            "lawyers": lambda: build_search(LawyerProfileDocument, ["full_name", "expertise", "degree"]),
            "clients": lambda: build_search(ClientProfileDocument, ["full_name", "national_id"]),
            "appointments": lambda: build_search(AppointmentDocument, ["lawyer_name", "status", "date"], status=status_filter, from_date=from_date, to_date=to_date),
            "payments": lambda: build_search(PaymentDocument, ["transaction_id", "status"]),
            "cases": lambda: build_search(CaseDocument, ["case_number", "title", "status"], status=status_filter, from_date=from_date, to_date=to_date),
        }

        if entity_type in all_searches:
            results[entity_type] = all_searches[entity_type]()
        else:
            for key, func in all_searches.items():
                results[key] = func()

        # ذخیره در کش
        _safe_redis_set(cache_conn, cache_key, results, ex=CACHE_TIMEOUT_RESULTS)
        return Response({"query": raw_query, "results": results}, status=200)


# 🕒 Search History
class SearchHistoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_conn = get_redis_connection()
        cache_key = f"search_history:{request.user.id}"

        cached = _safe_redis_get(cache_conn, cache_key)
        if cached is not None:
            return Response({"history": cached}, status=200)

        try:
            searches = SearchHistory.objects.filter(user=request.user).order_by("-created_at").values("query", "created_at")
            data = list(searches)
        except Exception:
            data = []

        _safe_redis_set(cache_conn, cache_key, data, ex=CACHE_TIMEOUT_SUGGEST)
        return Response({"history": data}, status=200)


# 💡 Search Suggestions
class SearchSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw_query = request.query_params.get("q", "").strip()
        if not raw_query:
            return Response({"suggestions": []}, status=200)

        cache_conn = get_redis_connection()
        key_raw = f"{request.user.id}:{raw_query}"
        cache_key = "search_suggestions:" + hashlib.md5(key_raw.encode()).hexdigest()

        cached = _safe_redis_get(cache_conn, cache_key)
        if cached is not None:
            return Response({"suggestions": cached}, status=200)

        try:
            # جستجو در تاریخچه اخیر کاربر
            recent_qs = SearchHistory.objects.filter(user=request.user, query__icontains=raw_query)
            recent_searches = recent_qs.order_by("-created_at").values_list("query", flat=True)[:10]
            recent_list = list(recent_searches)

            # جستجو در محبوب‌ترین کوئری‌ها
            popular_qs = SearchHistory.objects.filter(query__icontains=raw_query)
            popular_searches = popular_qs.values("query").annotate(count=Count("id")).order_by("-count")[:10].values_list("query", flat=True)
            popular_list = list(popular_searches)

        except Exception:
            recent_list, popular_list = [], []

        # ترکیب و حذف تکراری‌ها
        combined = list(dict.fromkeys(recent_list + popular_list))
        suggestions = [s for s in combined if raw_query.lower() in s.lower()]

        _safe_redis_set(cache_conn, cache_key, suggestions, ex=CACHE_TIMEOUT_SUGGEST)
        return Response({"suggestions": suggestions}, status=200)
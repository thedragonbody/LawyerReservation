import json
import hashlib
import logging
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_redis import get_redis_connection
from elasticsearch_dsl import Q
from django.db.models import Count

from searchs.models import SearchHistory
from searchs.utils import preprocess_query
from users.documents import UserDocument
from appointments.documents import OnlineAppointmentDocument
from payments.documents import PaymentDocument
from cases.documents import CaseDocument

# تنظیمات کش و محدودیت
CACHE_TIMEOUT_RESULTS = 60 * 5  # 5 دقیقه
CACHE_TIMEOUT_SUGGEST = 60 * 3   # 3 دقیقه
RATE_LIMIT_DEFAULT = 50          # 50 درخواست در دقیقه

logger = logging.getLogger("searchs")

# ---------------------- Helper Functions ----------------------

def _safe_redis_get(cache_conn, key):
    try:
        val = cache_conn.get(key)
        if val is None:
            return None
        if isinstance(val, bytes):
            val = val.decode("utf-8")
        return json.loads(val)
    except Exception as e:
        logger.warning(f"Redis GET failed for key {key}: {e}")
        return None

def _safe_redis_set(cache_conn, key, value, ex=None):
    try:
        cache_conn.set(key, json.dumps(value, default=str), ex=ex)
    except Exception as e:
        logger.warning(f"Redis SET failed for key {key}: {e}")

def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "anon")

def _check_rate_limit(cache_conn, user_identifier, rate_limit=RATE_LIMIT_DEFAULT):
    rate_key = f"search_rate:{user_identifier}"
    try:
        pipe = cache_conn.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, 60)
        res = pipe.execute()
        current = int(res[0]) if res and res[0] else 0
        return current <= rate_limit
    except Exception as e:
        logger.warning(f"Rate limit check failed for {user_identifier}: {e}")
        return True

# ---------------------- Pagination ----------------------

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

def paginate_list(request, queryset):
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    return page, paginator

# ---------------------- Views ----------------------

class GlobalSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raw_query = request.query_params.get("q", "").strip()
        if not raw_query:
            return Response({"detail": "لطفاً عبارت جستجو را وارد کنید."}, status=400)

        entity_type = request.query_params.get("type")
        status_filter = request.query_params.get("status")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        normalized_q = preprocess_query(raw_query)
        cache_conn = get_redis_connection()

        cache_key = "search_global:" + hashlib.md5(
            f"{normalized_q}:{entity_type or 'all'}:{status_filter or ''}:{from_date or ''}:{to_date or ''}".encode()
        ).hexdigest()

        user_identifier = f"user:{request.user.id}" if request.user.is_authenticated else f"ip:{_client_ip(request)}"
        if not _check_rate_limit(cache_conn, user_identifier):
            return Response({"detail": "تعداد درخواست‌ها بیش از حد است. لطفاً بعداً تلاش کنید."}, status=429)

        cached = _safe_redis_get(cache_conn, cache_key)
        if cached is not None:
            # اعمال pagination روی cached
            if entity_type:
                items = cached.get(entity_type, [])
                page_items, paginator = paginate_list(request, items)
                return paginator.get_paginated_response({"query": raw_query, "results": {entity_type: page_items}})
            else:
                # اگر all search است، pagination فقط روی هر دسته جداگانه اعمال می‌شود
                paginated_results = {}
                for key, items in cached.items():
                    page_items, _ = paginate_list(request, items)
                    paginated_results[key] = page_items
                return Response({"query": raw_query, "results": paginated_results}, status=200)

        results = {}

        if request.user.is_authenticated:
            try:
                SearchHistory.objects.update_or_create(
                    user=request.user,
                    normalized_query=normalized_q,
                    defaults={"query": raw_query}
                )
            except Exception as e:
                logger.warning(f"Failed to save search history: {e}")

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
            except Exception as e:
                logger.warning(f"Elasticsearch query failed for {doc_class.__name__}: {e}")
                return []

        all_searches = {
            "users": lambda: build_search(UserDocument, ["first_name", "last_name", "email", "full_name"]),
            #"lawyers": lambda: build_search(LawyerProfileDocument, ["full_name", "expertise", "degree"]),
            #"clients": lambda: build_search(ClientProfileDocument, ["full_name", "national_id"]),
            "appointments": lambda: build_search(OnlineAppointmentDocument, ["lawyer_name", "status", "date"], status=status_filter, from_date=from_date, to_date=to_date),
            "payments": lambda: build_search(PaymentDocument, ["transaction_id", "status"]),
            "cases": lambda: build_search(CaseDocument, ["case_number", "title", "status"], status=status_filter, from_date=from_date, to_date=to_date),
        }

        if entity_type in all_searches:
            items = all_searches[entity_type]()
            page_items, paginator = paginate_list(request, items)
            results[entity_type] = page_items
        else:
            for key, func in all_searches.items():
                items = func()
                page_items, _ = paginate_list(request, items)
                results[key] = page_items

        _safe_redis_set(cache_conn, cache_key, results, ex=CACHE_TIMEOUT_RESULTS)
        return Response({"query": raw_query, "results": results}, status=200)

class SearchHistoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_conn = get_redis_connection()
        cache_key = f"search_history:{request.user.id}"
        cached = _safe_redis_get(cache_conn, cache_key)
        if cached is not None:
            return Response({"history": cached}, status=200)

        try:
            searches = SearchHistory.objects.filter(user=request.user).select_related("user").order_by("-created_at").values("query", "created_at")
            data = list(searches)
        except Exception as e:
            logger.warning(f"Failed to fetch search history: {e}")
            data = []

        _safe_redis_set(cache_conn, cache_key, data, ex=CACHE_TIMEOUT_SUGGEST)
        return Response({"history": data}, status=200)

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
            recent_qs = SearchHistory.objects.filter(user=request.user, query__icontains=raw_query).select_related("user")
            recent_list = list(recent_qs.order_by("-created_at").values_list("query", flat=True)[:10])

            popular_qs = SearchHistory.objects.filter(query__icontains=raw_query).select_related("user")
            popular_list = list(popular_qs.values("query").annotate(count=Count("id")).order_by("-count")[:10].values_list("query", flat=True))
        except Exception as e:
            logger.warning(f"Failed to fetch search suggestions: {e}")
            recent_list, popular_list = [], []

        combined = list(dict.fromkeys(recent_list + popular_list))
        suggestions = [s for s in combined if raw_query.lower() in s.lower()]
        suggestions = suggestions[:20]

        _safe_redis_set(cache_conn, cache_key, suggestions, ex=CACHE_TIMEOUT_SUGGEST)
        return Response({"suggestions": suggestions}, status=200)
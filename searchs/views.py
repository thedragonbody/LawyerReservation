from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_redis import get_redis_connection
from elasticsearch_dsl import Q
from searchs.models import SearchHistory
from searchs.utils import preprocess_query
from users.documents import UserDocument, LawyerProfileDocument, ClientProfileDocument
from appointments.documents import AppointmentDocument
from payments.documents import PaymentDocument
from cases.documents import CaseDocument
from django.db.models import Count
from datetime import datetime

CACHE_TIMEOUT_RESULTS = 60 * 5  # 5 دقیقه
CACHE_TIMEOUT_SUGGEST = 60 * 3   # 3 دقیقه
RATE_LIMIT = 50                  # 50 درخواست در دقیقه

# ---------------------------- Global Multi-Model Search ----------------------------

class GlobalSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "لطفاً عبارت جستجو را وارد کنید."}, status=400)

        entity_type = request.query_params.get("type")  # users, lawyers, clients, appointments, payments, cases
        status_filter = request.query_params.get("status")  # فقط برای appointments و cases
        from_date = request.query_params.get("from_date")  # YYYY-MM-DD
        to_date = request.query_params.get("to_date")      # YYYY-MM-DD

        normalized_q = preprocess_query(query)
        cache_conn = get_redis_connection()
        cache_key = f"search_global:{normalized_q}:{entity_type or 'all'}:{status_filter}:{from_date}:{to_date}"
        rate_key = f"search_rate:{request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR','anon')}"

        # Rate-limit
        count = cache_conn.get(rate_key)
        if count and int(count) >= RATE_LIMIT:
            return Response({"detail": "تعداد درخواست‌ها بیش از حد است، لطفاً بعدا تلاش کنید."}, status=429)
        else:
            cache_conn.incr(rate_key)
            cache_conn.expire(rate_key, 60)

        # Cache نتایج
        cached_results = cache_conn.get(cache_key)
        if cached_results:
            return Response({"query": query, "results": eval(cached_results)})

        results = {}

        # ثبت تاریخچه
        if request.user.is_authenticated:
            SearchHistory.objects.update_or_create(
                user=request.user,
                normalized_query=normalized_q,
                defaults={"query": query}
            )

        # تابع جستجو
        def build_search(doc_class, fields, status=None, from_date=None, to_date=None):
            q = Q("multi_match", query=query, fields=fields, fuzziness="AUTO")
            
            # فیلتر وضعیت
            if status:
                q &= Q("match", status=status)
            
            # فیلتر تاریخ
            if from_date or to_date:
                date_range = {}
                if from_date:
                    date_range["gte"] = from_date
                if to_date:
                    date_range["lte"] = to_date
                q &= Q("range", date=date_range)
            
            return [hit.to_dict() for hit in doc_class.search().query(q).execute()]

        all_searches = {
            "users": lambda: build_search(UserDocument, ["first_name", "last_name", "email", "full_name"]),
            "lawyers": lambda: build_search(LawyerProfileDocument, ["full_name", "expertise", "degree"]),
            "clients": lambda: build_search(ClientProfileDocument, ["full_name", "national_id"]),
            "appointments": lambda: build_search(AppointmentDocument, ["lawyer_name", "status", "date"], status=status_filter, from_date=from_date, to_date=to_date),
            "payments": lambda: build_search(PaymentDocument, ["transaction_id", "status"]),
            "cases": lambda: build_search(CaseDocument, ["case_number", "title", "status"], status=status_filter, from_date=from_date, to_date=to_date),
        }

        # اعمال فیلتر type
        if entity_type in all_searches:
            results[entity_type] = all_searches[entity_type]()
        else:
            for key, func in all_searches.items():
                results[key] = func()

        # Cache
        cache_conn.set(cache_key, str(results), ex=CACHE_TIMEOUT_RESULTS)
        return Response({"query": query, "results": results}, status=200)
# ---------------------------- Search History ----------------------------
class SearchHistoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_conn = get_redis_connection()
        cache_key = f"search_history:{request.user.id}"

        cached = cache_conn.get(cache_key)
        if cached:
            return Response({"history": eval(cached)})

        searches = SearchHistory.objects.filter(user=request.user).order_by('-created_at').values("query", "created_at")
        searches_list = list(searches)
        cache_conn.set(cache_key, str(searches_list), CACHE_TIMEOUT_SUGGEST)
        return Response({"history": searches_list}, status=200)

# ---------------------------- Search Suggestions / Autocomplete ----------------------------
class SearchSuggestionsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"suggestions": []})

        entity_type = request.query_params.get("type")  # optional: users, lawyers, clients, appointments, payments, cases
        cache_conn = get_redis_connection()
        cache_key = f"search_suggestions:{request.user.id}:{entity_type}:{query}"

        # کش
        cached = cache_conn.get(cache_key)
        if cached:
            return Response({"suggestions": eval(cached)})

        # ----------------- Recent Searches -----------------
        recent_qs = SearchHistory.objects.filter(user=request.user)
        if entity_type:
            recent_qs = recent_qs.filter(entity_type=entity_type)
        recent_searches = recent_qs.order_by('-created_at').values_list("query", flat=True)

        # ----------------- Popular Searches -----------------
        popular_qs = SearchHistory.objects.all()
        if entity_type:
            popular_qs = popular_qs.filter(entity_type=entity_type)
        popular_searches = popular_qs.values("query").annotate(count=Count("id")).order_by("-count")[:5].values_list("query", flat=True)

        # ترکیب و حذف تکراری‌ها، recent اولویت دارد
        suggestions = list(dict.fromkeys(list(recent_searches) + list(popular_searches)))

        # فیلتر با توجه به عبارت تایپ شده
        suggestions = [s for s in suggestions if query.lower() in s.lower()]

        # کش برای 3 دقیقه
        cache_conn.set(cache_key, str(suggestions), CACHE_TIMEOUT_SUGGEST)

        return Response({"suggestions": suggestions}, status=200)
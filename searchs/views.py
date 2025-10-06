from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from searchs.models import SearchHistory
from searchs.utils import preprocess_query
from users.models import User
from users.serializers import UserSerializer

# ---------------------------- Global Simple Search ----------------------------
class GlobalSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "لطفاً عبارت جستجو را وارد کنید."}, status=400)

        normalized_q = preprocess_query(query)

        # ثبت تاریخچه جستجو برای کاربر
        if request.user.is_authenticated:
            SearchHistory.objects.update_or_create(
                user=request.user,
                normalized_query=normalized_q,
                defaults={"query": query}
            )

        # جستجوی ساده در مدل User (قابل گسترش برای مدل‌های دیگر)
        users = User.objects.filter(
            first_name__icontains=query
        )[:10]
        users_data = UserSerializer(users, many=True).data

        results = {
            "users": users_data
        }

        return Response({"query": query, "results": results}, status=200)


# ---------------------------- Search History ----------------------------
class SearchHistoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        searches = SearchHistory.objects.filter(user=request.user).order_by('-created_at')[:10].values("query", "created_at")
        return Response({"history": list(searches)}, status=200)


# ---------------------------- Search Suggestions ----------------------------
class SearchSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        recent_searches = SearchHistory.objects.filter(user=request.user).order_by('-created_at')[:5].values_list("query", flat=True)
        suggestions = list(recent_searches)
        return Response({"suggestions": suggestions}, status=200)
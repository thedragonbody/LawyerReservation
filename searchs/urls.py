from django.urls import path
from .views import GlobalSearchView, SearchHistoryListView, SearchSuggestionsView

urlpatterns = [
    path('', GlobalSearchView.as_view(), name='global_search'),
    path('history/', SearchHistoryListView.as_view(), name='search_history'),
    path('suggestions/', SearchSuggestionsView.as_view(), name='search_suggestions'),
]
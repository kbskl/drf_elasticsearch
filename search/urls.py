from django.urls import path
from search.views import SearchUsers, SearchCategories, SearchArticles, SearchArticlesDjango

app_name = "search"

urlpatterns = [
    path('user/<str:query>/', SearchUsers.as_view()),
    path('category/<str:query>/', SearchCategories.as_view()),
    path('article/<str:query>/', SearchArticles.as_view()),
    path('article-django/<str:query>/', SearchArticlesDjango.as_view()),
]

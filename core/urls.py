from django.urls import path, include
from rest_framework import routers
from core.views import UserViewSet, CategoryViewSet, ArticleViewSet

app_name = "core"
router = routers.DefaultRouter()
router.register(r'user', UserViewSet)
router.register(r'category', CategoryViewSet)
router.register(r'article', ArticleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

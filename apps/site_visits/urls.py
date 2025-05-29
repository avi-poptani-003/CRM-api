# site_visits/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SiteVisitViewSet

router = DefaultRouter()
router.register(r'site-visits', SiteVisitViewSet, basename='sitevisit') # Matches your API endpoint

urlpatterns = [
    path('', include(router.urls)),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeadViewSet

router = DefaultRouter()
router.register(r'leads', LeadViewSet, basename='lead')

urlpatterns = [
    path('', include(router.urls)),
    path('leads/import/', LeadViewSet.as_view({'post': 'import_leads'}), name='lead-import'),
    path('leads/export/', LeadViewSet.as_view({'get': 'export'}), name='lead-export'),
    path('leads/dashboard_stats/', LeadViewSet.as_view({'get': 'dashboard_stats'}), name='lead-dashboard-stats'),
]

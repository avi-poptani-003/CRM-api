from rest_framework.routers import DefaultRouter
from .views import SiteVisitViewSet

router = DefaultRouter()
router.register(r'site-visits', SiteVisitViewSet)

urlpatterns = router.urls
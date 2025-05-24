from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(('apps.accounts.urls', 'accounts'), namespace='accounts')),
    path('api/', include(('apps.property.urls', 'property'), namespace='property')),
    path('api/', include(('apps.leads.urls', 'leads'), namespace='leads')),
]

# Add media URL configuration for property images
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

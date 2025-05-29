# site_visits_app/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import SiteVisit
from .serializers import SiteVisitSerializer

class SiteVisitViewSet(viewsets.ModelViewSet):
    serializer_class = SiteVisitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = SiteVisit.objects.all() # Start with all, then filter if necessary for user roles

        # Correctly use select_related with the actual ForeignKey field names
        # Remove prefetching of 'agent__profile' and 'client_user__profile'
        # if your User model does not have a 'profile' accessor or if it's not needed.
        # The BasicUserSerializer will attempt to get phone_number gracefully.
        return queryset.select_related(
            'property',
            'agent',
            'client_user'
        ).prefetch_related(
            'property__images' # Keep this if your Property model has an 'images' related manager
                               # and BasicPropertySerializer needs it for performance.
        ).order_by('-date', '-time')

    def perform_create(self, serializer):
        # Logic is now primarily in serializer.create()
        serializer.save()
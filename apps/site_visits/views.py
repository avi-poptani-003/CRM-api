# site_visits_app/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated # Or your preferred permission
from .models import SiteVisit
from .serializers import SiteVisitSerializer

class SiteVisitViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows site visits to be viewed or edited.
    """
    serializer_class = SiteVisitSerializer
    permission_classes = [IsAuthenticated] # Adjust permissions as needed

    def get_queryset(self):
        """
        Optionally override to customize the queryset, e.g., based on user role.
        Admins/Managers might see all visits, Agents might see only their assigned visits.
        """
        user = self.request.user
        queryset = SiteVisit.objects.all()

        # Example: If agents should only see their visits (and you have a 'role' on user model)
        # if hasattr(user, 'role') and user.role == 'agent':
        #     queryset = queryset.filter(agent=user)
        # elif hasattr(user, 'role') and user.role == 'manager':
        #     # Managers might see visits by agents they manage, or all in a region, etc.
        #     pass # Add manager-specific filtering if needed

        # Optimized queryset
        return queryset.select_related(
            'property',
            'agent',    # For agent_details
            'client_user' # For client_details
        ).prefetch_related(
            'property__images' # Example if Property model has 'images' and it's used
        ).order_by('-date', '-time')

    def perform_create(self, serializer):
        # The logic for client creation/linking and agent assignment is now robustly
        # handled within the SiteVisitSerializer.create() method.
        # You could add additional logic here if needed, e.g., sending notifications.
        serializer.save()

    # You can add perform_update if specific logic is needed during updates,
    # but typically serializer.save() handles it based on instance presence.
    # def perform_update(self, serializer):
    #     serializer.save()
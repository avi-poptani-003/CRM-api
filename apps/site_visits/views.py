from rest_framework import viewsets, permissions
from .models import SiteVisit
from .serializers import SiteVisitSerializer, SiteVisitCreateUpdateSerializer
from apps.accounts.permission import IsAgentOrAbove  # Assuming you have this permission

class SiteVisitViewSet(viewsets.ModelViewSet):
    queryset = SiteVisit.objects.all().select_related('property', 'client', 'agent')
    serializer_class = SiteVisitSerializer

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SiteVisitCreateUpdateSerializer
        return SiteVisitSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAgentOrAbove] # Only agents/admins can manage visits
        else:
            permission_classes = [permissions.IsAuthenticated] # Authenticated users can view
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        # Example: Filter visits based on the logged-in user's role
        user = self.request.user
        if user.is_authenticated:
            if user.role == 'agent':
                return self.queryset.filter(agent=user) | self.queryset.filter(client=user)
            elif user.role == 'client':
                return self.queryset.filter(client=user)
            elif user.role == 'admin':
                return self.queryset # Admins see all
        return SiteVisit.objects.none() # No visits for unauthenticated users or other roles
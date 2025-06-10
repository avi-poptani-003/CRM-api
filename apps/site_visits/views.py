# site_visits_app/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated # Or your preferred permission
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
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
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Returns a short list of the next upcoming site visits.
        """
        today = timezone.now().date()
        
        # Filter for visits that are from today onwards and are either scheduled or confirmed
        upcoming_visits = self.get_queryset().filter(
            date__gte=today,
            status__in=['scheduled', 'confirmed']
        ).order_by('date', 'time')[:5]  # Order by ascending date and time, limit to 5

        serializer = self.get_serializer(upcoming_visits, many=True)
        return Response(serializer.data)

    # You can add perform_update if specific logic is needed during updates,
    # but typically serializer.save() handles it based on instance presence.
    # def perform_update(self, serializer):
    #     serializer.save()

    @action(detail=False, methods=['get'])
    def summary_counts(self, request):
        """
        Returns a summary count of total, pending, and upcoming site visits.
        """
        queryset = self.get_queryset()
        today = timezone.now().date()

        # Calculate the counts
        total_visits = queryset.count()
        
        # "Pending" visits are those that are either scheduled or confirmed
        pending_visits = queryset.filter(status__in=['scheduled', 'confirmed']).count()
        
        # Upcoming visits are those scheduled for today or any future date
        upcoming_visits = queryset.filter(date__gte=today).count()

        return Response({
            'total_visits': total_visits,
            'pending_visits': pending_visits,
            'upcoming_visits': upcoming_visits,
        })
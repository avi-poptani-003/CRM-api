from django.db import models
from apps.property.models import Property  # Assuming Property is in apps.property
from apps.accounts.models import User  # Assuming CustomUser for agents/clients

class SiteVisit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='site_visits')
    client = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='client_visits')
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='agent_scheduled_visits')
    date = models.DateField()
    time = models.TimeField()
    status_choices = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='scheduled')
    feedback = models.TextField(blank=True, null=True)
    # You might want to add a field for location if it's different from property's
    # location = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Visit to {self.property.title} on {self.date} by {self.agent.username}"
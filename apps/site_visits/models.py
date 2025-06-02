# site_visits_app/models.py
from django.db import models
from django.conf import settings
from apps.property.models import Property # Adjust import as per your project


class SiteVisit(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='site_visits_for_property'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='site_visits_as_agent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
        # Ensure this User model has a 'role' field (e.g., role='agent')
        # or some other way to identify agents, which will be used in serializers/admin.
    )
    client_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='site_visits_as_client',
        on_delete=models.CASCADE
        # Ensure this User model can have a 'role' field (e.g., role='client')
    )
    client_name_manual = models.CharField(max_length=255, blank=True, null=True, help_text="Client name if not linked to a user account")
    client_phone_manual = models.CharField(max_length=20, blank=True, null=True, help_text="Client phone if not linked to a user account")
    date = models.DateField()
    time = models.CharField(max_length=20) # Consider models.TimeField if appropriate for your time string format
    status = models.CharField(
        max_length=50,
        choices=[
            ('scheduled', 'Scheduled'),
            ('confirmed', 'Confirmed'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('no_show', 'No Show'),
        ],
        default='scheduled'
    )
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']
        verbose_name = "Site Visit"
        verbose_name_plural = "Site Visits"

    def __str__(self):
        client_display_name_str = "N/A Client"
        if self.client_user:
            client_display_name_str = self.client_user.get_full_name() or self.client_user.username
        elif self.client_name_manual:
            client_display_name_str = self.client_name_manual
        
        property_title_str = self.property.title if self.property else "N/A Property"
        
        return f"Visit for {property_title_str} with {client_display_name_str} on {self.date}"
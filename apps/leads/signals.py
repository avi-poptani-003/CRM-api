from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Lead
from .utils import send_lead_assignment_email
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(pre_save, sender=Lead)
def handle_lead_assignment(sender, instance, **kwargs):
    """
    Signal handler to send email notifications when a lead is assigned to an agent.
    """
    try:
        # If this is a new lead, old_instance won't exist
        old_instance = Lead.objects.get(pk=instance.pk)
        old_assigned_to = old_instance.assigned_to
    except Lead.DoesNotExist:
        old_assigned_to = None
    
    new_assigned_to = instance.assigned_to
    
    # Send email if:
    # 1. Lead is newly assigned (old_assigned_to was None)
    # 2. Lead is reassigned to a different agent
    if new_assigned_to and (old_assigned_to != new_assigned_to):
        send_lead_assignment_email(instance, new_assigned_to)

from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import SiteVisit 
from .utils import send_site_visit_assignment_email

@receiver(pre_save, sender=SiteVisit)
def handle_site_visit_assignment(sender, instance, **kwargs):
    """
    Signal handler to send email notifications when a site visit is assigned to an agent.
    """
    try:
        # If this is a new site visit, old_instance won't exist
        old_instance = SiteVisit.objects.get(pk=instance.pk)
        old_agent = old_instance.agent
    except SiteVisit.DoesNotExist:
        old_agent = None
    
    new_agent = instance.agent
    
    # Send email if:
    # 1. Site visit is newly assigned (old_agent was None)
    # 2. Site visit is reassigned to a different agent
    if new_agent and (old_agent != new_agent):
        send_site_visit_assignment_email(instance, new_agent)

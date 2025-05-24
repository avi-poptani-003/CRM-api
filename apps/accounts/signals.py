from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def set_superuser_as_admin(sender, instance, created, **kwargs):
    """
    Signal to ensure superusers always have the admin role
    """
    if instance.is_superuser and instance.role != 'admin':
        instance.role = 'admin'
        instance.save(update_fields=['role'])
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    ADMIN = 'admin', _('Admin')
    MANAGER = 'manager', _('Manager')
    AGENT = 'agent', _('Agent')


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    # Additional fields for the user model
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.AGENT,
    )
    
    # Additional metadata fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Specify USERNAME_FIELD and REQUIRED_FIELDS
    # email is already a field in AbstractUser, as are first_name and last_name
    # USERNAME_FIELD = 'username' # This is the default in AbstractUser
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'phone_number']
    
    
    class Meta:
        db_table = 'users'
        
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == UserRole.ADMIN or self.is_superuser
    
    def is_manager(self):
        return self.role == UserRole.MANAGER
    
    def is_agent(self):
        return self.role == UserRole.AGENT
        
    def save(self, *args, **kwargs):
        # Automatically set superusers as admins
        if self.is_superuser and self.role != UserRole.ADMIN:
            self.role = UserRole.ADMIN
        super().save(*args, **kwargs)


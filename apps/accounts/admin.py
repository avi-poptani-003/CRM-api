from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model() # loads the custom model from the models.py


class UserAdmin(BaseUserAdmin):
    """
    Custom admin for the User model
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active') #in the localhost:8000/admin it show this fields to the user.
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser') # Adds sidebar filters for easy sorting.
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'phone_number' ,'password1', 'password2', 'role'),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)


admin.site.register(User, UserAdmin)
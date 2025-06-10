# apps/leads/admin.py

from django.contrib import admin
from .models import Lead

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    # --- THIS LINE IS UPDATED ---
    list_display = ('name', 'status', 'property', 'priority', 'assigned_to', 'created_at') # Added 'property'
    # --- END OF UPDATE ---
    
    list_filter = ('status', 'source', 'priority', 'created_at', 'property') # Also added 'property' here for filtering
    search_fields = ('name', 'email', 'phone', 'company')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.save()
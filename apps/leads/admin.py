from django.contrib import admin
from .models import Lead

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'status', 'source', 'priority', 'assigned_to', 'created_at')
    list_filter = ('status', 'source', 'priority', 'created_at')
    search_fields = ('name', 'email', 'phone', 'company')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.save()

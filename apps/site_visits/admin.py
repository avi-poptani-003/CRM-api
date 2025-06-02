# site_visits_app/admin.py
from django.contrib import admin
from .models import SiteVisit
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'property_title',
        'client_display_name',
        'agent_display_name',
        'date',
        'time',
        'status',
        'created_at'
    )
    list_filter = ('status', 'date', 'agent', 'property__property_type') # Filter by property type
    search_fields = (
        'property__title',
        'client_user__username',
        'client_user__first_name',
        'client_user__last_name',
        'client_name_manual',
        'agent__username',        # Search in related agent's username
        'agent__first_name',
        'agent__last_name',
        'status'
    )
    readonly_fields = ('created_at', 'updated_at')

    raw_id_fields = ('property', 'agent', 'client_user')

    fieldsets = (
        (None, { # Main section for the visit
            'fields': ('property', 'status')
        }),
        ('Client Information', {
            'fields': (
                'client_user',            # Link to a User model instance for the client
                'client_name_manual',     # Manual entry if no User account is linked
                'client_phone_manual'     # Manual entry if no User account is linked
            )
        }),
        ('Scheduling & Assignment', {
            'fields': ('date', 'time', 'agent')
        }),
        ('Feedback & Timestamps', {
            'classes': ('collapse',), # This section will be collapsible
            'fields': ('feedback', 'created_at', 'updated_at')
        }),
    )

    # MODIFIED: Filter agent dropdown in admin
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "agent":
            # Assumes User model has a 'role' field. Adjust if your logic is different.
            kwargs["queryset"] = User.objects.filter(role="agent")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def property_title(self, obj):
        if obj.property:
            return obj.property.title
        return None # Or "N/A"
    property_title.short_description = 'Property'

    def client_display_name(self, obj):
        if obj.client_user:
            name = obj.client_user.get_full_name()
            return name if name else obj.client_user.username
        return obj.client_name_manual or 'N/A'
    client_display_name.short_description = 'Client'

    def agent_display_name(self, obj):
        if obj.agent:
            name = obj.agent.get_full_name()
            return name if name else obj.agent.username
        return 'N/A' # Or 'Unassigned'
    agent_display_name.short_description = 'Agent'

    def get_queryset(self, request):
        # Optimize database queries for the admin list view
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'property',
            'agent',
            'client_user' # Ensure this matches the ForeignKey name in your SiteVisit model
        )
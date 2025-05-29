# # site_visits_app/admin.py
# from django.contrib import admin
# from .models import SiteVisit

# @admin.register(SiteVisit)
# class SiteVisitAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'property_title',
#         'client_display_name',
#         'agent_display_name',
#         'date',
#         'time',
#         'status',
#         'created_at'
#     )
#     list_filter = ('status', 'date', 'agent', 'property__property_type') # Filter by property type
#     search_fields = (
#         'property__title',
#         'client_user__username',
#         'client_user__first_name',
#         'client_user__last_name',
#         'client_name_manual',
#         'agent__username',
#         'agent__first_name',
#         'agent__last_name',
#         'status'
#     )
#     readonly_fields = ('created_at', 'updated_at')

#     # Use raw_id_fields for better performance with many related objects
#     raw_id_fields = ('property', 'agent', 'client_user')

#     fieldsets = (
#         (None, {
#             'fields': ('property', 'status')
#         }),
#         ('Client Information', {
#             'fields': ('client_user', 'client_name_manual', 'client_phone_manual')
#         }),
#         ('Scheduling & Assignment', {
#             'fields': ('date', 'time', 'agent')
#         }),
#         ('Feedback & Timestamps', {
#             'classes': ('collapse',), # Collapsible section
#             'fields': ('feedback', 'created_at', 'updated_at')
#         }),
#     )

#     # Custom methods to display related object names in list_display
#     def property_title(self, obj):
#         if obj.property:
#             return obj.property.title
#         return None
#     property_title.short_description = 'Property' # Column header

#     def client_display_name(self, obj):
#         if obj.client_user:
#             name = obj.client_user.get_full_name()
#             return name if name else obj.client_user.username
#         return obj.client_name_manual or 'N/A'
#     client_display_name.short_description = 'Client'

#     def agent_display_name(self, obj):
#         if obj.agent:
#             name = obj.agent.get_full_name()
#             return name if name else obj.agent.username
#         return 'N/A'
#     agent_display_name.short_description = 'Agent'

#     def get_queryset(self, request):
#         # Optimize queryset for admin display
#         return super().get_queryset(request).select_related(
#             'property',
#             'agent',
#             'client_user'
#         )

# # If you have other models in site_visits_app, register them here as well.
# # For example:
# # from .models import AnotherSiteVisitModel
# # admin.site.register(AnotherSiteVisitModel)

# site_visits_app/admin.py
from django.contrib import admin
from .models import SiteVisit # Assuming your SiteVisit model is in the current app's models.py

@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'property_title',        # Custom method to display property's title
        'client_display_name',   # Custom method for client's name
        'agent_display_name',    # Custom method for agent's name
        'date',
        'time',
        'status',
        'created_at'
    )
    list_filter = (
        'status',
        'date',
        'agent',                  # Filters by the 'agent' ForeignKey
        'property__property_type' # Filters by 'property_type' of the related 'property'
    )
    search_fields = (
        'property__title',        # Search in related property's title
        'client_user__username',  # Search in related client_user's username
        'client_user__first_name',
        'client_user__last_name',
        'client_name_manual',     # Search in the manually entered client name
        'agent__username',        # Search in related agent's username
        'agent__first_name',
        'agent__last_name',
        'status'                  # Search in the status field
    )
    readonly_fields = ('created_at', 'updated_at')

    # Use raw_id_fields for ForeignKey fields for better performance
    # and usability if you have many properties or users.
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
            # The help_text in your SiteVisit model for client_name_manual and client_phone_manual
            # will be displayed here, clarifying their purpose.
        }),
        ('Scheduling & Assignment', {
            'fields': ('date', 'time', 'agent')
        }),
        ('Feedback & Timestamps', {
            'classes': ('collapse',), # This section will be collapsible
            'fields': ('feedback', 'created_at', 'updated_at')
        }),
    )

    # Custom method to display the property's title in list_display
    def property_title(self, obj):
        if obj.property:
            return obj.property.title
        return None
    property_title.short_description = 'Property' # Sets the column header name

    # Custom method to display the client's name (from User or manual field)
    def client_display_name(self, obj):
        if obj.client_user:
            name = obj.client_user.get_full_name()
            return name if name else obj.client_user.username
        return obj.client_name_manual or 'N/A'
    client_display_name.short_description = 'Client'

    # Custom method to display the agent's name
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
from django.contrib import admin
from .models import Property, PropertyImage, PropertyAmenity, PropertySpecification

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1

class PropertyAmenityInline(admin.TabularInline):
    model = PropertyAmenity
    extra = 1

class PropertySpecificationInline(admin.TabularInline):
    model = PropertySpecification
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'property_type', 'listing_type', 'status', 'price', 'location', 'created_at')
    search_fields = ('title', 'location', 'property_sub_type')
    list_filter = ('property_type', 'status', 'listing_type')
    inlines = [PropertyImageInline, PropertyAmenityInline, PropertySpecificationInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'is_primary', 'created_at')
    list_filter = ('is_primary',)

@admin.register(PropertyAmenity)
class PropertyAmenityAdmin(admin.ModelAdmin):
    list_display = ('property', 'name')

@admin.register(PropertySpecification)
class PropertySpecificationAdmin(admin.ModelAdmin):
    list_display = ('property', 'key', 'value')

# apps/property/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class PropertyType(models.TextChoices):
    HOUSE = 'house', 'House'
    COMMERCIAL = 'commercial', 'Commercial'
    LAND = 'land', 'Land'

class PropertyStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    UNDER_CONSTRUCTION = 'under_construction', 'Under Construction'
    COMING_SOON = 'coming_soon', 'Coming Soon'
    SOLD_OUT = 'sold_out', 'Sold Out'

class ListingType(models.TextChoices):
    FOR_SALE = 'for_sale', 'For Sale'
    FOR_RENT = 'for_rent', 'For Rent'

class Property(models.Model):
    # Basic Information
    title = models.CharField(max_length=255)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    property_sub_type = models.CharField(max_length=50)
    listing_type = models.CharField(max_length=20, choices=ListingType.choices, default=ListingType.FOR_SALE)
    status = models.CharField(max_length=20, choices=PropertyStatus.choices, default=PropertyStatus.AVAILABLE)
    
    # Location and Price
    location = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    
    # Area Information
    area = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total area in sq.ft")
    carpet_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Carpet area in sq.ft")
    dimensions_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dimensions_width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Property Details
    description = models.TextField()
    floor = models.CharField(max_length=50, null=True, blank=True)
    facing = models.CharField(max_length=50, null=True, blank=True)
    age_of_property = models.CharField(max_length=50, null=True, blank=True)
    balconies = models.CharField(max_length=50, null=True, blank=True)
    furnishing_status = models.CharField(max_length=50, null=True, blank=True)
    possession_status = models.CharField(max_length=50, null=True, blank=True)
    possession_timeline = models.CharField(max_length=50, null=True, blank=True)
    
    # EMI Calculator Information
    loan_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    loan_term = models.IntegerField(null=True, blank=True, help_text="Loan term in years")
    
    # Contact Information
    contact_name = models.CharField(max_length=100, null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    thumbnail_image = models.ImageField(upload_to='property_images/', null=True, blank=True)
    
    # Progress (for under construction properties)
    progress = models.IntegerField(default=0, help_text="Construction progress in percentage")
    units_total = models.IntegerField(default=0)
    units_available = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Properties"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def units_available_display(self):
        if self.units_total > 0:
            return f"{self.units_available} of {self.units_total} units available"
        return "N/A"

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='property_images/')
    is_primary = models.BooleanField(default=False)  # Added is_primary field
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Image for {self.property.title} ({self.id})"

class PropertyAmenity(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='amenities')
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = "Property Amenities"
    
    def __str__(self):
        return self.name

class PropertySpecification(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='specifications')
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    
    class Meta:
        verbose_name_plural = "Property Specifications"
    
    def __str__(self):
        return f"{self.key}: {self.value}"
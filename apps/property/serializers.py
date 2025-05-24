# apps/property/serializers.py
from rest_framework import serializers
from .models import Property, PropertyImage
import logging

logger = logging.getLogger(__name__)

class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'is_primary', 'created_at']
        read_only_fields = ['id', 'created_at']

class PropertySerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Property
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        try:
            request = self.context.get('request')
            if not request:
                raise serializers.ValidationError("Request context is required")

            property_instance = Property.objects.create(**validated_data)
            
            # Handle image uploads
            images = request.FILES.getlist('images')
            logger.info(f"Processing {len(images)} images")
            
            for i, image in enumerate(images):
                PropertyImage.objects.create(
                    property=property_instance,
                    image=image,
                    is_primary=(i == 0)
                )
            
            # Set thumbnail if images exist
            if images:
                property_instance.thumbnail_image = images[0]
                property_instance.save()
            
            return property_instance
        
        except Exception as e:
            logger.exception(f"Error creating property: {str(e)}")
            raise
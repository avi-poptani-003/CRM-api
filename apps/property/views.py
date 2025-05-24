# apps/property/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Property, PropertyImage
from .serializers import PropertySerializer, PropertyImageSerializer

class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            user = self.request.user
            # Return all properties for admins and managers
            if hasattr(user, 'is_admin') and (user.is_admin() or user.is_manager()):
                return Property.objects.all().order_by('-created_at')
            # Return own properties for others
            return Property.objects.filter(created_by=user).order_by('-created_at')
        except Exception as e:
            print(f"Error in get_queryset: {str(e)}")
            return Property.objects.none()
    
    def perform_create(self, serializer):
        # Set the created_by field to the current user
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_primary_image(self, request, pk=None):
        property_instance = self.get_object()
        image_id = request.data.get('image_id')
        
        if not image_id:
            return Response({'error': 'Image ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the image
        try:
            image = PropertyImage.objects.get(id=image_id, property=property_instance)
        except PropertyImage.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Set all images as non-primary
        PropertyImage.objects.filter(property=property_instance).update(is_primary=False)
        
        # Set the selected image as primary
        image.is_primary = True
        image.save()
        
        return Response({'success': True})
    
    @action(detail=True, methods=['delete'])
    def delete_image(self, request, pk=None):
        property_instance = self.get_object()
        image_id = request.data.get('image_id')
        
        if not image_id:
            return Response({'error': 'Image ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the image
        try:
            image = PropertyImage.objects.get(id=image_id, property=property_instance)
        except PropertyImage.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if this is the primary image
        is_primary = image.is_primary
        
        # Delete the image
        image.delete()
        
        # If this was the primary image, set another image as primary if available
        if is_primary:
            remaining_image = PropertyImage.objects.filter(property=property_instance).first()
            if remaining_image:
                remaining_image.is_primary = True
                remaining_image.save()
        
        return Response({'success': True})
    
    def destroy(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                instance = self.get_object()
                # Delete all associated images first
                PropertyImage.objects.filter(property=instance).delete()
                # Then delete the property
                instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': f'Failed to delete property: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
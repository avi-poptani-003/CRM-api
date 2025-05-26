from rest_framework import serializers
from .models import SiteVisit
from apps.property.serializers import PropertySerializer # Import if you want nested property details
from apps.accounts.serializers import UserSerializer # Import if you want nested user details

class SiteVisitSerializer(serializers.ModelSerializer):
    property_details = PropertySerializer(source='property', read_only=True)
    client_details = UserSerializer(source='client', read_only=True)
    agent_details = UserSerializer(source='agent', read_only=True)

    class Meta:
        model = SiteVisit
        fields = '__all__'
        # Or specify fields: ['id', 'property', 'client', 'agent', 'date', 'time', 'status', 'feedback', 'property_details', 'client_details', 'agent_details']

class SiteVisitCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteVisit
        fields = ['property', 'client', 'agent', 'date', 'time', 'status', 'feedback']
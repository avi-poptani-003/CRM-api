# site_visits_app/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SiteVisit
from apps.property.models import Property # Adjust import as per your project

User = get_user_model()

class BasicUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField() # Changed to SerializerMethodField

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'phone_number']

    def get_full_name(self, obj):
        name = obj.get_full_name()
        return name if name else obj.username

    def get_phone_number(self, obj):
        # Attempt to get phone number from various common locations
        if hasattr(obj, 'phone_number') and obj.phone_number: # Direct attribute
            return obj.phone_number
        if hasattr(obj, 'profile') and hasattr(obj.profile, 'phone_number') and obj.profile.phone_number: # From a 'profile' object
            return obj.profile.phone_number
        return None

class BasicPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'title', 'location', 'property_type', 'contact_name', 'contact_phone']


class SiteVisitSerializer(serializers.ModelSerializer):
    property_details = BasicPropertySerializer(source='property', read_only=True)
    agent_details = BasicUserSerializer(source='agent', read_only=True)
    client_details = BasicUserSerializer(source='client_user', read_only=True)

    property = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())
    agent = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)

    client_name = serializers.CharField(write_only=True, required=True, allow_blank=False)
    client_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = SiteVisit
        fields = [
            'id',
            'property', 'property_details',
            'agent', 'agent_details',
            'client_user', 'client_details',
            'client_name', 'client_phone',
            'client_name_manual', 'client_phone_manual',
            'date', 'time', 'status', 'feedback',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'client_user', 'client_name_manual', 'client_phone_manual')

    def create(self, validated_data):
        client_name_input = validated_data.pop('client_name')
        client_phone_input = validated_data.pop('client_phone', None)
        
        client_user_instance = None
        created_new_user = False

        # Attempt to find existing user by phone or email (if provided and makes sense for your User model)
        # This logic needs to be robust based on your User model's fields (e.g., unique email, phone_number field)
        if client_phone_input:
            # Example: Assuming your User model (or a related profile) has a 'phone_number' field.
            # Adjust this query:
            if hasattr(User, 'phone_number'):
                 client_user_instance = User.objects.filter(phone_number=client_phone_input).first()
            elif hasattr(User, 'profile') and hasattr(User.profile, 'phone_number'):
                 client_user_instance = User.objects.filter(profile__phone_number=client_phone_input).first()

        if not client_user_instance and '@' in client_name_input: # Rudimentary check if client_name might be an email
            client_user_instance = User.objects.filter(email__iexact=client_name_input).first()

        # If no existing user, you might create one (simplified example)
        if not client_user_instance and client_name_input:
            try:
                # Ensure username is unique. This is a very basic way.
                # Production systems need more robust unique username generation.
                base_username = client_name_input.lower().replace(" ", "_").replace("@", "_at_")
                username_candidate = base_username
                counter = 1
                while User.objects.filter(username=username_candidate).exists():
                    username_candidate = f"{base_username}_{counter}"
                    counter += 1

                client_user_instance, created_new_user = User.objects.get_or_create(
                    username=username_candidate,
                    defaults={
                        'first_name': client_name_input.split(' ')[0],
                        'last_name': " ".join(client_name_input.split(' ')[1:]) if len(client_name_input.split(' ')) > 1 else '',
                        'email': client_name_input if '@' in client_name_input else f'{username_candidate}@example.com', # Placeholder email
                    }
                )
                if created_new_user:
                    client_user_instance.set_unusable_password()
                    client_user_instance.save()
                    print(f"Created new client user: {client_user_instance.username}")
                    # If you have a profile model to store phone_number:
                    # if hasattr(client_user_instance, 'profile') and client_phone_input:
                    #     client_user_instance.profile.phone_number = client_phone_input
                    #     client_user_instance.profile.save()
                    # Or if phone_number is directly on User model and wasn't set via defaults:
                    # elif hasattr(client_user_instance, 'phone_number') and client_phone_input and not client_user_instance.phone_number:
                    #     client_user_instance.phone_number = client_phone_input
                    #     client_user_instance.save()


            except Exception as e:
                print(f"Error creating client user: {e}")
                # Fallback to manual fields if user creation fails
                return SiteVisit.objects.create(
                    client_name_manual=client_name_input,
                    client_phone_manual=client_phone_input,
                    **validated_data
                )
        
        site_visit = SiteVisit.objects.create(
            client_user=client_user_instance,
            client_name_manual=client_name_input if not client_user_instance else None,
            client_phone_manual=client_phone_input if not client_user_instance else None,
            **validated_data
        )
        return site_visit
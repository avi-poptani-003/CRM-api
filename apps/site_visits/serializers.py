# site_visits_app/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SiteVisit
from apps.property.models import Property # Adjust import as per your project

User = get_user_model()

class BasicUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        # Ensure 'role' is a field on your User model or adapt to access it (e.g., via a profile)
        fields = ['id', 'username', 'full_name', 'email', 'phone_number', 'role']

    def get_full_name(self, obj):
        name = obj.get_full_name()
        return name if name else obj.username

    def get_phone_number(self, obj):
        if hasattr(obj, 'phone_number') and obj.phone_number:
            return obj.phone_number
        if hasattr(obj, 'profile') and hasattr(obj.profile, 'phone_number') and obj.profile.phone_number:
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
    
    # MODIFIED: Filter agents by role
    agent = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='agent'), # Assumes User model has a 'role' field
        allow_null=True,
        required=False
    )

    # These fields are used for creating/identifying the client
    client_name = serializers.CharField(write_only=True, required=True, allow_blank=False)
    client_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = SiteVisit
        fields = [
            'id',
            'property', 'property_details',
            'agent', 'agent_details',
            'client_user', 'client_details',      # For associating with an existing/new User model client
            'client_name', 'client_phone',        # Write-only fields for client identification/creation input
            'client_name_manual', 'client_phone_manual', # For clients not linked to a user account
            'date', 'time', 'status', 'feedback',
            'created_at', 'updated_at'
        ]
        # client_user, client_name_manual, client_phone_manual are now handled by create logic
        read_only_fields = ('id', 'created_at', 'updated_at', 'client_user', 'client_name_manual', 'client_phone_manual')

    def create(self, validated_data):
        client_name_input = validated_data.pop('client_name')
        client_phone_input = validated_data.pop('client_phone', None)
        
        client_user_instance = None
        created_new_user = False # To track if a new user was made

        # Attempt to find existing user by phone or email (if provided and makes sense for your User model)
        if client_phone_input:
            # Adjust this query based on your User model's phone number field
            if hasattr(User, 'phone_number'): # Direct attribute on User
                 client_user_instance = User.objects.filter(phone_number=client_phone_input).first()
            elif hasattr(User, 'profile') and hasattr(User.profile, 'phone_number'): # On a related 'profile'
                 client_user_instance = User.objects.filter(profile__phone_number=client_phone_input).first()

        if not client_user_instance and '@' in client_name_input: # Rudimentary check if client_name might be an email
            client_user_instance = User.objects.filter(email__iexact=client_name_input).first()

        # If no existing user, create one with 'client' role
        if not client_user_instance and client_name_input:
            try:
                base_username = client_name_input.lower().replace(" ", "_").replace("@", "_at_").replace(".", "_dot_")
                username_candidate = base_username
                counter = 1
                while User.objects.filter(username=username_candidate).exists():
                    username_candidate = f"{base_username}_{counter}"
                    counter += 1

                user_defaults = {
                    'first_name': client_name_input.split(' ')[0],
                    'last_name': " ".join(client_name_input.split(' ')[1:]) if len(client_name_input.split(' ')) > 1 else '',
                    'email': client_name_input if '@' in client_name_input else f'{username_candidate}@example.com', # Placeholder email
                    'role': 'client'  # MODIFIED: Assign 'client' role
                }
                # Add phone number to defaults if your User model supports it directly and it's unique
                # if client_phone_input and hasattr(User, 'phone_number'):
                #     user_defaults['phone_number'] = client_phone_input
                
                client_user_instance, created_new_user = User.objects.get_or_create(
                    username=username_candidate, # Or use email if it's unique and preferred for username
                    defaults=user_defaults
                )
                
                if created_new_user:
                    client_user_instance.set_unusable_password()
                    # If role or phone_number wasn't set via defaults (e.g., on a profile), set and save here.
                    # Example for phone on profile:
                    # if hasattr(client_user_instance, 'profile') and client_phone_input:
                    #     client_user_instance.profile.phone_number = client_phone_input
                    #     client_user_instance.profile.save()
                    client_user_instance.save()
                    print(f"Created new client user: {client_user_instance.username} with role 'client'")

            except Exception as e: # Catch potential errors during user creation (e.g., IntegrityError if username/email not unique)
                print(f"Error creating client user: {e}. Falling back to manual fields.")
                # If user creation fails, save with manual fields.
                # Ensure 'agent' is still in validated_data if it was passed.
                return SiteVisit.objects.create(
                    client_name_manual=client_name_input,
                    client_phone_manual=client_phone_input,
                    **validated_data  # validated_data here will contain 'property', 'agent' (if any), 'date', 'time', 'status'
                )
        
        # Prepare data for SiteVisit creation
        site_visit_data = {
            'client_user': client_user_instance,
            # Only fill manual fields if no client_user_instance is associated or if a new user wasn't successfully created/linked
            'client_name_manual': client_name_input if not client_user_instance or created_new_user == False else None,
            'client_phone_manual': client_phone_input if not client_user_instance or created_new_user == False else None,
            **validated_data # Includes 'property', 'agent', 'date', 'time', 'status', 'feedback' (if any)
        }
        
        site_visit = SiteVisit.objects.create(**site_visit_data)
        return site_visit
from django.contrib.auth import get_user_model
from rest_framework import generics, status, permissions # Make sure permissions is imported
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)
# Assuming your permission.py file is in the same directory and you need classes from it for other views,
# you might import them here. For this specific change, we are using built-in DRF permissions
# and the IsAdminUser class defined below.
# from .permission import IsManager # Example if you needed it elsewhere

User = get_user_model()

# Custom permission for admin users (used for POST in UserListCreateView)
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token view that uses our serializer with additional user data
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data.get('access')
            refresh = response.data.get('refresh')
            response.set_cookie(
                key='access_token',
                value=access,
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE, # Use settings for secure flag
                samesite='Lax',
                max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()
            )
            response.set_cookie(
                key='refresh_token',
                value=refresh,
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE, # Use settings for secure flag
                samesite='Lax',
                max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()
            )
            response.data.pop('access', None)
            response.data.pop('refresh', None)
        return response


class RegisterView(generics.CreateAPIView):
    """
    API view for user registration (Manager and Agent roles only by frontend logic, backend allows any for now)
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny] # Or restrict further if needed, e.g., IsAdminUser


class UserListCreateView(generics.ListCreateAPIView):
    """
    API view for listing all users (all authenticated users)
    and creating new users (admin only).
    """
    queryset = User.objects.all()
    # Default serializer_class for GET, overridden by get_serializer_class if needed
    # serializer_class = UserSerializer # Not strictly necessary if get_serializer_class covers all cases

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserRegistrationSerializer
        return UserSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.request.method == 'POST':
            # Only admin users can create new users
            return [IsAdminUser()]
        # Any authenticated user can list users (GET)
        return [permissions.IsAuthenticated()]

    def post(self, request, *args, **kwargs): # This method is for CREATE
        # This logic will only be reached if IsAdminUser passes for POST requests,
        # as enforced by get_permissions.
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            if User.objects.filter(username=username).exists():
                return Response(
                    {"username": ["This username is already taken."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user = serializer.save() # User is created here

            # Send welcome email
            try:
                subject = f"Welcome to the Team, {user.first_name}!"
                message_body = f"""
Hi {user.first_name} {user.last_name},

Welcome to the team! Your account has been successfully created by an administrator.

Here are your account details:
Username: {user.username}
Role: {user.get_role_display()}

You can log in using the password that was set during your account creation.
If you have any questions, please contact your administrator.

Best regards,
The Admin Team
"""
                send_mail(
                    subject,
                    message_body,
                    settings.DEFAULT_FROM_EMAIL, # Your default 'from' email address
                    [user.email], # Send to the new user's email
                    fail_silently=False, # Raise an error if sending fails
                )
            except Exception as e:
                # Log the error (e.g., using Python's logging module)
                print(f"Error sending welcome email to {user.email}: {e}")
                # You might want to inform the admin that the user was created but the email failed
                # For now, we'll let the user creation succeed even if email fails.

            return Response(
                UserSerializer(user).data, # Respond with the created user's data
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update and delete user details
    """
    serializer_class = UserSerializer
    # Permissions here need careful consideration based on who can view/edit whose profile
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all() # This will be used if 'pk' is in URL

    def get_object(self):
        # For retrieve/update operations for the logged-in user via /api/auth/user/
        if 'pk' not in self.kwargs:
            return self.request.user
        
        # For operations on a specific user ID via /api/auth/user/<pk>/
        # This part needs to be robust. Can any authenticated user see any other user by ID?
        # Or should it be admin only, or manager viewing their team?
        # The current implementation allows admin to get any user by pk.
        # Other users trying to access another user by pk would need more specific permission logic.
        obj = generics.get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        
        # Example of more granular permission:
        # Allow user to see their own details, or admin to see any.
        if obj == self.request.user or (self.request.user.is_authenticated and self.request.user.role == 'admin'):
            return obj
        
        # If user is a manager, they might be able_to see their team members.
        # This would require checking if obj is in request.user.managed_team (example logic)

        # If none of the above, deny permission.
        # The default object-level permission handling by DRF might also apply if set.
        self.check_object_permissions(self.request, obj) # This is good practice
        return obj


class LogoutView(APIView):
    """
    API view for user logout - blacklists the refresh token
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # The refresh token might be in cookies now, not request.data
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response
        except Exception as e:
            print(f"Logout error: {e}") # Log the error
            # It's generally safe to just clear cookies and respond with success on logout
            # to avoid leaking info about token validity.
            response = Response({"detail": "Logout processed."}, status=status.HTTP_200_OK)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response


class PasswordChangeView(APIView):
    """
    API view for changing user password
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            # The check for old_password is now typically done in the serializer's validate method
            user.set_password(serializer.validated_data['new_password'])
            user.password_last_changed_at = timezone.now()
            user.save()
            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    """
    API view for requesting a password reset
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email__iexact=email) # Case-insensitive email lookup
                
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/" # Ensure FRONTEND_URL is in settings
                
                send_mail(
                    'Password Reset for Real Estate CRM',
                    f'Click the following link to reset your password: {reset_url}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                
                return Response(
                    {"detail": "Password reset email has been sent."},
                    status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                # Do not reveal that the user does not exist
                return Response(
                    {"detail": "If your email address exists in our database, you will receive a password reset link shortly."},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                # Log actual email sending errors or other exceptions
                print(f"Error during password reset request for {email}: {e}")
                return Response(
                    {"error": "An error occurred. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    API view for confirming a password reset
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            try:
                uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
                user = User.objects.get(pk=uid)
                
                if default_token_generator.check_token(user, serializer.validated_data['token']):
                    user.set_password(serializer.validated_data['password'])
                    user.save()
                    return Response(
                        {"detail": "Password has been reset successfully."},
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {"error": "The reset link is invalid or has expired."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response(
                    {"error": "The reset link is invalid."}, # Avoid saying "expired" if it's just invalid
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                print(f"Error during password reset confirm: {e}")
                return Response(
                    {"error": "An unexpected error occurred. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view that sets the new access token as an HttpOnly cookie
    and expects the refresh token from an HttpOnly cookie.
    """
    def post(self, request, *args, **kwargs):
        # Override to ensure refresh token is taken from cookies if not in request body
        # DRF's TokenRefreshView expects 'refresh' in request.data
        # If your frontend sends it in the body, this is fine.
        # If it relies purely on cookies, you'd need to modify how serializer gets the token.
        
        # For now, assuming frontend might still send it, or serializer handles cookie extraction
        # If refresh token is ONLY in cookie, you need to pass it to the serializer:
        # refresh_token_from_cookie = request.COOKIES.get('refresh_token')
        # if refresh_token_from_cookie and 'refresh' not in request.data:
        #     request.data['refresh'] = refresh_token_from_cookie
            
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access = response.data.get('access')
            response.set_cookie(
                key='access_token',
                value=access,
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE, # Use Django settings
                samesite='Lax',
                max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()
            )
            # Optionally remove the access token from the response body if set in cookie
            if 'access' in response.data:
                 response.data.pop('access', None)
        return response
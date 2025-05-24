from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Try to get the token from the Authorization header first
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)
        # If not present, try to get the token from the cookie
        raw_token = request.COOKIES.get('access_token')
        if raw_token is not None:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        return None

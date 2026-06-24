from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings

from ..permissions import IsAuthenticated
from ..models import User

# CHECK DB FOR COMPETITOR ACCOUNT ASSOCIATED WITH EMAIL
@api_view(['GET'])
@permission_classes([AllowAny])
def check_email(request):
    email = request.query_params.get('email', '')
    exists = User.objects.filter(email__iexact=email, user_type='C').exists()
    return Response({'exists': exists})

def set_auth_cookies(response, access, refresh=None):
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS, access,
        httponly=settings.AUTH_COOKIE_HTTP_ONLY,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    if refresh:
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH, refresh,
            httponly=settings.AUTH_COOKIE_HTTP_ONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )


class CookieTokenObtainPairView(TokenObtainPairView):
    def finalize_response(self, request, response, *args, **kwargs):
        if response.status_code == 200 and 'access' in response.data:
            access = response.data.pop('access')
            refresh = response.data.pop('refresh')
            set_auth_cookies(response, access, refresh)
            response.data = {'detail': 'logged in'}
        return super().finalize_response(request, response, *args, **kwargs)


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if not refresh:
            return Response({'detail': 'No refresh token'}, status=400)

        serializer = self.get_serializer(data={'refresh': refresh})
        serializer.is_valid(raise_exception=True)

        access = serializer.validated_data['access']
        new_refresh = serializer.validated_data.get('refresh')  # only if ROTATE_REFRESH_TOKENS=True

        response = Response({'detail': 'refreshed'})
        set_auth_cookies(response, access, new_refresh)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_cookie = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if refresh_cookie:
            try:
                RefreshToken(refresh_cookie).blacklist()
            except Exception:
                pass

        response = Response({'detail': 'logged out'})
        response.delete_cookie(
            settings.AUTH_COOKIE_ACCESS,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        response.delete_cookie(
            settings.AUTH_COOKIE_REFRESH,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        return response
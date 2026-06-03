from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r'blog', BlogView, basename='blog')

urlpatterns = [
    re_path(r'^auth/', include('djoser.urls')),
    re_path(r'^auth/', include('djoser.urls.jwt')),
    path("auth/signup/", signup, name="signup"),
    path("auth/signin/", signin, name="signin"),
    path("auth/signout/", signout, name="signout"),
    path("csrf/", get_csrf_token, name="get_csrf_token"),
    path("college_data/", college_data, name="college_data"),
    # path("reset-password/", reset_password_link, name="reset_password"),
    # path("reset-password-confirm/", reset_password_confirm, name="reset_password_confirm"),
    path('check-email/', check_email, name="check_email"),
    path('profile/', CompetitorView.as_view(), name="my_profile"),
    path('registration/', RegistrationView.as_view(), name="registration"),
    path('events/', EventsView.as_view(), name="get_events"),
    path('groupset/', CreateGroupsetView.as_view(), name="groupset"),
    path('groupset-members/', JoinGroupsetView.as_view(), name="groupset_members"),
    path('settings/', SettingsView.as_view({'get': 'retrieve', 
                                                   'post': 'create',
                                                   'patch': 'update'}), 
                                                   name="competition_settings"),
    path('', include(router.urls))
]



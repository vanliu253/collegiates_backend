from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import generics, viewsets, mixins
from rest_framework.permissions import AllowAny

from django.db import transaction

from ..permissions import IsCompetitor, IsOrganizer, IsAuthenticated
from ..models import User, Registration, Groupset, GroupsetMember, Settings, Event, Blog
from ..serializers import EventRegistrationSerializer, \
    CompetitorSerializer, GroupsetSerializer, \
        GroupsetMemberSerializer, EventSerializer, \
        SettingsSerializer, BlogSerializer \

def requires_settings(method):
    def wrapper(self, request, *args, **kwargs):
        config = Settings.load()
        if config is None:
            return Response(
                {"detail": "No settings have been created yet."},
                status=status.HTTP_404_NOT_FOUND
            )
        self.config = config
        return method(self, request, *args, **kwargs)
    return wrapper

class EventsView(generics.ListAPIView):
    """
        GET: List all events a competitor can register for
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsCompetitor]

    def get_queryset(self):
        queryset = Event.objects.filter(
            event_level__iexact = self.request.user.skill_level,
            gender_category__iexact = self.request.user.gender
        )
        return queryset

class RegistrationView(generics.ListCreateAPIView):
    """
        GET: List all events a user is registered to for this current competition year
        POST: Register user for current competition year with multiple events
    """
    queryset = Registration.objects.select_related('event')
    serializer_class = EventRegistrationSerializer
    permission_classes = [IsCompetitor]
    
    def get_serializer(self, *args, **kwargs):
        kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)

    @requires_settings
    def perform_create(self, serializer):
        serializer.save(competitor=self.request.user,
                        comp_year=self.config.reg_year)

    def get_queryset(self):
        if not hasattr(self, 'config'):
            return Registration.objects.none()
        return Registration.objects.filter(
            competitor = self.request.user,
            comp_year = self.config.reg_year
        ).prefetch_related('event')
    
    @requires_settings
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)    

# todo: convert into viewset with separate permissions for competitor/organizer
class CompetitorView(generics.RetrieveUpdateDestroyAPIView):
    """
        GET: Retrieve competitor info + registration
        DELETE: Delete competitor account
        PATCH: Update competitor information
    """
    queryset = User.objects.prefetch_related('events')
    serializer_class = CompetitorSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class CreateGroupsetView(generics.CreateAPIView):
    """
        POST: Create a new groupset and add competitor as leader
    """

    queryset = Groupset.objects.prefetch_related('members')
    serializer_class = GroupsetSerializer
    permission_classes = [IsCompetitor]

    @requires_settings
    def perform_create(self, serializer):
        with transaction.atomic():
            groupset = serializer.save(school=self.request.user.school, comp_year=self.config.reg_year) # type: ignore
            GroupsetMember.objects.create(groupset=groupset, member=self.request.user, leader=True)

class JoinGroupsetView(generics.ListCreateAPIView):
    """
        GET: List all groupsets that a competitor can sign up for
        POST: Add competitor as a member of a groupset
    """

    queryset = Groupset.objects.prefetch_related('members')
    serializer_class = GroupsetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            self.serializer_class = GroupsetMemberSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if not hasattr(self, 'config'):
            return Groupset.objects.none()
        
        if self.request.user.is_organizer:
            return Groupset.objects.filter(
                comp_year = self.config.reg_year
            ).prefetch_related('members')

        return Groupset.objects.filter(
            school = self.request.user.school,
            comp_year = self.config.reg_year
        ).prefetch_related('members')

    @requires_settings
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @requires_settings
    def perform_create(self, serializer):
        if self.request.user.is_competitor:
            serializer.save(member=self.request.user, leader=False)
    
class SettingsView(viewsets.GenericViewSet, 
                          mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin,
                          mixins.UpdateModelMixin):
    """
        GET: retrieve competition settings
        POST: create competition settings
        PATCH: update competition settings
    """
    queryset = Settings.objects.first()
    serializer_class = SettingsSerializer
    permission_classes = [IsOrganizer]

    def get_object(self):
        return Settings.load()
    
class BlogView(viewsets.ModelViewSet):
    """
        GET: retrieve blog post
        POST: create blog post
        PATCH: update blog post
        DELETE: delete blog post
    """

    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [IsOrganizer]

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.request.method == 'GET':
            permission_classes = [AllowAny]
        return [permissions() for permissions in permission_classes]

from django.contrib import admin

# Register your models here.
from .models import Blog, College, Event, User, Registration, Groupset, Settings

admin.site.register(Blog)
admin.site.register(College)
admin.site.register(Event)
admin.site.register(User)
admin.site.register(Registration)
admin.site.register(Groupset)
admin.site.register(Settings)

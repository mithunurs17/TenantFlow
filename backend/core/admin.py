from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
admin.site.register(User,UserAdmin)
for model in [Workspace,Membership,Project,Sprint,Issue,Comment,AuditEvent,Subscription]: admin.site.register(model)

from rest_framework.permissions import BasePermission
from .models import Membership
class WorkspaceAccess(BasePermission):
 def has_permission(self,request,view):
  return bool(request.user and request.user.is_authenticated and Membership.objects.filter(user=request.user).exists())

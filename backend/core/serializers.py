from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import serializers
from .models import *
User=get_user_model()

class RegisterSerializer(serializers.Serializer):
 email=serializers.EmailField()
 password=serializers.CharField(min_length=10,write_only=True)
 workspace_name=serializers.CharField(max_length=140)
 def create(self,data):
  from django.db import transaction
  with transaction.atomic():
   user=User.objects.create_user(username=data["email"],email=data["email"],password=data["password"])
   base=slugify(data["workspace_name"])[:120] or "workspace"; slug=base; i=2
   while Workspace.objects.filter(slug=slug).exists(): slug=f"{base}-{i}"; i+=1
   ws=Workspace.objects.create(name=data["workspace_name"],slug=slug)
   Membership.objects.create(workspace=ws,user=user,role="owner")
   Subscription.objects.create(workspace=ws)
   return user
class ProjectSerializer(serializers.ModelSerializer):
 class Meta: model=Project; fields=["id","name","key","description","created_at"]; read_only_fields=["id","created_at"]
class SprintSerializer(serializers.ModelSerializer):
 class Meta: model=Sprint; fields=["id","project","name","starts_at","ends_at","active","created_at"]; read_only_fields=["id","created_at"]
class IssueSerializer(serializers.ModelSerializer):
 issue_key=serializers.ReadOnlyField()
 class Meta: model=Issue; fields=["id","project","sprint","title","description","status","priority","assignee","reporter","issue_no","issue_key","created_at"]; read_only_fields=["id","reporter","issue_no","issue_key","created_at"]
 def validate(self,attrs):
  if self.instance and "status" in attrs:
   valid={choice[0] for choice in Issue.STATUS}
   old=self.instance.status; new=attrs["status"]
   if new not in valid: raise serializers.ValidationError({"status":"Unknown workflow status."})
  project=attrs.get("project",getattr(self.instance,"project",None))
  ws=self.context["workspace"]
  if project and project.workspace_id!=ws.id: raise serializers.ValidationError("Project is outside your workspace.")
  sprint=attrs.get("sprint",getattr(self.instance,"sprint",None))
  if sprint and (sprint.workspace_id!=ws.id or sprint.project_id!=project.id): raise serializers.ValidationError("Sprint must belong to this project and workspace.")
  assignee=attrs.get("assignee",getattr(self.instance,"assignee",None))
  if assignee and not Membership.objects.filter(workspace=ws,user=assignee).exists(): raise serializers.ValidationError("Assignee must be a workspace member.")
  return attrs
class CommentSerializer(serializers.ModelSerializer):
 class Meta: model=Comment; fields=["id","issue","author","body","created_at"]; read_only_fields=["id","issue","author","created_at"]
class AuditSerializer(serializers.ModelSerializer):
 class Meta: model=AuditEvent; fields=["id","actor","entity_type","entity_id","action","payload","at"]

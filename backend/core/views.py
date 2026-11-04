import json
import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from rest_framework import generics,viewsets,status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from .models import *
from .serializers import *

class HealthView(APIView):
 permission_classes=[AllowAny]
 def get(self,request): return Response({"ok":True,"service":"tenantflow-api"})
class RegisterView(generics.GenericAPIView):
 serializer_class=RegisterSerializer
 permission_classes=[AllowAny]
 def post(self,request):
  s=self.get_serializer(data=request.data); s.is_valid(raise_exception=True); user=s.save()
  from rest_framework_simplejwt.tokens import RefreshToken
  token=RefreshToken.for_user(user)
  return Response({"user":{"id":user.id,"email":user.email},"refresh":str(token),"access":str(token.access_token)},status=201)

class TenantViewSet(viewsets.ModelViewSet):
 def get_workspace(self):
  membership=Membership.objects.filter(user=self.request.user).select_related("workspace").order_by("id").first()
  if not membership: from rest_framework.exceptions import PermissionDenied; raise PermissionDenied("Workspace membership required.")
  return membership.workspace
 def role(self):
  return Membership.objects.filter(user=self.request.user,workspace=self.get_workspace()).values_list("role",flat=True).first()
 def perform_create(self,serializer):
  if self.role()=="viewer": from rest_framework.exceptions import PermissionDenied; raise PermissionDenied("Viewers cannot create records.")
  serializer.save(workspace=self.get_workspace())
 def perform_update(self,serializer):
  if self.role()=="viewer": from rest_framework.exceptions import PermissionDenied; raise PermissionDenied("Viewers cannot edit records.")
  obj=serializer.save()
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=self.request.user,entity_type=obj.__class__.__name__.lower(),entity_id=str(obj.pk),action="updated")
 def perform_destroy(self,obj):
  if self.role() not in ("owner","admin"): from rest_framework.exceptions import PermissionDenied; raise PermissionDenied("Admin role required.")
  obj.delete()
class ProjectViewSet(TenantViewSet):
 serializer_class=ProjectSerializer
 def get_queryset(self): return Project.objects.filter(workspace=self.get_workspace())
 def perform_create(self,serializer):
  super().perform_create(serializer)
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=self.request.user,entity_type="project",entity_id=str(serializer.instance.pk),action="created")
class SprintViewSet(TenantViewSet):
 serializer_class=SprintSerializer
 def get_queryset(self): return Sprint.objects.filter(workspace=self.get_workspace(),project__workspace=self.get_workspace())
 def perform_create(self,serializer):
  project=serializer.validated_data["project"]
  if project.workspace_id!=self.get_workspace().id: from rest_framework.exceptions import ValidationError; raise ValidationError("Invalid project.")
  super().perform_create(serializer)
class IssueViewSet(TenantViewSet):
 serializer_class=IssueSerializer
 def get_queryset(self):
  qs=Issue.objects.filter(workspace=self.get_workspace(),project__workspace=self.get_workspace()).select_related("project","assignee","reporter")
  project=self.request.query_params.get("project"); status_val=self.request.query_params.get("status")
  if project: qs=qs.filter(project_id=project)
  if status_val: qs=qs.filter(status=status_val)
  return qs
 def get_serializer_context(self): return {**super().get_serializer_context(),"workspace":self.get_workspace()}
 @transaction.atomic
 def perform_create(self,serializer):
  project=serializer.validated_data["project"]
  if project.workspace_id!=self.get_workspace().id: from rest_framework.exceptions import ValidationError; raise ValidationError("Invalid project.")
  last=Issue.objects.filter(project=project).aggregate(m=Max("issue_no"))["m"] or 0
  obj=serializer.save(workspace=self.get_workspace(),reporter=self.request.user,issue_no=last+1)
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=self.request.user,entity_type="issue",entity_id=str(obj.pk),action="created",payload={"status":obj.status})
 def perform_update(self,serializer):
  before=serializer.instance.status
  obj=serializer.save()
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=self.request.user,entity_type="issue",entity_id=str(obj.pk),action="updated",payload={"from_status":before,"to_status":obj.status})
 @action(detail=True,methods=["get","post"])
 def comments(self,request,pk=None):
  issue=self.get_object()
  if request.method=="GET": return Response(CommentSerializer(issue.comments.all(),many=True).data)
  if self.role()=="viewer": from rest_framework.exceptions import PermissionDenied; raise PermissionDenied("Viewers cannot comment.")
  s=CommentSerializer(data=request.data); s.is_valid(raise_exception=True)
  comment=s.save(workspace=self.get_workspace(),issue=issue,author=request.user)
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=request.user,entity_type="comment",entity_id=str(comment.pk),action="created")
  return Response(CommentSerializer(comment).data,status=201)
class AuditView(generics.ListAPIView):
 serializer_class=AuditSerializer
 def get_queryset(self):
  ws=Membership.objects.filter(user=self.request.user).values_list("workspace_id",flat=True).first()
  return AuditEvent.objects.filter(workspace_id=ws).select_related("actor").order_by("-at")[:300]
class CheckoutView(APIView):
 def post(self,request):
  if not settings.STRIPE_SECRET_KEY: return Response({"detail":"Set STRIPE_SECRET_KEY to enable test checkout."},status=503)
  stripe.api_key=settings.STRIPE_SECRET_KEY
  price_id=request.data.get("price_id")
  if not price_id: return Response({"detail":"price_id required"},status=400)
  ws=Membership.objects.filter(user=request.user).select_related("workspace").first().workspace
  try:
   session=stripe.checkout.Session.create(mode="subscription",line_items=[{"price":price_id,"quantity":1}],
    success_url=settings.CORS_ALLOWED_ORIGINS[0]+"/?billing=success",cancel_url=settings.CORS_ALLOWED_ORIGINS[0]+"/?billing=cancel",
    client_reference_id=str(ws.id),metadata={"workspace_id":str(ws.id)})
   return Response({"checkout_url":session.url})
  except Exception as e: return Response({"detail":str(e)},status=400)
class StripeWebhookView(APIView):
 permission_classes=[AllowAny]
 authentication_classes=[]
 def post(self,request):
  try: event=stripe.Webhook.construct_event(request.body,request.META.get("HTTP_STRIPE_SIGNATURE",""),settings.STRIPE_WEBHOOK_SECRET)
  except Exception: return HttpResponse(status=400)
  if event["type"]=="customer.subscription.updated":
   obj=event["data"]["object"]; wsid=obj.get("metadata",{}).get("workspace_id")
   if wsid: Subscription.objects.filter(workspace_id=wsid).update(stripe_subscription_id=obj["id"],status=obj["status"],plan="paid")
  return HttpResponse(status=200)

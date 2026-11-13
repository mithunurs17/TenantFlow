import json
import stripe
from django.conf import settings
from django.db import transaction, models
from django.db.models import Max
from django.http import HttpResponse, FileResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
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
  user=self.request.user
  membership=Membership.objects.filter(user=user,workspace_id=user.active_workspace_id).select_related("workspace").first() if user.active_workspace_id else None
  if not membership:
   membership=Membership.objects.filter(user=user).select_related("workspace").order_by("id").first()
  if not membership:
   from rest_framework.exceptions import PermissionDenied
   raise PermissionDenied("Workspace membership required.")
  return membership.workspace
 def role(self):
  return Membership.objects.filter(user=self.request.user,workspace=self.get_workspace()).values_list("role",flat=True).first()
 def require_roles(self,*roles):
  from rest_framework.exceptions import PermissionDenied
  if self.role() not in roles: raise PermissionDenied("Your workspace role does not allow this action.")
 def perform_create(self,serializer):
  self.require_roles("owner","admin","member")
  serializer.save(workspace=self.get_workspace())
 def perform_update(self,serializer):
  self.require_roles("owner","admin","member")
  obj=serializer.save()
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=self.request.user,entity_type=obj.__class__.__name__.lower(),entity_id=str(obj.pk),action="updated")
 def perform_destroy(self,obj):
  self.require_roles("owner","admin")
  obj.delete()

class WorkspaceView(APIView):
 def get(self,request):
  memberships=Membership.objects.filter(user=request.user).select_related("workspace")
  return Response({"active_workspace_id":str(request.user.active_workspace_id) if request.user.active_workspace_id else None,
   "workspaces":[{"id":str(m.workspace_id),"name":m.workspace.name,"slug":m.workspace.slug,"role":m.role} for m in memberships]})
 def post(self,request):
  from django.utils.text import slugify
  from rest_framework.exceptions import ValidationError
  name=(request.data.get("name") or "").strip()
  if not name: raise ValidationError({"name":"Workspace name is required."})
  self.check_permissions(request)
  base=slugify(name)[:120] or "workspace"; slug=base; i=2
  while Workspace.objects.filter(slug=slug).exists(): slug=f"{base}-{i}"; i+=1
  with transaction.atomic():
   ws=Workspace.objects.create(name=name,slug=slug)
   Membership.objects.create(workspace=ws,user=request.user,role="owner")
   Subscription.objects.create(workspace=ws)
  request.user.active_workspace=ws; request.user.save(update_fields=["active_workspace"])
  return Response({"id":str(ws.id),"name":ws.name,"role":"owner"},status=201)


class WorkspaceMembersView(APIView):
 def get(self,request):
  wsid=request.user.active_workspace_id
  if not wsid: wsid=Membership.objects.filter(user=request.user).values_list("workspace_id",flat=True).first()
  if not Membership.objects.filter(user=request.user,workspace_id=wsid).exists(): return Response({"detail":"Workspace membership required."},status=403)
  return Response([{"id":m.id,"user_id":m.user_id,"email":m.user.email,"role":m.role} for m in Membership.objects.filter(workspace_id=wsid).select_related("user")])
 def post(self,request):
  wsid=request.user.active_workspace_id
  membership=Membership.objects.filter(user=request.user,workspace_id=wsid).first()
  if not membership or membership.role not in ("owner","admin"): return Response({"detail":"Only owners/admins can add members."},status=403)
  email=(request.data.get("email") or "").strip().lower(); role=request.data.get("role","member")
  if role not in ("admin","member","viewer"): return Response({"detail":"Invalid role."},status=400)
  user=User.objects.filter(email=email).first()
  if not user: return Response({"detail":"User must register before being added to this workspace."},status=404)
  member,created=Membership.objects.get_or_create(workspace=membership.workspace,user=user,defaults={"role":role})
  if not created: return Response({"detail":"User is already a workspace member."},status=409)
  AuditEvent.objects.create(workspace=membership.workspace,actor=request.user,entity_type="membership",entity_id=str(member.pk),action="added",payload={"email":email,"role":role})
  return Response({"id":member.id,"email":user.email,"role":member.role},status=201)

class ActiveWorkspaceView(APIView):
 def post(self,request):
  wsid=request.data.get("workspace_id")
  membership=Membership.objects.filter(user=request.user,workspace_id=wsid).select_related("workspace").first()
  if not membership: return Response({"detail":"You are not a member of this workspace."},status=403)
  request.user.active_workspace=membership.workspace
  request.user.save(update_fields=["active_workspace"])
  return Response({"workspace_id":str(membership.workspace_id),"role":membership.role})

class ProjectViewSet(TenantViewSet):
 serializer_class=ProjectSerializer
 def perform_create(self,serializer):
  ws=self.get_workspace()
  sub=Subscription.objects.filter(workspace=ws).first()
  if (not sub or sub.plan=="free") and Project.objects.filter(workspace=ws).count()>=3:
   from rest_framework.exceptions import PermissionDenied
   raise PermissionDenied("Free plan limit reached (3 projects). Upgrade to create more.")
  super().perform_create(serializer)
  AuditEvent.objects.create(workspace=ws,actor=self.request.user,entity_type="project",entity_id=str(serializer.instance.pk),action="created")
 def get_queryset(self): return Project.objects.filter(workspace=self.get_workspace())
class SprintViewSet(TenantViewSet):
 serializer_class=SprintSerializer
 def get_queryset(self): return Sprint.objects.filter(workspace=self.get_workspace(),project__workspace=self.get_workspace()).select_related("project")
 def perform_create(self,serializer):
  ws=self.get_workspace()
  sub=Subscription.objects.filter(workspace=ws).first()
  if (not sub or sub.plan=="free") and Issue.objects.filter(workspace=ws).count()>=50:
   from rest_framework.exceptions import PermissionDenied
   raise PermissionDenied("Free plan limit reached (50 issues). Upgrade to create more.")
  project=serializer.validated_data["project"]
  if project.workspace_id!=self.get_workspace().id:
   from rest_framework.exceptions import ValidationError
   raise ValidationError("Invalid project.")
  super().perform_create(serializer)
 @action(detail=True,methods=["post"])
 def start(self,request,pk=None):
  sprint=self.get_object(); self.require_roles("owner","admin","member")
  Sprint.objects.filter(project=sprint.project,active=True).exclude(pk=sprint.pk).update(active=False)
  sprint.active=True
  if not sprint.starts_at: sprint.starts_at=timezone.localdate()
  sprint.save()
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=request.user,entity_type="sprint",entity_id=str(sprint.pk),action="started")
  return Response(SprintSerializer(sprint).data)
 @action(detail=True,methods=["post"])
 def complete(self,request,pk=None):
  sprint=self.get_object(); self.require_roles("owner","admin","member")
  sprint.active=False; sprint.ends_at=timezone.localdate(); sprint.save()
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=request.user,entity_type="sprint",entity_id=str(sprint.pk),action="completed")
  return Response(SprintSerializer(sprint).data)

class IssueViewSet(TenantViewSet):
 serializer_class=IssueSerializer
 def get_queryset(self):
  qs=Issue.objects.filter(workspace=self.get_workspace(),project__workspace=self.get_workspace()).select_related("project","assignee","reporter")
  project=self.request.query_params.get("project"); status_val=self.request.query_params.get("status")
  if project: qs=qs.filter(project_id=project)
  if status_val: qs=qs.filter(status=status_val)
  search=self.request.query_params.get("search")
  if search: qs=qs.filter(models.Q(title__icontains=search)|models.Q(description__icontains=search))
  sprint=self.request.query_params.get("sprint")
  if sprint: qs=qs.filter(sprint_id=sprint)
  if self.request.query_params.get("assignee")=="me": qs=qs.filter(assignee=self.request.user)
  return qs
 def get_serializer_context(self): return {**super().get_serializer_context(),"workspace":self.get_workspace()}
 @transaction.atomic
 def perform_create(self,serializer):
  ws=self.get_workspace()
  sub=Subscription.objects.filter(workspace=ws).first()
  if (not sub or sub.plan=="free") and Issue.objects.filter(workspace=ws).count()>=50:
   from rest_framework.exceptions import PermissionDenied
   raise PermissionDenied("Free plan limit reached (50 issues). Upgrade to create more.")
  project=serializer.validated_data["project"]
  if project.workspace_id!=self.get_workspace().id: from rest_framework.exceptions import ValidationError; raise ValidationError("Invalid project.")
  last=Issue.objects.filter(project=project).aggregate(m=Max("issue_no"))["m"] or 0
  obj=serializer.save(workspace=self.get_workspace(),reporter=self.request.user,issue_no=last+1)
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=self.request.user,entity_type="issue",entity_id=str(obj.pk),action="created",payload={"status":obj.status})
 def perform_update(self,serializer):
  self.require_roles("owner","admin","member")
  before=serializer.instance.status
  obj=serializer.save()
  AuditEvent.objects.create(workspace=self.get_workspace(),actor=self.request.user,entity_type="issue",entity_id=str(obj.pk),action="updated",payload={"from_status":before,"to_status":obj.status,"title":obj.title,"priority":obj.priority,"project_id":obj.project_id})
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
  price_id=(request.data.get("price_id") or settings.STRIPE_PRICE_ID or "").strip()
  if not price_id: return Response({"detail":"Professional plan billing is not configured yet. Please contact your workspace administrator."},status=503)
  if not price_id.startswith("price_"): return Response({"detail":"The configured Stripe Price ID is invalid. Please contact support."},status=503)
  ws=Membership.objects.filter(user=request.user,workspace_id=request.user.active_workspace_id).select_related("workspace").first()
  if not ws: ws=Membership.objects.filter(user=request.user).select_related("workspace").first()
  if not ws: return Response({"detail":"Workspace membership required."},status=403)
  if ws.role not in ("owner","admin"): return Response({"detail":"Only workspace owners/admins can manage billing."},status=403)
  sub,_=Subscription.objects.get_or_create(workspace=ws.workspace)
  try:
   customer_id=sub.stripe_customer_id
   if not customer_id:
    customer=stripe.Customer.create(email=request.user.email,name=ws.workspace.name,metadata={"workspace_id":str(ws.workspace_id)})
    customer_id=customer.id; sub.stripe_customer_id=customer_id; sub.save(update_fields=["stripe_customer_id"])
   origin=settings.CORS_ALLOWED_ORIGINS[0].rstrip("/")
   session=stripe.checkout.Session.create(mode="subscription",customer=customer_id,line_items=[{"price":price_id,"quantity":1}],
    success_url=origin+"/?billing=success",cancel_url=origin+"/?billing=cancel",
    client_reference_id=str(ws.workspace_id),metadata={"workspace_id":str(ws.workspace_id)},
    subscription_data={"metadata":{"workspace_id":str(ws.workspace_id)}})
   return Response({"checkout_url":session.url})
  except stripe.error.StripeError as e: return Response({"detail":str(e)},status=400)

class BillingManageView(APIView):
 def get(self,request):
  wsid=request.user.active_workspace_id or Membership.objects.filter(user=request.user).values_list("workspace_id",flat=True).first()
  sub=Subscription.objects.filter(workspace_id=wsid).first() if wsid else None
  if not sub: return Response({"plan":"free","status":"active","period_end":None,"cancel_at_period_end":False})
  return Response({"plan":sub.plan,"status":sub.status,"period_end":sub.period_end,"cancel_at_period_end":False})
 def post(self,request):
  wsid=request.user.active_workspace_id or Membership.objects.filter(user=request.user).values_list("workspace_id",flat=True).first()
  membership=Membership.objects.filter(user=request.user,workspace_id=wsid).first() if wsid else None
  if not membership or membership.role not in ("owner","admin"): return Response({"detail":"Only workspace owners/admins can manage billing."},status=403)
  sub=Subscription.objects.filter(workspace_id=wsid).first()
  if not sub or not sub.stripe_subscription_id: return Response({"detail":"No active Stripe subscription found."},status=404)
  if not settings.STRIPE_SECRET_KEY: return Response({"detail":"Stripe is not configured."},status=503)
  try:
   stripe.api_key=settings.STRIPE_SECRET_KEY
   result=stripe.Subscription.modify(sub.stripe_subscription_id,cancel_at_period_end=True)
   return Response({"status":result.status,"cancel_at_period_end":result.cancel_at_period_end})
  except stripe.error.StripeError as e: return Response({"detail":str(e)},status=400)

class StripeWebhookView(APIView):
 permission_classes=[AllowAny]
 authentication_classes=[]
 def post(self,request):
  try:
   event=stripe.Webhook.construct_event(request.body,request.META.get("HTTP_STRIPE_SIGNATURE",""),settings.STRIPE_WEBHOOK_SECRET)
  except Exception: return HttpResponse(status=400)
  etype=event["type"]; obj=event["data"]["object"]
  wsid=(obj.get("metadata") or {}).get("workspace_id") or obj.get("client_reference_id")
  if etype.startswith("customer.subscription.") and wsid:
   period=datetime.fromtimestamp(obj["current_period_end"],tz=dt_timezone.utc) if obj.get("current_period_end") else None
   Subscription.objects.update_or_create(workspace_id=wsid,defaults={
    "stripe_customer_id":obj.get("customer") or "","stripe_subscription_id":obj.get("id") or "",
    "status":obj.get("status","inactive"),"plan":"paid" if obj.get("status") in ("active","trialing") else "free","period_end":period})
  elif etype=="checkout.session.completed" and obj.get("subscription") and wsid:
   Subscription.objects.update_or_create(workspace_id=wsid,defaults={"stripe_customer_id":obj.get("customer") or "",
    "stripe_subscription_id":obj.get("subscription"),"status":"incomplete","plan":"free"})
  elif etype=="customer.subscription.deleted" and wsid:
   Subscription.objects.filter(workspace_id=wsid).update(status="canceled",plan="free")
  elif etype=="invoice.payment_failed" and wsid:
   Subscription.objects.filter(workspace_id=wsid).update(status="past_due")
  return HttpResponse(status=200)

class AttachmentView(APIView):
 def get_issue(self,request,issue_id):
  wsid=request.user.active_workspace_id
  if not wsid: wsid=Membership.objects.filter(user=request.user).values_list("workspace_id",flat=True).first()
  return get_object_or_404(Issue,pk=issue_id,workspace_id=wsid,project__workspace_id=wsid)
 def get(self,request,issue_id):
  issue=self.get_issue(request,issue_id)
  download_id=request.query_params.get("download")
  if download_id:
   attachment=get_object_or_404(Attachment,pk=download_id,issue=issue,workspace=issue.workspace)
   return FileResponse(attachment.file.open("rb"),as_attachment=True,filename=attachment.original_name,content_type=attachment.content_type or "application/octet-stream")
  return Response([{"id":a.id,"name":a.original_name,"size":a.size,"content_type":a.content_type,"uploaded_by":a.uploaded_by.email,"created_at":a.created_at} for a in issue.attachments.select_related("uploaded_by")])
 def post(self,request,issue_id):
  issue=self.get_issue(request,issue_id)
  if not Membership.objects.filter(user=request.user,workspace=issue.workspace,role__in=["owner","admin","member"]).exists(): return Response({"detail":"Permission denied."},status=403)
  file=request.FILES.get("file")
  if not file: return Response({"detail":"file is required"},status=400)
  if file.size>10*1024*1024: return Response({"detail":"Maximum attachment size is 10 MB."},status=400)
  attachment=Attachment.objects.create(workspace=issue.workspace,issue=issue,uploaded_by=request.user,file=file,original_name=file.name,content_type=file.content_type or "",size=file.size)
  AuditEvent.objects.create(workspace=issue.workspace,actor=request.user,entity_type="attachment",entity_id=str(attachment.pk),action="uploaded",payload={"issue":issue.issue_key,"name":file.name,"size":file.size})
  return Response({"id":attachment.id,"name":attachment.original_name},status=201)
 def delete(self,request,issue_id):
  issue=self.get_issue(request,issue_id); aid=request.data.get("attachment_id")
  attachment=get_object_or_404(Attachment,pk=aid,issue=issue)
  if not (attachment.uploaded_by_id==request.user.id or Membership.objects.filter(user=request.user,workspace=issue.workspace,role__in=["owner","admin"]).exists()): return Response({"detail":"Permission denied."},status=403)
  attachment.file.delete(save=False); attachment.delete()
  return Response(status=204)


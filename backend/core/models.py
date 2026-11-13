import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    email=models.EmailField(unique=True)
    active_workspace=models.ForeignKey("Workspace",null=True,blank=True,on_delete=models.SET_NULL,related_name="active_users")
    USERNAME_FIELD="email"
    REQUIRED_FIELDS=["username"]

class Workspace(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=140)
    slug=models.SlugField(max_length=150,unique=True)
    created_at=models.DateTimeField(auto_now_add=True)

class Membership(models.Model):
    ROLE=[("owner","Owner"),("admin","Admin"),("member","Member"),("viewer","Viewer")]
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="memberships")
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="memberships")
    role=models.CharField(max_length=12,choices=ROLE,default="member")
    class Meta: constraints=[models.UniqueConstraint(fields=["workspace","user"],name="unique_workspace_member")]

class TenantModel(models.Model):
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: abstract=True

class Project(TenantModel):
    name=models.CharField(max_length=140)
    key=models.CharField(max_length=12)
    description=models.TextField(blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["workspace","key"],name="unique_project_key")]
    def __str__(self): return f"{self.key}: {self.name}"

class Sprint(TenantModel):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name="sprints")
    name=models.CharField(max_length=140)
    starts_at=models.DateField(null=True,blank=True)
    ends_at=models.DateField(null=True,blank=True)
    active=models.BooleanField(default=False)

class Issue(TenantModel):
    STATUS=[("backlog","Backlog"),("todo","To do"),("progress","In progress"),("review","Review"),("done","Done")]
    PRIORITY=[("low","Low"),("medium","Medium"),("high","High"),("urgent","Urgent")]
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name="issues")
    sprint=models.ForeignKey(Sprint,null=True,blank=True,on_delete=models.SET_NULL,related_name="issues")
    title=models.CharField(max_length=240)
    description=models.TextField(blank=True)
    status=models.CharField(max_length=12,choices=STATUS,default="backlog")
    priority=models.CharField(max_length=12,choices=PRIORITY,default="medium")
    assignee=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL,related_name="assigned_issues")
    reporter=models.ForeignKey(User,on_delete=models.PROTECT,related_name="reported_issues")
    issue_no=models.PositiveIntegerField()
    class Meta: ordering=["project_id","issue_no"]; constraints=[models.UniqueConstraint(fields=["project","issue_no"],name="unique_issue_number")]
    @property
    def issue_key(self): return f"{self.project.key}-{self.issue_no}"

class Comment(TenantModel):
    issue=models.ForeignKey(Issue,on_delete=models.CASCADE,related_name="comments")
    author=models.ForeignKey(User,on_delete=models.PROTECT)
    body=models.TextField(max_length=6000)

class AuditEvent(TenantModel):
    actor=models.ForeignKey(User,null=True,on_delete=models.SET_NULL)
    entity_type=models.CharField(max_length=40)
    entity_id=models.CharField(max_length=64)
    action=models.CharField(max_length=50)
    payload=models.JSONField(default=dict)
    at=models.DateTimeField(default=timezone.now,db_index=True)

class Subscription(TenantModel):
    stripe_customer_id=models.CharField(max_length=140,blank=True)
    stripe_subscription_id=models.CharField(max_length=140,blank=True)
    plan=models.CharField(max_length=24,default="free")
    status=models.CharField(max_length=24,default="active")
    period_end=models.DateTimeField(null=True,blank=True)


class Attachment(TenantModel):
    issue=models.ForeignKey(Issue,on_delete=models.CASCADE,related_name="attachments")
    uploaded_by=models.ForeignKey(User,on_delete=models.PROTECT)
    file=models.FileField(upload_to="tenant-attachments/%Y/%m/")
    original_name=models.CharField(max_length=255)
    content_type=models.CharField(max_length=120,blank=True)
    size=models.PositiveBigIntegerField(default=0)

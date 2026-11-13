from rest_framework.routers import DefaultRouter
from django.urls import path,include
from .views import ProjectViewSet,SprintViewSet,IssueViewSet,AuditView,CheckoutView,StripeWebhookView,WorkspaceView,ActiveWorkspaceView,WorkspaceMembersView,AttachmentView,BillingManageView
router=DefaultRouter()
router.register("projects",ProjectViewSet,basename="project")
router.register("sprints",SprintViewSet,basename="sprint")
router.register("issues",IssueViewSet,basename="issue")
urlpatterns=[path("",include(router.urls)),path("workspaces/",WorkspaceView.as_view()),path("workspaces/active/",ActiveWorkspaceView.as_view()),path("workspaces/members/",WorkspaceMembersView.as_view()),path("issues/<int:issue_id>/attachments/",AttachmentView.as_view()),path("audit/",AuditView.as_view()),path("billing/checkout/",CheckoutView.as_view()),path("billing/manage/",BillingManageView.as_view()),path("billing/webhook/",StripeWebhookView.as_view())]

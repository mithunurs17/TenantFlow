from rest_framework.routers import DefaultRouter
from django.urls import path,include
from .views import ProjectViewSet,SprintViewSet,IssueViewSet,AuditView,CheckoutView,StripeWebhookView
router=DefaultRouter()
router.register("projects",ProjectViewSet,basename="project")
router.register("sprints",SprintViewSet,basename="sprint")
router.register("issues",IssueViewSet,basename="issue")
urlpatterns=[path("",include(router.urls)),path("audit/",AuditView.as_view()),path("billing/checkout/",CheckoutView.as_view()),path("billing/webhook/",StripeWebhookView.as_view())]

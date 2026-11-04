from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core.views import RegisterView, HealthView
urlpatterns=[
 path("admin/",admin.site.urls),path("api/health/",HealthView.as_view()),
 path("api/auth/register/",RegisterView.as_view()),path("api/auth/token/",TokenObtainPairView.as_view()),
 path("api/auth/refresh/",TokenRefreshView.as_view()),path("api/",include("core.urls")),
]

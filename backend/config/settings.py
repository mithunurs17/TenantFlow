import os
from pathlib import Path
import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend").split(",")
INSTALLED_APPS = [
 "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions",
 "django.contrib.messages","django.contrib.staticfiles","rest_framework","corsheaders","core",
]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","corsheaders.middleware.CorsMiddleware",
 "django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware",
 "django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware",
 "django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF="config.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[],"APP_DIRS":True,
 "OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth",
 "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION="config.wsgi.application"
DATABASES={"default":dj_database_url.config(default=os.getenv("DATABASE_URL","sqlite:///db.sqlite3"))}
AUTH_USER_MODEL="core.User"
AUTH_PASSWORD_VALIDATORS=[{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
 {"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"}]
LANGUAGE_CODE="en-us"; TIME_ZONE="Asia/Kolkata"; USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS=[os.getenv("FRONTEND_URL","http://localhost:5173")]
REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES":["rest_framework_simplejwt.authentication.JWTAuthentication"],
 "DEFAULT_PERMISSION_CLASSES":["rest_framework.permissions.IsAuthenticated"]}
from datetime import timedelta
SIMPLE_JWT={"ACCESS_TOKEN_LIFETIME":timedelta(hours=8)}
CELERY_BROKER_URL=os.getenv("REDIS_URL","redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER=os.getenv("CELERY_TASK_ALWAYS_EAGER","False").lower()=="true"
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")

MEDIA_URL="/media/"
MEDIA_ROOT=BASE_DIR/"media"
REST_FRAMEWORK.update({"DEFAULT_PAGINATION_CLASS":"rest_framework.pagination.PageNumberPagination","PAGE_SIZE":100})

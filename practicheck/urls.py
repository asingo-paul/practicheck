from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.http import JsonResponse

# Views
def home(request):
    return render(request, "home.html")  # ✅ use your template

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("health/", health_check),          # Health endpoint
    path("", home, name="home"),            # Root landing page
    path("admin/", admin.site.urls),

    # App urls
    path("accounts/", include("accounts.urls")),
    path("attachments/", include(("attachments.urls", "attachments"), namespace="attachments")),
    path("evaluations/", include(("evaluations.urls", "evaluations"), namespace="evaluations")),
    path("accounts/", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

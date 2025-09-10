# from django.urls import path
# from . import views

# app_name = "evaluations"   # 👈 Add this line

# urlpatterns = [
#     path("", views.index, name="index"),   # example
# ]

# evaluations/urls.py
from django.urls import path
from . import views

app_name = "evaluations"

urlpatterns = [
    path("supervisor/dashboard/", views.supervisor_dashboard, name="supervisor_dashboard"),
    path('lecturer/dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
]


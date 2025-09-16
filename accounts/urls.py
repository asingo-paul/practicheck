from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("upload-profile-picture/", views.upload_profile_picture, name="upload_profile_picture"),
    path('check-username/', views.check_username, name='check_username'),
    path('about/', views.about, name='about'),

    # Password reset
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html"), name="password_reset_confirm"),
    path("password-reset-complete/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
]

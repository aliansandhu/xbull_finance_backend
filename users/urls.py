from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import SignupView, LoginViewSet, ForgotPasswordViewSet, PasswordResetConfirmView, \
    VerifyAccountViewSet, ProfileUpdateView, PasswordResetView, SimpleUserRegisterViewSet

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("register-user/", SimpleUserRegisterViewSet.as_view(), name="register-user"),
    path("login/", LoginViewSet.as_view(), name="login"),
    path("forgot-password/", ForgotPasswordViewSet.as_view(), name="forgot-password"),
    path("reset-password/<str:uuid>/", PasswordResetConfirmView.as_view(), name="reset-password"),
    path('token/refresh', TokenRefreshView.as_view()),
    path('verify-user/<str:uuid>/', VerifyAccountViewSet.as_view(), name="verify-user", kwargs={'format': None}),
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
]

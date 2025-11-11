from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import update_last_login
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.renderers import JSONRenderer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (
    UserSignupSerializer,
    LoginViewSerializer,
    PasswordResetRequestSerializer,
    ConfirmPasswordSerializer, VerifyAccountSerializer, UserSerializer, PasswordResetSerializer,
    SimpleUserRegisterSerializer,
)
from .utils import send_email

User = get_user_model()


class SignupView(generics.CreateAPIView):

    def post(self, request, *args, **kwargs):
        data = request.data

        serializer = UserSignupSerializer(data=data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.create(serializer.validated_data)
        verification_uuid = urlsafe_base64_encode(force_bytes(user.email, encoding='utf-8'))
        verification_url = f'https://academy.xfinancebull.com/verify-user/{verification_uuid}?format=json'
        name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.email
        send_email(
            sender=settings.EMAIL_HOST_USER,
            recipients=[{'email': user.email}],
            name=name,
            link=verification_url,
            email_type='signup',
        )

        return Response(
            {"message": "A verification email has been sent to you. Kindly verify to continue with login"},
            status=status.HTTP_201_CREATED
        )


class SimpleUserRegisterViewSet(generics.CreateAPIView):
    serializer_class = SimpleUserRegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        user.is_active = True
        user.save()
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return Response(
            {
                "user": UserSerializer(user).data,
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
            status=status.HTTP_201_CREATED
        )


class LoginViewSet(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = LoginViewSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            return Response({"error": "Email and password are required.", "success": False},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist.", "success": False},
                            status=status.HTTP_401_UNAUTHORIZED)
        if user.check_password(password):
            if user.is_active:
                refresh = RefreshToken.for_user(user)
                update_last_login(None, user)
                return Response({"token": str(refresh.access_token), "user": UserSerializer(user).data,
                                 "success": True}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Account is not active. Please verify your email before Login", "success": False},
                    status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"error": "Invalid email or password.", "success": False},
                            status=status.HTTP_401_UNAUTHORIZED)


class ForgotPasswordViewSet(APIView):

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"error": "User with this email does not exist.", "success": False},
                                status=status.HTTP_404_NOT_FOUND)
            uuid = urlsafe_base64_encode(force_bytes(user.email, encoding='utf-8'))
            reset_password_url = f"https://academy.xfinancebull.com/reset-password/{uuid}"
            name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.email
            send_email(
                sender=settings.EMAIL_HOST_USER,
                recipients=[{'email': user.email}],
                name=name,
                link=reset_password_url,
                email_type='forgot_password',
            )
            return Response(
                {"message": "Password reset email has been sent.", "success": True},
                status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    serializer_class = ConfirmPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'uid': kwargs['uuid']})
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            new_password = serializer.validated_data['password']
            user.set_password(new_password)
            user.save()
            return Response(
                {"detail": "Password has been successfully reset.", "success": True},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"message": f'{e}', "success": False},
                status=400,
            )


class VerifyAccountViewSet(APIView):
    serializer_class = VerifyAccountSerializer
    renderer_classes = [JSONRenderer]  # Force JSON response

    def get(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data, context={'uid': kwargs['uuid']})
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            user.is_active = True
            user.save()
            return Response(
                {"detail": "Your account has been verified", "success": True},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"message": f'{e}', "success": False},
                status=400,
            )


class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    """
    API to retrieve and update the profile of the authenticated user.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated,]

    def get_object(self):
        """Retrieve the user object for the current authenticated user."""
        return self.request.user

    def patch(self, request, *args, **kwargs):
        """
        Update the user's profile.
        """
        return self.update(request, *args, **kwargs)


class PasswordResetView(generics.UpdateAPIView):
    """
    API to reset the password for the authenticated user.
    """
    serializer_class = PasswordResetSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Retrieve the user object for the current authenticated user."""
        return self.request.user

    def patch(self, request, *args, **kwargs):
        """
        Update the user's password.
        """
        # Validate the serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get the validated password
        new_password = serializer.validated_data['new_password']

        # Update the password
        user = self.get_object()
        user.password = make_password(new_password)
        user.save()

        return Response({"detail": "Password has been successfully updated."}, status=status.HTTP_200_OK)

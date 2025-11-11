from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "email", "password", "confirm_password", "first_name", "last_name", "x_handle",
        ]

    def validate(self, data):
        """Ensure that password and confirm_password match."""
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        """Remove confirm_password before saving and create the user."""
        validated_data.pop("confirm_password")
        return User.objects.create_user(**validated_data)


class SimpleUserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class LoginViewSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super(LoginViewSerializer, cls).get_token(user)
        token['email'] = user.email
        return token


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data, **kwargs):
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")
        try:
            user_id_bytes = urlsafe_base64_decode(self.context['uid'])
            user_id = force_str(user_id_bytes)
            user = User.objects.get(email=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid UID.")

        data['user'] = user
        return data


class VerifyAccountSerializer(serializers.Serializer):

    def validate(self, data):
        try:
            user_id_bytes = urlsafe_base64_decode(self.context['uid'])
            user_id = force_str(user_id_bytes)
            user = User.objects.get(email=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid UID.")

        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number', 'x_handle', 'is_active', 'is_superuser',
                  'address', 'city', 'state', 'zip_code',]


class UserAdminSerializer(serializers.ModelSerializer):
    last_login = serializers.DateTimeField(read_only=True)
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number', 'x_handle', 'id', 'last_login']


class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("The passwords do not match.")
        return data

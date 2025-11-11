import pytz
from django_extensions.db.models import TimeStampedModel, ActivatorModel
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now
from phonenumber_field.modelfields import PhoneNumberField

# Create your models here.

TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.all_timezones]


class BaseModel(TimeStampedModel, ActivatorModel):
    is_deleted = models.BooleanField(default=False)
    created_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'base'

    class Meta:
        abstract = True

    @property
    def is_active(self):
        return self.status == ActivatorModel.ACTIVE_STATUS

    def deactivate(self, *args, **kwargs):
        self.status = super().INACTIVE_STATUS
        self.deactivate_date = now()
        super().save(*args, **kwargs)


class CustomUserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifier"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        if extra_fields.get("is_superuser"):
            user.is_active = True
        else:
            user.is_active = False
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)
    address = models.TextField(blank=True, null=True)
    phone_number = PhoneNumberField(region="US", blank=True, null=True)
    city = models.CharField(max_length=50, default=None, null=True, blank=True)
    state = models.CharField(max_length=50, default=None, null=True, blank=True)
    zip_code = models.CharField(max_length=50, default=None, null=True, blank=True)
    time_zone = models.CharField(max_length=32, choices=TIMEZONE_CHOICES)
    x_handle = models.CharField(max_length=255, null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []


    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email

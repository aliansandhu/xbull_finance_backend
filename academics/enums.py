from django.db import models


class CourseTypeEnum(models.TextChoices):
    FREE = "free", "Free"
    PAID = "paid", "Paid"


class QuestionTypeEnum(models.TextChoices):
    MCQ = "mcq", "MCQ"
    TRUE_FALSE = "true_false", "True/False"
    TEXT = "text", "Text"

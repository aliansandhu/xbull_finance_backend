from django.db import models
from django.utils.crypto import get_random_string

from academics.enums import CourseTypeEnum, QuestionTypeEnum
from academics.utils import video_upload_path, CustomS3Storage
from users.models import BaseModel


class Course(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    course_type = models.CharField(max_length=10, choices=CourseTypeEnum.choices, default=CourseTypeEnum.FREE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    level = models.CharField(max_length=50, null=True, blank=True)
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    lessons = models.PositiveIntegerField(default=0)
    slug = models.SlugField(max_length=255, unique=True)
    tier = models.PositiveIntegerField(default=0)
    course_image = models.URLField(null=True, blank=True)
    course_badge = models.URLField(null=True, blank=True)


    class Meta:
        db_table = 'courses'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = f"{self.title.lower().replace(' ', '-')}-{self.level.lower().replace(' ', '-')}"
        super().save(*args, **kwargs)


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")

    class Meta:
        ordering = ["order"]
        db_table = 'modules'

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class VideoLecture(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lectures")
    title = models.CharField(max_length=255)
    video_url = models.URLField(null=True, blank=True)
    video_file = models.FileField(upload_to=video_upload_path, storage=CustomS3Storage(), null=True, blank=True)
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        db_table = 'video_lectures'

    def __str__(self):
        return f"{self.module.title} - {self.title}"


class Quiz(models.Model):
    module = models.ForeignKey("Module", on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        db_table = "quizzes"

    def __str__(self):
        return f"{self.module.title} - {self.title} (Attempt {self.order})"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QuestionTypeEnum.choices, default=QuestionTypeEnum.MCQ)

    class Meta:
        db_table = 'questions'

    def __str__(self):
        return f"{self.quiz.module.title} - {self.text}"


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = 'question_options'

    def __str__(self):
        return f"{self.question.text} - {self.text}"


class UserVideoProgress(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name="video_progress")
    video = models.ForeignKey('academics.VideoLecture', on_delete=models.CASCADE, related_name="user_progress")
    watched_seconds = models.PositiveIntegerField(default=0)  # Track last watched second
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "video")
        db_table = 'user_video_progress'

    def __str__(self):
        return f"{self.user.email} - {self.video.title} - {'Completed' if self.completed else f'Watched {self.watched_seconds}s'}"


class UserModuleProgress(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="module_progress")
    module = models.ForeignKey("academics.Module", on_delete=models.CASCADE, related_name="user_module_progress")
    video_completed = models.BooleanField(default=False)
    quiz_passed = models.BooleanField(default=False)
    attempted = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    failed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "module")
        db_table = "user_module_progress"

    def __str__(self):
        return f"{self.user.email} - {self.module.title} - {'Completed' if self.completed else 'In Progress'}"


class UserCourseProgress(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name="course_progress")
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE, related_name="user_course_progress")
    completed_modules = models.PositiveIntegerField(default=0)  # Count of completed modules
    total_modules = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "course")
        db_table = 'user_course_progress'

    def __str__(self):
        return f"{self.user.email} - {self.course.title} - {'Completed' if self.completed else f'{self.completed_modules}/{self.total_modules} Modules'}"


class UserCertification(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="certifications")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="certifications")
    certificate_url = models.URLField(unique=True)
    issued_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')
        db_table = 'user_certifications'

    def __str__(self):
        return f"Certificate for {self.user.email} - {self.course.title}"

    def save(self, *args, **kwargs):
        """Generate a unique certification URL if not already set"""
        if not self.certificate_url:
            unique_code = get_random_string(length=12)
            self.certificate_url = f"https://certificates.yourdomain.com/{unique_code}"
        super().save(*args, **kwargs)


class UserQuizAttempt(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    passed = models.BooleanField(default=False)
    attempt_count = models.IntegerField(default=1)
    attempt_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_quiz_attempts"

    def __str__(self):
        return f"{self.user.email} - {self.quiz.title} - {'Passed' if self.passed else 'Failed'}"

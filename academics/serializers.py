from rest_framework import serializers
from .models import Course, Module, VideoLecture, Quiz, Question, QuestionOption, UserVideoProgress, UserModuleProgress, \
    UserCourseProgress
from django.conf import settings


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'course_type', 'level', 'lessons', 'duration', 'slug', 'tier',
                  'course_image', 'course_badge',]


class ModuleSerializer(serializers.ModelSerializer):
    lectures_count = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    lessons = serializers.SerializerMethodField()
    has_quiz = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'title', 'lectures_count', 'total_duration', 'color', 'lessons', 'has_quiz']

    def get_lectures_count(self, obj):
        """Count the number of lectures in the module"""
        return obj.lectures.count()

    def get_total_duration(self, obj):
        """Sum the duration of all lectures and format it as hours, minutes, and seconds"""
        total_seconds = sum(obj.lectures.values_list('duration', flat=True))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours}H {minutes}M {seconds}S"

    def get_lessons(self, obj):
        """Get a list of lecture titles"""
        return list(obj.lectures.values_list('title', 'id'))

    def get_has_quiz(self, obj):
        """Check if this module has a quiz"""
        return Quiz.objects.filter(module=obj).exists()

    def get_color(self, obj):
        """Assign colors based on module order or predefined logic"""
        color_map = ["bg-orange-500", "bg-blue-500", "bg-green-500", "bg-purple-500"]
        return color_map[obj.order % len(color_map)]


class VideoLectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoLecture
        fields = ['id', 'title', 'video_url', 'video_file', 'duration', 'order', 'module']

    def get_streaming_url(self, obj):
        """Generate a URL for streaming video."""
        return f"{settings.MEDIA_URL}stream-video/{obj.id}/"

class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "text"]

class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "question_type", "options"]

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "questions"]


class UserVideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVideoProgress
        fields = ['video', 'watched_seconds', 'completed']


class UserModuleProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModuleProgress
        fields = ['module', 'video_completed', 'quiz_passed', 'completed']


class UserCourseProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCourseProgress
        fields = ['course', 'completed_modules', 'total_modules', 'completed']


class UserCourseProgressAdminSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = UserCourseProgress
        fields = ['course', 'user', 'user_name', 'course_title', 'completed_modules', 'total_modules', 'completed',
                  'progress_percentage']

    def get_course_title(self, obj):
        return f"{obj.course.title}-{obj.course.level}"

    def get_user_name(self, obj):
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return f"{obj.user.email}"

    def get_progress_percentage(self, obj):
        modules = Module.objects.filter(course=obj.course)
        total_modules = modules.count()
        completed_modules = UserModuleProgress.objects.filter(user=obj.user, module__in=modules, completed=True).count()

        total_videos = VideoLecture.objects.filter(module__in=modules).count()
        completed_videos = UserVideoProgress.objects.filter(user=obj.user, video__module__in=modules,
                                                            completed=True).count()

        module_percentage = (completed_modules / total_modules) * 50 if total_modules > 0 else 0  # 50% weight
        video_percentage = (completed_videos / total_videos) * 50 if total_videos > 0 else 0  # 50% weight
        overall_progress_percentage = module_percentage + video_percentage

        course_completed = completed_modules == total_modules if total_modules > 0 else False

        return {
            "completed_modules": completed_modules,
            "total_modules": total_modules,
            "total_videos": total_videos,
            "completed_videos": completed_videos,
            "progress_percentage": round(overall_progress_percentage, 2),
            "completed": course_completed
        }


class UserProgressSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    module_progress = serializers.SerializerMethodField()
    video_progress = serializers.SerializerMethodField()
    # quiz_results = serializers.SerializerMethodField()

    class Meta:
        model = UserCourseProgress
        fields = [
            'course',
            'user',
            'module_progress',
            'video_progress',
            # 'quiz_results',
            'progress_percentage'
        ]

    def get_course(self, obj):
        return f"{obj.course.title}-{obj.course.level}" if obj.course else None

    def get_user(self, obj):
        return {"email": obj.user.email, "name": f"{obj.user.first_name} {obj.user.last_name}",
                "x_handle": obj.user.x_handle}

    def get_progress_percentage(self, obj):
        modules = Module.objects.filter(course=obj.course)
        total_modules = modules.count()
        completed_modules = UserModuleProgress.objects.filter(user=obj.user, module__in=modules, completed=True).count()

        total_videos = VideoLecture.objects.filter(module__in=modules).count()
        completed_videos = UserVideoProgress.objects.filter(user=obj.user, video__module__in=modules, completed=True).count()

        module_percentage = (completed_modules / total_modules) * 50 if total_modules > 0 else 0
        video_percentage = (completed_videos / total_videos) * 50 if total_videos > 0 else 0
        overall_progress_percentage = module_percentage + video_percentage

        return round(overall_progress_percentage, 2)

    def get_module_progress(self, obj):
        modules = Module.objects.filter(course=obj.course)

        total_modules = modules.count()
        completed_modules = UserModuleProgress.objects.filter(user=obj.user, module__in=modules, completed=True).count()
        current_modules = UserModuleProgress.objects.filter(user=obj.user, module__in=modules, completed=False).count()

        current_module_progress = 0
        if current_modules > 0:
            total_progress = 0
            for module in modules:
                progress = UserModuleProgress.objects.filter(user=obj.user, module=module).first()

                if progress and not progress.completed:
                    video_percentage = 100 if progress.video_completed else 0
                    quiz_percentage = 100 if progress.quiz_passed else 0
                    module_progress = (video_percentage * 0.5) + (quiz_percentage * 0.5)
                    total_progress += module_progress
            current_module_progress = total_progress / current_modules if current_modules > 0 else 0

        module_percentage = (completed_modules / total_modules) * 100 if total_modules > 0 else 0

        return {
            "completed_modules": completed_modules,
            "current_modules": current_modules,
            "current_module_progress": round(current_module_progress, 2),
            "total_modules": total_modules,
            "module_percentage": round(module_percentage, 2),
        }

    def get_video_progress(self, obj):
        modules = Module.objects.filter(course=obj.course)
        total_videos = VideoLecture.objects.filter(module__in=modules).count()
        completed_videos = UserVideoProgress.objects.filter(user=obj.user, video__module__in=modules, completed=True).count()

        video_percentage = (completed_videos / total_videos) * 100 if total_videos > 0 else 0
        return {
            "completed_videos": completed_videos,
            "total_videos": total_videos,
            "video_percentage": round(video_percentage, 2),
        }

    # def get_quiz_results(self, obj):
    #     modules = Module.objects.filter(course=obj.course)
    #     quizzes = Quiz.objects.filter(module__in=modules)
    #     quiz_results = []
    #
    #     for quiz in quizzes:
    #         attempts = UserQuizAttempt.objects.filter(user=obj.user, quiz=quiz)
    #         total_attempts = attempts.count()
    #         correct_answers = attempts.filter(passed=True).count()
    #
    #         quiz_results.append({
    #             "quiz_title": quiz.title,
    #             "total_attempts": total_attempts,
    #             "correct_answers": correct_answers,
    #             "quiz_percentage": round((correct_answers / total_attempts) * 100, 2) if total_attempts > 0 else 0,
    #         })

    #    return quiz_results

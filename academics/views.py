from math import ceil

from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, generics, filters
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from users.serializers import UserAdminSerializer
from .models import Course, Module, VideoLecture, Quiz, UserCourseProgress, \
    UserModuleProgress, UserVideoProgress, UserQuizAttempt
from .serializers import (
    CourseSerializer, ModuleSerializer, VideoLectureSerializer,
    QuizSerializer, UserCourseProgressSerializer,
    UserModuleProgressSerializer, UserVideoProgressSerializer, UserCourseProgressAdminSerializer, UserProgressSerializer
)

from django.db.models import Sum

User = get_user_model()


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Retrieves all courses associated with the user & tracks progress.
    - Shows completed modules vs total modules
    - Calculates progress percentage based on module and video completion
    - Provides total video lectures count and course duration in hours
    """
    permission_classes = [AllowAny,]
    serializer_class = CourseSerializer

    def get_queryset(self):
        """Return all courses the user has access to."""
        return Course.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        """Retrieve courses & track progress for the authenticated user."""
        user = request.user
        courses = self.get_queryset()
        course_data = []

        for course in courses:
            course_serialized = self.get_serializer(course).data

            # Get modules for this course (needed for all users)
            modules = Module.objects.filter(course=course)
            total_modules = modules.count()

            # Calculate total video duration (seconds → hours) - for all users
            total_duration_seconds = (
                    VideoLecture.objects.filter(module__in=modules)
                    .aggregate(Sum("duration"))["duration__sum"]
                    or 0
            )
            total_duration_hours = total_duration_seconds / 3600

            # Calculate total video counts - for all users
            total_videos = VideoLecture.objects.filter(module__in=modules).count()

            # Base structure with total counts (available for all users)
            progress_data = {
                "completed_modules": 0,
                "total_modules": total_modules,  # ✅ Show for all users
                "total_videos": total_videos,  # ✅ Show for all users
                "completed_videos": 0,
                "total_duration_hours": round(total_duration_hours, 2),  # ✅ Show for all users
                "progress_percentage": 0,
                "completed": False,
            }

            # User-specific progress (only for authenticated users)
            if user.is_authenticated:
                completed_modules = UserModuleProgress.objects.filter(
                    user=user, module__in=modules, completed=True
                ).count()

                completed_videos = UserVideoProgress.objects.filter(
                    user=user, video__module__in=modules, completed=True
                ).count()

                # Compute progress percentages
                module_percentage = (completed_modules / total_modules) * 50 if total_modules > 0 else 0
                video_percentage = (completed_videos / total_videos) * 50 if total_videos > 0 else 0
                overall_progress_percentage = module_percentage + video_percentage

                # Update or create course progress record
                course_completed = completed_modules == total_modules if total_modules > 0 else False
                course_progress, _ = UserCourseProgress.objects.get_or_create(
                    user=user, course=course, defaults={"total_modules": total_modules}
                )
                course_progress.completed_modules = completed_modules
                course_progress.completed = course_completed
                course_progress.save()

                # ✅ Update user-specific progress data
                progress_data.update({
                    "completed_modules": completed_modules,
                    "completed_videos": completed_videos,
                    "progress_percentage": round(overall_progress_percentage, 2),
                    "completed": course_completed,
                })

            # ✅ Always include progress data (with totals for all, user-specific for authenticated)
            course_serialized.update(progress_data)
            course_data.append(course_serialized)

        return Response(course_data, status=status.HTTP_200_OK)


class CourseProgressView(generics.RetrieveUpdateAPIView):
    """
    API to track and update course progress.
    - Updates progress when a module is completed
    - Calculates progress percentage
    - Marks course as completed when all modules are completed
    """
    serializer_class = UserCourseProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Retrieve user's course progress."""
        user = self.request.user
        course_id = self.kwargs.get('course_id')
        return get_object_or_404(UserCourseProgress, user=user, course_id=course_id)

    def patch(self, request, *args, **kwargs):
        """Update user's course progress manually if needed."""
        user = request.user
        course_id = self.kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id)

        # Get or create course progress and ensure 'total_modules' is set
        course_progress, created = UserCourseProgress.objects.get_or_create(user=user, course=course)

        # Calculate the total modules and completed modules
        total_modules = Module.objects.filter(course=course).count()
        completed_modules = UserModuleProgress.objects.filter(user=user, module__course=course, completed=True).count()

        # Ensure total_modules is set on the instance
        if created:
            course_progress.total_modules = total_modules

        # Calculate progress percentage
        progress_percentage = (completed_modules / total_modules) * 100 if total_modules > 0 else 0

        # Check if the course is completed
        course_completed = completed_modules == total_modules if total_modules > 0 else False

        # Update the course progress
        course_progress.completed_modules = completed_modules
        course_progress.completed = course_completed

        # Save the progress
        course_progress.save()

        return Response({
            "course_id": course.id,
            "course_title": course.title,
            "completed_modules": completed_modules,
            "total_modules": total_modules,
            "progress_percentage": round(progress_percentage, 2),
            "completed": course_completed
        }, status=status.HTTP_200_OK)


class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny,]
    serializer_class = ModuleSerializer

    def get_queryset(self):
        """Filter modules based on course ID if provided"""
        course_id = self.kwargs.get("course_id")

        if course_id:
            course = get_object_or_404(Course, id=course_id)
            data = Module.objects.filter(course=course)
            return data
        return Module.objects.none()

    def list(self, request, *args, **kwargs):
        """Handle GET request to return modules by course ID"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=200)


class VideoLectureViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny,]
    authentication_classes = []  # Disable authentication for this view
    serializer_class = VideoLectureSerializer

    def get_queryset(self):
        """Return video lectures for a specific module"""
        module_id = self.kwargs.get("module_id")
        if module_id:
            return VideoLecture.objects.filter(module_id=module_id)
        return VideoLecture.objects.all()

    def list(self, request, *args, **kwargs):
        """Handle GET request and include quizzes along with lectures"""
        module_id = kwargs.get("module_id")
        if not module_id:
            return Response({"error": "Module ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if module exists
        module = get_object_or_404(Module, id=module_id)

        # Get videos
        video_queryset = self.get_queryset()
        video_serializer = self.get_serializer(video_queryset, many=True)

        # Get quiz for the module (if available)
        quiz = Quiz.objects.filter(module=module).first()
        quiz_serializer = QuizSerializer(quiz) if quiz else None

        # Construct response
        response_data = {
            "id": module.id,
            "module": module.title,
            "videos": video_serializer.data,
            "quiz": quiz_serializer.data if quiz else None
        }

        return Response(response_data, status=status.HTTP_200_OK)


class QuizViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication for this view

    def retrieve(self, request, *args, **kwargs):
        """Fetch quiz for a module"""
        module_id = kwargs.get("module_id")
        if not module_id:
            return Response({"error": "Module ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        module = get_object_or_404(Module, id=module_id)
        quiz = Quiz.objects.filter(module=module).first()
        if not quiz:
            return Response({
                "message": "No quiz found for this module."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=200)


class VideoProgressView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update video progress for a user.
    - `GET`: Fetch user's video progress.
    - `PATCH`: Update watched seconds and mark completion.
    """
    serializer_class = UserVideoProgressSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication for this view

    def get(self, request, *args, **kwargs):
        """Fetch user's video progress."""
        user = request.user
        video_id = self.kwargs.get('video_id')

        video = get_object_or_404(VideoLecture, id=video_id)
        
        # For anonymous users, return default progress
        if not user.is_authenticated:
            return Response({
                "video": video.id,
                "watched_seconds": 0,
                "completed": False
            }, status=status.HTTP_200_OK)
        
        video_progress, created = UserVideoProgress.objects.get_or_create(user=user, video=video)
        return Response(self.serializer_class(video_progress).data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        """Update user's video watch progress."""
        user = request.user
        video_id = self.kwargs.get('video_id')
        
        # For anonymous users, return error or skip update
        if not user.is_authenticated:
            return Response({
                "error": "Authentication required to update video progress"
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        watched_seconds = request.data.get("watched_seconds")
        completed = request.data.get("completed")

        video = get_object_or_404(VideoLecture, id=video_id)
        video_progress, created = UserVideoProgress.objects.get_or_create(user=user, video=video)

        if watched_seconds:
            video_progress.watched_seconds = int(ceil(watched_seconds))

        if int(ceil(watched_seconds)) >= video.duration or completed:
            video_progress.completed = True

        video_progress.save()

        module = video.module
        total_videos = VideoLecture.objects.filter(module=module).count()
        completed_videos = UserVideoProgress.objects.filter(user=user, video__module=module, completed=True).count()

        module_progress, _ = UserModuleProgress.objects.get_or_create(user=user, module=module)
        module_progress.video_completed = completed_videos == total_videos
        module_progress.save()

        return Response(self.serializer_class(video_progress).data, status=status.HTTP_200_OK)


class SubmitQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, module_id):
        user = request.user
        module = get_object_or_404(Module, id=module_id)
        quiz = get_object_or_404(Quiz, module=module, id=request.data.get("quiz_id", None))

        submitted_answers = request.data.get("answers", {})  # {question_id: option_id}
        correct_answers = 0
        total_questions = quiz.questions.count()

        # Validate answers and calculate score
        for question in quiz.questions.all():
            correct_option = question.options.filter(is_correct=True).first()
            selected_answer_id = submitted_answers.get(str(question.id), {}).get("id", None)
            if selected_answer_id and str(correct_option.id) == str(selected_answer_id):
                correct_answers += 1

        score = (correct_answers / total_questions) * 100
        passed = score >= 90  # Passing score is 90%

        user_quiz_attempt, created = UserQuizAttempt.objects.get_or_create(user=user, quiz=quiz)
        user_quiz_attempt.score = score
        user_quiz_attempt.passed = passed
        user_quiz_attempt.save()

        # Update UserModuleProgress
        module_progress, _ = UserModuleProgress.objects.get_or_create(user=user, module=module)
        module_progress.quiz_passed = passed
        module_progress.completed = module_progress.video_completed and passed
        attempted_quizzes = UserQuizAttempt.objects.filter(user=user, quiz__module=module)
        module_progress.save()

        # Reset logic when the user fails any quiz
        if not passed:
            # Reset quizzes only, not videos
            total_quizzes = Quiz.objects.filter(module=module).count()
            cycle_completed = attempted_quizzes.count() // total_quizzes

            if quiz.order == total_quizzes and (cycle_completed * total_quizzes == attempted_quizzes.count()):
                # Reset quiz attempts if last in cycle
                UserQuizAttempt.objects.filter(user=user, quiz__module=module).delete()

            # Reset module progress (but keep video status intact)
            module_progress.completed = False
            module_progress.quiz_passed = False
            if module_progress.attempted >= 1:
                for attempt in attempted_quizzes:
                    attempt.attempted = False

            module_progress.attempted += 1

            module_progress.save()

        return Response({
            "score": score,
            "quiz_passed": passed,
            "module_completed": module_progress.completed
        }, status=status.HTTP_200_OK)


class ModuleProgressView(generics.RetrieveUpdateAPIView):
    """
    API to fetch detailed module progress for a user.
    - Includes video-wise completion status
    - Shows module progress percentage
    - Indicates if quiz is passed
    - Marks module as completed if criteria are met
    """
    serializer_class = UserModuleProgressSerializer
    permission_classes = [AllowAny,]

    def get(self, request, *args, **kwargs):
        user = request.user
        module_id = self.kwargs.get("module_id")
        module = get_object_or_404(Module, id=module_id)

        # Always fetch module videos and quizzes (common for both cases)
        videos = VideoLecture.objects.filter(module=module)
        quizzes = Quiz.objects.filter(module=module)

        total_videos = videos.count()

        # --- CASE 1: Anonymous user ---
        if not user.is_authenticated:
            # Construct "empty" progress data
            video_progress_list = [
                {"video_id": v.id, "title": v.title, "completed": False} for v in videos
            ]

            quiz_progress_list = [
                {
                    "quiz_id": q.id,
                    "quiz_title": q.title,
                    "attempted": False,
                    "passed": False,
                    "call_next": False,
                }
                for q in quizzes
            ]

            return Response(
                {
                    "module_id": module.id,
                    "module_title": module.title,
                    "completed": False,
                    "videos": video_progress_list,
                    "total_videos": total_videos,
                    "total_watched": 0,
                    "video_completed": False,
                    "progress_percentage": 0,
                    "quiz_progress": quiz_progress_list,
                    "quiz_passed": False,
                    "attempted": False,
                },
                status=status.HTTP_200_OK,
            )

        # --- CASE 2: Authenticated user ---
        module_progress, _ = UserModuleProgress.objects.get_or_create(user=user, module=module)

        video_progress_list = []
        completed_videos = 0

        for video in videos:
            video_progress, _ = UserVideoProgress.objects.get_or_create(user=user, video=video)
            video_progress_list.append(
                {
                    "video_id": video.id,
                    "title": video.title,
                    "completed": video_progress.completed,
                }
            )
            if video_progress.completed:
                completed_videos += 1

        # Calculate video progress percentage
        progress_percentage = (completed_videos / total_videos) * 100 if total_videos > 0 else 0

        # Handle quiz progress
        quiz_progress_list = []
        user_attempts = {a.quiz_id: a for a in UserQuizAttempt.objects.filter(user=user, quiz__in=quizzes)}

        all_attempted = all(quiz.id in user_attempts for quiz in quizzes)
        none_passed = all((not user_attempts[quiz.id].passed) for quiz in quizzes if quiz.id in user_attempts)

        if all_attempted and none_passed:
            for quiz in quizzes:
                quiz_progress_list.append(
                    {
                        "quiz_id": quiz.id,
                        "quiz_title": quiz.title,
                        "call_next": True,
                        "attempted": False,
                        "passed": False,
                    }
                )
            all_quizzes_passed = False
        else:
            all_quizzes_passed = True
            for quiz in quizzes:
                user_quiz_attempt = user_attempts.get(quiz.id)
                if user_quiz_attempt:
                    quiz_passed = user_quiz_attempt.passed
                    quiz_progress_list.append(
                        {
                            "quiz_id": quiz.id,
                            "quiz_title": quiz.title,
                            "attempted": True,
                            "passed": quiz_passed,
                        }
                    )
                    if not quiz_passed:
                        all_quizzes_passed = False
                else:
                    quiz_progress_list.append(
                        {
                            "quiz_id": quiz.id,
                            "quiz_title": quiz.title,
                            "attempted": False,
                            "passed": False,
                        }
                    )
                    all_quizzes_passed = False

        # Determine completion status
        is_completed = completed_videos == total_videos and all_quizzes_passed

        # Update module progress
        module_progress.video_completed = completed_videos == total_videos
        module_progress.quiz_passed = all_quizzes_passed
        module_progress.completed = is_completed
        module_progress.save()

        return Response(
            {
                "module_id": module.id,
                "module_title": module.title,
                "completed": is_completed,
                "videos": video_progress_list,
                "total_videos": total_videos,
                "total_watched": completed_videos,
                "video_completed": module_progress.video_completed,
                "progress_percentage": progress_percentage,
                "quiz_progress": quiz_progress_list,
                "quiz_passed": all_quizzes_passed,
                "attempted": module_progress.attempted,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, *args, **kwargs):
        user = request.user
        module_id = self.kwargs.get('module_id')
        module = get_object_or_404(Module, id=module_id)

        total_videos = VideoLecture.objects.filter(module=module).count()
        completed_videos = UserVideoProgress.objects.filter(user=user, video__module=module, completed=True).count()
        all_videos_watched = completed_videos == total_videos

        # Get quizzes for the module
        quizzes = Quiz.objects.filter(module=module)
        all_quizzes_passed = True  # Assume quiz passed initially

        for quiz in quizzes:
            user_quiz_attempt = UserQuizAttempt.objects.filter(user=user, quiz=quiz).first()
            if user_quiz_attempt and not user_quiz_attempt.passed:
                all_quizzes_passed = False  # User failed at least one quiz
                break

        module_progress, _ = UserModuleProgress.objects.get_or_create(user=user, module=module)
        module_progress.video_completed = all_videos_watched
        module_progress.quiz_passed = all_quizzes_passed
        module_progress.completed = module_progress.video_completed and module_progress.quiz_passed
        module_progress.save()

        # If module is completed, check if the next module is available
        if module_progress.completed:
            next_module = Module.objects.filter(course=module.course, order=module.order + 1).first()
            if next_module:
                # Create progress for the next module
                UserModuleProgress.objects.get_or_create(user=user, module=next_module)

        return Response(self.serializer_class(module_progress).data, status=status.HTTP_200_OK)


class GetNextQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, module_id):
        """Fetch the next available quiz for the user in a cyclic manner."""
        user = request.user
        module = get_object_or_404(Module, id=module_id)

        # Fetch all quizzes for this module, ordered by their sequence.
        quizzes = Quiz.objects.filter(module=module).order_by('order')
        attempted_quizzes = UserQuizAttempt.objects.filter(user=user, quiz__module=module)
        if not attempted_quizzes.exists():
            next_quiz = quizzes.order_by("order").first()
        else:
            if attempted_quizzes.count() >= 2:
                # More than 2 attempts → reset and restart
                attempted_quizzes.delete()
                next_quiz = quizzes.order_by("order").first()
            else:
                # Continue to the next quiz in order
                last_attempt = attempted_quizzes.order_by("-attempt_date").first()
                next_order = (last_attempt.quiz.order % quizzes.count()) + 1
                next_quiz = quizzes.filter(order=next_order).first()

        if next_quiz:
            serializer = QuizSerializer(next_quiz)
            return Response(serializer.data, status=200)


        else:
            next_quiz = quizzes.order_by("order").first()
            serializer = QuizSerializer(next_quiz)
            return Response(serializer.data, status=200)


### ADMIN VIEWS


class AdminPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminUserCourseProgressListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, ]
    queryset = UserCourseProgress.objects.all()
    serializer_class = UserCourseProgressAdminSerializer
    # pagination_class = AdminPagination


class AdminUsersAllListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserAdminSerializer
    pagination_class = None

    def get_queryset(self):
        return User.objects.filter(is_active=True)


class AdminUsersListView(generics.ListAPIView, generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserAdminSerializer
    pagination_class = AdminPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]

    ordering_fields = ["email", "first_name", "last_name", "phone_number", "x_handle", "last_login"]
    ordering = ["id"]

    def get_queryset(self):
        return User.objects.filter(is_active=True)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(
            {"detail": f"User {user.username} has been deactivated."},
            status=status.HTTP_200_OK
        )


class UserProgressView(APIView):
    def get(self, request, course_id, user_id):
        try:
            course = Course.objects.get(id=course_id)
            user = User.objects.get(id=user_id)
            user_course_progress = UserCourseProgress.objects.get(user=user, course=course)
            serializer = UserProgressSerializer(user_course_progress)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Course.DoesNotExist:
            return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except UserCourseProgress.DoesNotExist:
            return Response({"detail": "UserCourseProgress not found for the given course and user"},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

from django.urls import path

from .utils import stream_video
from .views import (
    CourseViewSet, ModuleViewSet, VideoLectureViewSet,
    QuizViewSet, CourseProgressView, ModuleProgressView, VideoProgressView, SubmitQuizView, GetNextQuizView,
    AdminUserCourseProgressListView, AdminUsersListView, UserProgressView, AdminUsersAllListView
)

urlpatterns = [
    path("courses/", CourseViewSet.as_view({'get': 'list'}), name="course-list"),
    path("courses/<int:pk>/", CourseViewSet.as_view({'get': 'retrieve'}), name="course-detail"),
    path("modules/", ModuleViewSet.as_view({'get': 'list'}), name="module-list"),
    path('modules/<int:course_id>/', ModuleViewSet.as_view({'get': 'list'})),
    path("modules/<int:pk>/", ModuleViewSet.as_view({'get': 'retrieve'}), name="module-detail"),
    path("lectures/<int:module_id>/", VideoLectureViewSet.as_view({'get': 'list'}), name="lecture-list"),
    path('modules/<int:module_id>/quiz/', QuizViewSet.as_view({'get': 'retrieve'})),
    path('modules/<int:module_id>/quiz/submit/', SubmitQuizView.as_view()),
    path("progress/course/<int:course_id>/", CourseProgressView.as_view(), name="course-progress"),
    path("progress/module/<int:module_id>/", ModuleProgressView.as_view(), name="module-progress"),
    path("progress/video/<int:video_id>/", VideoProgressView.as_view(), name="video-progress"),
    path("stream-video/<int:video_id>/", stream_video, name="stream-video"),
    path("module/<int:module_id>/next-quiz/", GetNextQuizView.as_view(), name="stream-video"),

    ### ADMIN ENDPOINTS
    path('admin-course-progress/', AdminUserCourseProgressListView.as_view(), name='course-progress-list'),
    path('admin-users-list/', AdminUsersListView.as_view(), name='users-list'),
    path('admin-users-list-all/', AdminUsersAllListView.as_view(), name='users-list-all'),
    path('admin-users-list/<int:pk>/', AdminUsersListView.as_view(), name='user-delete'),
    path('user-progress/<int:course_id>/<int:user_id>/', UserProgressView.as_view(), name='user-progress'),
]

from django.contrib import admin

from academics.models import Course, Module, VideoLecture, Quiz, Question, QuestionOption, UserCourseProgress, \
    UserModuleProgress, UserVideoProgress, UserQuizAttempt


# Register your models here.

class VideoLectureAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "get_course", "video_url", "video_file", "duration", "order")
    list_filter = ("module__course", "module")  # ✅ Filter by course and module
    search_fields = ("title", "module__title", "module__course__title")  # ✅ Search by title, module, and course
    ordering = ("order",)  # ✅ Order by sequence

    def get_course(self, obj):
        """Display the course name from the module"""
        return obj.module.course.title
    get_course.short_description = "Course"  # ✅ Custom column name in admin


# ✅ Register VideoLecture in Django Admin with the custom view
admin.site.register(VideoLecture, VideoLectureAdmin)
admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(QuestionOption)
admin.site.register(UserCourseProgress)
admin.site.register(UserModuleProgress)
admin.site.register(UserVideoProgress)
admin.site.register(UserQuizAttempt)

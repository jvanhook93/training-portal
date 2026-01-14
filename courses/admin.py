from django.contrib import admin
from django.utils.timezone import now
from .models import (
    Course,
    CourseVersion,
    Assignment,
    AssignmentCycle,
    VideoProgress,
    Quiz,
    QuizQuestion,
    QuizChoice,
)

# ---------
# Inlines
# ---------

class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 3
    fields = ("text", "is_correct")
    ordering = ("id",)


class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    extra = 1
    fields = ("order", "prompt")
    ordering = ("order", "id")
    show_change_link = True


# ---------
# Admins
# ---------

# ---------
# Inlines
# ---------

class CourseVersionInline(admin.TabularInline):
    model = CourseVersion
    extra = 1
    fields = (
        "version",
        "is_published",
        "published_at",
        "retired_at",
        "pass_score",
        "video_file",
        "pdf_file",
    )
    readonly_fields = ("published_at",)
    show_change_link = True


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 3
    fields = ("text", "is_correct")
    ordering = ("id",)


class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    extra = 1
    fields = ("order", "prompt")
    ordering = ("order", "id")
    show_change_link = True


# ---------
# Actions
# ---------

@admin.action(description="Publish selected course versions (set published_at)")
def publish_course_versions(modeladmin, request, queryset):
    # Mark published and set published_at if missing.
    updated = 0
    for cv in queryset:
        changed = False

        if not cv.is_published:
            cv.is_published = True
            changed = True

        if cv.published_at is None:
            cv.published_at = now()
            changed = True

        # Optional: if you publish, you probably don't want it retired.
        # Uncomment if you want this behavior:
        # if cv.retired_at is not None:
        #     cv.retired_at = None
        #     changed = True

        if changed:
            cv.save(update_fields=["is_published", "published_at"])
            updated += 1

    modeladmin.message_user(request, f"Published {updated} course version(s).")


@admin.action(description="Unpublish selected course versions")
def unpublish_course_versions(modeladmin, request, queryset):
    updated = queryset.update(is_published=False)
    modeladmin.message_user(request, f"Unpublished {updated} course version(s).")


# ---------
# Admins
# ---------

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "is_active", "created_at")
    search_fields = ("code", "title")
    list_filter = ("is_active",)
    inlines = (CourseVersionInline,)


@admin.register(CourseVersion)
class CourseVersionAdmin(admin.ModelAdmin):
    list_display = ("course", "version", "is_published", "published_at", "retired_at", "pass_score")
    search_fields = ("course__code", "course__title", "version")
    list_filter = ("is_published", "course__code")
    autocomplete_fields = ("course", "created_by")
    readonly_fields = ("created_at",)
    actions = (publish_course_versions, unpublish_course_versions)

    # Optional: make uploads visible/organized on the edit page
    fields = (
        "course",
        "version",
        "changelog",
        "video_file",
        "pdf_file",
        "pass_score",
        "is_published",
        "published_at",
        "retired_at",
        "created_by",
        "created_at",
    )

    # This gives you a nice “Quiz” link on the CourseVersion page if it exists
    def quiz_status(self, obj):
        return "✅" if hasattr(obj, "course_quiz") else "—"


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("course_version", "is_required")
    list_filter = ("is_required", "course_version__course__code")
    search_fields = ("course_version__course__code", "course_version__course__title", "course_version__version")
    autocomplete_fields = ("course_version",)

    inlines = (QuizQuestionInline,)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "short_prompt")
    list_filter = ("quiz__course_version__course__code",)
    search_fields = ("prompt",)
    ordering = ("quiz", "order", "id")
    autocomplete_fields = ("quiz",)

    inlines = (QuizChoiceInline,)

    def short_prompt(self, obj):
        return (obj.prompt[:60] + "…") if len(obj.prompt) > 60 else obj.prompt


@admin.register(QuizChoice)
class QuizChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "text", "is_correct")
    list_filter = ("is_correct", "question__quiz__course_version__course__code")
    search_fields = ("text", "question__prompt")
    autocomplete_fields = ("question",)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("assignee", "course_version", "status", "assigned_at", "due_at")
    list_filter = ("status", "course_version__course__code")
    search_fields = ("assignee__username", "assignee__email", "course_version__course__title", "course_version__version")
    autocomplete_fields = ("assignee", "course_version", "assigned_by")


@admin.register(AssignmentCycle)
class AssignmentCycleAdmin(admin.ModelAdmin):
    list_display = ("assignment", "completed_at", "expires_at", "score", "passed", "certificate_id")
    list_filter = ("passed", "assignment__course_version__course__code")
    search_fields = ("certificate_id", "assignment__assignee__username", "assignment__assignee__email")
    readonly_fields = ("certificate_id",)


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "course_version", "percent", "started_at", "completed_at", "last_ping_at")
    list_filter = ("percent", "course_version__course__code")
    search_fields = ("user__username", "user__email", "course_version__course__title")
    autocomplete_fields = ("user", "course_version")

from django.contrib import admin

from .models import RadioChat, RadioProgram


@admin.register(RadioProgram)
class RadioProgramAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "day_of_week",
        "start_time",
        "end_time",
        "status",
        "recording_status",
        "presenter",
    )
    list_filter = ("status", "recording_status", "day_of_week")
    search_fields = ("title", "presenter")


@admin.register(RadioChat)
class RadioChatAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "created_at", "is_deleted")
    list_filter = ("is_deleted",)
    raw_id_fields = ("user",)

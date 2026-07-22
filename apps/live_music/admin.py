from django.contrib import admin

from .models import MusicLiveSession, MusicLiveSlot


@admin.register(MusicLiveSession)
class MusicLiveSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "recording_status", "live_started_at", "created_at")
    list_filter = ("status", "recording_status")
    search_fields = ("title",)


@admin.register(MusicLiveSlot)
class MusicLiveSlotAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "day_of_week", "start_time", "end_time")
    list_filter = ("day_of_week",)
    search_fields = ("title",)

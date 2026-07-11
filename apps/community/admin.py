from django.contrib import admin

from .models import Challenge, ChallengeParticipant, CommunityPost, Poll, PollOption


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 2


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ("author", "post_type", "like_count", "created_at")
    list_filter = ("post_type",)
    raw_id_fields = ("author",)


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "deadline", "participant_count", "is_active")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(ChallengeParticipant)
class ChallengeParticipantAdmin(admin.ModelAdmin):
    list_display = ("challenge", "user", "joined_at")
    raw_id_fields = ("challenge", "user")


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ("question", "vote_count", "is_active", "expires_at")
    inlines = [PollOptionInline]

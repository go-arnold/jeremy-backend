from django.contrib import admin

from .models import PodcastEpisode, PodcastSeries


class EpisodeInline(admin.TabularInline):
    model = PodcastEpisode
    extra = 0
    fields = ("title", "episode_number", "season_number", "duration", "is_featured", "published_at")


@admin.register(PodcastSeries)
class PodcastSeriesAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "episode_count")
    list_filter = ("category", "is_featured")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [EpisodeInline]


@admin.register(PodcastEpisode)
class PodcastEpisodeAdmin(admin.ModelAdmin):
    list_display = ("title", "series", "episode_number", "season_number", "play_count", "published_at")
    list_filter = ("series", "is_featured")
    search_fields = ("title",)
    raw_id_fields = ("series",)

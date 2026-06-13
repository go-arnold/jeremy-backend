from django.contrib import admin

from .models import Artist, ArtistPhoto, ArtistVideo, Genre, Release


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class ReleaseInline(admin.TabularInline):
    model = Release
    extra = 0
    fields = ("title", "format", "release_date", "cover")


class VideoInline(admin.TabularInline):
    model = ArtistVideo
    extra = 0
    fields = ("title", "video_url", "duration", "order")


class PhotoInline(admin.TabularInline):
    model = ArtistPhoto
    extra = 0
    fields = ("image", "caption", "order")


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "is_featured", "release_count", "created_at")
    list_filter = ("is_featured", "genres", "city")
    search_fields = ("name", "city", "bio")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("genres",)
    inlines = [ReleaseInline, VideoInline, PhotoInline]


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "format", "release_date")
    list_filter = ("format",)
    search_fields = ("title", "artist__name")
    raw_id_fields = ("artist",)

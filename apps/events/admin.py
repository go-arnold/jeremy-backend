from django.contrib import admin

from .models import City, Event, EventScheduleItem


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "country")
    prepopulated_fields = {"slug": ("name",)}


class ScheduleInline(admin.TabularInline):
    model = EventScheduleItem
    extra = 0
    fields = ("time", "title", "artist", "duration_minutes", "order")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "city", "category", "status", "date", "is_featured")
    list_filter = ("status", "category", "city", "is_featured")
    search_fields = ("title", "venue_name")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("artists",)
    inlines = [ScheduleInline]
    date_hierarchy = "date"

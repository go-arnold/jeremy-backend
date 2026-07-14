from django.contrib import admin

from .models import Badge, ConsumptionLog, UserBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "criteria_type", "threshold_seconds", "order", "is_active")
    list_filter = ("criteria_type", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "earned_at")
    list_filter = ("badge",)
    raw_id_fields = ("user",)


@admin.register(ConsumptionLog)
class ConsumptionLogAdmin(admin.ModelAdmin):
    list_display = ("user", "content_type", "object_id", "seconds", "created_at")
    list_filter = ("content_type",)
    raw_id_fields = ("user",)

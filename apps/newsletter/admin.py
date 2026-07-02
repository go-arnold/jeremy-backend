from django.contrib import admin

from .models import Newsletter, Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_confirmed", "is_active", "subscribed_at")
    list_filter = ("is_confirmed", "is_active")
    search_fields = ("email",)


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ("subject", "status", "recipient_count", "created_at", "sent_at")
    list_filter = ("status",)
    raw_id_fields = ("created_by",)

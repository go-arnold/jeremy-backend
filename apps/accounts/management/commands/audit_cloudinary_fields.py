from django.apps import apps as django_apps
from django.core.management.base import BaseCommand

from apps.media_uploads.validation import _extract_public_id

# Every (app_label, model_name, field_name) pair backed by a CloudinaryField and reachable
# through a write serializer at some point — see apps.media_uploads.fields.CloudinaryUrlField
# for the fix that stops new bad values from being written; this command finds/repairs rows
# that already went bad before that fix existed.
CLOUDINARY_FIELDS = [
    ("podcasts", "PodcastEpisode", "cover"),
    ("podcasts", "PodcastEpisode", "audio_file"),
    ("podcasts", "PodcastSeries", "cover"),
    ("events", "Event", "image"),
    ("community", "Challenge", "cover"),
    ("releases", "MusicRelease", "cover"),
    ("emissions", "Emission", "cover"),
    ("webtv", "WebTVVideo", "thumbnail"),
    ("radio", "RadioProgram", "cover"),
    ("live_music", "MusicLiveSession", "cover"),
    ("live_music", "MusicLiveSlot", "cover"),
    ("articles", "Article", "featured_image"),
    ("artists", "Artist", "photo"),
    ("artists", "Artist", "cover_image"),
    ("accounts", "User", "avatar"),
    ("accounts", "User", "cover_image"),
]


class Command(BaseCommand):
    help = (
        "Finds CloudinaryField values that are raw URLs instead of clean public_ids (the bug "
        "class fixed by apps.media_uploads.fields.CloudinaryUrlField) — a truncated/malformed "
        "URL, or a real one with the wrong scheme. Reports every affected row by default. "
        "Pass --fix to repair rows in place: a well-formed URL (any scheme) is reduced to its "
        "public_id (no image lost); a malformed/truncated one is cleared to null (falls back "
        "to the frontend's placeholder — nothing left to recover the original image from)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix", action="store_true", help="Apply repairs instead of only reporting them."
        )

    def handle(self, *args, **options):
        fix = options["fix"]
        total_broken = 0
        total_repaired = 0
        total_cleared = 0

        for app_label, model_name, field_name in CLOUDINARY_FIELDS:
            try:
                model = django_apps.get_model(app_label, model_name)
            except LookupError:
                self.stderr.write(f"Skipping unknown model {app_label}.{model_name}")
                continue

            qs = model.objects.exclude(**{field_name: ""}).exclude(**{f"{field_name}__isnull": True})
            for obj in qs:
                raw_value = str(getattr(obj, field_name))
                if not raw_value.lower().startswith("http"):
                    continue  # already a clean public_id

                total_broken += 1
                label = f"{app_label}.{model_name}#{obj.pk}.{field_name}"

                normalized = (
                    "https://" + raw_value.split("://", 1)[1]
                    if raw_value.lower().startswith("http://")
                    else raw_value
                )
                parsed = _extract_public_id(normalized)

                if parsed:
                    public_id, _resource_type = parsed
                    self.stdout.write(f"[REPAIRABLE] {label}: {raw_value!r} -> {public_id!r}")
                    if fix:
                        setattr(obj, field_name, public_id)
                        obj.save(update_fields=[field_name])
                        total_repaired += 1
                else:
                    self.stdout.write(self.style.WARNING(f"[MALFORMED]  {label}: {raw_value!r} -> null"))
                    if fix:
                        setattr(obj, field_name, None)
                        obj.save(update_fields=[field_name])
                        total_cleared += 1

        if total_broken == 0:
            self.stdout.write(self.style.SUCCESS("No broken CloudinaryField values found."))
            return

        if not fix:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{total_broken} broken value(s) found — re-run with --fix to repair them."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nRepaired {total_repaired} value(s), cleared {total_cleared} unrecoverable "
                    f"value(s) to null (out of {total_broken} broken)."
                )
            )

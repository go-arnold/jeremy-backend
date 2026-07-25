"""
Deletes every content row in the database EXCEPT User accounts (and Django/Celery framework
tables: ContentType, Permission, Group, Session, django_celery_beat's schedules, JWT token
blacklist, django_migrations). Used two ways:

  1. Before seed_full_test_data, to start from a clean slate.
  2. After testing, to remove the seeded fake data again.

Two modes:
  --all (default)     : delete every content row, no exceptions. Blunt, complete, irreversible.
  --since-watermark    : only delete rows created after seed_full_test_data's watermark file
                         (safer if real content may have been added since seeding — e.g. an
                         admin created something for real during the test period).

Requires --yes to actually run (dry-run by default, prints counts only).

Run: python manage.py flush_test_data --yes
     python manage.py flush_test_data --since-watermark --yes
"""

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

WATERMARK_PATH = os.path.join(settings.BASE_DIR, ".seed_watermark.json")


def _content_models():
    """Every model this command is allowed to touch. Deliberately does NOT include `User`,
    `ListenHistory` (real per-user history, not seed content), or any Django/Celery/session/auth
    table. Order doesn't matter — Django's delete() collector resolves FK dependencies itself."""
    from apps.articles.models import Article, ArticleLike, Category, Tag
    from apps.articles.models import Comment as ArticleComment
    from apps.artists.models import Artist, ArtistPhoto, ArtistVideo, Genre
    from apps.artists.models import Release as ArtistRelease
    from apps.community.models import (
        Challenge,
        ChallengeParticipant,
        CommunityPost,
        Poll,
        PollOption,
        PollVote,
        PostLike,
    )
    from apps.emissions.models import Emission
    from apps.engagement.models import Comment as EngagementComment
    from apps.engagement.models import Like, SavedItem, Share
    from apps.events.models import City, Event, EventRegistration, EventScheduleItem
    from apps.gamification.models import Badge, ConsumptionLog, UserBadge
    from apps.home.models import FeaturedContent
    from apps.live_music.models import MusicLiveSession, MusicLiveSlot
    from apps.newsletter.models import Newsletter, Subscriber
    from apps.podcasts.models import PodcastEpisode, PodcastSeries
    from apps.radio.models import RadioChat, RadioProgram
    from apps.realtime.models import LiveChatMessage
    from apps.releases.models import MusicRelease
    from apps.webtv.models import WebTVVideo

    return [
        # Generic engagement first (has no dependents) — though order is cosmetic, Django's
        # collector handles the real dependency graph regardless.
        EngagementComment,
        Like,
        Share,
        SavedItem,
        LiveChatMessage,
        # Newsletter
        Subscriber,
        Newsletter,
        # Community
        PostLike,
        PollVote,
        PollOption,
        Poll,
        ChallengeParticipant,
        CommunityPost,
        Challenge,
        # Articles (own comment/like models, not generic engagement)
        ArticleComment,
        ArticleLike,
        Article,
        Tag,
        Category,
        # Gamification
        UserBadge,
        ConsumptionLog,
        Badge,
        # Live content
        WebTVVideo,
        Emission,
        RadioChat,
        RadioProgram,
        MusicLiveSlot,
        MusicLiveSession,
        # Podcasts
        PodcastEpisode,
        PodcastSeries,
        # Releases / artists
        MusicRelease,
        ArtistRelease,
        ArtistPhoto,
        ArtistVideo,
        Artist,
        Genre,
        # Events
        EventRegistration,
        EventScheduleItem,
        Event,
        City,
        # Home
        FeaturedContent,
    ]


class Command(BaseCommand):
    help = "Deletes every content row except User accounts. Dry-run unless --yes is passed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true", help="Actually delete (default: dry-run, counts only)"
        )
        parser.add_argument(
            "--since-watermark",
            action="store_true",
            help="Only delete rows created after seed_full_test_data's watermark file, "
            "instead of everything (safer if real content was added since seeding).",
        )

    def handle(self, *args, **options):
        models = _content_models()
        watermark = None
        if options["since_watermark"]:
            if not os.path.exists(WATERMARK_PATH):
                self.stderr.write(
                    self.style.ERROR(
                        f"No watermark file at {WATERMARK_PATH} — run without --since-watermark, or re-seed first."
                    )
                )
                return
            with open(WATERMARK_PATH) as f:
                watermark = json.load(f)

        total = 0
        for model in models:
            key = f"{model._meta.app_label}.{model._meta.model_name}"
            qs = model.objects.all()
            if watermark is not None:
                max_pk = watermark.get(key)
                if max_pk is None:
                    continue  # model didn't exist at seed time (or nothing to compare) — skip
                qs = qs.filter(pk__gt=max_pk)
            count = qs.count()
            total += count
            if count:
                self.stdout.write(f"{'Would delete' if not options['yes'] else 'Deleting'} {count:>6} {key}")

        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN — {total} rows would be deleted. Re-run with --yes to actually delete."
                )
            )
            return

        for model in models:
            key = f"{model._meta.app_label}.{model._meta.model_name}"
            qs = model.objects.all()
            if watermark is not None:
                max_pk = watermark.get(key)
                if max_pk is None:
                    continue
                qs = qs.filter(pk__gt=max_pk)
            qs.delete()

        if os.path.exists(WATERMARK_PATH) and not options["since_watermark"]:
            os.remove(WATERMARK_PATH)

        self.stdout.write(self.style.SUCCESS(f"Deleted {total} rows. User accounts untouched."))

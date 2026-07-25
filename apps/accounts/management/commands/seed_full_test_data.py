"""
Comprehensive test-data seed for a full frontend visibility/gap-hunting pass: fills every app
(including the ones the old seed_data.py never touched — Live Music, Radio chat, generic
engagement Likes/Comments/Shares/Saves, Gamification, Home FeaturedContent, Artist galleries,
real ChallengeParticipant/PollVote rows) with realistic, hundreds-per-table data spanning
2025-01-01 through 2027-06-30 (deliberately past AND future so upcoming/live/past-style filters
have real data on both sides).

Media strategy (deliberately lightweight, no meaningful Cloudinary quota risk):
  - CloudinaryField images (photos/covers/thumbnails/banners): one small pool of picsum.photos
    placeholders uploaded to Cloudinary ONCE with fixed public_ids, then reused at random across
    every record. Re-running the command detects existing uploads and skips them.
  - Plain URLField video/audio (video_url, audio_url, preview_url): a handful of well-known,
    stable public sample media URLs (Google's GTV sample bucket for video, SoundHelix for audio),
    reused across records — no upload needed at all, since these fields don't require a real
    Cloudinary asset to look/behave correctly.

Writes a watermark file (max pk per model BEFORE seeding) so `flush_test_data --since-watermark`
can remove exactly what this command created, even if real content was added in between.

Run: python manage.py seed_full_test_data [--no-images]
"""

import json
import os
import random
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

fake = Faker(["fr_FR", "en_US"])
User = get_user_model()

WATERMARK_PATH = os.path.join(settings.BASE_DIR, ".seed_watermark.json")

RANGE_START = datetime(2025, 1, 1, tzinfo=timezone.get_current_timezone())
RANGE_END = datetime(2027, 6, 30, tzinfo=timezone.get_current_timezone())

# ── Sample media (no upload needed — plain URLField values) ─────────────────────────────────
SAMPLE_VIDEOS = [
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
]
SAMPLE_AUDIO = [f"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-{i}.mp3" for i in range(1, 11)]

CONGOLESE_ARTISTS = [
    ("Innoss'B", "Goma", "Musique"),
    ("Ferre Gola", "Kinshasa", "Rumba"),
    ("Fally Ipupa", "Kinshasa", "Rumba"),
    ("Alesh", "Goma", "Hip-hop"),
    ("MPR", "Bukavu", "Urbain"),
    ("Werrason", "Kinshasa", "Rumba"),
    ("Koffi Olomide", "Kinshasa", "Rumba"),
    ("Awilo Longomba", "Kinshasa", "Ndombolo"),
    ("Josey", "Goma", "Afropop"),
    ("Singuila", "Kinshasa", "R&B"),
    ("Maître Gims", "Kinshasa", "Hip-hop"),
    ("Dadju", "Kinshasa", "Afropop"),
    ("Locko", "Douala", "Afropop"),
    ("Yemi Alade", "Lagos", "Afrobeats"),
    ("Sauti Sol", "Nairobi", "Afropop"),
    ("Tiwa Savage", "Lagos", "Afrobeats"),
    ("Burna Boy", "Port Harcourt", "Afrobeats"),
    ("Wizkid", "Lagos", "Afrobeats"),
    ("Diamond Platnumz", "Dar es Salaam", "Bongo"),
    ("Harmonize", "Dar es Salaam", "Bongo"),
]
GENRES_DATA = ["Musique", "Hip-hop", "Rumba", "Afro", "Urbain", "R&B", "Ndombolo", "Jazz", "Bongo", "Soul"]
EVENT_CITIES = ["Goma", "Bukavu", "Kinshasa", "Butembo", "Lubumbashi", "Matadi", "Kisangani"]
RADIO_PROGRAMS = [
    "Kivu Morning Flow",
    "Héritage Urbain",
    "Youth Talk",
    "Jazz du Lac",
    "Matin Frais",
    "Le Grand Mix",
    "Parole aux Jeunes",
    "Culture & Création",
    "Soirée Rumba",
    "Nuit des Beats",
]
PODCAST_SERIES = [
    ("Kivu Talk", "talk"),
    ("Voix de Goma", "culture"),
    ("Urban Beats", "musique"),
    ("Société Ouverte", "societe"),
    ("Jeunesse Active", "jeunesse"),
    ("Sport Passion", "sport"),
    ("Artiste en Vue", "culture"),
    ("Le Studio", "musique"),
]
VIDEO_CATEGORIES = ["freestyles", "studio_sessions", "docs", "interviews", "premiers", "concerts"]
ARTICLE_CATEGORIES = [
    ("Musique", "primary"),
    ("Culture", "teal"),
    ("Société", "navy"),
    ("Mode", "yellow"),
    ("Arts Visuels", "primary"),
    ("Littérature", "teal"),
    ("Danse", "navy"),
    ("Sport", "yellow"),
]

_IMG_SPECS = {
    "portrait": [(800, 800, i) for i in range(150)],
    "banner": [(1200, 630, i + 20) for i in range(120)],
    "square": [(500, 500, i + 50) for i in range(120)],
    "thumbnail": [(1280, 720, i + 80) for i in range(120)],
}


def fake_dt(start=RANGE_START, end=RANGE_END):
    return fake.date_time_between(start_date=start, end_date=end, tzinfo=timezone.get_current_timezone())


class Command(BaseCommand):
    help = "Seed hundreds-per-table realistic test data across every app for a frontend visibility/gap pass."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-images", action="store_true", help="Skip Cloudinary image upload (image fields null)"
        )

    def handle(self, *args, **options):
        self._write_watermark()
        images = {} if options["no_images"] else self._upload_placeholder_images()
        # This command issues thousands of queries — under DEBUG=True (local dev), Django
        # retains every single one in memory for the debug toolbar, which measurably slows down
        # (and eventually bloats the memory of) a long-running script like this one. Harmless to
        # disable for the duration of a one-off management command.
        from django.conf import settings as dj_settings

        previous_debug = dj_settings.DEBUG
        dj_settings.DEBUG = False
        try:
            self._run(images)
        finally:
            dj_settings.DEBUG = previous_debug

    def _run(self, images):
        with transaction.atomic():
            users = self._seed_users(200)
            genres = self._seed_genres()
            artists = self._seed_artists(150, genres, images)
            self._seed_artist_galleries(artists, images)
            self._seed_favorite_artists(users, artists)
            self._seed_releases(300, artists, images)
            categories = self._seed_article_categories()
            articles = self._seed_articles(300, users, categories, images)
            self._seed_article_engagement(articles, users)
            cities = self._seed_cities()
            self._seed_events(200, cities, artists, users, images)
            self._seed_radio(images)
            self._seed_podcasts(20, 300, images)
            webtv_videos = self._seed_webtv_videos(200, artists, images)
            emissions = self._seed_emissions(150, artists, images)
            live_sessions = self._seed_live_music(40, artists, images)
            self._seed_gamification(users)
            community_posts = self._seed_community(users, images)
            self._seed_home(artists, emissions, articles, images)
            self._seed_generic_engagement(users, artists, webtv_videos, emissions, community_posts)
            self._seed_live_chat(users, webtv_videos, emissions, live_sessions)
            self._seed_newsletter(users)
        self.stdout.write(self.style.SUCCESS("seed_full_test_data: done."))

    # ── Watermark (for later surgical cleanup) ──────────────────────────────────────────────

    def _write_watermark(self):

        from apps.accounts.management.commands.flush_test_data import _content_models

        watermark = {}
        for model in _content_models():
            key = f"{model._meta.app_label}.{model._meta.model_name}"
            last = model.objects.order_by("-pk").values_list("pk", flat=True).first()
            watermark[key] = last or 0
        with open(WATERMARK_PATH, "w") as f:
            json.dump(watermark, f, indent=2)
        self.stdout.write(f"Watermark written to {WATERMARK_PATH}")

    # ── Image pool ───────────────────────────────────────────────────────────────────────────

    def _ri(self, pool: dict, category: str):
        imgs = pool.get(category, [])
        return random.choice(imgs) if imgs else None

    def _upload_placeholder_images(self) -> dict:
        try:
            import cloudinary.api
            import cloudinary.uploader
        except ImportError:
            self.stdout.write(
                self.style.WARNING("cloudinary package not installed — image fields will be null")
            )
            return {}

        try:
            cloudinary.api.ping()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Cloudinary unreachable ({e!r}) — check CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET "
                    "in .env. Image fields will be null for this run."
                )
            )
            return {}

        total = sum(len(v) for v in _IMG_SPECS.values())
        self.stdout.write(f"Preparing {total} seed images on Cloudinary...")
        pool: dict = {}
        uploaded = reused = failed = 0

        for category, items in _IMG_SPECS.items():
            ids: list = []
            for w, h, seed in items:
                pid = f"artdukivu/seed/{category}/{seed}"
                try:
                    cloudinary.api.resource(pid)
                    ids.append(pid)
                    reused += 1
                    continue
                except Exception:
                    pass
                try:
                    url = f"https://picsum.photos/seed/adk{seed}/{w}/{h}"
                    r = cloudinary.uploader.upload(url, public_id=pid, resource_type="image")
                    ids.append(r["public_id"])
                    uploaded += 1
                except Exception as e:
                    failed += 1
                    self.stdout.write(self.style.WARNING(f"  Skipped {pid}: {e!r}"))
            pool[category] = ids

        if uploaded == 0 and reused == 0:
            self.stdout.write(
                self.style.ERROR(
                    f"No images uploaded or reused ({failed} failed) — image fields will be null. "
                    "Check network egress to picsum.photos from this host and Cloudinary credentials."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Image pool ready: {uploaded} uploaded, {reused} reused, {failed} failed."
                )
            )
        return pool

    # ── Users ────────────────────────────────────────────────────────────────────────────────

    def _seed_users(self, count: int):
        roles = [User.ROLE_EDITOR, User.ROLE_MODERATOR, User.ROLE_VIEWER, User.ROLE_VIEWER, User.ROLE_VIEWER]
        batch = []
        for _ in range(count):
            username = (fake.user_name() + str(random.randint(1, 999999)))[:30]
            batch.append(
                User(
                    email=fake.unique.email(),
                    username=username,
                    handle=f"@{username[:20]}",
                    bio=fake.sentence(nb_words=10)[:199],
                    role=random.choice(roles),
                    is_verified=random.random() > 0.5,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                )
            )
        User.objects.bulk_create(batch, ignore_conflicts=True)
        users = list(User.objects.order_by("-pk")[:count])
        self.stdout.write(f"Created {len(users)} users")
        return users

    # ── Artists ──────────────────────────────────────────────────────────────────────────────

    def _seed_genres(self):
        from apps.artists.models import Genre

        return [
            Genre.objects.get_or_create(name=n, defaults={"slug": n.lower().replace(" ", "-")})[0]
            for n in GENRES_DATA
        ]

    def _seed_artists(self, count: int, genres, images: dict):
        from apps.artists.models import Artist

        genre_map = {g.name: g for g in genres}
        names = list(CONGOLESE_ARTISTS)
        while len(names) < count:
            names.append((fake.name(), random.choice(EVENT_CITIES), random.choice(GENRES_DATA)))
        created = []
        for i, (name, city, genre_name) in enumerate(names[:count]):
            slug = f"{name.lower().replace(' ', '-').replace(chr(39), '')}-{i}"[:220]
            artist, was_created = Artist.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    name=name,
                    city=city,
                    country="Congo (DRC)",
                    bio=fake.paragraph(nb_sentences=6),
                    is_featured=(i < 10),
                    photo=self._ri(images, "portrait"),
                    cover_image=self._ri(images, "banner"),
                    social_links={
                        "instagram": f"https://instagram.com/{slug}",
                        "youtube": f"https://youtube.com/@{slug}",
                    },
                    release_count=0,
                    video_count=0,
                ),
            )
            if was_created:
                g = genre_map.get(genre_name)
                if g:
                    artist.genres.add(g)
            created.append(artist)
        self.stdout.write(f"Created {len(created)} artists")
        return created

    def _seed_artist_galleries(self, artists, images: dict):
        from apps.artists.models import ArtistPhoto, ArtistVideo

        photos, videos = [], []
        for artist in random.sample(artists, min(60, len(artists))):
            for order in range(random.randint(2, 5)):
                pid = self._ri(images, "banner")
                if pid:
                    photos.append(
                        ArtistPhoto(artist=artist, image=pid, caption=fake.sentence(nb_words=6), order=order)
                    )
            for order in range(random.randint(1, 3)):
                videos.append(
                    ArtistVideo(
                        artist=artist,
                        title=fake.catch_phrase()[:199],
                        thumbnail=self._ri(images, "thumbnail"),
                        video_url=random.choice(SAMPLE_VIDEOS),
                        duration=f"{random.randint(2, 15)}:{random.randint(0, 59):02d}",
                        view_count=random.randint(0, 20000),
                        published_at=fake_dt(end=timezone.now()).date(),
                        order=order,
                    )
                )
        ArtistPhoto.objects.bulk_create(photos, ignore_conflicts=True)
        ArtistVideo.objects.bulk_create(videos, ignore_conflicts=True)
        self.stdout.write(f"Created {len(photos)} artist photos, {len(videos)} artist videos")

    def _seed_favorite_artists(self, users, artists):
        for user in random.sample(users, min(80, len(users))):
            user.favorite_artists.set(random.sample(artists, min(random.randint(1, 6), len(artists))))

    # ── Releases ─────────────────────────────────────────────────────────────────────────────

    def _seed_releases(self, count: int, artists, images: dict):
        from apps.releases.models import MusicRelease

        formats = [c for c, _ in MusicRelease.FORMAT_CHOICES]
        batch = []
        for i in range(count):
            artist = random.choice(artists)
            title = f"{fake.catch_phrase()} Vol.{random.randint(1, 5)}"[:200]
            batch.append(
                MusicRelease(
                    artist=artist,
                    title=title,
                    slug=f"release-{i}-{fake.slug()}"[:220],
                    release_date=fake_dt().date(),
                    format=random.choice(formats),
                    cover=self._ri(images, "square"),
                    is_featured=(i < 8),
                    is_premiere=random.random() > 0.85,
                    description=fake.paragraph(nb_sentences=3),
                    preview_url=random.choice(SAMPLE_AUDIO),
                    streaming_links={"spotify": f"https://spotify.com/album/{fake.uuid4()}"},
                )
            )
        MusicRelease.objects.bulk_create(batch, ignore_conflicts=True)
        self.stdout.write(f"Created {count} releases")

    # ── Articles (own ArticleLike/Comment — NOT the generic engagement system) ────────────────

    def _seed_article_categories(self):
        from apps.articles.models import Category, Tag

        cats = [
            Category.objects.get_or_create(name=n, defaults={"color": c})[0] for n, c in ARTICLE_CATEGORIES
        ]
        for t in [
            "Electro",
            "Bukavu",
            "Goma",
            "Festival",
            "Underground",
            "Jazz",
            "Rumba",
            "Hip-hop",
            "Culture",
            "Jeunesse",
            "Mode",
            "Art",
        ]:
            Tag.objects.get_or_create(name=t)
        return cats

    def _seed_articles(self, count: int, users, categories, images: dict):
        from apps.articles.models import Article, Tag

        tags = list(Tag.objects.all())
        staff = [u for u in users if u.role in ("admin", "editor")] or users[:10]
        batch = []
        for i in range(count):
            status = "published" if i < int(count * 0.9) else "draft"
            batch.append(
                Article(
                    title=fake.sentence(nb_words=8).rstrip(".")[:299],
                    slug=f"article-{i}-{fake.slug()}"[:319],
                    excerpt=fake.paragraph(nb_sentences=2),
                    content="\n\n".join(fake.paragraph(nb_sentences=6) for _ in range(5)),
                    author=random.choice(staff),
                    category=random.choice(categories),
                    featured_image=self._ri(images, "banner"),
                    article_type=random.choice(["blog", "blog", "magazine"]),
                    status=status,
                    is_featured=(i < 6),
                    read_time=random.randint(2, 12),
                    view_count=random.randint(50, 50000),
                    like_count=0,
                    published_at=fake_dt(end=timezone.now()) if status == "published" else None,
                )
            )
        Article.objects.bulk_create(batch, ignore_conflicts=True)
        articles = list(Article.objects.filter(status="published"))
        for article in random.sample(articles, min(len(articles), count * 3 // 4)):
            article.tags.set(random.sample(tags, min(3, len(tags))))
        self.stdout.write(f"Created {count} articles")
        return articles

    def _seed_article_engagement(self, articles, users):
        from apps.articles.models import Article, ArticleLike, Comment

        likes, comments = [], []
        like_counts = {}  # article.pk -> len(likers), tracked in-memory to avoid a re-query per article
        for article in random.sample(articles, min(len(articles), 220)):
            likers = random.sample(users, min(random.randint(0, 40), len(users)))
            like_counts[article.pk] = len(likers)
            for u in likers:
                likes.append(ArticleLike(article=article, user=u))
            n_comments = random.randint(0, 6)
            for _ in range(n_comments):
                comments.append(
                    Comment(
                        article=article,
                        author=random.choice(users),
                        content=fake.sentence(nb_words=random.randint(5, 25)),
                    )
                )
        ArticleLike.objects.bulk_create(likes, ignore_conflicts=True)
        Comment.objects.bulk_create(comments)
        # A few replies, now that parents have real pks.
        saved_comments = list(Comment.objects.filter(article__in=articles).order_by("-pk")[: len(comments)])
        replies = []
        for parent in random.sample(saved_comments, min(len(saved_comments), 80)):
            replies.append(
                Comment(
                    article=parent.article,
                    author=random.choice(users),
                    content=fake.sentence(nb_words=15),
                    parent=parent,
                )
            )
        Comment.objects.bulk_create(replies)
        # Sync denormalized like_count on Article itself (in-memory tally above — no per-article
        # re-query, that was the biggest single slowdown in an earlier version of this script).
        for article in articles:
            article.like_count = like_counts.get(article.pk, 0)
        Article.objects.bulk_update(articles, ["like_count"])
        for c in saved_comments:
            c.like_count = random.randint(0, 30)
        Comment.objects.bulk_update(saved_comments, ["like_count"])
        self.stdout.write(
            f"Created {len(likes)} article likes, {len(comments) + len(replies)} article comments"
        )

    # ── Events ───────────────────────────────────────────────────────────────────────────────

    def _seed_cities(self):
        from apps.events.models import City

        return [City.objects.get_or_create(name=n)[0] for n in EVENT_CITIES]

    def _seed_events(self, count: int, cities, artists, users, images: dict):
        from apps.events.models import Event, EventRegistration, EventScheduleItem

        categories = [c for c, _ in Event.CATEGORY_CHOICES]
        now = timezone.now()
        batch = []
        for i in range(count):
            event_date = fake_dt()
            status = Event.STATUS_PAST if event_date < now else Event.STATUS_UPCOMING
            if abs((event_date - now).total_seconds()) < 3600 * 6:
                status = Event.STATUS_LIVE
            batch.append(
                Event(
                    title=f"{fake.catch_phrase()} {random.choice(['Festival', 'Concert', 'Show', 'Expo'])}"[
                        :299
                    ],
                    slug=f"event-{i}-{fake.slug()}"[:319],
                    description=fake.paragraph(nb_sentences=4),
                    date=event_date,
                    end_date=event_date + timedelta(hours=random.randint(2, 8)),
                    venue_name=fake.company()[:199],
                    venue_address=fake.address()[:299],
                    city=random.choice(cities),
                    category=random.choice(categories),
                    image=self._ri(images, "banner"),
                    status=status,
                    is_featured=(i < 5),
                    ticket_price=random.choice([None, 5000, 10000, 15000, 20000]),
                    max_capacity=random.choice([None, 200, 500, 1000, 5000]),
                    current_registrations=random.randint(0, 200),
                )
            )
        Event.objects.bulk_create(batch, ignore_conflicts=True)
        events = list(Event.objects.all())
        for event in random.sample(events, min(len(events), count // 3)):
            event.artists.set(random.sample(artists, min(random.randint(1, 4), len(artists))))

        schedule_items = []
        for event in random.sample(events, min(len(events), count // 2)):
            for order in range(random.randint(2, 5)):
                schedule_items.append(
                    EventScheduleItem(
                        event=event,
                        time=f"{random.randint(9, 22):02d}:00",
                        title=fake.sentence(nb_words=5)[:199],
                        artist=random.choice(artists) if random.random() > 0.3 else None,
                        duration_minutes=random.choice([30, 45, 60, 90]),
                        order=order,
                    )
                )
        EventScheduleItem.objects.bulk_create(schedule_items)

        registrations = []
        for event in random.sample(events, min(len(events), count // 2)):
            for u in random.sample(users, min(random.randint(0, 25), len(users))):
                registrations.append(EventRegistration(event=event, user=u))
        EventRegistration.objects.bulk_create(registrations, ignore_conflicts=True)

        self.stdout.write(
            f"Created {count} events (past/live/upcoming spread across 2025-2027), "
            f"{len(schedule_items)} schedule items, {len(registrations)} registrations"
        )

    # ── Radio ────────────────────────────────────────────────────────────────────────────────

    def _seed_radio(self, images: dict):
        from apps.radio.models import RadioChat, RadioProgram

        batch = []
        for day in range(7):
            for start_h, end_h in [
                (6, 8),
                (8, 10),
                (10, 12),
                (12, 14),
                (14, 16),
                (16, 18),
                (18, 20),
                (20, 22),
                (22, 24),
            ]:
                batch.append(
                    RadioProgram(
                        title=random.choice(RADIO_PROGRAMS),
                        slug=f"radio-{day}-{start_h}-{fake.slug()}"[:219],
                        description=fake.sentence(nb_words=12),
                        start_time=f"{start_h:02d}:00",
                        end_time=f"{end_h % 24:02d}:00",
                        day_of_week=day,
                        presenter=fake.name(),
                        cover=self._ri(images, "square"),
                        status=RadioProgram.STATUS_UPCOMING,
                        listener_count=random.randint(0, 500),
                    )
                )
        RadioProgram.objects.bulk_create(batch, ignore_conflicts=True)
        users = list(User.objects.order_by("-pk")[:100])
        chats = (
            [
                RadioChat(user=random.choice(users), message=fake.sentence(nb_words=random.randint(3, 20)))
                for _ in range(500)
            ]
            if users
            else []
        )
        RadioChat.objects.bulk_create(chats)
        self.stdout.write(f"Created {len(batch)} radio programs, {len(chats)} chat messages")

    # ── Podcasts ─────────────────────────────────────────────────────────────────────────────

    def _seed_podcasts(self, series_count: int, episode_count: int, images: dict):
        from apps.podcasts.models import PodcastEpisode, PodcastSeries

        series_list = []
        names = list(PODCAST_SERIES)
        while len(names) < series_count:
            names.append((f"{fake.company()} Podcast", random.choice([c for _, c in PODCAST_SERIES])))
        for title, category in names[:series_count]:
            s, _ = PodcastSeries.objects.get_or_create(
                title=title[:200],
                defaults=dict(
                    description=fake.paragraph(nb_sentences=3),
                    category=category,
                    cover=self._ri(images, "square"),
                    episode_count=0,
                ),
            )
            series_list.append(s)
        batch = []
        per_series = max(1, episode_count // len(series_list))
        for series in series_list:
            for ep_num in range(1, per_series + 1):
                batch.append(
                    PodcastEpisode(
                        series=series,
                        title=f"Épisode {ep_num}: {fake.catch_phrase()}"[:299],
                        slug=f"ep-{series.pk}-{ep_num}-{fake.slug()}"[:319],
                        description=fake.paragraph(nb_sentences=3),
                        duration=f"{random.randint(15, 90)}:{random.randint(0, 59):02d}",
                        episode_number=ep_num,
                        season_number=random.randint(1, 3),
                        cover=self._ri(images, "square"),
                        audio_url=random.choice(SAMPLE_AUDIO),
                        play_count=random.randint(100, 50000),
                        is_featured=(ep_num == 1),
                        status="published",
                        published_at=fake_dt(end=timezone.now()),
                        guests=[
                            {"name": fake.name(), "role": fake.job()} for _ in range(random.randint(0, 2))
                        ],
                    )
                )
        PodcastEpisode.objects.bulk_create(batch, ignore_conflicts=True)
        for s in series_list:
            s.episode_count = s.episodes.count()
        PodcastSeries.objects.bulk_update(series_list, ["episode_count"])
        self.stdout.write(f"Created {len(series_list)} podcast series, {len(batch)} episodes")

    # ── Web TV ───────────────────────────────────────────────────────────────────────────────

    def _seed_webtv_videos(self, count: int, artists, images: dict):
        from apps.webtv.models import WebTVVideo

        batch = []
        for i in range(count):
            category = random.choice(VIDEO_CATEGORIES)
            broadcast_mode = random.choice(
                [WebTVVideo.MODE_PLAYOUT, WebTVVideo.MODE_PLAYOUT, WebTVVideo.MODE_CAMERA]
            )
            was_broadcast = random.random() > 0.4  # simulate a past finished broadcast, camera mode only
            recording_status = WebTVVideo.RECORDING_NONE
            video_url = ""
            if broadcast_mode == WebTVVideo.MODE_PLAYOUT:
                video_url = random.choice(SAMPLE_VIDEOS)
            elif was_broadcast:
                recording_status = WebTVVideo.RECORDING_READY
                video_url = random.choice(SAMPLE_VIDEOS)
            batch.append(
                WebTVVideo(
                    title=fake.catch_phrase()[:299],
                    slug=f"video-{i}-{fake.slug()}"[:319],
                    description=fake.paragraph(nb_sentences=2),
                    video_url=video_url,
                    broadcast_mode=broadcast_mode,
                    recording_status=recording_status,
                    duration=f"{random.randint(2, 30)}:{random.randint(0, 59):02d}",
                    category=category,
                    thumbnail=self._ri(images, "thumbnail"),
                    is_premier=(category == "premiers" and i < 6),
                    location=random.choice(EVENT_CITIES + [""]),
                    view_count=random.randint(500, 500000),
                    published_at=fake_dt(end=timezone.now()),
                )
            )
        WebTVVideo.objects.bulk_create(batch, ignore_conflicts=True)
        videos = list(WebTVVideo.objects.order_by("-pk")[:count])
        for video in random.sample(videos, min(len(videos), count // 3)):
            video.artists.set(random.sample(artists, min(2, len(artists))))
        self.stdout.write(f"Created {count} Web TV videos")
        return videos

    # ── Emissions ────────────────────────────────────────────────────────────────────────────

    def _seed_emissions(self, count: int, artists, images: dict):
        from apps.emissions.models import Emission

        statuses = [
            Emission.STATUS_LIVE,
            Emission.STATUS_SCHEDULED,
            Emission.STATUS_SCHEDULED,
            Emission.STATUS_RECORDED,
        ]
        batch = []
        for i in range(count):
            status = random.choice(statuses)
            recording_status = (
                Emission.RECORDING_READY
                if status == Emission.STATUS_RECORDED and random.random() > 0.3
                else Emission.RECORDING_NONE
            )
            batch.append(
                Emission(
                    title=fake.catch_phrase()[:199],
                    slug=f"emission-{i}-{fake.slug()}"[:219],
                    description=fake.paragraph(nb_sentences=3),
                    status=status,
                    scheduled_at=fake_dt(),
                    cover=self._ri(images, "banner"),
                    duration_minutes=random.randint(30, 120),
                    viewer_count=random.randint(0, 2000),
                    total_views=random.randint(100, 50000),
                    recording_status=recording_status,
                    video_url=random.choice(SAMPLE_VIDEOS)
                    if recording_status == Emission.RECORDING_READY
                    else "",
                )
            )
        Emission.objects.bulk_create(batch, ignore_conflicts=True)
        emissions = list(Emission.objects.order_by("-pk")[:count])
        for em in random.sample(emissions, min(len(emissions), count // 2)):
            em.hosts.set(random.sample(artists, min(2, len(artists))))
        self.stdout.write(f"Created {count} emissions")
        return emissions

    # ── Live Music ───────────────────────────────────────────────────────────────────────────

    def _seed_live_music(self, count: int, artists, images: dict):
        from apps.live_music.models import MusicLiveSession, MusicLiveSlot

        statuses = [
            MusicLiveSession.STATUS_ENDED,
            MusicLiveSession.STATUS_ENDED,
            MusicLiveSession.STATUS_SCHEDULED,
            MusicLiveSession.STATUS_LIVE,
        ]
        sessions = []
        for i in range(count):
            status = random.choice(statuses)
            recording_status = (
                MusicLiveSession.RECORDING_READY
                if status == MusicLiveSession.STATUS_ENDED and random.random() > 0.3
                else MusicLiveSession.RECORDING_NONE
            )
            sessions.append(
                MusicLiveSession(
                    title=f"Son en direct: {fake.catch_phrase()}"[:199],
                    slug=f"live-music-{i}-{fake.slug()}"[:219],
                    cover=self._ri(images, "square"),
                    status=status,
                    scheduled_at=fake_dt(),
                    recording_status=recording_status,
                    audio_url=random.choice(SAMPLE_AUDIO)
                    if recording_status == MusicLiveSession.RECORDING_READY
                    else "",
                )
            )
        MusicLiveSession.objects.bulk_create(sessions, ignore_conflicts=True)
        sessions = list(MusicLiveSession.objects.order_by("-pk")[:count])
        for s in random.sample(sessions, min(len(sessions), count // 2)):
            s.artists.set(random.sample(artists, min(random.randint(1, 3), len(artists))))

        slots = []
        for day in range(7):
            for start_h in (9, 13, 17, 21):
                slots.append(
                    MusicLiveSlot(
                        title=fake.catch_phrase()[:199],
                        cover=self._ri(images, "square"),
                        artist=random.choice(artists) if random.random() > 0.2 else None,
                        day_of_week=day,
                        start_time=f"{start_h:02d}:00",
                        end_time=f"{start_h + 2:02d}:00",
                        duration_minutes=120,
                    )
                )
        MusicLiveSlot.objects.bulk_create(slots)
        self.stdout.write(f"Created {len(sessions)} live music sessions, {len(slots)} programme slots")
        return sessions

    # ── Gamification ─────────────────────────────────────────────────────────────────────────

    def _seed_gamification(self, users):
        from apps.gamification.models import Badge, ConsumptionLog, UserBadge

        badge_specs = [
            ("Bienvenue", 0),
            ("Auditeur assidu", 3600),
            ("Fan de radio", 18000),
            ("Grand consommateur", 72000),
            ("Légende du Kivu", 180000),
        ]
        badges = []
        for order, (name, threshold) in enumerate(badge_specs):
            # order is a PositiveSmallIntegerField (smallint, max 32767) — threshold_seconds
            # (up to 180000) overflows it; confirmed live via a real DataError. Use a small
            # separate ordinal instead.
            b, _ = Badge.objects.get_or_create(
                slug=name.lower().replace(" ", "-"),
                defaults=dict(
                    name=name,
                    description=fake.sentence(nb_words=10),
                    criteria_type=Badge.CRITERIA_LISTENING_SECONDS,
                    threshold_seconds=threshold,
                    order=order,
                ),
            )
            badges.append(b)

        content_types = [c for c, _ in ConsumptionLog.CONTENT_TYPE_CHOICES]
        logs = []
        totals = {}
        for user in random.sample(users, min(120, len(users))):
            n = random.randint(1, 15)
            total_seconds = 0
            for _ in range(n):
                seconds = random.randint(60, 3600)
                total_seconds += seconds
                logs.append(
                    ConsumptionLog(
                        user=user,
                        content_type=random.choice(content_types),
                        object_id=random.randint(1, 200),
                        title=fake.sentence(nb_words=5),
                        cover_url="",
                        seconds=seconds,
                        created_at=fake_dt(end=timezone.now()),
                    )
                )
            totals[user.pk] = total_seconds
        ConsumptionLog.objects.bulk_create(logs)

        user_badges = []
        for user in random.sample(users, min(120, len(users))):
            total = totals.get(user.pk, 0)
            for badge in badges:
                if badge.threshold_seconds <= total:
                    user_badges.append(UserBadge(user=user, badge=badge))
        UserBadge.objects.bulk_create(user_badges, ignore_conflicts=True)
        self.stdout.write(
            f"Created {len(badges)} badges, {len(logs)} consumption logs, {len(user_badges)} user badges"
        )

    # ── Community ────────────────────────────────────────────────────────────────────────────

    def _seed_community(self, users, images: dict):
        from apps.community.models import (
            Challenge,
            ChallengeParticipant,
            CommunityPost,
            Poll,
            PollOption,
            PollVote,
            PostLike,
        )

        # Challenges + real participations (participate_in_challenge's write path: a
        # ChallengeParticipant row + a matching challenge_response CommunityPost).
        challenges = []
        for i in range(15):
            deadline = fake_dt(start=timezone.now())
            c, _ = Challenge.objects.get_or_create(
                slug=f"challenge-{i}-{fake.slug()}"[:219],
                defaults=dict(
                    title=f"Défi: {fake.catch_phrase()}"[:199],
                    description=fake.paragraph(nb_sentences=3),
                    cover=self._ri(images, "banner"),
                    prize=random.choice(["500$", "Matériel studio", "Visibilité", ""]),
                    deadline=deadline,
                    is_active=random.random() > 0.2,
                    participant_count=0,
                ),
            )
            challenges.append(c)

        posts = []
        participants = []
        for challenge in challenges:
            responders = random.sample(users, min(random.randint(3, 25), len(users)))
            for user in responders:
                participants.append(ChallengeParticipant(challenge=challenge, user=user))
                posts.append(
                    CommunityPost(
                        author=user,
                        title=fake.sentence(nb_words=6)[:199],
                        content=fake.paragraph(nb_sentences=3),
                        media=[{"type": "image", "url": self._ri(images, "square") or ""}],
                        post_type=CommunityPost.TYPE_CHALLENGE_RESPONSE,
                        challenge=challenge,
                        # NOT relative to challenge.deadline: deadline is always in the future
                        # (fake_dt(start=now) above), so a deadline-relative window here
                        # frequently produced start > end for Faker (deadline - 30d still being
                        # in the future) — confirmed live. A response just needs to have
                        # happened before "now", full stop.
                        created_at=fake_dt(end=timezone.now()),
                    )
                )
        ChallengeParticipant.objects.bulk_create(participants, ignore_conflicts=True)
        CommunityPost.objects.bulk_create(posts)
        for challenge in challenges:
            challenge.participant_count = challenge.participants.count()
        Challenge.objects.bulk_update(challenges, ["participant_count"])
        # Pin one winning response per challenge that already has responses.
        for challenge in challenges:
            response = challenge.responses.order_by("?").first()
            if response:
                response.is_pinned_result = True
                response.save(update_fields=["is_pinned_result"])

        # Other regular post types.
        other_types = [CommunityPost.TYPE_TALENT, CommunityPost.TYPE_ART, CommunityPost.TYPE_NEWS]
        other_posts = [
            CommunityPost(
                author=random.choice(users),
                content=fake.paragraph(nb_sentences=random.randint(2, 6)),
                post_type=random.choice(other_types),
                media=[{"type": "image", "url": self._ri(images, "square") or ""}],
                created_at=fake_dt(end=timezone.now()),
            )
            for _ in range(300)
        ]
        CommunityPost.objects.bulk_create(other_posts)

        all_posts = list(CommunityPost.objects.order_by("-pk")[: len(posts) + len(other_posts)])
        post_likes = []
        post_like_counts = {}  # in-memory tally — avoids a per-post re-query (~600 posts here)
        for post in all_posts:
            likers = random.sample(users, min(random.randint(0, 30), len(users)))
            post_like_counts[post.pk] = len(likers)
            for u in likers:
                post_likes.append(PostLike(post=post, user=u))
        PostLike.objects.bulk_create(post_likes, ignore_conflicts=True)
        for post in all_posts:
            post.like_count = post_like_counts.get(post.pk, 0)
        CommunityPost.objects.bulk_update(all_posts, ["like_count"])

        # Polls with REAL PollVote rows, counters kept in sync (mirrors services.vote_poll).
        poll_questions = [
            "Quel artiste du Kivu devrait headliner le prochain Festival Amani?",
            "Quel genre musical représente le mieux la jeunesse congolaise?",
            "Quelle ville a la meilleure scène musicale de l'Est Congo?",
            "Quel format préférez-vous pour découvrir de nouveaux artistes?",
            "Quelle émission regardez-vous le plus?",
            "Quel réseau utilisez-vous pour suivre vos artistes préférés?",
            "Combien de temps par jour écoutez-vous de la musique congolaise?",
            "Quel type de contenu communautaire préférez-vous?",
        ]
        for question in poll_questions:
            poll, created = Poll.objects.get_or_create(
                question=question, defaults={"is_active": random.random() > 0.15}
            )
            if not created:
                continue
            options = [PollOption.objects.create(poll=poll, text=fake.word().capitalize()) for _ in range(4)]
            voters = random.sample(users, min(random.randint(30, 200), len(users)))
            votes = [PollVote(poll=poll, user=u, option=random.choice(options)) for u in voters]
            PollVote.objects.bulk_create(votes, ignore_conflicts=True)
            counts = {}
            for v in votes:
                counts[v.option_id] = counts.get(v.option_id, 0) + 1
            for option in options:
                option.vote_count = counts.get(option.pk, 0)
            PollOption.objects.bulk_update(options, ["vote_count"])
            poll.vote_count = sum(o.vote_count for o in options)
            poll.save(update_fields=["vote_count"])

        self.stdout.write(
            f"Created {len(challenges)} challenges, {len(participants)} participations, {len(posts) + len(other_posts)} posts, {len(post_likes)} post likes, {len(poll_questions)} polls"
        )
        return all_posts

    # ── Home ─────────────────────────────────────────────────────────────────────────────────

    def _seed_home(self, artists, emissions, articles, images: dict):
        from django.contrib.contenttypes.models import ContentType

        from apps.home.models import FeaturedContent, HomeBanner

        banner = HomeBanner.get_solo()
        banner.title = "Bienvenue sur Art du Kivu"
        banner.title_highlight = "Art du Kivu"
        banner.subtitle = "La scène musicale et culturelle de l'Est de la RDC, en direct."
        banner.cta_label = "Découvrir"
        banner.cta_url = "https://art-du-kivu.example.com/decouvrir"
        banner.image = self._ri(images, "banner")
        banner.save()

        picks = []
        order = 0
        for artist in random.sample(artists, min(4, len(artists))):
            picks.append((artist, order))
            order += 1
        for emission in random.sample(emissions, min(3, len(emissions))):
            picks.append((emission, order))
            order += 1
        for article in random.sample(articles, min(3, len(articles))):
            picks.append((article, order))
            order += 1

        created = 0
        for obj, ordinal in picks:
            ct = ContentType.objects.get_for_model(obj)
            _, was_created = FeaturedContent.objects.get_or_create(
                content_type=ct, object_id=obj.pk, defaults={"order": ordinal}
            )
            created += was_created
        self.stdout.write(f"Configured home banner, created {created} featured-content entries")

    # ── Generic engagement (Like/Comment/Share/SavedItem via content_type+object_id) ─────────

    def _seed_generic_engagement(self, users, artists, webtv_videos, emissions, community_posts):
        from django.contrib.contenttypes.models import ContentType

        from apps.engagement.models import Comment, Like, SavedItem, Share
        from apps.live_music.models import MusicLiveSession
        from apps.podcasts.models import PodcastEpisode
        from apps.radio.models import RadioProgram
        from apps.releases.models import MusicRelease

        targets = [
            (artists, "artist"),
            (list(MusicRelease.objects.order_by("-pk")[:300]), "release"),
            (webtv_videos, "webtv video"),
            (emissions, "emission"),
            (list(RadioProgram.objects.order_by("-pk")[:80]), "radio program"),
            (list(MusicLiveSession.objects.order_by("-pk")[:40]), "live music session"),
            (community_posts, "community post"),
            (list(PodcastEpisode.objects.order_by("-pk")[:300]), "podcast episode"),
        ]

        likes, comments, shares, saves = [], [], [], []
        for objs, _label in targets:
            if not objs:
                continue
            ct = ContentType.objects.get_for_model(objs[0])
            for obj in random.sample(objs, min(len(objs), max(1, len(objs) * 2 // 3))):
                for u in random.sample(users, min(random.randint(0, 15), len(users))):
                    likes.append(Like(content_type=ct, object_id=obj.pk, user=u))
                for _ in range(random.randint(0, 5)):
                    comments.append(
                        Comment(
                            content_type=ct,
                            object_id=obj.pk,
                            author=random.choice(users),
                            content=fake.sentence(nb_words=random.randint(5, 20)),
                        )
                    )
                for u in random.sample(users, min(random.randint(0, 4), len(users))):
                    shares.append(Share(content_type=ct, object_id=obj.pk, user=u))
                for u in random.sample(users, min(random.randint(0, 6), len(users))):
                    saves.append(SavedItem(content_type=ct, object_id=obj.pk, user=u))

        Like.objects.bulk_create(likes, ignore_conflicts=True)
        Comment.objects.bulk_create(comments)
        Share.objects.bulk_create(shares)
        SavedItem.objects.bulk_create(saves, ignore_conflicts=True)
        self.stdout.write(
            f"Created generic engagement: {len(likes)} likes, {len(comments)} comments, {len(shares)} shares, {len(saves)} saves"
        )

    # ── Live chat (webtv/emissions/live_music — Radio uses its own separate RadioChat) ───────

    def _seed_live_chat(self, users, webtv_videos, emissions, live_sessions):
        from django.contrib.contenttypes.models import ContentType

        from apps.realtime.models import LiveChatMessage

        messages = []
        for objs in (webtv_videos, emissions, live_sessions):
            if not objs:
                continue
            ct = ContentType.objects.get_for_model(objs[0])
            for obj in random.sample(objs, min(len(objs), max(1, len(objs) * 2 // 3))):
                for _ in range(random.randint(0, 15)):
                    messages.append(
                        LiveChatMessage(
                            content_type=ct,
                            object_id=obj.pk,
                            author=random.choice(users),
                            message=fake.sentence(nb_words=random.randint(3, 20)),
                        )
                    )
        LiveChatMessage.objects.bulk_create(messages)
        self.stdout.write(f"Created {len(messages)} live chat messages")

    # ── Newsletter ───────────────────────────────────────────────────────────────────────────

    def _seed_newsletter(self, users):
        from apps.newsletter.models import Newsletter, Subscriber

        subscribers = []
        for user in users:
            confirmed = random.random() > 0.15
            subscribers.append(
                Subscriber(
                    email=user.email,
                    is_confirmed=confirmed,
                    is_active=random.random() > 0.05,
                    confirmed_at=fake_dt(end=timezone.now()) if confirmed else None,
                )
            )
        for _ in range(50):
            subscribers.append(
                Subscriber(
                    email=fake.unique.email(), is_confirmed=True, confirmed_at=fake_dt(end=timezone.now())
                )
            )
        Subscriber.objects.bulk_create(subscribers, ignore_conflicts=True)

        staff = [u for u in users if u.role == "editor"] or users[:5]
        statuses = [
            Newsletter.STATUS_SENT,
            Newsletter.STATUS_SENT,
            Newsletter.STATUS_DRAFT,
            Newsletter.STATUS_SENDING,
        ]
        newsletters = []
        for _ in range(20):
            status = random.choice(statuses)
            newsletters.append(
                Newsletter(
                    subject=fake.sentence(nb_words=8)[:199],
                    body_html=f"<p>{fake.paragraph(nb_sentences=8)}</p>",
                    status=status,
                    created_by=random.choice(staff),
                    recipient_count=random.randint(100, 5000) if status == Newsletter.STATUS_SENT else 0,
                    sent_at=fake_dt(end=timezone.now()) if status == Newsletter.STATUS_SENT else None,
                )
            )
        Newsletter.objects.bulk_create(newsletters)
        self.stdout.write(
            f"Created {len(subscribers)} newsletter subscribers, {len(newsletters)} newsletter campaigns"
        )

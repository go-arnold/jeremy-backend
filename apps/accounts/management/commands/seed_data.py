"""
Management command to seed the database with large, realistic mock data.
Run: python manage.py seed_data [--reset]
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

fake = Faker(["fr_FR", "en_US"])
User = get_user_model()

CONGOLESE_ARTISTS = [
    ("Innoss'B", "Goma", "Musique"), ("Ferre Gola", "Kinshasa", "Rumba"),
    ("Fally Ipupa", "Kinshasa", "Rumba"), ("Alesh", "Goma", "Hip-hop"),
    ("MPR", "Bukavu", "Urbain"), ("Werrason", "Kinshasa", "Rumba"),
    ("Koffi Olomide", "Kinshasa", "Rumba"), ("Awilo Longomba", "Kinshasa", "Ndombolo"),
    ("Josey", "Goma", "Afropop"), ("Singuila", "Kinshasa", "R&B"),
    ("Maître Gims", "Kinshasa", "Hip-hop"), ("Dadju", "Kinshasa", "Afropop"),
    ("Locko", "Douala", "Afropop"), ("Yemi Alade", "Lagos", "Afrobeats"),
    ("Sauti Sol", "Nairobi", "Afropop"), ("Tiwa Savage", "Lagos", "Afrobeats"),
    ("Burna Boy", "Port Harcourt", "Afrobeats"), ("Wizkid", "Lagos", "Afrobeats"),
    ("Diamond Platnumz", "Dar es Salaam", "Bongo"), ("Harmonize", "Dar es Salaam", "Bongo"),
]
GENRES_DATA = ["Musique", "Hip-hop", "Rumba", "Afro", "Urbain", "R&B", "Ndombolo", "Jazz", "Bongo", "Soul"]
EVENT_CITIES = ["Goma", "Bukavu", "Kinshasa", "Butembo", "Lubumbashi", "Matadi", "Kisangani"]
RADIO_PROGRAMS = [
    "Kivu Morning Flow", "Héritage Urbain", "Youth Talk", "Jazz du Lac",
    "Matin Frais", "Le Grand Mix", "Parole aux Jeunes", "Culture & Création",
    "Soirée Rumba", "Nuit des Beats",
]
PODCAST_SERIES = [
    ("Kivu Talk", "talk"), ("Voix de Goma", "culture"), ("Urban Beats", "musique"),
    ("Société Ouverte", "societe"), ("Jeunesse Active", "jeunesse"),
    ("Sport Passion", "sport"), ("Artiste en Vue", "culture"), ("Le Studio", "musique"),
]
VIDEO_CATEGORIES = ["freestyles", "studio_sessions", "docs", "interviews", "premiers"]
ARTICLE_CATEGORIES = [
    ("Musique", "primary"), ("Culture", "teal"), ("Société", "navy"),
    ("Mode", "yellow"), ("Arts Visuels", "primary"), ("Littérature", "teal"),
    ("Danse", "navy"), ("Sport", "yellow"),
]


class Command(BaseCommand):
    help = "Seed the database with large realistic mock data."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Clear existing data first")
        parser.add_argument("--users", type=int, default=100)
        parser.add_argument("--artists", type=int, default=80)
        parser.add_argument("--articles", type=int, default=200)
        parser.add_argument("--events", type=int, default=80)
        parser.add_argument("--podcasts", type=int, default=20)
        parser.add_argument("--episodes", type=int, default=150)
        parser.add_argument("--videos", type=int, default=120)
        parser.add_argument("--releases", type=int, default=250)

    def handle(self, *args, **options):
        if options["reset"]:
            self._clear_data()
        with transaction.atomic():
            users = self._seed_users(options["users"])
            genres = self._seed_genres()
            artists = self._seed_artists(options["artists"], genres)
            self._seed_favorite_artists(users, artists)
            self._seed_releases(options["releases"], artists)
            categories = self._seed_article_categories()
            self._seed_articles(options["articles"], users, categories)
            cities = self._seed_cities()
            self._seed_events(options["events"], cities, artists)
            self._seed_radio_programs()
            self._seed_podcast_series_and_episodes(options["podcasts"], options["episodes"])
            self._seed_webtv_videos(options["videos"], artists)
            self._seed_emissions(30, artists)
            self._seed_community()
        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))

    def _clear_data(self):
        from apps.artists.models import Artist, Genre, Release, ArtistVideo, ArtistPhoto
        from apps.articles.models import Article, Category, Tag, Comment
        from apps.events.models import Event, City
        from apps.podcasts.models import PodcastSeries, PodcastEpisode
        from apps.radio.models import RadioProgram, RadioChat
        from apps.webtv.models import WebTVVideo
        from apps.releases.models import MusicRelease
        from apps.emissions.models import Emission
        from apps.community.models import CommunityPost, Challenge, Poll
        models_to_clear = [
            Comment, Article, Tag, Category,
            ArtistPhoto, ArtistVideo, Release, MusicRelease,
            PodcastEpisode, PodcastSeries, RadioChat, RadioProgram,
            WebTVVideo, Emission, CommunityPost, Challenge, Poll,
            Event, City, Artist, Genre,
        ]
        for model in models_to_clear:
            model.objects.all().delete()
        self.stdout.write("Cleared existing data.")

    def _seed_users(self, count: int):
        existing = User.objects.count()
        if existing > 5:
            return list(User.objects.all())
        users = []
        # Admin user
        if not User.objects.filter(email="admin@artdukivu.com").exists():
            admin = User.objects.create_superuser(
                email="admin@artdukivu.com", username="admin",
                password="AdminPass123!", role=User.ROLE_ADMIN,
            )
            users.append(admin)
        # Regular users
        roles = [User.ROLE_EDITOR, User.ROLE_MODERATOR, User.ROLE_VIEWER]
        batch = []
        for i in range(count):
            email = fake.unique.email()
            username = fake.user_name() + str(random.randint(1, 9999))
            batch.append(User(
                email=email, username=username[:30],
                handle=f"@{username[:20]}",
                bio=fake.sentence(nb_words=10),
                role=random.choice(roles),
                is_verified=random.random() > 0.3,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
            ))
        User.objects.bulk_create(batch, ignore_conflicts=True)
        users.extend(list(User.objects.all()))
        self.stdout.write(f"Created {len(batch)} users")
        return users

    def _seed_genres(self):
        from apps.artists.models import Genre
        genre_objs = []
        for name in GENRES_DATA:
            g, _ = Genre.objects.get_or_create(name=name, defaults={"slug": name.lower().replace(" ", "-").replace("&", "")})
            genre_objs.append(g)
        return genre_objs

    def _seed_artists(self, count: int, genres):
        from apps.artists.models import Artist, Release
        artists = []
        all_names = list(CONGOLESE_ARTISTS) + [
            (fake.name(), random.choice(EVENT_CITIES), random.choice(GENRES_DATA))
            for _ in range(max(0, count - len(CONGOLESE_ARTISTS)))
        ]
        genre_map = {g.name: g for g in genres}
        for i, (name, city, genre_name) in enumerate(all_names[:count]):
            # slug = f"{name.lower().replace(' ', '-').replace(\"'\", '')}-{i}" if i > 0 else name.lower().replace(' ', '-').replace("'", '')
            slug = f"{name.lower().replace(' ', '-').replace("'", '')}-{i}" if i > 0 else name.lower().replace(' ', '-').replace("'", '')
            a, created = Artist.objects.get_or_create(
                slug=slug[:200],
                defaults={
                    "name": name, "city": city,
                    "bio": fake.paragraph(nb_sentences=5),
                    "is_featured": i < 10,
                    "social_links": {
                        "instagram": f"https://instagram.com/{slug}",
                        "youtube": f"https://youtube.com/@{slug}",
                    },
                }
            )
            if created:
                g = genre_map.get(genre_name)
                if g:
                    a.genres.add(g)
                artists.append(a)
        self.stdout.write(f"Created {len(artists)} artists")
        return list(Artist.objects.all())

    def _seed_favorite_artists(self, users, artists):
        sample_artists = artists[:20]
        for user in random.sample(users, min(50, len(users))):
            favs = random.sample(sample_artists, min(random.randint(1, 6), len(sample_artists)))
            user.favorite_artists.set(favs)

    def _seed_releases(self, count: int, artists):
        from apps.releases.models import MusicRelease
        formats = ["album", "single", "clip", "documentaire", "expo"]
        batch = []
        for i in range(count):
            artist = random.choice(artists)
            title = f"{fake.catch_phrase()} Vol.{random.randint(1,5)}"
            slug = f"release-{i}-{fake.slug()}"[:220]
            rel_date = fake.date_between(start_date="-3y", end_date="+6m")
            batch.append(MusicRelease(
                artist=artist, title=title[:200], slug=slug,
                release_date=rel_date,
                format=random.choice(formats),
                is_featured=(i == 0),
                is_premiere=random.random() > 0.8,
                description=fake.paragraph(nb_sentences=3),
                streaming_links={
                    "spotify": f"https://spotify.com/album/{fake.uuid4()}",
                    "youtube": f"https://youtube.com/watch?v={fake.uuid4()[:11]}",
                },
            ))
        MusicRelease.objects.bulk_create(batch, ignore_conflicts=True)
        self.stdout.write(f"Created {count} releases")

    def _seed_article_categories(self):
        from apps.articles.models import Category, Tag
        cats = []
        for name, color in ARTICLE_CATEGORIES:
            c, _ = Category.objects.get_or_create(name=name, defaults={"color": color})
            cats.append(c)
        tags_data = ["Electro", "Bukavu", "Goma", "Festival", "Underground", "Jazz",
                     "Rumba", "Hip-hop", "Culture", "Jeunesse", "Mode", "Art"]
        for tag_name in tags_data:
            Tag.objects.get_or_create(name=tag_name)
        return cats

    def _seed_articles(self, count: int, users, categories):
        from apps.articles.models import Article, Tag
        tags = list(Tag.objects.all())
        staff_users = [u for u in users if u.is_staff or u.role in ("admin", "editor")] or users[:5]
        batch = []
        for i in range(count):
            pub_date = fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.get_current_timezone())
            title = fake.sentence(nb_words=8).rstrip(".")[:299]
            slug = f"article-{i}-{fake.slug()}"[:319]
            batch.append(Article(
                title=title, slug=slug,
                excerpt=fake.paragraph(nb_sentences=2),
                content="\n\n".join([fake.paragraph(nb_sentences=6) for _ in range(5)]),
                author=random.choice(staff_users) if staff_users else None,
                category=random.choice(categories),
                article_type=random.choice(["blog", "magazine"]),
                status="published",
                is_featured=(i < 5),
                read_time=random.randint(2, 12),
                view_count=random.randint(50, 50000),
                like_count=random.randint(0, 500),
                published_at=pub_date,
            ))
        Article.objects.bulk_create(batch, ignore_conflicts=True)
        # Add tags
        articles = list(Article.objects.all())
        for article in random.sample(articles, min(count // 2, len(articles))):
            article.tags.set(random.sample(tags, min(3, len(tags))))
        self.stdout.write(f"Created {count} articles")

    def _seed_cities(self):
        from apps.events.models import City
        cities = []
        for name in EVENT_CITIES:
            c, _ = City.objects.get_or_create(name=name)
            cities.append(c)
        return cities

    def _seed_events(self, count: int, cities, artists):
        from apps.events.models import Event
        categories = ["concert", "festival", "exposition", "conference", "spectacle"]
        statuses = ["upcoming", "upcoming", "upcoming", "past", "live"]
        batch = []
        for i in range(count):
            event_date = fake.date_time_between(start_date="-6m", end_date="+6m", tzinfo=timezone.get_current_timezone())
            title = f"{fake.catch_phrase()} {random.choice(['Festival', 'Concert', 'Show', 'Expo'])}"[:299]
            slug = f"event-{i}-{fake.slug()}"[:319]
            batch.append(Event(
                title=title, slug=slug,
                description=fake.paragraph(nb_sentences=4),
                date=event_date,
                end_date=event_date + timedelta(hours=random.randint(2, 8)),
                venue_name=fake.company()[:199],
                venue_address=fake.address()[:299],
                city=random.choice(cities),
                category=random.choice(categories),
                status=random.choice(statuses),
                is_featured=(i < 3),
                ticket_price=random.choice([None, 5000, 10000, 15000, 20000]),
                max_capacity=random.choice([None, 200, 500, 1000, 5000]),
                current_registrations=random.randint(0, 200),
            ))
        Event.objects.bulk_create(batch, ignore_conflicts=True)
        events = list(Event.objects.all())
        for event in random.sample(events, min(count // 3, len(events))):
            event.artists.set(random.sample(artists, min(random.randint(1, 4), len(artists))))
        self.stdout.write(f"Created {count} events")

    def _seed_radio_programs(self):
        from apps.radio.models import RadioProgram
        batch = []
        for day in range(7):
            times = [(8, 10), (10, 12), (12, 14), (14, 16), (18, 20), (20, 22)]
            for idx, (start_h, end_h) in enumerate(times):
                name = random.choice(RADIO_PROGRAMS)
                slug = f"radio-{day}-{start_h}-{fake.slug()}"[:219]
                batch.append(RadioProgram(
                    title=name, slug=slug,
                    description=fake.sentence(nb_words=12),
                    start_time=f"{start_h:02d}:00",
                    end_time=f"{end_h:02d}:00",
                    day_of_week=day,
                    presenter=fake.name(),
                    status="upcoming",
                ))
        RadioProgram.objects.bulk_create(batch, ignore_conflicts=True)
        self.stdout.write(f"Created {len(batch)} radio programs")

    def _seed_podcast_series_and_episodes(self, series_count: int, episode_count: int):
        from apps.podcasts.models import PodcastSeries, PodcastEpisode
        series_list = []
        for i, (title, category) in enumerate(PODCAST_SERIES[:series_count]):
            s, _ = PodcastSeries.objects.get_or_create(
                title=title,
                defaults={
                    "description": fake.paragraph(nb_sentences=3),
                    "category": category,
                    "is_featured": i < 3,
                    "episode_count": 0,
                }
            )
            series_list.append(s)
        while len(series_list) < series_count:
            title = f"{fake.company()} Podcast"
            s, _ = PodcastSeries.objects.get_or_create(
                title=title[:200],
                defaults={
                    "description": fake.paragraph(nb_sentences=3),
                    "category": random.choice([c for _, c in PODCAST_SERIES]),
                }
            )
            series_list.append(s)
        batch = []
        per_series = episode_count // max(len(series_list), 1)
        for series in series_list:
            for ep_num in range(1, per_series + 1):
                slug = f"ep-{series.pk}-{ep_num}-{fake.slug()}"[:319]
                pub = fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.get_current_timezone())
                batch.append(PodcastEpisode(
                    series=series,
                    title=f"Épisode {ep_num}: {fake.catch_phrase()}"[:299],
                    slug=slug,
                    description=fake.paragraph(nb_sentences=3),
                    duration=f"{random.randint(15, 90)}:{random.randint(0, 59):02d}",
                    episode_number=ep_num,
                    season_number=random.randint(1, 3),
                    play_count=random.randint(100, 50000),
                    is_featured=(ep_num == 1),
                    published_at=pub,
                    guests=[{"name": fake.name(), "role": fake.job()} for _ in range(random.randint(0, 2))],
                ))
        PodcastEpisode.objects.bulk_create(batch, ignore_conflicts=True)
        for s in series_list:
            s.episode_count = s.episodes.count()
            s.save(update_fields=["episode_count"])
        self.stdout.write(f"Created {len(batch)} podcast episodes")

    def _seed_webtv_videos(self, count: int, artists):
        from apps.webtv.models import WebTVVideo
        batch = []
        for i in range(count):
            category = random.choice(VIDEO_CATEGORIES)
            slug = f"video-{i}-{fake.slug()}"[:319]
            pub = fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.get_current_timezone())
            batch.append(WebTVVideo(
                title=f"{fake.catch_phrase()}"[:299],
                slug=slug,
                description=fake.paragraph(nb_sentences=2),
                video_url=f"https://youtube.com/watch?v={fake.uuid4()[:11]}",
                duration=f"{random.randint(2, 30)}:{random.randint(0, 59):02d}",
                category=category,
                is_premier=(category == "premiers" and i < 5),
                location=random.choice(EVENT_CITIES + [""]),
                view_count=random.randint(500, 500000),
                published_at=pub,
            ))
        WebTVVideo.objects.bulk_create(batch, ignore_conflicts=True)
        videos = list(WebTVVideo.objects.all())
        for video in random.sample(videos, min(count // 3, len(videos))):
            video.artists.set(random.sample(artists, min(2, len(artists))))
        self.stdout.write(f"Created {count} WebTV videos")

    def _seed_emissions(self, count: int, artists):
        from apps.emissions.models import Emission
        statuses = ["live", "scheduled", "scheduled", "recorded"]
        batch = []
        for i in range(count):
            sched = fake.date_time_between(start_date="-3m", end_date="+1m", tzinfo=timezone.get_current_timezone())
            slug = f"emission-{i}-{fake.slug()}"[:219]
            batch.append(Emission(
                title=f"{fake.catch_phrase()}"[:199],
                slug=slug,
                description=fake.paragraph(nb_sentences=3),
                status=random.choice(statuses),
                scheduled_at=sched,
                duration_minutes=random.randint(30, 120),
                viewer_count=random.randint(0, 2000),
                total_views=random.randint(100, 50000),
            ))
        Emission.objects.bulk_create(batch, ignore_conflicts=True)
        emissions = list(Emission.objects.all())
        for em in random.sample(emissions, min(count // 2, len(emissions))):
            em.hosts.set(random.sample(artists, min(2, len(artists))))
        self.stdout.write(f"Created {count} emissions")

    def _seed_community(self):
        from apps.community.models import Challenge, CommunityPost, Poll, PollOption
        users = list(User.objects.all()[:30])
        if not users:
            return
        # Posts
        post_types = ["talent", "art", "news"]
        posts = [
            CommunityPost(
                author=random.choice(users),
                content=fake.paragraph(nb_sentences=random.randint(2, 6)),
                post_type=random.choice(post_types),
                like_count=random.randint(0, 200),
                comment_count=random.randint(0, 50),
            ) for _ in range(150)
        ]
        CommunityPost.objects.bulk_create(posts)
        # Challenges
        for i in range(10):
            slug = f"challenge-{i}-{fake.slug()}"[:219]
            Challenge.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": f"Challenge: {fake.catch_phrase()}"[:199],
                    "description": fake.paragraph(nb_sentences=3),
                    "prize": random.choice(["500$", "Matériel studio", "Visibilité", ""]),
                    "deadline": fake.date_time_between(start_date="now", end_date="+3m", tzinfo=timezone.get_current_timezone()),
                    "participant_count": random.randint(10, 500),
                }
            )
        # Polls
        poll_questions = [
            "Quel artiste du Kivu devrait headliner le prochain Festival Amani?",
            "Quel genre musical représente le mieux la jeunesse congolaise?",
            "Quelle ville a la meilleure scène musicale de l'Est Congo?",
            "Quel format préférez-vous pour découvrir de nouveaux artistes?",
        ]
        for question in poll_questions:
            poll, created = Poll.objects.get_or_create(question=question)
            if created:
                options = [fake.word().capitalize() for _ in range(4)]
                for opt in options:
                    PollOption.objects.create(poll=poll, text=opt, vote_count=random.randint(10, 500))
                poll.vote_count = sum(o.vote_count for o in poll.options.all())
                poll.save(update_fields=["vote_count"])
        self.stdout.write("Created community content")

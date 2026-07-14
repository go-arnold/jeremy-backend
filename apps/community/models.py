from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models

from apps.engagement.models import Engageable


class CommunityPost(Engageable):
    TYPE_TALENT = "talent"
    TYPE_ART = "art"
    TYPE_NEWS = "news"
    TYPE_CHOICES = [
        (TYPE_TALENT, "Talent"),
        (TYPE_ART, "Art"),
        (TYPE_NEWS, "News"),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_posts"
    )
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(max_length=2000)
    media = models.JSONField(default=list, blank=True)
    post_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["post_type", "-created_at"])]

    def __str__(self):
        return f"{self.author} — {self.post_type}"


class PostLike(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")


class Challenge(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    cover = CloudinaryField("cover", blank=True, null=True)
    prize = models.CharField(max_length=100, blank=True)
    deadline = models.DateTimeField(db_index=True)
    participant_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug

            self.slug = make_slug(self.title, Challenge)
        super().save(*args, **kwargs)


class ChallengeParticipant(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("challenge", "user")


class Poll(models.Model):
    question = models.CharField(max_length=300)
    vote_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=200)
    vote_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["id"]

    @property
    def percentage(self):
        total = self.poll.vote_count
        return round(self.vote_count / total * 100) if total > 0 else 0

    def __str__(self):
        return self.text


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("poll", "user")

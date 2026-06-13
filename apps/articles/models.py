from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    color = models.CharField(max_length=30, default="primary", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(models.Model):
    TYPE_BLOG = "blog"
    TYPE_MAGAZINE = "magazine"
    TYPE_CHOICES = [(TYPE_BLOG, "Blog"), (TYPE_MAGAZINE, "Magazine")]

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_PUBLISHED, "Published")]

    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=320, unique=True, db_index=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    featured_image = CloudinaryField("featured_image", blank=True, null=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="articles"
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="articles")
    tags = models.ManyToManyField(Tag, blank=True)
    article_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_BLOG)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    read_time = models.PositiveSmallIntegerField(default=5)
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["article_type", "status"]),
            models.Index(fields=["is_featured", "status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug
            self.slug = make_slug(self.title, Article)
        super().save(*args, **kwargs)


class ArticleLike(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("article", "user")


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField(max_length=1000)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    like_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["article", "-created_at"])]

    def __str__(self):
        return f"{self.author} on {self.article}"

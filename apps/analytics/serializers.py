from rest_framework import serializers


class DashboardCountsSerializer(serializers.Serializer):
    artists = serializers.IntegerField()
    articles = serializers.IntegerField()
    events = serializers.IntegerField()
    event_registrations = serializers.IntegerField()
    podcast_series = serializers.IntegerField()
    podcast_episodes = serializers.IntegerField()
    radio_programs = serializers.IntegerField()
    webtv_videos = serializers.IntegerField()
    releases = serializers.IntegerField()
    community_posts = serializers.IntegerField()
    challenges = serializers.IntegerField()
    polls = serializers.IntegerField()
    users = serializers.IntegerField()


class DashboardTotalsSerializer(serializers.Serializer):
    article_views = serializers.IntegerField()
    article_likes = serializers.IntegerField()
    webtv_views = serializers.IntegerField()
    podcast_plays = serializers.IntegerField()
    post_likes = serializers.IntegerField()


class TopArticleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    slug = serializers.CharField()
    view_count = serializers.IntegerField()


class TopWebTVVideoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    slug = serializers.CharField()
    view_count = serializers.IntegerField()


class TopPodcastEpisodeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    slug = serializers.CharField()
    play_count = serializers.IntegerField()


class DashboardStatsSerializer(serializers.Serializer):
    counts = DashboardCountsSerializer()
    totals = DashboardTotalsSerializer()
    top_articles = TopArticleSerializer(many=True)
    top_webtv_videos = TopWebTVVideoSerializer(many=True)
    top_podcast_episodes = TopPodcastEpisodeSerializer(many=True)

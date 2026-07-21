from django.db import IntegrityError, transaction
from django.db.models import F

from .models import Challenge, ChallengeParticipant, CommunityPost, Poll, PollOption, PollVote, PostLike


@transaction.atomic
def create_post(validated_data: dict, author) -> CommunityPost:
    return CommunityPost.objects.create(author=author, **validated_data)


@transaction.atomic
def delete_post(post: CommunityPost) -> None:
    post.delete()


@transaction.atomic
def toggle_post_like(post: CommunityPost, user) -> dict:
    like, created = PostLike.objects.get_or_create(post=post, user=user)
    if not created:
        like.delete()
        CommunityPost.objects.filter(pk=post.pk).update(like_count=F("like_count") - 1)
        return {"action": "unliked"}
    CommunityPost.objects.filter(pk=post.pk).update(like_count=F("like_count") + 1)
    return {"action": "liked"}


@transaction.atomic
def join_challenge(challenge: Challenge, user) -> dict:
    _, created = ChallengeParticipant.objects.get_or_create(challenge=challenge, user=user)
    if not created:
        return {"error": "already_joined"}
    Challenge.objects.filter(pk=challenge.pk).update(participant_count=F("participant_count") + 1)
    return {"ok": True}


@transaction.atomic
def participate_in_challenge(challenge: Challenge, user, *, title: str, content: str, media: list) -> dict:
    """Records participation (same one-shot-per-user semantics as join_challenge) AND creates
    the CommunityPost the participation renders as — has_participated (ChallengeSerializer)
    depends on the ChallengeParticipant row this also writes."""
    _, created = ChallengeParticipant.objects.get_or_create(challenge=challenge, user=user)
    if not created:
        return {"error": "already_joined"}
    Challenge.objects.filter(pk=challenge.pk).update(participant_count=F("participant_count") + 1)
    post = CommunityPost.objects.create(
        author=user,
        title=title,
        content=content,
        media=media,
        post_type=CommunityPost.TYPE_CHALLENGE_RESPONSE,
        challenge=challenge,
    )
    return {"post": post}


@transaction.atomic
def publish_challenge_result(
    challenge: Challenge, user, *, title: str, content: str, media: list
) -> CommunityPost:
    return CommunityPost.objects.create(
        author=user,
        title=title,
        content=content,
        media=media,
        post_type=CommunityPost.TYPE_CHALLENGE_RESPONSE,
        challenge=challenge,
        is_pinned_result=True,
    )


@transaction.atomic
def create_challenge(validated_data: dict) -> Challenge:
    return Challenge.objects.create(**validated_data)


@transaction.atomic
def update_challenge(challenge: Challenge, validated_data: dict) -> Challenge:
    for attr, value in validated_data.items():
        setattr(challenge, attr, value)
    challenge.save()
    return challenge


@transaction.atomic
def delete_challenge(challenge: Challenge) -> None:
    challenge.delete()


@transaction.atomic
def create_poll(validated_data: dict) -> Poll:
    data = dict(validated_data)
    options = data.pop("options", [])
    poll = Poll.objects.create(**data)
    if options:
        PollOption.objects.bulk_create(
            [PollOption(poll=poll, text=opt["text"]) for opt in options],
            batch_size=500,
        )
    return poll


@transaction.atomic
def update_poll(poll: Poll, validated_data: dict) -> Poll:
    for attr, value in validated_data.items():
        setattr(poll, attr, value)
    poll.save()
    return poll


@transaction.atomic
def delete_poll(poll: Poll) -> None:
    poll.delete()


@transaction.atomic
def bulk_delete_posts(ids: list) -> int:
    deleted, _ = CommunityPost.objects.filter(pk__in=ids).delete()
    return deleted


@transaction.atomic
def bulk_create_challenges(items: list) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    objs = []
    for data in items:
        d = dict(data)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["title"], Challenge, used)
        objs.append(Challenge(**d))
    return Challenge.objects.bulk_create(objs, batch_size=500)


@transaction.atomic
def bulk_update_challenges(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in Challenge.objects.filter(pk__in=ids)}
    fields: set = set()
    to_update = []
    for data in items:
        obj = obj_map.get(data["id"])
        if not obj:
            continue
        for k, v in data.items():
            if k != "id":
                setattr(obj, k, v)
                fields.add(k)
        to_update.append(obj)
    if to_update and fields:
        Challenge.objects.bulk_update(to_update, list(fields), batch_size=500)
    return len(to_update)


@transaction.atomic
def bulk_delete_challenges(ids: list) -> int:
    deleted, _ = Challenge.objects.filter(pk__in=ids).delete()
    return deleted


@transaction.atomic
def bulk_delete_polls(ids: list) -> int:
    deleted, _ = Poll.objects.filter(pk__in=ids).delete()
    return deleted


@transaction.atomic
def vote_poll(poll: Poll, user, option_id: int) -> dict:
    try:
        option = PollOption.objects.get(pk=option_id, poll=poll)
    except PollOption.DoesNotExist:
        return {"error": "invalid_option"}
    if PollVote.objects.filter(poll=poll, user=user).exists():
        return {"error": "already_voted"}
    try:
        with transaction.atomic():
            PollVote.objects.create(poll=poll, user=user, option=option)
    except IntegrityError:
        # Concurrent request won the race against the .exists() check above;
        # the unique_together("poll", "user") constraint caught the duplicate.
        return {"error": "already_voted"}
    PollOption.objects.filter(pk=option.pk).update(vote_count=F("vote_count") + 1)
    Poll.objects.filter(pk=poll.pk).update(vote_count=F("vote_count") + 1)
    return {"ok": True}

from apps.search.services import _display_title, _image_url


def test_display_title_truncates_community_post_content():
    data = {"content": "x" * 100}
    title = _display_title(data, "community_post")
    assert title.endswith("…")
    assert len(title) == 81


def test_display_title_keeps_short_community_post_content():
    data = {"content": "hello world"}
    assert _display_title(data, "community_post") == "hello world"


def test_display_title_prefers_title_over_name():
    assert _display_title({"title": "T", "name": "N"}, "article") == "T"


def test_display_title_falls_back_to_name():
    assert _display_title({"name": "N"}, "artist") == "N"


def test_display_title_defaults_to_empty_string():
    assert _display_title({}, "artist") == ""


def test_image_url_picks_first_available_field():
    assert _image_url({"cover_url": "c", "thumbnail_url": "t"}) == "c"
    assert _image_url({"thumbnail_url": "t"}) == "t"
    assert _image_url({}) is None

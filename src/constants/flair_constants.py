import enum


class Flair(enum.Enum):
    # General usage.
    Discussion = {
        "id": "eeafce2a-7ef5-11e8-a46a-0e47aad96570",
        "text": "Discussion",
        "color": 0x7193FF,
        "css_class": "discussion",
    }
    Help = {"id": "27fb5e62-95a6-11e8-bed8-0e50d50ad3e0", "text": "Help", "color": 0x9E8D49, "css_class": "question"}
    WhatToWatch = {
        "id": "93f12e3a-a677-11e8-95fb-0e236bd29d76",
        "text": "What to Watch?",
        "color": 0x373C3F,
        "css_class": "recommendation",
    }
    Rewatch = {
        "id": "bfd20a82-7ef5-11e8-abc8-0eb61748988c",
        "text": "Rewatch",
        "color": 0x0079D3,
        "css_class": "rewatch",
    }
    OfficialMedia = {
        "id": "cd0dac30-95a5-11e8-a987-0efcb5fa8468",
        "text": "Official Media",
        "color": 0x0AA18F,
        "css_class": "official-media",
    }
    News = {"id": "beff6124-95a5-11e8-8d67-0e6af0b19360", "text": "News", "color": 0xFF4500, "css_class": "news"}
    Video = {"id": "4c412b40-95a5-11e8-8dfc-0e1ca46ce554", "text": "Video", "color": 0xCC3600, "css_class": "video"}
    VideoEdit = {
        "id": "273daa7a-6b63-11ec-8edd-0ad3d103245c",
        "text": "Video Edit",
        "color": 0x800080,
        "css_class": "video-edit",
    }
    Fanart = {"id": "1df6db84-7ef5-11e8-99eb-0eb15123315a", "text": "Fanart", "color": 0x73AD34, "css_class": "fanart"}
    OCFanart = {
        "id": "088023b0-26f6-11e9-a414-0e8f1d9789c4",
        "text": "OC Fanart",
        "color": 0x94E044,
        "css_class": "fanart-oc",
    }
    Cosplay = {
        "id": "4e153a72-7ef5-11e8-836b-0e9e30ff7edc",
        "text": "Cosplay",
        "color": 0xCC5289,
        "css_class": "cosplay",
    }
    WatchThis = {
        "id": "5e032f7a-7ef5-11e8-baae-0ede56c491fc",
        "text": "Watch This!",
        "color": 0xCCAC2B,
        "css_class": "wt",
    }
    Writing = {
        "id": "5f4ba6a2-95a5-11e8-a286-0eece46d6264",
        "text": "Writing",
        "color": 0xDDBD37,
        "css_class": "writing",
    }
    Clip = {"id": "a151d11e-7ef5-11e8-a8ae-0e4f0a02689c", "text": "Clip", "color": 0x00A6A5, "css_class": "clip"}
    Misc = {"id": "06c1953e-7ef6-11e8-8fad-0eb8e5dc3b5c", "text": "Misc.", "color": 0x646D73, "css_class": "misc"}
    Contest = {
        "id": "4441273c-95a6-11e8-821e-0e0287dc30f2",
        "text": "Contest",
        "color": 0x007373,
        "css_class": "contest",
    }

    # Special use cases.
    Weekly = {"id": "185e62f4-a4fd-11e8-b891-0e92c6b8258a", "text": "Weekly", "color": 0xFF56CC, "css_class": "weekly"}
    WritingClub = {
        "id": "8fa32252-95a6-11e8-863c-0e740a9d569a",
        "text": "Writing Club",
        "color": 0xE55A76,
        "css_class": "writing-club",
    }
    Meme = {"id": "98e5300a-79a1-11e9-a711-0e19cc83462e", "text": "Meme", "color": 0xEDEFF1, "css_class": "meme"}
    Episode = {
        "id": "9a86e3de-95a6-11e8-b585-0e5d87ca40ca",
        "text": "Episode",
        "color": 0x005BA1,
        "css_class": "episode",
    }
    Satire = {"id": "d48b1194-7ef5-11e8-99a8-0e5bf1b703b6", "text": "Satire", "color": 0x6B6031, "css_class": "satire"}

    # Mod usage only.
    ModBlue = {
        "id": "fa3f3eaa-e9e2-11e1-a86c-12313d28169d",
        "text": "Announcement",
        "color": 0x5687E3,
        "css_class": "blue",
    }
    ModGreen = {
        "id": "0df72bde-9fd6-11e2-85d5-12313d27e9a2",
        "text": "Announcement",
        "color": 0x46D160,
        "css_class": "green",
    }
    ModOther = {
        "id": "ad78cd48-c810-11e4-851a-22000b2801d0",
        "text": "(mod other)",
        "color": 0xEDEFF1,
        "css_class": "misleading",
    }
    AMALive = {"id": "6f000028-c681-11e7-bd06-0e2105b672b2", "text": "AMA Live", "color": 0xEA0027, "css_class": "red"}
    AMAFinished = {
        "id": "6b431fb6-c68f-11e7-8c1c-0e80bc468864",
        "text": "AMA Finished",
        "color": 0xB8001F,
        "css_class": "palered",
    }
    Awards = {"id": "69ee74c2-0c72-11eb-b127-0e7a0759b271", "text": "Awards", "color": 0xEA0027, "css_class": ""}

    # Deprecated, can probably remove at some point.
    FanartMisc = {
        "id": "32be3392-26f6-11e9-b0c5-0e1d097812b4",
        "text": "Fanart Misc",
        "color": 0x349E48,
        "css_class": "fanart-misc",
    }

    Unflaired = {"id": "", "text": "None", "color": 0, "css_class": ""}

    @property
    def color(self):
        return self.value.get("color")

    @property
    def id(self):
        return self.value.get("id")

    @property
    def text(self):
        return self.value.get("text")

    @property
    def css_class(self):
        return self.value.get("css_class")

    @classmethod
    def get_flair_by_id(cls, flair_template_id):
        for flair in cls:
            if flair.id == flair_template_id:
                return flair
        return None

import typing as t
from dataclasses import field

from marshmallow import Schema
from marshmallow_dataclass import dataclass


@dataclass
class MediaAssets:
    @dataclass
    class Cover:
        image_id: str

    @dataclass
    class Screenshot:
        width: int
        height: int
        image_id: str

    cover: Cover
    screenshots: t.Optional[list[Screenshot]] = field(default_factory=list)
    Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name


@dataclass
class UpsertAppReleaseRequestDTO:
    @dataclass
    class Distro:
        format: str
        url: str
        files: list[str] = field(default_factory=list)
        Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name

    @dataclass
    class Refs:
        ag_id: t.Optional[int]
        lutris_id: t.Optional[str]
        mg_id: t.Optional[int]
        pcgw_id: t.Optional[str]
        qz_id: t.Optional[int]
        Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name

    @dataclass
    class Reqs:
        @dataclass
        class Ua:
            lock_pointer: bool = False

        color_bits: t.Optional[int]
        screen_width: int
        screen_height: int
        midi: bool = False
        ua: Ua = field(default_factory=Ua)
        Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name

    @dataclass
    class Runner:
        name: str
        ver: str
        Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name

    reqs: Reqs
    distro: Distro
    esrb_rating: t.Optional[int]
    igdb_slug: str
    lang: str
    media_assets: t.Optional[MediaAssets]  # localized media assets
    name: str
    platform: str
    publisher: str
    refs: Refs
    runner: Runner
    ts_added: str  # required to properly render main webapp page, even in the case of the full re-init of db
    uuid: str
    year_released: int
    Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name


@dataclass
class UpsertAppReleaseResponseDTO:
    app_release_uuid: str
    Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name

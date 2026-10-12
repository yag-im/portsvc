from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class _Model(BaseModel):
    # unknown fields are rejected, as marshmallow did by default
    model_config = ConfigDict(extra="forbid")


class MediaAssets(_Model):
    class Cover(_Model):
        image_id: str

    class Screenshot(_Model):
        width: int
        height: int
        image_id: str

    cover: Cover | None = None
    screenshots: list[Screenshot] | None = Field(default_factory=list)


class PortDescr(_Model):
    class Distro(_Model):
        format: str
        url: str
        files: list[str] = Field(default_factory=list)

    class Refs(_Model):
        ag_id: str | int | None = None
        lutris_id: str | None = None
        mg_id: int | None = None
        pcgw_id: str | None = None
        qz_id: int | None = None

    class Reqs(_Model):
        class Ua(_Model):
            lock_pointer: bool | None = None

        color_bits: int | None = None
        screen_width: int
        screen_height: int
        midi: bool | None = False
        ua: Ua | None = None
        loading_duration: int | None = 0

    class Runner(_Model):
        name: str
        ver: str

    distro: Distro
    esrb_rating: int | None = None
    igdb_slug: str
    lang: str
    media_assets: MediaAssets | None = None  # localized media assets
    name: str
    platform: str
    publisher: str
    refs: Refs
    reqs: Reqs
    runner: Runner
    uuid: str
    year_released: int
    is_visible: bool = True
    tags: list[str] | None = Field(default_factory=list)


class PortInstaller(_Model):
    tasks: list[dict] = Field(default_factory=list)


class UpsertAppReleaseRequestDTO(_Model):
    descr: PortDescr
    installer: PortInstaller


class UpsertAppReleaseResponseDTO(_Model):
    app_release_uuid: str

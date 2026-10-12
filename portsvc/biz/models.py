from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from portsvc.biz.sqldb import Base


class AppDAO(Base):
    __tablename__ = "games"
    __table_args__ = {"schema": "games"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    addl_artifacts: Mapped[Any | None] = mapped_column(JSONB)
    alternative_names: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    companies: Mapped[Any | None] = mapped_column(JSONB)
    esrb_rating: Mapped[int | None] = mapped_column(Integer)
    genres: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    igdb: Mapped[Any | None] = mapped_column(JSONB)
    long_descr: Mapped[str | None] = mapped_column(String)
    media_assets: Mapped[Any | None] = mapped_column(JSONB)
    name: Mapped[str | None] = mapped_column(String)
    platforms: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    refs: Mapped[Any | None] = mapped_column(JSONB)
    short_descr: Mapped[str | None] = mapped_column(String)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))


class AppCompanyDAO(Base):
    __tablename__ = "companies"
    __table_args__ = {"schema": "games"}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String)


class AppPlatformDAO(Base):
    __tablename__ = "platforms"
    __table_args__ = {"schema": "games"}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String)
    abbreviation: Mapped[str | None] = mapped_column(String)
    alternative_name: Mapped[str | None] = mapped_column(String)
    slug: Mapped[str | None] = mapped_column(String)


class AppReleaseDAO(Base):
    __tablename__ = "releases"
    __table_args__ = {"schema": "games"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    app_reqs: Mapped[Any | None] = mapped_column(JSONB)
    game: Mapped[AppDAO] = relationship(AppDAO)
    game_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey(AppDAO.id))
    companies: Mapped[Any | None] = mapped_column(JSONB)
    distro: Mapped[Any | None] = mapped_column(JSONB)
    is_visible: Mapped[bool | None] = mapped_column(Boolean)
    lang: Mapped[str | None] = mapped_column(String)
    media_assets: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    name: Mapped[str | None] = mapped_column(String)
    platform: Mapped[AppPlatformDAO] = relationship(AppPlatformDAO)
    platform_id: Mapped[int | None] = mapped_column(Integer, ForeignKey(AppPlatformDAO.id))
    runner: Mapped[Any | None] = mapped_column(JSONB)
    uuid: Mapped[str | None] = mapped_column(String)
    year_released: Mapped[int | None] = mapped_column(Integer)


class UsersDcsDAO(Base):
    __tablename__ = "users_dcs"
    __table_args__ = {"schema": "stats"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dcs: Mapped[Any | None] = mapped_column(JSONB)
    user_id: Mapped[int | None] = mapped_column(BigInteger)

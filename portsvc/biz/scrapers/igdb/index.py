from portsvc.biz.scrapers.igdb.misc import get_data

HOST_URL = "https://api.igdb.com/v4"


def get_game_by_slug(slug: str) -> dict | None:
    res = get_data(
        f"{HOST_URL}/games",
        data=f"""
        fields
            *,
            alternative_names.name,
            bundles.name,
            cover.image_id,
            franchises.name,
            game_modes.name,
            genres.name,
            involved_companies.*,
            game_engines.name,
            release_dates.human,
            release_dates.region,
            age_ratings.category,
            age_ratings.rating,
            age_ratings.synopsis,
            age_ratings.content_descriptions.description,
            screenshots.image_id,
            screenshots.height,
            screenshots.width;
        where slug = "{slug}";
        sort id asc;
    """,
    )
    if not res:
        return None
    return res[0]

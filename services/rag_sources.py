from services.albert_collections import AlbertCollectionsClient

_albert = AlbertCollectionsClient()
_cached_collections = None


def get_albert_collections(force_reload: bool = False):
    global _cached_collections

    if _cached_collections is None or force_reload:
        cols = _albert.list_collections()
        _cached_collections = {
            col["id"]: col.get("name", col["id"])
            for col in cols
        }

    return _cached_collections

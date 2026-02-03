from openai import OpenAI
from typing import List, Dict
from config.settings import BASE_URL, API_KEY


class AlbertCollectionsClient:

    def __init__(self):
        self.client = OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY,
        )
        self.headers = {
            "Authorization": f"Bearer {API_KEY}"
        }

    def list_collections(self) -> List[Dict]:
        r = self.client._client.request(
            method="GET",
            url="/collections",
            headers=self.headers,
            params={"limit": 100},
        )
        return r.json().get("data", [])

    def search(
        self,
        collection_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        r = self.client._client.request(
            method="POST",
            url=f"/collections/{collection_id}/search",
            headers=self.headers,
            json={
                "query": query,
                "limit": limit,
            }
        )

        return r.json().get("data", [])

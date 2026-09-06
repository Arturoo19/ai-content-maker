import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class ImageSearchError(Exception):
    pass


@dataclass(frozen=True)
class ImageCandidate:
    title: str
    image_url: str
    source_url: str | None = None
    author: str | None = None
    license: str | None = None


class WikimediaImageSearchService:
    def search(self, *, query: str, limit: int = 5) -> list[ImageCandidate]:
        params = urlencode(
            {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": 6,
                "gsrlimit": limit,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
            }
        )
        request = Request(
            f"https://commons.wikimedia.org/w/api.php?{params}",
            headers={"User-Agent": "ai-content-maker/0.1"},
        )

        try:
            with urlopen(request, timeout=20) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise ImageSearchError("Wikimedia Commons rejected the image search.") from error
        except URLError as error:
            raise ImageSearchError("Wikimedia Commons is unavailable.") from error
        except json.JSONDecodeError as error:
            raise ImageSearchError("Wikimedia Commons returned an invalid response.") from error

        pages = response_data.get("query", {}).get("pages", {})
        candidates: list[ImageCandidate] = []
        for page in pages.values():
            image_info = (page.get("imageinfo") or [{}])[0]
            image_url = image_info.get("url")
            if not image_url:
                continue
            if not _is_supported_image_url(image_url):
                continue

            metadata = image_info.get("extmetadata", {})
            candidates.append(
                ImageCandidate(
                    title=page.get("title", ""),
                    image_url=image_url,
                    source_url=image_info.get("descriptionurl"),
                    author=_metadata_value(metadata, "Artist"),
                    license=_metadata_value(metadata, "LicenseShortName")
                    or _metadata_value(metadata, "UsageTerms"),
                )
            )

        return candidates


def _metadata_value(metadata: dict, key: str) -> str | None:
    value = metadata.get(key, {}).get("value")
    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _is_supported_image_url(image_url: str) -> bool:
    path = urlsplit(image_url).path.lower()
    return path.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))

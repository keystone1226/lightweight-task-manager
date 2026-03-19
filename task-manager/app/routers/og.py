"""Open Graph preview endpoint."""

import re

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["og"])

_TIMEOUT = 4.0
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TaskManager/1.0; +og-preview)",
    "Accept": "text/html,application/xhtml+xml",
}


class OGPreview(BaseModel):
    title: str | None = None
    description: str | None = None
    image: str | None = None
    site_name: str | None = None
    url: str | None = None


def _meta(html: str, prop: str) -> str | None:
    """Extract a single <meta property/name> content value."""
    pattern = rf'<meta[^>]+(?:property|name)=["\'](?:og:)?{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']'
    m = re.search(pattern, html, re.IGNORECASE)
    if m:
        return m.group(1).strip() or None

    # reversed attribute order
    pattern2 = rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\'](?:og:)?{re.escape(prop)}["\']'
    m2 = re.search(pattern2, html, re.IGNORECASE)
    return (m2.group(1).strip() or None) if m2 else None


@router.get("/og-preview", response_model=OGPreview)
async def og_preview(url: str) -> OGPreview:
    """Fetch a URL and return its Open Graph metadata."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=_TIMEOUT, headers=_HEADERS
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception:
        return OGPreview()

    return OGPreview(
        title=_meta(html, "title") or _meta(html, "og:title"),
        description=_meta(html, "description") or _meta(html, "og:description"),
        image=_meta(html, "og:image") or _meta(html, "og:image:url"),
        site_name=_meta(html, "og:site_name"),
        url=_meta(html, "og:url") or url,
    )

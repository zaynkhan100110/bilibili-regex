
#!/usr/bin/env python3
"""
Bilibili Video ID and Embed Extractor

Extracts Bilibili BV/AV identifiers, video metadata, page information,
CID values, and embeddable player URLs.

Supports:
- Standard Bilibili video URLs
- BV identifiers
- AV identifiers
- b23.tv short links
- Multi-part videos using the p parameter
- JSON output
"""

import argparse
import json
import re
import sys

from urllib.parse import (
    parse_qs,
    urlencode,
    urlparse,
)

import requests


API_BASE = "https://api.bilibili.com"

VIDEO_INFO_ENDPOINT = (
    f"{API_BASE}/x/web-interface/view"
)

PAGE_LIST_ENDPOINT = (
    f"{API_BASE}/x/player/pagelist"
)

PLAYER_URL = (
    "https://player.bilibili.com/player.html"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
}


class BilibiliError(Exception):
    """Raised when Bilibili extraction fails."""


def extract_bvid(value):
    """
    Extract a BV identifier from a URL or text.

    Example:
        BV1xx411c7mD
    """

    if not value:
        return None

    match = re.search(
        r"\b(BV[0-9A-Za-z]{10})\b",
        value,
        re.IGNORECASE,
    )

    return match.group(1) if match else None


def extract_avid(value):
    """
    Extract an AV identifier.

    Supports:
        av123456
        /video/av123456
        https://www.bilibili.com/video/av123456
    """

    if not value:
        return None

    match = re.search(
        r"\bav([0-9]+)\b",
        value,
        re.IGNORECASE,
    )

    return match.group(1) if match else None


def extract_query_ids(value):
    """
    Extract BV/AV identifiers from URL query parameters.
    """

    try:
        parsed = urlparse(value)
        query = parse_qs(parsed.query)

        bvid = (
            query.get("bvid", [None])[0]
        )

        aid = (
            query.get("aid", [None])[0]
        )

        return bvid, aid

    except Exception:
        return None, None


def extract_page_number(value):
    """
    Extract the selected video page from ?p=2 or #p=2.

    Bilibili page numbers are 1-based.
    """

    try:
        parsed = urlparse(value)

        query = parse_qs(parsed.query)

        page_value = query.get("p", [None])[0]

        if not page_value and parsed.fragment:
            fragment = parsed.fragment.lstrip("?")
            fragment_query = parse_qs(fragment)
            page_value = fragment_query.get("p", [None])[0]

        if page_value:
            page = int(page_value)

            if page >= 1:
                return page

    except (ValueError, TypeError):
        pass

    return 1


def validate_url(value):
    """
    Validate a Bilibili URL before making an HTTP request.

    Bare BV/AV identifiers are handled separately.
    """

    value = value.strip()

    if not value:
        raise BilibiliError("Empty URL or identifier.")

    if not re.match(r"^https?://", value, re.IGNORECASE):
        value = "https://" + value

    parsed = urlparse(value)

    hostname = (parsed.hostname or "").lower()

    allowed_hosts = (
        "bilibili.com",
        "b23.tv",
    )

    allowed = any(
        hostname == domain
        or hostname.endswith("." + domain)
        for domain in allowed_hosts
    )

    if not allowed:
        raise BilibiliError(
            "Unsupported URL host. "
            "Use a bilibili.com or b23.tv URL."
        )

    return value


def create_session():
    """
    Create a reusable HTTP session.
    """

    session = requests.Session()

    session.headers.update(HEADERS)

    return session


def resolve_url(session, url, timeout=20):
    """
    Resolve Bilibili short links such as b23.tv.

    The final redirect must lead to a Bilibili domain.
    """

    try:
        response = session.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            stream=True,
        )

        response.raise_for_status()

        final_url = response.url

        parsed = urlparse(final_url)

        hostname = (parsed.hostname or "").lower()

        if not (
            hostname == "bilibili.com"
            or hostname.endswith(".bilibili.com")
        ):
            raise BilibiliError(
                "Short link redirected outside Bilibili."
            )

        return final_url

    except requests.RequestException as error:
        raise BilibiliError(
            f"Could not resolve URL: {error}"
        ) from error


def api_request(session, endpoint, params, timeout=20):
    """
    Make a request to a Bilibili API endpoint.
    """

    try:
        response = session.get(
            endpoint,
            params=params,
            timeout=timeout,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        raise BilibiliError(
            f"Network request failed: {error}"
        ) from error

    try:
        result = response.json()

    except ValueError as error:
        raise BilibiliError(
            "Bilibili returned an invalid JSON response."
        ) from error

    if not isinstance(result, dict):
        raise BilibiliError(
            "Unexpected Bilibili API response."
        )

    code = result.get("code")

    if code != 0:
        message = result.get(
            "message",
            "Unknown Bilibili API error",
        )

        raise BilibiliError(
            f"Bilibili API error {code}: {message}"
        )

    return result.get("data")


def get_video_info(
    session,
    bvid=None,
    aid=None,
    timeout=20,
):
    """
    Retrieve video metadata using the Bilibili view API.

    Returns:
        Video metadata dictionary.
    """

    params = {}

    if bvid:
        params["bvid"] = bvid

    elif aid:
        params["aid"] = aid

    else:
        raise BilibiliError(
            "A BV or AV identifier is required."
        )

    data = api_request(
        session,
        VIDEO_INFO_ENDPOINT,
        params,
        timeout,
    )

    if not isinstance(data, dict):
        raise BilibiliError(
            "Video information was not returned."
        )

    return data


def get_video_pages(
    session,
    bvid=None,
    aid=None,
    timeout=20,
):
    """
    Retrieve all pages/parts belonging to a video.
    """

    params = {}

    if bvid:
        params["bvid"] = bvid

    elif aid:
        params["aid"] = aid

    else:
        raise BilibiliError(
            "A BV or AV identifier is required."
        )

    data = api_request(
        session,
        PAGE_LIST_ENDPOINT,
        params,
        timeout,
    )

    if not isinstance(data, list):
        return []

    return data


def get_selected_page(pages, page_number):
    """
    Select a page using a 1-based page number.

    Raises an error if the requested page does not exist.
    """

    if not pages:
        raise BilibiliError(
            "Bilibili did not return any video pages."
        )

    if page_number < 1:
        raise BilibiliError(
            "Page number must be at least 1."
        )

    if page_number > len(pages):
        raise BilibiliError(
            f"Page {page_number} does not exist. "
            f"This video has {len(pages)} page(s)."
        )

    return pages[page_number - 1]


def make_player_url(
    bvid=None,
    aid=None,
    cid=None,
    page=1,
):
    """
    Build a Bilibili player URL.

    BV identifiers are preferred. AV identifiers are
    supported as a fallback.
    """

    params = {}

    if bvid:
        params["bvid"] = bvid

    elif aid:
        params["aid"] = aid

    else:
        raise BilibiliError(
            "Cannot build player URL without a BV or AV ID."
        )

    if cid:
        params["cid"] = cid

    if page and page > 1:
        params["p"] = page

    return (
        PLAYER_URL
        + "?"
        + urlencode(params)
    )


def make_iframe(player_url):
    """
    Generate an HTML iframe for embedding.
    """

    return (
        '<iframe '
        'width="640" '
        'height="360" '
        f'src="{player_url}" '
        'frameborder="0" '
        'allowfullscreen '
        'scrolling="no">'
        '</iframe>'
    )


def extract_identifiers(original_value, resolved_url=None):
    """
    Extract identifiers from both the original input
    and the resolved URL.
    """

    candidates = [
        resolved_url,
        original_value,
    ]

    bvid = None
    aid = None

    for candidate in candidates:
        if not candidate:
            continue

        if not bvid:
            bvid = extract_bvid(candidate)

        if not aid:
            aid = extract_avid(candidate)

        query_bvid, query_aid = extract_query_ids(
            candidate
        )

        if not bvid and query_bvid:
            bvid = query_bvid

        if not aid and query_aid:
            aid = str(query_aid)

    return bvid, aid


def build_result(
    session,
    original_value,
    page_number=1,
    timeout=20,
):
    """
    Main extraction workflow.

    Returns a structured dictionary.
    """

    original_value = original_value.strip()

    if not original_value:
        raise BilibiliError(
            "Empty URL or identifier."
        )

    resolved_url = original_value

    # Bare BV and AV identifiers do not need URL resolution.
    is_bare_id = bool(
        re.fullmatch(
            r"(?:BV[0-9A-Za-z]{10}|av[0-9]+)",
            original_value,
            re.IGNORECASE,
        )
    )

    if not is_bare_id:
        validated_url = validate_url(
            original_value
        )

        hostname = (
            urlparse(validated_url).hostname or ""
        ).lower()

        if hostname == "b23.tv":
            resolved_url = resolve_url(
                session,
                validated_url,
                timeout,
            )
        else:
            resolved_url = validated_url

    bvid, aid = extract_identifiers(
        original_value,
        resolved_url,
    )

    if not bvid and not aid:
        raise BilibiliError(
            "Could not find a valid BV or AV identifier."
        )

    # Get canonical metadata from Bilibili.
    info = get_video_info(
        session,
        bvid=bvid,
        aid=aid,
        timeout=timeout,
    )

    bvid = info.get("bvid") or bvid
    aid = info.get("aid") or aid

    title = info.get("title", "")
    owner = info.get("owner") or {}

    # Use the page list returned by the view API when available.
    pages = info.get("pages") or []

    if not pages:
        pages = get_video_pages(
            session,
            bvid=bvid,
            aid=aid,
            timeout=timeout,
        )

    selected_page = get_selected_page(
        pages,
        page_number,
    )

    cid = selected_page.get("cid")

    if not cid:
        raise BilibiliError(
            "Could not retrieve the CID for the selected page."
        )

    player_url = make_player_url(
        bvid=bvid,
        aid=aid,
        cid=cid,
        page=page_number,
    )

    iframe = make_iframe(player_url)

    return {
        "platform": "Bilibili",
        "original_url": original_value,
        "resolved_url": resolved_url,
        "bvid": bvid,
        "aid": aid,
        "cid": cid,
        "title": title,
        "description": info.get("desc", ""),
        "author": owner.get("name", ""),
        "author_mid": owner.get("mid"),
        "duration": info.get("duration"),
        "selected_page": page_number,
        "page_count": len(pages),
        "page_title": selected_page.get("part", ""),
        "pages": [
            {
                "page": item.get("page"),
                "cid": item.get("cid"),
                "title": item.get("part"),
                "duration": item.get("duration"),
            }
            for item in pages
        ],
        "player_url": player_url,
        "iframe": iframe,
    }


def print_result(result):
    """
    Print human-readable extraction results.
    """

    print()
    print("=" * 65)
    print("BILIBILI VIDEO EXTRACTOR")
    print("=" * 65)

    print()
    print("VIDEO INFORMATION")
    print("-" * 65)

    print(f"Title:          {result['title']}")
    print(f"Author:         {result['author']}")
    print(f"BV ID:          {result['bvid'] or 'NOT FOUND'}")
    print(f"AV ID:          {result['aid'] or 'NOT FOUND'}")
    print(f"CID:            {result['cid']}")
    print(f"Duration:       {result['duration']} seconds")
    print(
        f"Selected page:  {result['selected_page']}"
        f" / {result['page_count']}"
    )
    print(f"Page title:     {result['page_title']}")

    print()
    print("PLAYER URL")
    print("-" * 65)
    print(result["player_url"])

    print()
    print("IFRAME")
    print("-" * 65)
    print(result["iframe"])

    print()
    print("VIDEO PAGES")
    print("-" * 65)

    for item in result["pages"]:
        print(
            f"Page {item['page']}: "
            f"{item['title']} "
            f"(CID: {item['cid']})"
        )

    print()
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract Bilibili BV/AV IDs, CID values, "
            "video metadata and embed URLs."
        )
    )

    parser.add_argument(
        "url",
        help="Bilibili video URL, b23.tv link, BV ID or AV ID.",
    )

    parser.add_argument(
        "-p",
        "--page",
        type=int,
        default=None,
        help="Select a video part/page (1-based).",
    )

    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=20,
        help="HTTP timeout in seconds (default: 20).",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )

    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero.")

    try:
        # Explicit --page overrides the URL's p parameter.
        page_number = (
            args.page
            if args.page is not None
            else extract_page_number(args.url)
        )

        if page_number < 1:
            raise BilibiliError(
                "Page number must be at least 1."
            )

        session = create_session()

        result = build_result(
            session,
            args.url,
            page_number=page_number,
            timeout=args.timeout,
        )

        if args.json:
            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print_result(result)

    except BilibiliError as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        sys.exit(2)

    except KeyboardInterrupt:
        print(
            "\nOperation cancelled.",
            file=sys.stderr,
        )
        sys.exit(130)


if __name__ == "__main__":
    main()

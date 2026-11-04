#!/usr/bin/env python3

import sys
import re
import requests
from urllib.parse import urlparse, parse_qs


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": UA,
    "Referer": "https://www.bilibili.com/",
}


def extract_bvid(url):
    """
    Extract BV ID from a Bilibili URL or plain text.
    """

    match = re.search(
        r"(BV[0-9A-Za-z]+)",
        url,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)


def extract_avid(url):
    """
    Extract AV ID from URLs such as:

        /video/av123456
        av123456
    """

    match = re.search(
        r"(?:/|^)av([0-9]+)",
        url,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    match = re.search(
        r"\bav([0-9]+)\b",
        url,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)


def resolve_url(url):
    """
    Resolve b23.tv short links and other redirects.
    """

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            allow_redirects=True,
            timeout=20,
        )

        return response.url

    except requests.RequestException as e:

        print(
            f"WARNING: Could not resolve URL: {e}"
        )

        return url


def get_video_info(bvid=None, aid=None):
    """
    Get Bilibili video information.

    Bilibili's web-interface/view endpoint returns
    information including aid, bvid and cid.
    """

    params = {}

    if bvid:
        params["bvid"] = bvid

    elif aid:
        params["aid"] = aid

    else:
        return None

    response = requests.get(
        "https://api.bilibili.com/x/web-interface/view",
        params=params,
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != 0:
        raise RuntimeError(
            data.get(
                "message",
                "Bilibili API returned an error"
            )
        )

    return data["data"]


def get_cid(bvid, page=1):
    """
    Get the CID for a particular page/part.

    For multi-part Bilibili videos, page=1 gives
    the first part.
    """

    response = requests.get(
        "https://api.bilibili.com/x/player/pagelist",
        params={
            "bvid": bvid,
        },
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != 0:
        raise RuntimeError(
            data.get(
                "message",
                "Could not get CID"
            )
        )

    pages = data.get("data", [])

    if not pages:
        return None

    index = page - 1

    if index >= len(pages):
        index = 0

    return pages[index].get("cid")


def make_iframe(bvid, aid=None, cid=None):
    """
    Build Bilibili's player iframe.

    bvid is preferred.
    """

    src = (
        "https://player.bilibili.com/player.html"
        f"?bvid={bvid}"
    )

    return (
        f'<iframe '
        f'width="640" '
        f'height="360" '
        f'src="{src}" '
        f'frameborder="0" '
        f'allowfullscreen '
        f'scrolling="no">'
        f'</iframe>'
    )


def main():

    if len(sys.argv) != 2:

        print(
            'Usage: python bili.py "<bilibili-url>"'
        )

        sys.exit(1)

    original_url = sys.argv[1].strip()

    if not original_url:
        print("ERROR: Empty URL.")
        sys.exit(1)

    print("Resolving Bilibili URL...")

    # ---------------------------------------------------------
    # If this is a b23.tv short URL, resolve it first.
    # ---------------------------------------------------------

    resolved_url = original_url

    if "b23.tv" in original_url.lower():

        resolved_url = resolve_url(
            original_url
        )

        print(
            f"Resolved URL: {resolved_url}"
        )

    # ---------------------------------------------------------
    # Extract IDs from URL.
    # ---------------------------------------------------------

    bvid = extract_bvid(
        resolved_url
    )

    aid = extract_avid(
        resolved_url
    )

    # Also check original URL in case redirect handling
    # didn't preserve the original ID.
    if not bvid:
        bvid = extract_bvid(
            original_url
        )

    if not aid:
        aid = extract_avid(
            original_url
        )

    # ---------------------------------------------------------
    # If we have neither, stop.
    # ---------------------------------------------------------

    if not bvid and not aid:

        print()
        print(
            "ERROR: Could not find a Bilibili BV or AV ID."
        )

        print()
        print(
            "Supported examples:"
        )

        print(
            "  https://www.bilibili.com/video/BV..."
        )

        print(
            "  https://www.bilibili.com/video/av123456"
        )

        print(
            "  https://b23.tv/..."
        )

        sys.exit(2)

    print()
    print("Fetching video information...")

    try:

        info = get_video_info(
            bvid=bvid,
            aid=aid,
        )

    except Exception as e:

        print()
        print(
            f"ERROR: Could not get video information:"
        )

        print(e)

        sys.exit(3)

    # ---------------------------------------------------------
    # Use canonical values returned by Bilibili.
    # ---------------------------------------------------------

    bvid = info.get(
        "bvid",
        bvid,
    )

    aid = info.get(
        "aid",
        aid,
    )

    title = info.get(
        "title",
        "",
    )

    # ---------------------------------------------------------
    # CID
    # ---------------------------------------------------------

    cid = None

    pages = info.get(
        "pages",
        [],
    )

    if pages:

        # First page/part.
        cid = pages[0].get(
            "cid"
        )

    if not cid and bvid:

        try:

            cid = get_cid(
                bvid
            )

        except Exception:
            pass

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("BILIBILI VIDEO")
    print("=" * 60)

    print()
    print("BV ID:")
    print(bvid or "NOT FOUND")

    print()
    print("AV ID:")
    print(aid or "NOT FOUND")

    print()
    print("CID:")
    print(cid or "NOT FOUND")

    if title:

        print()
        print("TITLE:")
        print(title)

    # ---------------------------------------------------------
    # IFRAME
    # ---------------------------------------------------------

    if bvid:

        iframe = make_iframe(
            bvid=bvid,
            aid=aid,
            cid=cid,
        )

        print()
        print("=" * 60)
        print("IFRAME")
        print("=" * 60)

        print(iframe)

        print()
        print("=" * 60)
        print("PLAYER URL")
        print("=" * 60)

        print(
            "https://player.bilibili.com/"
            f"player.html?bvid={bvid}"
        )


if __name__ == "__main__":
    main()



# Bilibili Regex

A Python-based Bilibili video identifier and metadata extractor.

`bilibili.py` extracts Bilibili video identifiers, retrieves video metadata through Bilibili's public web API, identifies the CID for individual video parts, and generates embeddable player URLs and HTML iframes.

It supports standard Bilibili video links, BV identifiers, AV identifiers, short links from `b23.tv`, and multi-part videos.

## Features

- **BV ID extraction** — Extracts Bilibili BV identifiers.
- **AV ID extraction** — Supports legacy AV identifiers.
- **Short-link resolution** — Resolves `b23.tv` links.
- **Video metadata** — Retrieves titles, descriptions, authors, and duration.
- **CID extraction** — Retrieves the content ID for the selected video part.
- **Multi-part support** — Selects individual parts using the `p` parameter or command-line option.
- **Canonical identifiers** — Uses the identifiers returned by Bilibili's API.
- **Player URL generation** — Generates a Bilibili embedded-player URL.
- **Iframe generation** — Produces HTML iframe markup.
- **JSON output** — Supports machine-readable output for scripts and integrations.
- **Timeout handling** — Allows configurable HTTP request timeouts.
- **Error handling** — Handles invalid links, API errors, network failures, and unavailable pages.

## Requirements

- Python 3.9 or newer
- Internet connection
- `requests`

## Installation

Clone the repository:

```bash
git clone https://github.com/zaynkhan100110/bilibili-regex.git
```

Enter the project directory:

```bash
cd bilibili-regex
```

Install the dependency:

```bash
python -m pip install requests
```

Alternatively, install dependencies from a requirements file if you add one:

```bash
python -m pip install -r requirements.txt
```

## Usage

### Standard Bilibili URL

```bash
python bilibili.py "https://www.bilibili.com/video/BV1xx411c7mD"
```

### BV identifier

```bash
python bilibili.py "BV1xx411c7mD"
```

### AV identifier

```bash
python bilibili.py "av123456"
```

### Legacy AV URL

```bash
python bilibili.py "https://www.bilibili.com/video/av123456"
```

### Bilibili short URL

```bash
python bilibili.py "https://b23.tv/example"
```

The script follows the short-link redirect and extracts the video identifier from the resulting Bilibili URL.

### Select a video part

Bilibili supports multi-part videos. Use `--page` to select a particular part.

```bash
python bilibili.py "https://www.bilibili.com/video/BV1xx411c7mD" --page 2
```

The page number is one-based:

- `--page 1` selects the first part.
- `--page 2` selects the second part.
- `--page 3` selects the third part.

You can also use Bilibili's URL parameter:

```bash
python bilibili.py "https://www.bilibili.com/video/BV1xx411c7mD?p=2"
```

An explicit `--page` option takes precedence over the URL's `p` parameter.

If the requested page does not exist, the script reports an error instead of silently selecting another part.

### Configure the HTTP timeout

The default timeout is 20 seconds.

```bash
python bilibili.py "BV1xx411c7mD" --timeout 30
```

### JSON output

Use `--json` to receive structured output:

```bash
python bilibili.py "BV1xx411c7mD" --json
```

Example structure:

```json
{
  "platform": "Bilibili",
  "original_url": "BV1xx411c7mD",
  "resolved_url": "BV1xx411c7mD",
  "bvid": "BV1xx411c7mD",
  "aid": 123456,
  "cid": 123456789,
  "title": "Example video",
  "description": "Example description",
  "author": "Example creator",
  "author_mid": 123456,
  "duration": 300,
  "selected_page": 1,
  "page_count": 2,
  "page_title": "Part 1",
  "pages": [],
  "player_url": "https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&cid=123456789",
  "iframe": "<iframe ...></iframe>"
}
```

The example values are illustrative. Actual results depend on the video and Bilibili API response.

## Output

The normal output includes:

| Field | Description |
|---|---|
| BV ID | Bilibili's modern video identifier |
| AV ID | Bilibili's legacy numeric video identifier |
| CID | Content ID for the selected video part |
| Title | Video title |
| Author | Video uploader |
| Duration | Video duration in seconds |
| Selected page | Selected part number |
| Page count | Total number of available parts |
| Page title | Title of the selected part |
| Player URL | Bilibili embedded-player URL |
| Iframe | HTML embed markup |

## How it works

### 1. Input processing

The script accepts a Bilibili URL, short link, BV identifier, or AV identifier.

### 2. Short-link resolution

For `b23.tv` links, the script follows HTTP redirects to obtain the final Bilibili URL.

### 3. Identifier extraction

Regular expressions identify BV and AV identifiers. URL query parameters are also checked for identifiers.

### 4. Video metadata retrieval

The script requests:

```text
https://api.bilibili.com/x/web-interface/view
```

This endpoint provides video metadata, including canonical identifiers and page information.

### 5. Page and CID retrieval

The script uses the page information returned by the video metadata endpoint.

If page information is unavailable, it requests:

```text
https://api.bilibili.com/x/player/pagelist
```

The selected page's CID is then used to construct the player URL.

### 6. Player generation

The script generates a URL in this format:

```text
https://player.bilibili.com/player.html?bvid=VIDEO_BVID&cid=VIDEO_CID
```

It also generates HTML iframe markup using that URL.

## Project structure

```text
bilibili-regex/
│
├── bilibili.py
├── README.md
├── requirements.txt
└── .gitignore
```

### Optional requirements.txt

```text
requests>=2.31.0,<3.0.0
```

### Optional .gitignore

```gitignore
__pycache__/
*.py[cod]
.venv/
venv/
.env
.idea/
.vscode/
.DS_Store
```

## Error handling

The script handles common failures:

| Error | Possible reason |
|---|---|
| Unsupported URL host | The supplied URL is not from Bilibili |
| Could not find a BV or AV ID | No supported identifier was found |
| Network request failed | Network connection or HTTP error |
| Invalid JSON response | API returned an unexpected response |
| Bilibili API error | Video is unavailable or API rejected the request |
| Page does not exist | Requested part number is outside the video's page range |
| Could not resolve URL | Short-link redirect failed |

Some videos may be unavailable because of privacy settings, region restrictions, deleted content, account restrictions, or changes to Bilibili's API.

## Limitations

- This project extracts identifiers and metadata; it does not download video files.
- It does not extract direct video or audio stream URLs.
- It does not bypass login requirements, geographic restrictions, or access controls.
- Bilibili may change its API behavior or response structure.
- Some videos may not be accessible through the public API.
- Generated iframe URLs depend on Bilibili's player and embedding policies.
- The availability of embedded playback may depend on the video, account, region, and browser.

## API endpoints

The script uses these Bilibili endpoints:

| Endpoint | Purpose |
|---|---|
| `/x/web-interface/view` | Retrieve video metadata |
| `/x/player/pagelist` | Retrieve video parts and CID values |

These are Bilibili API endpoints, not endpoints hosted by this project.

## Troubleshooting

### requests is not installed

Run:

```bash
python -m pip install requests
```

### The video cannot be found

Check that:

- The URL is correct.
- The video is publicly accessible.
- The BV or AV identifier is valid.
- The video has not been deleted or restricted.

### The short link does not resolve

Try opening the `b23.tv` link in a browser and pass the resulting Bilibili video URL to the script.

### A selected page does not exist

Check the video's available parts and use a valid one-based page number.

### The player does not load

Open the generated player URL in a browser. If it still fails, the video may have embedding restrictions or require access that the public player does not provide.

## Responsible use

Use this project in accordance with Bilibili's terms, applicable laws, and the rights of video creators.

Respect copyright, privacy, rate limits, and access restrictions. Do not use this project to circumvent platform protections or download content without authorization.

## Contributing

Contributions, bug reports, and improvements are welcome.

When submitting changes:

1. Keep the script compatible with supported Python versions.
2. Handle API errors explicitly.
3. Avoid unnecessary requests.
4. Document new command-line options.
5. Test standard URLs, short links, BV IDs, AV IDs, and multi-part videos.


## Note

This script is a part of my <a href="https://github.com/zaynkhan100110/ump">ump</a>

## License
Don't sell it

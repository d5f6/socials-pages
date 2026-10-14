# socials-pages

A link-in-bio page in the style of Linktree. The content lives in
[`socials.yml`](socials.yml); every push to `main` checks the file, builds a
static page and publishes it with GitHub Pages.

## Editing the page

1. Open [`socials.yml`](socials.yml) on GitHub and click the pencil icon
   (works in the GitHub app on a phone, too).
2. Change the file and click **Commit changes**.
3. After about a minute the change is live. Progress shows under **Actions**.

If the file contains a mistake, the run fails, the page keeps its previous
state and GitHub sends an email. The run page names the line and the problem.

```yaml
name: Dennis
bio: |
  Erste Zeile
  Zweite Zeile
avatar: avatar.jpg

links:
  - url: https://mastodon.social/@name    # icon and label are detected
  - url: github.com/name                  # https:// is added automatically
    label: Mein Code
  - url: name@example.org                 # becomes a mailto: link
  - url: https://example.org
    hidden: true                          # kept in the file, not shown
  - url: https://pixel.example/@name
    platform: pixelfed                    # only if detection picks the wrong icon
```

| Field | Notes |
| --- | --- |
| `name` | Up to 80 characters. Without an avatar, its initials are shown. |
| `bio` | Up to 300 characters; line breaks are kept. |
| `avatar` | Image file in the repository (JPEG, PNG, WebP or GIF, up to 25 MB). Upload via **Add file → Upload files**. It is cropped to a square, resized and all metadata (camera, GPS) is removed. |
| `links[].url` | Required. `https://`, `http://` or an email address. |
| `links[].label` | Optional. Defaults to the platform name, the host for websites, or the address for email. |
| `links[].platform` | Optional. One of the keys in [`socials_pages/platforms.py`](socials_pages/platforms.py). |
| `links[].hidden` | Optional. `true` hides the link. |

Every link carries `rel="me"`, so a Mastodon profile that links to this page
shows it as verified.

Note that the repository is public: removed links stay visible in the Git
history.

## Local development

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.lock
.venv/bin/pytest
.venv/bin/python -m socials_pages            # socials.yml -> _site/
python3 -m http.server -d _site 8000         # preview on http://localhost:8000
```

## Deployment

`.github/workflows/pages.yml` runs the tests, builds the page and deploys it.
Repository settings: **Pages → Build and deployment → Source: GitHub Actions**.

Custom domain:

1. Verify the parent domain under the account's **Settings → Pages → Verified
   domains**, so nobody else can claim a subdomain.
2. DNS: `CNAME` record from the subdomain to `<user>.github.io`.
3. Repository **Settings → Pages → Custom domain**, then **Enforce HTTPS** once
   the certificate is issued.

## Security

- Plain HTML and CSS. A Content-Security-Policy `<meta>` tag forbids scripts and
  external resources (GitHub Pages cannot set response headers).
- Only `http`, `https` and `mailto` URLs are accepted; all text is HTML-escaped.
- The avatar is re-encoded, which drops EXIF and GPS data.
- GitHub Actions are pinned to commit SHAs; the build job can only read the
  repository, and only the deploy job may publish.

## Icons

Brand icons come from [simple-icons](https://simpleicons.org) (CC0) and are
stored as path data in `socials_pages/icons.json`. To update them, see
`scripts/build_icons.py`. LinkedIn is not part of simple-icons, so it uses a
neutral outline icon.

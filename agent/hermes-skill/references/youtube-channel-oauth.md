# YouTube channel authorization and safe operation

Use this reference when granting the dedicated `clawdj` Hermes profile access to YouTube. This is separate from Google Workspace integration: YouTube uses the YouTube Data/Analytics APIs and YouTube-specific OAuth scopes.

## Current project state

YouTube OAuth remains an active follow-up. Ernest is creating the Google Cloud project/OAuth client. Do not let media work or cross-machine setup erase this task.

Public channel:

```text
https://www.youtube.com/@claw-dj
```

Currently verified canonical channel ID:

```text
UClafA-9ft1J1iAKo1JMZmwQ
```

Recheck the direct URL if ownership or channel structure changes.

## Authorization model

Prefer OAuth 2.0 Desktop App authorization. Ernest signs in on Google's consent page. Hermes must never request or handle his Google password, 2FA codes, recovery codes, browser cookies, raw access token, or refresh token.

Store the OAuth client JSON and token locally under the isolated `clawdj` profile with restrictive permissions. Never commit them or place them in a media folder.

Browser control of an already signed-in YouTube Studio session is possible for interactive work, but OAuth/API access is more reliable for structured reads, uploads, and automation.

## Google Cloud setup

1. Create/select a dedicated project such as `claw-dj-youtube-agent`.
2. Enable YouTube Data API v3.
3. Enable YouTube Analytics API only if analytics are needed.
4. Configure Google Auth Platform:
   - app name: `claw-dj Hermes Agent`;
   - External audience for a normal personal account; Internal only for an eligible managed Workspace organization;
   - add the channel-owning account as a test user while the app is in Testing.
5. Create an OAuth 2.0 Desktop App client and download its JSON.
6. Ask Ernest only for the local JSON path, never its contents.

Console links:

- <https://console.cloud.google.com/projectselector2/home/dashboard>
- <https://console.cloud.google.com/apis/library/youtube.googleapis.com>
- <https://console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com>
- <https://console.cloud.google.com/auth/overview>
- <https://console.cloud.google.com/auth/clients>

## Stage scopes

Initial read/upload integration:

```text
https://www.googleapis.com/auth/youtube.readonly
https://www.googleapis.com/auth/youtube.upload
```

Optional analytics:

```text
https://www.googleapis.com/auth/yt-analytics.readonly
```

Add later for editing existing resources, thumbnails, playlists, and comment operations:

```text
https://www.googleapis.com/auth/youtube.force-ssl
```

Do not grant Gmail, Drive, Calendar, monetary analytics, or broad Google-account scopes for this YouTube-only workflow.

## Channel verification

Google accounts can manage personal channels and Brand Accounts. After OAuth, call `channels.list(mine=true)` before any write. Stop unless the returned channel ID equals `UClafA-9ft1J1iAKo1JMZmwQ`.

## Safe first-write sequence

1. Confirm read-only channel and video listing.
2. Confirm analytics read if enabled.
3. Present the intended file, title, description, tags, and privacy status to Ernest.
4. After confirmation, upload the first API video as `private`.
5. Read it back and verify channel ID, title, description, duration, and processing status.
6. Require a second explicit approval before making it unlisted, public, or scheduled.

Default policy:

- Read metadata/analytics: no confirmation.
- Draft titles, descriptions, tags, comments, and replies: no confirmation.
- Upload: confirmation required; privacy defaults to private.
- Publish/schedule or edit public metadata: confirmation required.
- Reply to/moderate comments: confirmation required.
- Delete videos, comments, or playlists: confirmation required.

OAuth access must remain revocable from the Google Account security page. Deleting the local token must disable Hermes access.

# Media storage (Cloudflare R2)

All user files (profile and gallery photos, Bondmaker photos, ID documents,
selfies, Bond Story media, chat photos, videos and voice notes) live in a
**private** R2 bucket. Nothing in it is public: the API hands out short-lived
signed links instead.

## How it works

1. The app asks for an upload link: `POST /api/v1/media/uploads/`
   ```json
   {"purpose": "profile_picture", "content_type": "image/jpeg", "size_bytes": 482113}
   ```
   Chat purposes also need `"chat_id"`.
2. The app `PUT`s the file to `upload_url`, sending exactly the returned
   `headers` (the `Content-Type` is part of the signature). The link expires
   after 15 minutes.
3. The app calls `POST /api/v1/media/uploads/{upload_id}/complete/`. The server
   checks the real size, the declared type, the file's first bytes and, for
   audio and video, the duration in the MP4 header. On success it returns a
   `ref` such as `r2://profile/12/4f0c...jpg`; files that break a rule are
   deleted and a 400 explains why. A 409 means the file has not arrived yet.
4. The app sends the `ref` in the field it is setting (for example
   `PATCH /api/v1/auth/profile/ {"profile_picture": "<ref>"}`).

Responses never contain references: every `r2://` value is turned into a
signed link when the response is rendered (links last 1 hour, 10 minutes for
identity documents). The part of the link before `?` is stable per file, so the
app can use it as its image cache key.

`DELETE /api/v1/media/uploads/{upload_id}/` cancels an upload that was never used.

## Rules

| Purpose | Types | Max size | Max length |
| --- | --- | --- | --- |
| `profile_picture`, `profile_gallery`, `bondmaker_profile_picture`, `bondmaker_cover_picture`, `post_image`, `chat_image` | jpeg, png, webp, heic | 10 MB | |
| `id_document`, `selfie` | jpeg, png, webp, heic | 10 MB | |
| `post_video`, `chat_video` | mp4, mov | 50 MB | 60 s |
| `chat_voice_note` | m4a (audio/mp4) | 10 MB | 120 s |

A field only accepts a reference that belongs to the requesting user, has
passed verification, was uploaded for that purpose (and that chat, for chat
media) and is not already used by another field. Outside URLs are rejected.
Existing Cloudinary URLs already stored on a record keep working and may be
left in place.

## Lifecycle

- Replacing or removing a file (new profile photo, gallery change, post or
  message "delete for everyone", account deletion) deletes the old object.
- Uploads never completed, or completed but never used, are removed after 24
  hours by `cleanup_stale_media_uploads` (Celery beat, hourly at :30). The same
  job retries any deletion that failed earlier.

## Cloudflare setup

1. Bucket `bondah-media` (exists). Keep the public development URL **disabled**
   and do **not** attach a custom domain: everything is served through signed
   links.
2. R2 > Manage API tokens > create a token with **Object Read & Write**,
   scoped to the `bondah-media` bucket only.
3. CORS is not needed for the mobile app (native uploads are not subject to
   CORS). Add a policy only if a web client will upload directly.

## Environment variables

| Variable | Required | Default |
| --- | --- | --- |
| `R2_ACCESS_KEY_ID` | yes | |
| `R2_SECRET_ACCESS_KEY` | yes | |
| `R2_ACCOUNT_ID` | no | the Bondah account |
| `R2_BUCKET` | no | `bondah-media` |
| `R2_ENDPOINT_URL` | no | `https://<account>.r2.cloudflarestorage.com` |
| `R2_UPLOAD_URL_TTL_SECONDS` | no | `900` |
| `R2_DOWNLOAD_URL_TTL_SECONDS` | no | `3600` |
| `R2_SENSITIVE_DOWNLOAD_URL_TTL_SECONDS` | no | `600` |

Without the two keys the upload endpoints answer 503 and stored references
render as `null`; everything else keeps working.

Never put the keys in code, commits, tickets or chat. If they leak, delete the
token in Cloudflare and create a new one.

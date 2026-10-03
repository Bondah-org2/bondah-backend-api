# Chat sync protocol

How a client keeps a chat correct across bad networks, app restarts and multiple
devices. The database is the source of truth; polling (and WebSockets later)
only make updates arrive faster. Every endpoint below is under `/api/v1/` and
needs a JWT.

## Core ideas

- **Event numbers.** Each chat has a counter. Creating, editing or deleting a
  message takes the next number. A message keeps two numbers:
  - `seq`: its permanent position in the conversation. Sort by this.
  - `change_seq`: the last event that touched it. Sync by this.
- **Cursor.** Each device stores, per chat, the highest `change_seq` it has
  applied. Catching up is always "give me everything after my cursor".
- **Idempotent sends.** The device creates a UUID `client_message_id` for every
  new message and reuses it on every retry. The server never stores the same id
  twice for a sender.
- **Receipts are cursors.** `last_delivered_seq` (highest event any of the
  user's devices synced) and `last_read_seq` (highest event the user read). Both
  only move forward.

## Device id

Send `X-Device-Id: <stable id per install>` on sync calls. It lets a phone and a
tablet track their own position. Without it everything counts as one device.

## Opening a chat for the first time

1. `GET chats/{id}/messages/` returns the latest page (`results`, oldest first)
   and `last_seq`. Store `last_seq` as the cursor.
2. Then poll `GET chats/{id}/sync/?after_seq={cursor}`.

Scrolling back: `GET chats/{id}/messages/?before_seq={first loaded seq}`.

## Staying up to date

`GET chats/{id}/sync/?after_seq={cursor}&limit=200`

Response:

| Field | Meaning |
| --- | --- |
| `events` | Messages created or changed after the cursor, in event order |
| `next_after_seq` | Store this as the new cursor once events are applied |
| `has_more` | Call again with `next_after_seq` until false |
| `last_seq` | The chat's latest event when the request started |
| `receipts` | Every member's delivered and read cursors |
| `typing_user_ids` | Other members typing right now |
| `presence` | `{user_id: {online, last_seen}}` for other members |

Applying events: upsert each message by `id`, keep the list sorted by `seq`.
If `hidden` is true the user deleted it for themselves: remove it. If
`is_deleted` is true show "message deleted". Ignore events for messages older
than the oldest one loaded; they belong to history you have not fetched.

Calling sync also acknowledges delivery of everything up to `after_seq` for
that device, so only advance the cursor after the events are saved locally.

Suggested polling: every 3 s while the chat is open and the app is in the
foreground, every 15 s on the inbox, never in the background (push covers it).

## Sending

`POST chats/{id}/send/`

```json
{
  "client_message_id": "8f2c4f0e-6b0a-4a8e-9d55-2f4b8d6f1c10",
  "message_type": "text",
  "content": "Hello",
  "reply_to_id": 123
}
```

- `201`: stored now. `200`: this `client_message_id` was already stored; the
  original message is returned. Treat both as success.
- `409`: the id was used in another chat. Generate a new id.
- `429`: rate limited (60 per minute). Retry later with the same id.
- Network error or timeout: retry with the same id. This is always safe.

Types: `text` (max 4000 characters), `image`, `video`, `voice_note` (requires
`voice_note_duration`, 1 to 120 seconds). Media types need `media_url`.

Show the message immediately as "sending", switch to "sent" when the response
arrives, and use its `seq`.

## Receipts

- Sent: the server returned the message (it has a `seq`).
- Delivered: every other member's `last_delivered_seq` is at least the
  message's `seq`.
- Read: every other member's `last_read_seq` is at least the message's `seq`.

In three-person intro chats show double ticks only when all others reached the
state; long-press can list who has read it using the same cursors.

Report reading with `POST chats/{id}/read/ {"last_read_seq": <highest seq on screen>}`.
Sending a message marks the sender as having read up to it.

## Typing

`POST chats/{id}/typing/ {"is_typing": true}` at most every few seconds while
typing (40 per minute limit). It expires after 6 seconds on its own; send
`false` when the user clears the input.

## Edit and delete

- `PATCH chats/{id}/messages/{message_id}/ {"content": "..."}`: sender only, text
  messages only.
- `DELETE chats/{id}/messages/{message_id}/ {"delete_type": "for_me" | "for_everyone"}`:
  `for_everyone` is sender only and leaves a tombstone.

Both produce a new event, so every device picks them up through sync.

## Inbox

`GET chats/` returns rows sorted by latest activity with `last_message`,
`unread_count`, `my_last_read_seq`, `last_seq`, the other `participants` and,
for Bondmaker intro chats, `match` (`match_request_id`, `match_request_status`).

A Bondmaker marks a match successful with
`POST match-requests/{match_request_id}/action/ {"action": "mark_successful"}`
(only while the request is `accepted`).

## Push

Each new message is pushed to other members unless they muted the chat, turned
push off, or have that chat open. The payload `data` is
`{"type": "chat_message", "chat_id", "message_id", "seq"}`. Treat a push as a
hint to sync that chat, not as the message itself.

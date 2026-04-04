# Slack Personal OAuth Frontend Notes

This document describes the frontend contract for connecting a user's Slack account to CoChat.

## Goal

- The current web user clicks `Connect Slack`
- CoChat starts a Slack OAuth flow for that specific user
- Slack redirects back to CoChat
- CoChat stores a user-scoped Slack token for that web user

This is a personal connection flow, not a workspace-shared Slack installation flow.

## Current assumption

The backend assumes authentication already exists elsewhere.

For now, the backend can operate in two modes:

- Preferred: the frontend sends the current application user id in the header below
- Fallback: if the header is omitted, the backend uses `MASTER_USER_ID`

Header format:

```http
X-Cochat-User-Id: <app user id>
```

This is a temporary auth stub until real login/session middleware is wired in.

## Flow

### 1. Request Slack OAuth URL

Frontend request:

```http
GET /api/v1/integrations/slack/oauth-url
X-Cochat-User-Id: 123
```

Response:

```json
{
  "url": "https://slack.com/oauth/v2/authorize?...",
  "state": "<signed state>",
  "user_id": 123
}
```

Frontend action:

- Redirect the browser to `response.url`

### 2. Slack authorization

The user approves Slack access in Slack's OAuth screen.

### 3. Slack callback

Slack redirects the browser to:

```text
GET /api/v1/integrations/slack/callback?code=...&state=...
```

The backend verifies the signed `state`, restores the application user id, exchanges the OAuth code, and stores the Slack connection.

Success response:

```json
{
  "status": "ok",
  "integration_id": 1,
  "app_user_id": 123,
  "team_id": "T...",
  "team_name": "Workspace Name",
  "slack_user_id": "U...",
  "account_identifier": "T...:U..."
}
```

## Recommended frontend sequence

Use the Slack integration UI in this order:

1. Call `GET /api/v1/integrations/slack/connection`
2. If `connected` is `false`, call `GET /api/v1/integrations/slack/oauth-url`
3. Redirect the browser to the returned Slack OAuth URL
4. After Slack callback succeeds, call `GET /api/v1/integrations/slack/connection` again
5. Use the returned `integration_id` to call `GET /api/v1/integrations/slack/conversations`
6. Let the user choose one conversation from the returned list
7. Call `POST /api/v1/integrations/slack/sync`
8. Use the returned `raw_event_ids` as the backend-side confirmation that Slack messages were saved

This is the current end-to-end flow for:

- connect Slack
- check connection state
- browse accessible conversations
- store selected Slack messages as `raw_events`
- disconnect Slack later if needed

## Multi-account behavior

The current user can connect more than one Slack account.

- Each connection is stored as a separate `integration_id`
- The backend distinguishes connections with:
  - `integration_id`
  - `slack_team_id`
  - `slack_user_id`
- Raw events from different Slack accounts are separated by `integration_id`

This means the frontend should treat `connected=true` as:

- at least one Slack account is connected
- more Slack accounts can still be added

Recommended UI:

- show the connected Slack account list
- keep a `Connect another Slack account` action available
- let the user sync one account or all connected accounts

## Connection status check

Frontend request:

```http
GET /api/v1/integrations/slack/connection
X-Cochat-User-Id: 123
```

Response:

```json
{
  "user_id": 123,
  "connected": true,
  "integrations": [
    {
      "integration_id": 1,
      "account_identifier": "T...:U...",
      "account_name": "Workspace Name",
      "status": "active"
    }
  ]
}
```

If the frontend does not send `X-Cochat-User-Id`, the response is based on the configured `MASTER_USER_ID`.

## Disconnect one Slack connection

Frontend request:

```http
DELETE /api/v1/integrations/slack/connection/1
X-Cochat-User-Id: 123
```

Response:

```json
{
  "status": "ok",
  "user_id": 123,
  "integration_id": 1,
  "disconnected": true
}
```

This marks the Slack integration as inactive and removes the stored Slack token.

## List accessible Slack conversations

Frontend request:

```http
GET /api/v1/integrations/slack/conversations?integration_id=1&limit=100
X-Cochat-User-Id: 123
```

Response:

```json
{
  "integration_id": 1,
  "count": 2,
  "conversations": [
    {
      "channel_id": "C0123456789",
      "channel_type": "channel",
      "is_im": false,
      "is_mpim": false,
      "is_private": false,
      "display_name": "general",
      "name": "general"
    },
    {
      "channel_id": "D0123456789",
      "channel_type": "im",
      "is_im": true,
      "is_mpim": false,
      "is_private": false,
      "display_name": "Jane Doe",
      "name": null
    }
  ]
}
```

Use this response to render the user's selectable Slack conversation list in the UI.

## Sync one conversation into raw events

Frontend request:

```http
POST /api/v1/integrations/slack/sync
X-Cochat-User-Id: 123
Content-Type: application/json

{
  "integration_id": 1,
  "channel_id": "C0123456789",
  "limit": 30
}
```

Response:

```json
{
  "status": "ok",
  "integration_id": 1,
  "channel_id": "C0123456789",
  "processed_messages": 30,
  "raw_event_ids": [101, 102, 103],
  "provider_event_ids": [
    "C0123456789:1712345678.000100",
    "C0123456789:1712345679.000200"
  ]
}
```

This endpoint reads recent Slack messages with the connected user's token and stores the original messages as `raw_events`.

## Sync all connected Slack accounts

Frontend request:

```http
POST /api/v1/integrations/slack/sync-all
X-Cochat-User-Id: 123
Content-Type: application/json

{
  "conversation_limit": 50,
  "message_limit": 30
}
```

Optional:

- `integration_ids`: restrict syncing to selected Slack accounts only

Response:

```json
{
  "status": "ok",
  "user_id": 123,
  "integration_count": 2,
  "processed_messages": 84,
  "integrations": [
    {
      "integration_id": 1,
      "account_name": "Workspace A",
      "slack_team_id": "T...",
      "slack_user_id": "U...",
      "conversation_count": 12,
      "processed_messages": 40
    },
    {
      "integration_id": 2,
      "account_name": "Workspace B",
      "slack_team_id": "T...",
      "slack_user_id": "U...",
      "conversation_count": 9,
      "processed_messages": 44
    }
  ]
}
```

Use this endpoint when the product wants one refresh action to collect messages from all connected Slack accounts.

## Read merged raw events across connected Slack accounts

Frontend request:

```http
GET /api/v1/integrations/slack/raw-events?limit=100
X-Cochat-User-Id: 123
```

Optional:

- `integration_ids=1&integration_ids=2` to restrict the merged view to selected accounts

Response:

```json
{
  "user_id": 123,
  "count": 2,
  "raw_events": [
    {
      "id": 301,
      "integration_id": 1,
      "provider_event_id": "C...:1712345678.000100",
      "event_type": "message",
      "received_at": "2026-04-05T10:00:00+00:00",
      "account_name": "Workspace A",
      "account_identifier": "T...:U...",
      "slack_team_id": "T...",
      "slack_user_id": "U...",
      "payload": {
        "text": "hello"
      }
    }
  ]
}
```

This merged view is the main backend response for showing one user's messages from multiple Slack accounts in a single UI.

## How to verify external integration

You can verify this flow locally without opening a PR.

### What can be tested now

- Slack OAuth URL generation
- Slack account connection and token storage
- Slack conversation list loading
- Slack message pull into `raw_events`
- Slack disconnect flow

### What you do not need

- You do not need Slack Events API webhook setup for this flow
- You do not need `ngrok` for this flow

This path is based on:

- OAuth callback
- Slack Web API pull (`conversations.list`, `conversations.history`)
- local DB persistence

### End-to-end verification checklist

1. Start the backend with valid Slack env values and a working local DB
2. Call `GET /api/v1/integrations/slack/oauth-url`
3. Open the returned Slack authorization URL in a browser
4. Complete Slack authorization and confirm callback response contains:
   - `integration_id`
   - `team_id`
   - `slack_user_id`
5. Call `GET /api/v1/integrations/slack/connection` and confirm:
   - `connected: true`
   - one active integration exists
6. Call `GET /api/v1/integrations/slack/conversations?integration_id=...`
7. Confirm that Slack channels/DMs visible to the connected Slack user are returned
8. Call `POST /api/v1/integrations/slack/sync`
9. Confirm the response contains:
   - `processed_messages`
   - `raw_event_ids`
   - `provider_event_ids`
10. Query the DB and confirm rows exist in:
   - `integration_accounts`
   - `integration_tokens`
   - `raw_events`

### Suggested DB checks

Example checks after one successful sync:

```sql
select id, user_id, provider, account_identifier, account_name, status
from integration_accounts
where provider = 'slack'
order by id desc;
```

```sql
select id, integration_id, updated_at
from integration_tokens
order by id desc;
```

```sql
select id, provider, integration_id, provider_event_id, event_type, received_at
from raw_events
where provider = 'slack'
order by id desc
limit 20;
```

### If shared DB changes are not merged yet

You can still verify the external integration locally as long as your local DB schema matches the current branch.

That means:

- you can confirm OAuth works
- you can confirm Slack API pull works
- you can confirm `raw_event` persistence works

Even if the shared DB changes are not yet ready for merge.

## What the frontend must do

- Know the current application user id
- Send `X-Cochat-User-Id` when requesting the Slack OAuth URL, or rely on the backend `MASTER_USER_ID` fallback
- Redirect the browser to the returned Slack OAuth URL
- After callback success, refresh the connection status from the backend
- Load accessible conversations for the connected integration
- Ask the backend to sync the selected conversation into `raw_events`
- Allow the user to disconnect an integration from the UI

## What the frontend does not need to do

- It does not build the Slack `state` value
- It does not store the Slack access token
- It does not parse the Slack OAuth response directly

## Notes

- The backend currently stores a user-scoped Slack connection using:
  - application user id
  - Slack team id
  - Slack user id
- The DB schema now also stores:
  - `integration_accounts.slack_team_id`
  - `integration_accounts.slack_user_id`
- `account_identifier` is still kept as a compatibility key:

```text
<team_id>:<slack_user_id>
```

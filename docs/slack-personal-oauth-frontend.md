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

For now, the frontend must send the current application user id in the request header below:

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

## Connection status check

Frontend request:

```http
GET /api/v1/integrations/slack/connection
X-Cochat-User-Id: 123
```

Response:

```json
{
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

## What the frontend must do

- Know the current application user id
- Send `X-Cochat-User-Id` when requesting the Slack OAuth URL
- Redirect the browser to the returned Slack OAuth URL
- After callback success, refresh the connection status from the backend
- Load accessible conversations for the connected integration
- Ask the backend to sync the selected conversation into `raw_events`

## What the frontend does not need to do

- It does not build the Slack `state` value
- It does not store the Slack access token
- It does not parse the Slack OAuth response directly

## Notes

- The backend currently stores a user-scoped Slack connection using:
  - application user id
  - Slack team id
  - Slack user id
- Until a richer schema is added, the current account key is stored as:

```text
<team_id>:<slack_user_id>
```

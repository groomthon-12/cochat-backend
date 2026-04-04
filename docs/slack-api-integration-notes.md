# Slack API Integration Notes

이 문서는 현재 `develop` 브랜치 기준 Slack 연동 흐름을 정리한 보강 문서다.  
목표는 Slack 이벤트를 백엔드로 수신하고, 원본 payload를 `raw_events` 테이블에 저장하는 과정까지를 코드 기준으로 이해하고 재현할 수 있게 하는 것이다.

## 목적

- Slack 워크스페이스를 OAuth로 연동한다.
- Slack Events API webhook으로 메시지 이벤트를 수신한다.
- 수신한 원본 이벤트를 `raw_events` 테이블에 저장한다.
- 이후 정규화와 후속 파이프라인은 저장된 `raw_event`를 기준으로 처리한다.

## 현재 코드 기준 흐름

### 1. OAuth 설치

Slack OAuth 진입점은 아래 두 엔드포인트다.

- `GET /api/v1/integrations/slack/oauth-url`
- `GET /api/v1/integrations/slack/callback`

관련 파일:

- [app/api/endpoints/integrations.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/api/endpoints/integrations.py)
- [app/integrations/slack/client.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/integrations/slack/client.py)
- [app/repositories/integration_repository.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/repositories/integration_repository.py)

처리 순서:

1. `/integrations/slack/oauth-url` 에서 Slack OAuth URL을 만든다.
2. 사용자가 Slack 권한 승인 화면에서 설치를 진행한다.
3. Slack이 `/integrations/slack/callback` 으로 `code`를 전달한다.
4. 백엔드가 access token을 교환한다.
5. `integration_accounts`, `integration_tokens` 테이블에 연동 정보를 저장한다.

현재 구현은 Slack workspace를 `team_id` 기준으로 저장한다.

### 2. Webhook 수신

Slack 이벤트 수신 엔드포인트는 아래와 같다.

- `POST /api/v1/webhooks/slack`

관련 파일:

- [app/ingress/slack_webhook.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/ingress/slack_webhook.py)

처리 순서:

1. `X-Slack-Request-Timestamp`, `X-Slack-Signature` 헤더를 검증한다.
2. `url_verification` 요청이면 `challenge`를 반환한다.
3. bot 메시지는 무시한다.
4. 현재는 `message`, `app_mention` 이벤트만 계속 처리한다.
5. `team_id`로 연동된 Slack integration을 찾는다.
6. 원본 이벤트를 `raw_events` 테이블에 저장한다.
7. 저장된 `raw_event.id`를 기준으로 후속 정규화 단계로 넘긴다.

## raw_event 저장 구조

원본 이벤트 저장 함수는 아래 파일에 있다.

- [app/repositories/raw_event_repository.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/repositories/raw_event_repository.py)

현재 저장 필드는 다음과 같다.

- `provider`
- `integration_id`
- `provider_event_id`
- `event_type`
- `payload`
- `received_at`

즉 `raw_event`는 정규화 결과가 아니라 Slack이 보낸 원본 이벤트를 그대로 저장하는 테이블이다.

## 로컬 검증 과정

### 1. Postgres 준비

로컬 기본 포트 `5432`는 다른 프로젝트가 사용 중이어서, `cochat-backend` 전용 Postgres를 `55432` 포트로 분리해 사용했다.

예시 환경 변수:

```env
DATABASE_URL=postgresql://cochat:cochat_dev@localhost:55432/cochat
ASYNC_DATABASE_URL=postgresql+asyncpg://cochat:cochat_dev@localhost:55432/cochat
SLACK_SIGNING_SECRET=...
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
SLACK_REDIRECT_URI=http://localhost:8000/api/v1/integrations/slack/callback
SLACK_BOT_TOKEN=
```

### 2. 테이블 생성

모델 기준으로 아래 테이블이 생성되는 것을 확인했다.

- `integration_accounts`
- `integration_tokens`
- `raw_events`

### 3. Slack integration seed

Webhook 저장 검증을 위해 Slack workspace용 `integration_accounts` row를 먼저 준비했다.

예시:

```sql
insert into integration_accounts (provider, account_identifier, account_name, status, created_at)
values ('slack', 'T0AQT172J6S', 'Jnu', 'active', now());
```

### 4. 서명된 webhook 요청 테스트

Slack이 실제로 보내는 형식과 동일하게 서명된 요청을 만들어 `POST /api/v1/webhooks/slack` 으로 테스트했다.

검증 payload 예시:

```json
{
  "team_id": "T0AQT172J6S",
  "event": {
    "type": "message",
    "user": "U0AQVC3QYD8",
    "channel": "C0ARPB3PARE",
    "ts": "1775301391.654399",
    "text": "raw event save test"
  }
}
```

### 5. 저장 결과 확인

`raw_events` 테이블에서 아래 값이 실제로 저장되는 것을 확인했다.

- `provider = 'slack'`
- `integration_id = 1`
- `provider_event_id = '1775301391.654399'`
- `event_type = 'message'`

저장된 payload 예시:

```json
{
  "ts": "1775301391.654399",
  "text": "raw event save test",
  "type": "message",
  "user": "U0AQVC3QYD8",
  "channel": "C0ARPB3PARE"
}
```

즉 현재 구현 기준으로 `raw_event` 저장은 실제로 수행되는 것을 확인했다.

## 정리

- 현재 `develop` 기준 Slack 연동은 Slack OAuth + Slack Events API webhook 기반이다.
- OAuth를 통해 Slack workspace 연동 정보와 토큰을 저장한다.
- 실제 이벤트는 `POST /api/v1/webhooks/slack` 으로 수신한다.
- 메시지 이벤트는 `raw_events` 테이블에 원본 그대로 저장된다.
- 정규화와 후속 파이프라인은 저장된 `raw_event`를 기준으로 이어지는 구조다.

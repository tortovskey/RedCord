# RedCord Online Beta Backend

Run locally:

```powershell
docker compose -f docker-compose.backend.yml up --build
```

Endpoints:

- `GET /health`
- `POST /auth/request-code`
- `POST /auth/verify-code`
- `POST /sync/status`
- `POST /sync/pull`
- `POST /sync/push`

If SMTP is not configured, login codes are written to backend logs.

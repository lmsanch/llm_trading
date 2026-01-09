# API Endpoints Documentation

## Authentication Overview

All API endpoints require authentication via `X-API-Key` header **except** for health check endpoints.

### Public Endpoints (No Authentication Required)

These endpoints are exempt from authentication and can be accessed without an API key:

| Method | Path | Purpose | Notes |
|--------|------|---------|-------|
| GET | `/` | Root health check | Returns service status and pipeline state |
| GET | `/health` | Health check | Standard health endpoint (not implemented) |
| GET | `/api/health` | API health check | Standard API health endpoint (not implemented) |

### Protected Endpoints (Authentication Required)

All endpoints below require a valid API key in the `X-API-Key` header.

#### Research Endpoints

| Method | Path | Purpose | Additional Auth |
|--------|------|---------|-----------------|
| GET | `/api/research/prompt` | Get current research prompt | Middleware only |
| GET | `/api/research/current` | Get current research packs | Middleware only |
| GET | `/api/research/latest` | Get latest research from DB | `Depends(get_api_key)` |
| GET | `/api/research/history` | Get research history | Middleware only |
| GET | `/api/research/status` | Poll research job status | Middleware only |
| GET | `/api/research/{job_id}` | Get research job results | Middleware only |
| GET | `/api/research/report/{report_id}` | Get specific research report | Middleware only |
| POST | `/api/research/generate` | Generate new research | `Depends(get_api_key)` |
| POST | `/api/research/verify` | Mark research as verified | `Depends(get_api_key)` |

#### Graph & Data Endpoints

| Method | Path | Purpose | Additional Auth |
|--------|------|---------|-----------------|
| GET | `/api/graphs/latest` | Get latest knowledge graphs | Middleware only |
| GET | `/api/metrics/returns/latest` | Get latest 7-day returns | Middleware only |
| GET | `/api/data-package/latest` | Get complete data package | Middleware only |

#### Market Endpoints

| Method | Path | Purpose | Additional Auth |
|--------|------|---------|-----------------|
| GET | `/api/market/snapshot` | Get market snapshot | Middleware only |
| GET | `/api/market/metrics` | Get market metrics | Middleware only |
| GET | `/api/market/prices` | Get current prices | Middleware only |

#### PM Pitch Endpoints

| Method | Path | Purpose | Additional Auth |
|--------|------|---------|-----------------|
| GET | `/api/pitches/current` | Get current PM pitches | `Depends(get_api_key)` |
| GET | `/api/pitches/status` | Poll pitch job status | Middleware only |
| POST | `/api/pitches/generate` | Generate PM pitches | `Depends(get_api_key)` |
| POST | `/api/pitches/{id}/approve` | Approve a PM pitch | `Depends(get_api_key)` |

#### Council Endpoints

| Method | Path | Purpose | Additional Auth |
|--------|------|---------|-----------------|
| GET | `/api/council/current` | Get council decision | Middleware only |
| POST | `/api/council/synthesize` | Run council synthesis | `Depends(get_api_key)` |

#### Trading Endpoints

| Method | Path | Purpose | Additional Auth |
|--------|------|---------|-----------------|
| GET | `/api/trades/pending` | Get pending trades | `Depends(get_api_key)` |
| POST | `/api/trades/execute` | Execute trades | `Depends(get_api_key)` |
| GET | `/api/positions` | Get current positions | `Depends(get_api_key)` |
| GET | `/api/accounts` | Get account summaries | `Depends(get_api_key)` |

#### Conversation Endpoints (Legacy)

| Method | Path | Purpose | Additional Auth |
|--------|------|---------|-----------------|
| GET | `/api/conversations` | List all conversations | Middleware only |
| POST | `/api/conversations` | Create new conversation | `Depends(get_api_key)` |
| GET | `/api/conversations/{id}` | Get conversation | `Depends(get_api_key)` |
| POST | `/api/conversations/{id}/message` | Send message | `Depends(get_api_key)` |
| POST | `/api/conversations/{id}/message/stream` | Send message (streaming) | `Depends(get_api_key)` |

## Authentication Levels

### Level 1: Public (No Authentication)
- Only health check endpoints (`/`, `/health`, `/api/health`)
- Intended for monitoring and load balancer health checks

### Level 2: Middleware Protection
- All endpoints not explicitly public
- Validated by `APIKeyMiddleware` before reaching the route handler
- Returns 401 if X-API-Key header is missing or invalid

### Level 3: Explicit Dependency Protection
- Critical endpoints that modify state or trigger expensive operations
- Use `Depends(get_api_key)` for additional validation
- Includes: research generation, pitch generation, council synthesis, trade execution

## Security Considerations

1. **API Key Management**: API keys are configured via the `API_KEYS` environment variable as a comma-separated list
2. **Constant-Time Comparison**: API keys are compared using `secrets.compare_digest()` to prevent timing attacks
3. **No Key Logging**: API keys are never logged in application logs
4. **HTTPS Recommended**: Always use HTTPS in production to prevent key interception
5. **Header Format**: API key must be provided in the `X-API-Key` header

## Example Usage

### Public Endpoint (No Authentication)
```bash
curl http://localhost:8000/
```

### Protected Endpoint (With Authentication)
```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/research/latest
```

### Protected POST Endpoint
```bash
curl -X POST \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"models": ["perplexity"]}' \
  http://localhost:8000/api/research/generate
```

## Error Responses

### Missing API Key
```json
{
  "detail": "Missing API key. Please provide X-API-Key header."
}
```
HTTP Status: 401 Unauthorized

### Invalid API Key
```json
{
  "detail": "Invalid API key"
}
```
HTTP Status: 401 Unauthorized

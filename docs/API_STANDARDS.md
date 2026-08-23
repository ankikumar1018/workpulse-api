# WorkPulse API Standards — WI-1.2

This document defines conventions for the WorkPulse REST API. All endpoints must follow these patterns for consistency, maintainability and API-first contract alignment.

## 1. Versioning & Base URL

- **Versioning**: Path-based `/api/v1` from the beginning
- **Protocol**: HTTPS (required in production)
- **Base URL**: `{scheme}://{host}/api/v1`
- **Example**: `https://api.workpulse.example.com/api/v1/organizations`

---

## 2. HTTP Semantics

| Operation | Method | Semantics | Example |
|-----------|--------|-----------|---------|
| Fetch resource | GET | Safe, idempotent. Returns single resource or 404. | `GET /organizations/{id}` |
| List resources | GET | Safe, idempotent. Supports pagination/filtering. | `GET /organizations?status=active&limit=20` |
| Create resource | POST | Unsafe, non-idempotent. Returns 201 + location. | `POST /organizations` |
| Update resource (full) | PUT | Unsafe, idempotent. Replaces entire representation. | `PUT /organizations/{id}` |
| Partial update | PATCH | Unsafe, idempotent. Updates selected fields only. | `PATCH /organizations/{id}` |
| Delete resource | DELETE | Unsafe, idempotent. Returns 204 or 200. | `DELETE /organizations/{id}` |

---

## 3. Resource Naming

- **Collections**: Plural nouns. `GET /organizations`, `GET /projects`, `GET /workers`
- **Single resources**: Include ID. `GET /organizations/{id}`
- **Sub-resources**: Show hierarchy. `GET /organizations/{org_id}/projects`, `GET /projects/{project_id}/departments`
- **Actions**: Avoid verb endpoints. Use state transitions instead. ❌ `POST /messages/send` → ✅ `POST /schedules` (which queues communication)

---

## 4. Request & Response Envelope

### Standard Response Envelope (200, 201)

```json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Acme Corp",
    "slug": "acme-corp",
    "status": "active",
    "subscription_status": "active",
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-15T10:30:00Z"
  },
  "timestamp": "2026-08-23T14:22:30.123456Z"
}
```

### List Response (200)

```json
{
  "status": "success",
  "data": [
    { "id": "...", "name": "..." },
    { "id": "...", "name": "..." }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  },
  "timestamp": "2026-08-23T14:22:30.123456Z"
}
```

### Error Response (4xx, 5xx)

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {
        "field": "name",
        "issue": "Field required"
      },
      {
        "field": "status",
        "issue": "Invalid enum value"
      }
    ]
  },
  "timestamp": "2026-08-23T14:22:30.123456Z",
  "request_id": "req_abc123def456"
}
```

---

## 5. Error Codes & HTTP Status

| Error Code | HTTP | Meaning | Example |
|-----------|------|---------|---------|
| `VALIDATION_ERROR` | 400 | Request body/params invalid. Details field included. | Missing required field. |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication. | No Bearer token provided. |
| `FORBIDDEN` | 403 | Authenticated but not authorized for this resource. | Non-admin accessing admin endpoint. |
| `NOT_FOUND` | 404 | Resource does not exist. | Organization ID not found. |
| `CONFLICT` | 409 | Resource already exists or constraint violated. | Slug already in use. |
| `UNPROCESSABLE_ENTITY` | 422 | Business rule violation (e.g., invalid state transition). | Cannot cancel completed work. |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests from this client. | Retry-After header included. |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server failure. | Database connection lost. |
| `SERVICE_UNAVAILABLE` | 503 | Server temporarily unavailable. | Cloud Tasks unreachable. |

---

## 6. Pagination & Filtering

### Query Parameters

```
GET /organizations?status=active&limit=20&offset=0&sort=-created_at
```

- **`limit`** (int, default=20, max=100): Number of items to return
- **`offset`** (int, default=0): Number of items to skip
- **`sort`** (string): Field name, prefix with `-` for descending. `sort=-created_at` or `sort=name`
- **`status`**, **`name`**, etc.: Filter by field value (resource-specific)

### Response Pagination Metadata

```json
{
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

---

## 7. Timestamps & Timezone

- **Timestamps stored**: UTC in ISO 8601 format with timezone info. `2026-08-23T14:22:30Z`
- **Timezone handling**: Business entities (schedules, projects) retain an explicit timezone field (e.g., `timezone: "America/New_York"`)
- **Client responsibility**: Convert for display

---

## 8. Idempotency

For critical mutation operations (message sends, schedule activation), clients may provide an **`Idempotency-Key`** header:

```
POST /schedules
Idempotency-Key: sche_unique_key_12345
Content-Type: application/json

{
  "department_id": "550e8400-e29b-41d4-a716-446655440000",
  "template_id": "...",
  "start_time": "09:00",
  "end_time": "17:00",
  "interval_seconds": 3600
}
```

**Behavior:**
- First call: Creates resource, returns 201.
- Repeat calls (same key): Returns 200 + original response. No duplicate side effects.
- Different payload (same key): Returns 400 Bad Request.

---

## 9. Authorization & Authentication

### JWT Bearer Token

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token contents** (decoded):
```json
{
  "sub": "user_550e8400",
  "org_id": "org_12345",
  "role": "admin",
  "iat": 1692374550,
  "exp": 1692378150
}
```

### Authorization Rules

- **Public**: `/health`, `/docs`, `/openapi.json`
- **Protected**: All `/api/v1/*` endpoints require valid JWT
- **Scoped**: Most endpoints validate that the requesting user's `org_id` matches the resource's organization
- **Role-based** (MVP): `admin` only. Expansion to RBAC deferred to Phase 3.

---

## 10. Validation & Error Details

### Request Validation (Pydantic)

All request bodies use Pydantic for validation. Invalid requests return 400 with details:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {
        "field": "name",
        "issue": "ensure this value has at least 1 characters"
      },
      {
        "field": "status",
        "issue": "Input should be 'active' or 'archived'"
      }
    ]
  }
}
```

### Business Rule Validation (422)

Business logic violations return 422 Unprocessable Entity:

```json
{
  "status": "error",
  "error": {
    "code": "UNPROCESSABLE_ENTITY",
    "message": "Cannot transition work item from 'done' to 'open'"
  }
}
```

---

## 11. Request IDs & Correlation

Every response includes a **`request_id`** in error responses and server logs:

```json
{
  "status": "error",
  "error": {...},
  "request_id": "req_8f3e7c2a9d1b4f6e"
}
```

This allows administrators and developers to correlate requests, logs and delivery events across the entire system.

---

## 12. CORS & Security Headers

- **Allowed origins** (production): API domain only, no `*`
- **Credentials**: CORS cookies disabled for JWT auth
- **Security headers**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000` (production only)

---

## 13. API Documentation

- **OpenAPI schema**: Automatically generated from FastAPI code at `/openapi.json`
- **Swagger UI**: Interactive explorer at `/docs`
- **ReDoc**: Alternative at `/redoc`
- **Code-first approach**: OpenAPI derived from code, not vice versa

---

## 14. Versioning Strategy

### Future API Versions

When a breaking change is required:
1. Introduce new version path: `/api/v2`
2. Keep previous version active during transition period
3. Communicate deprecation timeline (e.g., 6+ months notice)
4. Do not silently break web or mobile clients

**Example timeline:**
- Month 1: Announce deprecation of `/api/v1/messages/send`
- Month 4: Release `/api/v2` with new pattern
- Month 7: Disable `/api/v1`

---

## 15. Representative Endpoint Examples

### Create Organization

```
POST /api/v1/organizations
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Acme Interior Design",
  "slug": "acme-corp"
}
```

**Response (201):**
```json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Acme Interior Design",
    "slug": "acme-corp",
    "status": "inactive",
    "subscription_status": null,
    "created_at": "2026-08-23T14:22:30Z",
    "updated_at": "2026-08-23T14:22:30Z"
  },
  "timestamp": "2026-08-23T14:22:30.123456Z"
}
```

### List Organizations (with pagination)

```
GET /api/v1/organizations?status=active&limit=20&offset=0
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Acme Corp",
      "slug": "acme-corp",
      "status": "active",
      "subscription_status": "active"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "has_more": false
  },
  "timestamp": "2026-08-23T14:22:30.123456Z"
}
```

### Update Organization (PATCH)

```
PATCH /api/v1/organizations/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "active"
}
```

**Response (200):** Updated organization object.

---

## Summary

- **Versioned path-based routing** (`/api/v1`)
- **Standard envelope** (status, data, pagination, timestamp)
- **Machine-readable errors** (code, message, details, request_id)
- **Pydantic validation** (clear field-level errors)
- **Idempotency support** for critical operations
- **JWT authentication** + organization scoping
- **Pagination** (limit, offset, total, has_more)
- **No verb endpoints** — state expressed through resource transitions
- **Future-proof versioning** — `/api/v2` when needed

---

**Next:** Implement representative CRUD endpoints for Organization and Project following these standards.

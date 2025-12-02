# OJS Sync Endpoints Update

## Summary

Updated all OJS sync endpoints to use per-journal OJS credentials instead of global configuration.

## Changes Made

### Updated Views (apps/integrations/views.py)

All OJS sync endpoints now:

1. **Require `journal_id` parameter** (via query params for GET, request body for POST/PUT/DELETE)
2. **Fetch journal-specific OJS credentials** (ojs_api_url, ojs_api_key, ojs_journal_id)
3. **Validate OJS configuration** before making requests
4. **Pass credentials to utility functions** that communicate with OJS

### Updated Endpoints

#### Reviews

- `GET /api/v1/integrations/ojs/reviews/?journal_id=<id>`
- `POST /api/v1/integrations/ojs/reviews/` (journal_id in body)
- `GET /api/v1/integrations/ojs/reviews/<review_id>/?journal_id=<id>`
- `PUT /api/v1/integrations/ojs/reviews/<review_id>/` (journal_id in body)
- `DELETE /api/v1/integrations/ojs/reviews/<review_id>/?journal_id=<id>`

#### Comments

- `GET /api/v1/integrations/ojs/comments/?journal_id=<id>`
- `POST /api/v1/integrations/ojs/comments/` (journal_id in body)
- `GET /api/v1/integrations/ojs/comments/<comment_id>/?journal_id=<id>`
- `PUT /api/v1/integrations/ojs/comments/<comment_id>/` (journal_id in body)
- `DELETE /api/v1/integrations/ojs/comments/<comment_id>/?journal_id=<id>`

#### Users

- `GET /api/v1/integrations/ojs/users/?journal_id=<id>`
- `POST /api/v1/integrations/ojs/users/` (journal_id in body)
- `GET /api/v1/integrations/ojs/users/<user_id>/?journal_id=<id>`
- `PUT /api/v1/integrations/ojs/users/<user_id>/` (journal_id in body)
- `DELETE /api/v1/integrations/ojs/users/<user_id>/?journal_id=<id>`

#### Articles

- `GET /api/v1/integrations/ojs/articles/?journal_id=<id>`
- `POST /api/v1/integrations/ojs/articles/` (journal_id in body)
- `GET /api/v1/integrations/ojs/articles/<article_id>/?journal_id=<id>`
- `PUT /api/v1/integrations/ojs/articles/<article_id>/` (journal_id in body)
- `DELETE /api/v1/integrations/ojs/articles/<article_id>/?journal_id=<id>`

#### Journals

- `GET /api/v1/integrations/ojs/journals/?journal_id=<id>`

#### Submissions

- `GET /api/v1/integrations/ojs/submissions/?journal_id=<id>`
- `POST /api/v1/integrations/ojs/submissions/` (journal_id in body)
- `PUT /api/v1/integrations/ojs/submissions/<submission_id>/` (journal_id in body)

### Error Responses

All endpoints now return appropriate error responses:

1. **Missing journal_id**: `400 Bad Request`

   ```json
   { "detail": "journal_id parameter is required." }
   ```

2. **Journal not found**: `404 Not Found`

   ```json
   { "detail": "Journal not found." }
   ```

3. **OJS not configured**: `400 Bad Request`

   ```json
   { "detail": "OJS not configured for this journal." }
   ```

4. **OJS API error**: `502 Bad Gateway`
   ```json
   { "detail": "Error message from OJS API" }
   ```

### Permission Changes

All OJS sync endpoints now require authentication:

```python
permission_classes = [IsAuthenticated]
```

## Usage Example

### Frontend/Client Usage

```javascript
// List reviews for a specific journal
const response = await fetch(
  "/api/v1/integrations/ojs/reviews/?journal_id=123",
  {
    headers: {
      Authorization: "Bearer <token>",
    },
  }
);

// Create a review
const response = await fetch("/api/v1/integrations/ojs/reviews/", {
  method: "POST",
  headers: {
    Authorization: "Bearer <token>",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    journal_id: 123,
    // ... other review data
  }),
});

// Update an article
const response = await fetch("/api/v1/integrations/ojs/articles/456/", {
  method: "PUT",
  headers: {
    Authorization: "Bearer <token>",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    journal_id: 123,
    // ... updated article data
  }),
});
```

## Benefits

1. **Multi-tenant support**: Each journal can connect to its own OJS instance
2. **Security**: API keys are scoped to journals, not globally accessible
3. **Flexibility**: Journals can have different OJS versions and configurations
4. **Clear error handling**: Better validation and error messages
5. **Consistent authentication**: All endpoints require user authentication

## Migration Notes

### For API Consumers

- **BREAKING CHANGE**: All OJS sync endpoints now require `journal_id` parameter
- Update all API calls to include the appropriate journal ID
- Ensure authentication tokens are included in all requests

### For Frontend Developers

- Update all OJS sync API calls to include `journal_id`
- Add journal selection UI before calling OJS sync endpoints
- Handle new error responses (missing journal_id, OJS not configured)

## Testing Checklist

- [ ] Test all endpoints with valid journal_id
- [ ] Test error handling for missing journal_id
- [ ] Test error handling for non-existent journal
- [ ] Test error handling for journals without OJS configured
- [ ] Test authentication requirement
- [ ] Test actual OJS API communication
- [ ] Update frontend components using these endpoints
- [ ] Update API documentation

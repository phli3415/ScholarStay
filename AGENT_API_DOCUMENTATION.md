# ScholarStay Agent API Documentation

## Overview

The Agent API provides endpoints for interacting with an AI assistant. Users can search and compare property listings through natural language queries. The system uses RAG (Retrieval Augmented Generation) technology and LangChain to handle complex queries and supports multi-turn conversations.

## Base URL

All API endpoints are prefixed with `/api/v1`

- **Development Server:** `http://127.0.0.1:8000/api/v1`

## Authentication

All Agent endpoints require user authentication. Use the **Bearer Token** authentication scheme with a **Firebase ID Token**.

```
Authorization: Bearer <YOUR_FIREBASE_ID_TOKEN>
```

---

## API Endpoints

### 1. 🔒 Chat with Agent (Streaming Response)

**Endpoint:** `POST /chat`

**Description:** Chat with the AI Agent and receive real-time streaming responses. The Agent automatically invokes appropriate tools (search listings, compare properties, etc.) based on user queries and returns analysis results.

**Request Body:**
```json
{
  "query": "I want to find a room close to the library with a price between $50-100",
  "session_id": "session_123456"
}
```

**Request Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | User's natural language query |
| session_id | string | Yes | Unique identifier for the chat session |

**Response:**
- **Status Code:** `200 OK`
- **Content-Type:** `text/plain` (streaming response)
- **Response Example:**
```
Let me search for rooms that match your criteria...
Found 3 matching listings:

1. Room A - $65/night
   Location: 500m from the library
   Features: Spacious, bright, WiFi provided

2. Room B - $75/night
   Location: 800m from the library
   Features: Private bathroom, kitchen access

3. Room C - $85/night
   Location: 200m from the library
   Features: Near campus, fully equipped

Based on your requirements, I recommend Room C...
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid authentication token
- `500 Internal Server Error` - Server error: `{"detail": "Chat error: ..."}`

**Usage Example (JavaScript):**
```javascript
const response = await fetch('/api/v1/chat', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${firebaseToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'I want a room close to the library',
    session_id: 'session_123456'
  })
});

// Handle streaming response
const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = new TextDecoder().decode(value);
  console.log(chunk);
}
```

---

### 2. 🔒 Get All User Chat Sessions

**Endpoint:** `GET /chat/sessions`

**Description:** Retrieve all chat sessions for the current user with pagination support.

**Query Parameters:**
| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| limit | integer | 20 | 1-100 | Number of sessions per page |
| offset | integer | 0 | ≥0 | Pagination offset |

**Request Example:**
```
GET /api/v1/chat/sessions?limit=10&offset=0
Authorization: Bearer <TOKEN>
```

**Success Response:**
- **Status Code:** `200 OK`
- **Content-Type:** `application/json`
- **Response Body:**
```json
{
  "sessions": [
    {
      "session_id": "session_123456",
      "title": "Room near library search",
      "created_at": "2026-01-20T10:30:00Z",
      "updated_at": "2026-01-20T15:45:00Z",
      "message_count": 5
    },
    {
      "session_id": "session_789012",
      "title": "Cheap student apartments",
      "created_at": "2026-01-19T14:20:00Z",
      "updated_at": "2026-01-19T16:00:00Z",
      "message_count": 3
    }
  ],
  "total": 15,
  "limit": 10,
  "offset": 0
}
```

**Response Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| sessions | array | List of chat sessions |
| sessions[].session_id | string | Unique session identifier |
| sessions[].title | string | Session title (auto-generated from first message) |
| sessions[].created_at | string | Session creation timestamp (ISO 8601 format) |
| sessions[].updated_at | string | Session last update timestamp |
| sessions[].message_count | integer | Total number of messages in the session |
| total | integer | Total number of user sessions |
| limit | integer | Pagination size |
| offset | integer | Pagination offset |

**Error Responses:**
- `401 Unauthorized` - Unauthenticated user
- `500 Internal Server Error` - `{"detail": "Failed to retrieve sessions: ..."}`

---

### 3. 🔒 Get Chat Session Details

**Endpoint:** `GET /chat/sessions/{session_id}`

**Description:** Retrieve complete details of a specific chat session, including all message records.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| session_id | string | Unique identifier for the chat session |

**Request Example:**
```
GET /api/v1/chat/sessions/session_123456
Authorization: Bearer <TOKEN>
```

**Success Response:**
- **Status Code:** `200 OK`
- **Content-Type:** `application/json`
- **Response Body:**
```json
{
  "session_id": "session_123456",
  "title": "Room near library search",
  "created_at": "2026-01-20T10:30:00Z",
  "updated_at": "2026-01-20T15:45:00Z",
  "messages": [
    {
      "role": "user",
      "content": "I want a room near the library with price between $50-100",
      "timestamp": "2026-01-20T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Let me search for you...",
      "tool_calls": [
        {
          "id": "call_abc123",
          "function": "search_listings",
          "args": "{\"location\": \"library\", \"price_min\": 50, \"price_max\": 100}"
        }
      ],
      "timestamp": "2026-01-20T10:30:05Z"
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "content": "{\"listings\": [{\"id\": 1, \"title\": \"Room A\", \"price\": 65}]}",
      "timestamp": "2026-01-20T10:30:06Z"
    },
    {
      "role": "assistant",
      "content": "Found 3 matching listings...",
      "timestamp": "2026-01-20T10:30:10Z"
    }
  ],
  "metadata": {
    "filtered_location": "library",
    "price_range": [50, 100]
  }
}
```

**Message Structure:**
| Field | Type | Description |
|-------|------|-------------|
| role | string | Message role: `user`/`assistant`/`tool` |
| content | string | Message content |
| timestamp | string | Message timestamp (ISO 8601 format) |
| tool_calls | array | (assistant only) List of tools invoked by Agent |
| tool_calls[].id | string | Unique ID of the tool call |
| tool_calls[].function | string | Function name invoked |
| tool_calls[].args | string | Function arguments (JSON string) |
| tool_call_id | string | (tool only) Corresponding tool call ID |
| metadata | object | Session metadata (e.g., filter conditions) |

**Error Responses:**
- `401 Unauthorized` - Unauthenticated user
- `404 Not Found` - Session not found or access denied
- `500 Internal Server Error` - `{"detail": "Failed to retrieve session: ..."}`

---

### 4. 🔒 Delete Chat Session

**Endpoint:** `DELETE /chat/sessions/{session_id}`

**Description:** Delete a specified chat session and all its message records.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| session_id | string | Unique identifier of the session to delete |

**Request Example:**
```
DELETE /api/v1/chat/sessions/session_123456
Authorization: Bearer <TOKEN>
```

**Success Response:**
- **Status Code:** `200 OK`
- **Content-Type:** `application/json`
- **Response Body:**
```json
{
  "message": "Session deleted successfully"
}
```

**Error Responses:**
- `401 Unauthorized` - Unauthenticated user
- `404 Not Found` - Session not found or access denied
- `500 Internal Server Error` - `{"detail": "Failed to delete session: ..."}`

**Usage Example (JavaScript):**
```javascript
const response = await fetch('/api/v1/chat/sessions/session_123456', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${firebaseToken}`
  }
});

if (response.ok) {
  console.log('Session deleted successfully');
}
```

---

## Agent Tool Capabilities

The Agent automatically invokes the following tools based on user queries:

| Tool Name | Function | Example Query |
|-----------|----------|----------------|
| `search_listings` | Search listings by criteria | "Find a room close to campus" |
| `compare_listings` | Compare multiple listings | "Compare the pros and cons of these two rooms" |
| `get_listing_details` | Get listing details | "Tell me detailed info about Room A" |
| `structured_search` | Structured property search | "Find houses with 2+ bedrooms" |
| `advanced_filter` | Advanced filtering | "Find the cheapest room near the library" |
| `compare_listings_by_address` | Compare listings by address | "Compare listings on different streets" |

---

## Error Handling

### Generic Error Response Format

All errors follow this format:

```json
{
  "detail": "Error description message"
}
```

### Common Error Codes

| Status Code | Description | Common Causes |
|-------------|-------------|---------------|
| 401 | Unauthorized | Expired or invalid Firebase token |
| 404 | Not Found | Resource not found or access denied |
| 500 | Internal Server Error | Server error or database exception |

---

## Best Practices

### 1. Session Management
- Create a new `session_id` for each independent user conversation
- Use UUID or timestamp as `session_id`
- Example: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

### 2. Streaming Handling
- Use streaming responses for long-running queries
- Display the Agent's reasoning process and results in real-time
- Avoid long HTTP timeouts

### 3. Error Recovery
- Implement retry mechanisms for temporary network errors
- Save user input to allow resubmission
- Display user-friendly error messages

### 4. Performance Optimization
- Cache frequently queried results
- Use pagination to limit the number of sessions loaded at once
- Periodically clean up old expired sessions

---

## Example Workflow

### Complete Chat Interaction Flow

```
1. User logs in and obtains Firebase ID Token
   ↓
2. Frontend generates unique session_id
   ↓
3. User enters query: "I need a room near the library for $60 per night"
   ↓
4. Call POST /chat endpoint to get streaming response
   - Agent analyzes the query
   - Automatically invokes search_listings tool
   - Returns search results
   ↓
5. Messages automatically saved to database with tool call records
   ↓
6. User can view chat history via GET /chat/sessions
   ↓
7. To delete a session, call DELETE /chat/sessions/{session_id}
```

---

## FAQ

**Q: When does the streaming response end?**
A: The stream closes automatically when the Agent completes analysis and generates the final response. The frontend should monitor the stream's `done` status.

**Q: How do I get information about the specific tools invoked by the Agent?**
A: Call `GET /chat/sessions/{session_id}` to get complete session details. The `tool_calls` field in messages contains all tool invocation records.

**Q: How long is session data retained?**
A: Users can manually delete sessions. The system does not automatically clean up historical data.

**Q: Can I edit messages that have been sent?**
A: Message editing is not supported. You can delete an entire session and start a new conversation.

---

## Changelog

### v1.0.0 (2026-01-23)
- Initial release of Agent API
- Support for streaming chat responses
- Complete session management functionality
- Support for 6 query tools

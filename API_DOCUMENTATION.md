
# ScholarStay API Documentation

This document provides a detailed overview of the ScholarStay backend API. It is intended for front-end developers who will be consuming these endpoints.

## Base URL

All API endpoints are prefixed with `/api/v1`.

- **Development Server:** `http://127.0.0.1:8000/api/v1`

## Authentication

Many endpoints require user authentication. This is handled using a **Bearer Token** authentication scheme. The token is a **Firebase ID Token** obtained from the Firebase client-side SDK upon user login.

To authenticate a request, include an `Authorization` header:

```
Authorization: Bearer <YOUR_FIREBASE_ID_TOKEN>
```

Endpoints that require authentication are marked with a 🔒 symbol.

---

## 1. Users API

Handles user registration and profile management.

### 1.1 🔒 Register User

- **Endpoint:** `POST /user/register`
- **Description:** Registers a new user in the application's local database after they have been authenticated by Firebase. This endpoint should be called once after the user's first login.
- **Request Body:**
  ```json
  {
    "username": "your_desired_username"
  }
  ```
- **Success Response:** `201 Created`
  ```json
  {
    "id": 1,
    "firebase_uid": "firebase_user_id_string",
    "username": "your_desired_username",
    "created_at": "2023-10-27T10:00:00Z",
    "updated_at": "2023-10-27T10:00:00Z"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `409 Conflict`: User with this Firebase UID is already registered.
  - `422 Unprocessable Entity`: Username is missing.

### 1.2 🔒 Get My Profile

- **Endpoint:** `GET /user/me`
- **Description:** Retrieves the profile information for the currently authenticated user.
- **Request Body:** None.
- **Success Response:** `200 OK`
  ```json
  {
    "id": 1,
    "firebase_uid": "firebase_user_id_string",
    "username": "your_username",
    "created_at": "2023-10-27T10:00:00Z",
    "updated_at": "2023-10-27T10:00:00Z"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `404 Not Found`: User is not registered in the local database.

### 1.3 🔒 Update My Profile

- **Endpoint:** `PUT /user/me`
- **Description:** Updates the username for the currently authenticated user.
- **Request Body:**
  ```json
  {
    "username": "your_new_username"
  }
  ```
- **Success Response:** `200 OK`
  ```json
  {
    "id": 1,
    "firebase_uid": "firebase_user_id_string",
    "username": "your_new_username",
    "created_at": "2023-10-27T10:00:00Z",
    "updated_at": "2023-10-27T10:05:00Z"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `404 Not Found`: User not found.
  - `422 Unprocessable Entity`: New username is missing.

### 1.4 🔒 Delete My Account

- **Endpoint:** `DELETE /user/me`
- **Description:** Deletes the user's account from the local database. **Note:** This does not delete the user from Firebase Authentication.
- **Request Body:** None.
- **Success Response:** `200 OK`
  ```json
  {
    "message": "User deleted successfully"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `404 Not Found`: User not found.

---

## 2. Houses API

Handles house listing creation, retrieval, and management.

### 2.1 🔒 Create House Listing

- **Endpoint:** `POST /houses/`
- **Description:** Creates a new house listing. The owner is automatically set to the current user. This endpoint expects `multipart/form-data`.
- **Form Data:**
  - `house_data_str` (string, required): A JSON string containing house details.
    ```json
    {
      "province": "Ontario",
      "city": "Waterloo",
      "street": "University Avenue West",
      "house_number": "123",
      "monthly_rent": 1000.50,
      "distance_to_university": 1.2,
      "has_kitchen": true,
      "has_washer": true,
      "has_parking": false,
      "is_rented": false,
      "description": "A cozy place near the university."
    }
    ```
  - `image` (file, optional): An image file for the listing.
- **Success Response:** `201 Created` (Returns the newly created house object)
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `422 Unprocessable Entity`: `house_data_str` contains invalid data.

### 2.2 🔒 Update House Listing

- **Endpoint:** `PUT /houses/{house_id}`
- **Description:** Updates an existing house listing. The user must be the owner of the listing.
- **Path Parameter:**
  - `house_id` (integer, required): The ID of the house to update.
- **Form Data:**
  - `house_data_str` (string, required): A JSON string containing the fields to update.
    ```json
    {
      "monthly_rent": 1100.00,
      "description": "Updated description with new details."
    }
    ```
  - `image` (file, optional): A new image file to replace the old one.
- **Success Response:** `200 OK` (Returns the updated house object)
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `403 Forbidden`: User is not the owner of the house.
  - `404 Not Found`: House with the given ID not found.

### 2.3 🔒 Delete House Listing

- **Endpoint:** `DELETE /houses/{house_id}`
- **Description:** Deletes a house listing. The user must be the owner.
- **Path Parameter:**
  - `house_id` (integer, required): The ID of the house to delete.
- **Success Response:** `200 OK`
  ```json
  {
    "message": "House deleted successfully"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `403 Forbidden`: User is not the owner of the house.
  - `404 Not Found`: House not found.

### 2.4 Get House by ID

- **Endpoint:** `GET /houses/{house_id}`
- **Description:** Retrieves a single house listing by its ID. Publicly accessible.
- **Path Parameter:**
  - `house_id` (integer, required): The ID of the house.
- **Success Response:** `200 OK` (Returns the house object)
- **Error Responses:**
  - `404 Not Found`: House not found.

### 2.5 Get All Houses (Paginated)

- **Endpoint:** `GET /houses/`
- **Description:** Retrieves a paginated list of all house listings. Publicly accessible.
- **Query Parameters:**
  - `limit` (integer, optional, default: 20): Number of results per page.
  - `offset` (integer, optional, default: 0): Number of results to skip.
- **Success Response:** `200 OK` (Returns a list of house objects)

### 2.6 Get Houses by Owner

- **Endpoint:** `GET /houses/owner/{owner_id}`
- **Description:** Retrieves all houses listed by a specific owner. Publicly accessible.
- **Path Parameter:**
  - `owner_id` (integer, required): The ID of the owner.
- **Success Response:** `200 OK` (Returns a list of house objects)

### 2.7 Search and Filter Houses

- **Endpoint:** `GET /houses/search/list`
- **Description:** A flexible search endpoint to find houses based on various criteria. All parameters are optional.
- **Query Parameters:** `province`, `city`, `max_rent`, `min_rent`, `has_kitchen`, `has_washer`, `has_parking`, `is_rented`, `max_distance`, `limit`, `offset`.
- **Success Response:** `200 OK` (Returns a list of matching house objects)

---

## 3. Bookmarks API

Handles user bookmarks for house listings. All endpoints are secure and user-centric.

### 3.1 🔒 Add a Bookmark

- **Endpoint:** `POST /bookmarks/`
- **Description:** Adds a house to the current user's bookmarks.
- **Request Body:**
  ```json
  {
    "house_id": 123
  }
  ```
- **Success Response:** `201 Created`
  ```json
  {
    "id": 1,
    "user_id": 42,
    "house_id": 123,
    "created_at": "2023-10-27T11:00:00Z"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `404 Not Found`: House with the given ID not found.
  - `409 Conflict`: Bookmark for this house already exists.

### 3.2 🔒 Get My Bookmarks

- **Endpoint:** `GET /bookmarks/me/`
- **Description:** Retrieves all bookmarks for the currently authenticated user, with associated house details included.
- **Success Response:** `200 OK`
  ```json
  [
    {
      "id": 1,
      "user_id": 42,
      "house_id": 123,
      "created_at": "2023-10-27T11:00:00Z",
      "house": {
        "id": 123,
        "province": "Ontario",
        "city": "Waterloo",
        "monthly_rent": 1000.5
      }
    }
  ]
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.

### 3.3 🔒 Check if Bookmarked

- **Endpoint:** `GET /bookmarks/check/{house_id}/`
- **Description:** Checks if a specific house is bookmarked by the current user.
- **Path Parameter:**
  - `house_id` (integer, required): The ID of the house to check.
- **Success Response:** `200 OK`
  ```json
  {
    "is_bookmarked": true
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.

### 3.4 🔒 Remove a Bookmark

- **Endpoint:** `DELETE /bookmarks/by-house/{house_id}/`
- **Description:** Removes a bookmark for the current user based on the house ID.
- **Path Parameter:**
  - `house_id` (integer, required): The ID of the house to un-bookmark.
- **Success Response:** `204 No Content`
- **Error Responses:**
  - `401 Unauthorized`: Invalid or missing token.
  - `404 Not Found`: Bookmark for this house was not found.

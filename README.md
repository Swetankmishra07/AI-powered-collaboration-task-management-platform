# 🚀 Smart Task Management API

A production-style, beginner-friendly REST API built with **Python**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0**, **MySQL**, **JWT Authentication**, and **Pytest**.

This project demonstrates core backend concepts including **User Registration**, **Password Hashing (Bcrypt)**, **Stateless JWT Authentication**, and **Ownership-Based Authorization Controls**.

---

## 🎯 Problem Statement & Features

Modern applications require secure API endpoints where users can log in and manage personal resources. 

### Key Features
1. **User Authentication**:
   - Registration with email validation and unique constraints.
   - Secure password hashing using **Bcrypt** with random salt.
   - JWT Access Token generation (`HS256`) with expiration timestamps.
2. **Ownership-Based Authorization**:
   - Users can only access, update, or delete tasks that **they own**.
   - Attempting to access another user's task returns HTTP `403 Forbidden`.
3. **Task CRUD Operations**:
   - `POST /tasks`: Create a new task (enforces status enum: `pending`, `in_progress`, `completed`).
   - `GET /tasks`: Fetch only tasks belonging to the current logged-in user.
   - `GET /tasks/{id}`: Fetch single task details with ownership verification.
   - `PUT /tasks/{id}`: Update task title, description, or status with ownership verification.
   - `DELETE /tasks/{id}`: Delete task with ownership verification (HTTP `204 No Content`).
4. **Interactive Documentation**:
   - Built-in **Swagger UI** (`/docs`) with Bearer Token `Authorize` button.
   - **ReDoc** interface (`/redoc`).
5. **Automated Testing**:
   - Complete unit and integration test suite using **Pytest** and `TestClient`.

---

## 🛠️ Technology Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI 0.110+
- **Data Validation & Schemas**: Pydantic v2 & `email-validator`
- **Database & ORM**: MySQL / SQLite fallback with SQLAlchemy 2.0 ORM
- **Database Driver**: PyMySQL & Cryptography
- **Security & Tokens**: PyJWT & Bcrypt
- **Testing**: Pytest & HTTPX TestClient

---

## 📁 Project Architecture & Folder Structure

```
smart_task_management_api/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app initialization & router mounting
│   ├── core/
│   │   ├── config.py          # Settings loaded from environment variables (.env)
│   │   └── security.py        # Password hashing & JWT encode/decode utilities
│   ├── database/
│   │   ├── database.py        # SQLAlchemy engine, SessionLocal, & get_db dependency
│   │   └── models.py          # User & Task ORM database models
│   ├── schemas/
│   │   ├── user.py            # User registration & response Pydantic DTOs
│   │   ├── auth.py            # Login request & token response Pydantic DTOs
│   │   └── task.py            # Task CRUD request/response Pydantic DTOs
│   ├── routes/
│   │   ├── auth.py            # /auth/register and /auth/login endpoints
│   │   └── tasks.py           # /tasks CRUD API endpoints
│   ├── services/
│   │   ├── auth_service.py    # Registration & login business logic
│   │   └── task_service.py    # Task CRUD business rules & ownership validation
│   ├── dependencies/
│   │   └── auth.py            # get_current_user security dependency
│   └── exceptions/
│       └── handlers.py        # Custom global HTTP & validation exception handlers
├── tests/
│   ├── test_auth.py           # Registration & authentication test cases
│   └── test_tasks.py          # Task CRUD & authorization boundary test cases
├── .env                       # Local environment variables (Git ignored)
├── .env.example               # Shared environment configuration template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🗄️ Database Design (Entity-Relationship)

```
+------------------------------------+          +------------------------------------+
|               USERS                |          |               TASKS                |
+------------------------------------+          +------------------------------------+
| id (PK, Int, AutoIncrement)        | 1      * | id (PK, Int, AutoIncrement)        |
| username (String, Unique, Index)   |----------| title (String, Index, Not Null)    |
| email (String, Unique, Index)      |          | description (Text, Nullable)       |
| password_hash (String, Not Null)   |          | status (String, Default: 'pending')|
| created_at (DateTime)              |          | user_id (FK -> users.id, Cascade)  |
+------------------------------------+          | created_at (DateTime)              |
                                                | updated_at (DateTime)              |
                                                +------------------------------------+
```

---

## 🔄 Complete Data Flow Diagram

```
CLIENT
  │
  │ 1. HTTP Request (e.g. GET /tasks/5 + Authorization: Bearer <JWT>)
  ▼
FASTAPI ROUTE (app/routes/tasks.py)
  │
  │ 2. Extracts Bearer Token -> Calls get_current_user Dependency
  ▼
JWT SECURITY (app/dependencies/auth.py & app/core/security.py)
  │
  │ 3. Decodes JWT -> Verifies Signature & Expiration -> Fetches User from DB
  ▼
PYDANTIC VALIDATION (app/schemas/task.py)
  │
  │ 4. Validates request body & parameters
  ▼
SERVICE LAYER (app/services/task_service.py)
  │
  │ 5. Enforces Ownership Rule: task.user_id == current_user.id
  │    If User ID doesn't match -> Raises 403 Forbidden Exception
  ▼
SQLALCHEMY ORM (app/database/database.py & app/database/models.py)
  │
  │ 6. Executes parameterized SQL query against MySQL / SQLite
  ▼
PYDANTIC SERIALIZATION (app/schemas/task.py)
  │
  │ 7. Converts ORM object into sanitized UserResponse / TaskResponse DTO
  ▼
CLIENT (HTTP 200 OK + JSON Payload)
```

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description | Auth Required | Status Code |
|---|---|---|---|---|
| `GET` | `/` | Health check endpoint | No | `200 OK` |
| `POST` | `/auth/register` | Register a new user | No | `201 Created` |
| `POST` | `/auth/login` | Login & receive JWT Bearer token | No | `200 OK` |
| `POST` | `/tasks` | Create a new task | Yes (Bearer) | `201 Created` |
| `GET` | `/tasks` | Get all tasks for current user | Yes (Bearer) | `200 OK` |
| `GET` | `/tasks/{id}` | Get specific task by ID | Yes (Bearer) | `200 OK` / `403` / `404` |
| `PUT` | `/tasks/{id}` | Update task details or status | Yes (Bearer) | `200 OK` / `403` / `404` |
| `DELETE` | `/tasks/{id}` | Delete task | Yes (Bearer) | `204 No Content` / `403` / `404` |

---

## 🚦 HTTP Status Codes Explained

- `200 OK`: Successful retrieval or update.
- `201 Created`: Resource successfully created (User registration or Task creation).
- `204 No Content`: Resource successfully deleted. No response body returned.
- `400 Bad Request`: Invalid request data (e.g. registering with an email that already exists).
- `401 Unauthorized`: Missing, invalid, or expired JWT token, or incorrect login credentials.
- `403 Forbidden`: Authenticated user is trying to access a task owned by another user.
- `404 Not Found`: Requested resource ID does not exist in the database.
- `422 Unprocessable Entity`: Input payload failed Pydantic schema validation.

---

## 💻 Setup & Execution Guide

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Create Virtual Environment
```bash
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```env
PROJECT_NAME="Smart Task Management API"
VERSION="1.0.0"
DATABASE_URL="mysql+pymysql://root:password@localhost:3306/task_db"
SECRET_KEY="super-secret-key-change-this-in-production-123456789"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```
*(Note: If a local MySQL server is not running on port 3306, the application automatically falls back to SQLite `task_db.sqlite3` for zero-friction testing).*

### 5. Run API Development Server
```bash
uvicorn app.main:app --reload
```
Access the application at `http://127.0.0.1:8000`.

### 6. Run Automated Tests
```bash
pytest -v
```

---

## 📚 Interactive Swagger UI Testing (`/docs`)

1. Open `http://127.0.0.1:8000/docs` in your web browser.
2. Call `POST /auth/register` to register a new user.
3. Call `POST /auth/login` to obtain an `access_token`.
4. Click the **Authorize 🔓** button at the top right of Swagger UI.
5. Paste your JWT access token and click **Authorize**.
6. Now execute any protected `/tasks` endpoint directly from the browser!

---

## 🎯 Backend Technical Interview Q&A Guide

### Q1: What problem does this project solve?
**Answer**: It solves the problem of secure, multi-tenant resource management by enforcing stateless authentication via JWT and granular ownership authorization at the service layer so users can only access their own data.

### Q2: Why choose FastAPI over Flask or Django?
**Answer**: FastAPI offers automatic Pydantic data validation, high performance built on ASGI/Starlette, built-in dependency injection (`Depends`), and automatic OpenAPI documentation without third-party plugins.

### Q3: What is the difference between Authentication and Authorization?
**Answer**:
- **Authentication**: Answers *"Who are you?"* (e.g. Verifying email and password, generating JWT).
- **Authorization**: Answers *"What are you allowed to do?"* (e.g. Verifying `task.user_id == current_user.id`).

### Q4: How does `get_current_user` work in FastAPI?
**Answer**: `get_current_user` is a FastAPI dependency using `Depends()`. It reads the `Authorization: Bearer <token>` header, decodes the JWT using our `SECRET_KEY`, validates token expiration, queries the database for the matching User ID, and injects the authenticated `current_user` object directly into route handlers.

### Q5: Why store hashed passwords instead of plain text?
**Answer**: Storing plain-text passwords exposes user credentials if the database is breached. We use **Bcrypt**, a one-way salted hashing algorithm. Salt prevents Rainbow Table attacks, and one-way hashing ensures original passwords cannot be recovered even if the database is leaked.

### Q6: Why separate Routes, Services, Schemas, and Models?
**Answer**: To maintain **Separation of Concerns**:
- **Routes**: Handle HTTP concerns (paths, verbs, status codes).
- **Services**: Contain pure business logic and authorization rules.
- **Schemas (Pydantic)**: Define API input/output validation contracts.
- **Models (SQLAlchemy)**: Define database tables and ORM persistence.

---

## 🌟 Future Improvements
- Add refresh tokens for long-lived sessions.
- Implement pagination (`limit` & `offset`) for `GET /tasks`.
- Add task filtering by status (`GET /tasks?status=completed`).
- Containerize application with Docker & Docker Compose.

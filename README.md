# 🚀 Smart Task Management API

A production-oriented REST API built with **Python**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0**, **PostgreSQL**, **Alembic**, **JWT Authentication**, and **Pytest**.

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
  - `POST /tasks`: Create a new task with controlled status and priority values.
  - `GET /tasks`: Fetch authorized tasks with pagination, filtering, sorting, and search.
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
- **Database & ORM**: PostgreSQL target with SQLAlchemy 2.0 ORM and Alembic migrations
- **Database Driver**: Psycopg for PostgreSQL; PyMySQL remains available for explicit legacy compatibility
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
  │ 6. Executes parameterized SQL query against the explicitly configured database
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
| `GET` | `/health/database` | Configured database connectivity check | No | `200 OK` / `503` |
| `GET` | `/health/redis` | Optional Redis cache connectivity check | No | `200 OK` / `503` |
| `POST` | `/auth/register` | Register a new user | No | `201 Created` |
| `POST` | `/auth/login` | Login & receive JWT Bearer token | No | `200 OK` |
| `POST` | `/auth/refresh` | Rotate a refresh token | No | `200 OK` / `401` |
| `POST` | `/auth/logout` | Revoke a refresh token | No | `204 No Content` |
| `GET` | `/users` | List users | Manager/Admin | `200 OK` / `403` |
| `PATCH` | `/users/{id}/role` | Change a user role | Admin | `200 OK` / `403` / `404` |
| `POST` | `/teams` | Create a team | Yes (Bearer) | `201 Created` |
| `GET` | `/teams` | List accessible teams | Yes (Bearer) | `200 OK` |
| `GET/PATCH/DELETE` | `/teams/{id}` | Access or manage a team | Scoped | `200` / `403` / `404` |
| `GET/POST` | `/teams/{id}/members` | List or add team members | Scoped | `200` / `201` / `403` |
| `DELETE` | `/teams/{id}/members/{user_id}` | Remove a team member | Team manager/owner/Admin | `204` / `403` |
| `POST` | `/projects` | Create a project in a managed team | Team manager/owner/Admin | `201 Created` |
| `GET` | `/projects` | List accessible projects | Yes (Bearer) | `200 OK` |
| `GET/PATCH/DELETE` | `/projects/{id}` | Access or manage a project | Scoped | `200` / `403` / `404` |
| `GET/POST` | `/projects/{id}/members` | List or add project members | Scoped | `200` / `201` / `403` |
| `DELETE` | `/projects/{id}/members/{user_id}` | Remove a project member | Project/team manager/Admin | `204` / `403` |
| `POST` | `/tasks/{id}/comments` | Create a task comment | Task scope | `201 Created` |
| `GET` | `/tasks/{id}/comments` | List task comments | Task scope | `200 OK` / `403` |
| `PATCH` | `/comments/{id}` | Edit a comment | Author/Manager/Admin | `200 OK` / `403` |
| `DELETE` | `/comments/{id}` | Delete a comment | Author/Manager/Admin | `204` / `403` |
| `GET` | `/tasks/{id}/activity` | View task activity history | Task scope | `200 OK` / `403` |
| `POST` | `/tasks` | Create a new task | Yes (Bearer) | `201 Created` |
| `GET` | `/tasks` | List authorized tasks with query filters | Yes (Bearer) | `200 OK` |
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
ENVIRONMENT="development"
DATABASE_URL="postgresql+psycopg://task_user:password@localhost:5432/task_db"
# Use a randomly generated secret with at least 32 characters.
SECRET_KEY="replace-with-a-long-random-secret"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

The application does not silently switch databases. Database configuration or connection errors stop startup and must be fixed explicitly.

Tables are not created when the application module is imported. Apply the versioned schema explicitly:
```bash
alembic upgrade head
```

### 5. Run API Development Server
```bash
uvicorn app.main:app --reload
```
Access the application at `http://127.0.0.1:8000`.

### 6. Run Automated Tests
```bash
pytest -v
```

## 🐳 Docker Compose

Docker Compose runs the API with PostgreSQL and Redis. It does not use or modify `task_db.sqlite3`.

1. Copy `.env.example` to `.env` and replace the database password and `SECRET_KEY` placeholders with local values. Keep `.env` out of version control.
2. Build and start the services:
```bash
docker compose up --build -d
```
3. Apply the versioned migrations explicitly from the API container:
```bash
docker compose exec api alembic upgrade head
```
4. Check service status at `http://127.0.0.1:8000/health/database` and open Swagger at `http://127.0.0.1:8000/docs`.
5. Stop the services without deleting persistent PostgreSQL or attachment volumes:
```bash
docker compose down
```

The API image runs as a non-root user. PostgreSQL data uses the `postgres_data` volume, and local attachment content uses the `attachment_data` volume mounted at `/app/storage/attachments`. Redis remains the optional application cache dependency, while Compose provides it for the containerized environment. AI remains disabled unless explicitly configured through environment variables. Tests continue to run locally with their isolated SQLite fixture and do not require Docker, PostgreSQL, Redis, or an external AI provider.

## 🚀 Deployment Readiness

This repository provides a provider-neutral container and Compose baseline, not an automatic cloud deployment. Production values must be supplied through the environment; replace the `SECRET_KEY` and `POSTGRES_PASSWORD` placeholders and set `ENVIRONMENT=production` before startup. Configure `DATABASE_URL`, `REDIS_URL`, `CORS_ALLOWED_ORIGINS`, JWT settings, AI settings, background-job settings, and attachment settings explicitly for the target environment. Never commit `.env` or credentials.

Build and run the image with the existing command:
```bash
docker build --file Dockerfile --tag smart-task-management-api:production .
docker run --rm --env-file .env -p 8000:8000 smart-task-management-api:production
```

Run migrations as a deliberate release operation against PostgreSQL; application startup does not reset or create the schema:
```bash
docker run --rm --env-file .env smart-task-management-api:production alembic upgrade head
```

`/health/database` verifies configured database connectivity and is used by the image and Compose healthchecks. `/health/redis` reports optional Redis status. The in-process background worker is controlled by `BACKGROUND_JOBS_ENABLED`; run it only where one process owns the work, or use the existing architecture with an operational process model that prevents duplicate workers. WebSocket broadcasting is process-local, so multiple API instances need a shared messaging design in a future phase. Local attachment storage is suitable for development or a single persistent instance only; use a durable shared storage provider behind `StorageProvider` before scaling across instances. AI remains opt-in and requires provider configuration.

GitHub Actions validates dependencies, the SQLite pytest suite, Alembic upgrade/downgrade, Compose syntax, and the Docker build on pushes and pull requests targeting `main`. It does not deploy or publish images.

## ✅ Continuous Integration

GitHub Actions runs on pushes to `main` and pull requests targeting `main`. The workflow installs `requirements.txt`, runs the SQLite pytest suite with CI-only environment values, upgrades and downgrades the Alembic schema on a temporary SQLite database, validates `docker compose config`, and builds the Docker image. It does not start PostgreSQL, Redis, or external AI services.

The local equivalents are:
```bash
python -m pip install -r requirements.txt
python -m pytest -q tests
DATABASE_URL=sqlite:///ci_test.sqlite3 python -m alembic upgrade head
docker compose config --quiet
docker build --file Dockerfile --tag smart-task-management-api:ci .
```

---

## 📚 Interactive Swagger UI Testing (`/docs`)

1. Open `http://127.0.0.1:8000/docs` in your web browser.
2. Call `POST /auth/register` to register a new user.
3. Call `POST /auth/login` to obtain an `access_token`.
4. Click the **Authorize 🔓** button at the top right of Swagger UI.
5. Paste your JWT access token and click **Authorize**.
6. Now execute any protected `/tasks` endpoint directly from the browser!

## 🧭 Database Migrations

Alembic is the production schema-management mechanism. The application does not create tables during import or startup.

Apply all migrations:
```bash
alembic upgrade head
```

Roll back the most recent migration in a safe development database:
```bash
alembic downgrade -1
```

Create a migration after changing SQLAlchemy models:
```bash
alembic revision --autogenerate -m "describe the schema change"
```

The normal workflow is to update models, generate and review the migration, apply it to an isolated database, run tests, and then apply it to the intended environment. PostgreSQL is the production target. SQLite is used only for isolated tests and local compatibility checks.

### Existing SQLite Data

`task_db.sqlite3` is preserved and is not migrated automatically. Before moving real data to PostgreSQL:

1. Back up the SQLite file.
2. Inspect and validate users and tasks.
3. Create an empty PostgreSQL database and apply `alembic upgrade head`.
4. Export users first, preserving IDs and password hashes.
5. Map legacy `pending` task statuses to `todo` where appropriate.
6. Import tasks after users so creator and assignee foreign keys remain valid.
7. Validate row counts, uniqueness, timestamps, and ownership relationships.

The repository SQLite artifact was inspected read-only and contains zero users and zero tasks.

## 🧠 Redis Cache

Redis is optional and is used only as a best-effort cache for user-scoped notification listings. PostgreSQL remains the source of truth. Configure `REDIS_URL` and `REDIS_CACHE_TTL_SECONDS` through the environment; leave `REDIS_URL` empty to disable caching.

Cache keys include the authenticated user ID and unread filter. Entries expire after the configured TTL, defaulting to 30 seconds. Notification creation, read-state changes, and deletion invalidate both cached listing variants. If Redis is unavailable, requests bypass the cache and continue against the database without changing database configuration or behavior.

## ⚙️ Background Jobs (Phase 10)

The API includes a lightweight database-backed background-job layer for work that should run outside an HTTP request. Jobs are stored in `background_jobs`, include an idempotency key, and are claimed and processed with fresh SQLAlchemy sessions. Failures are logged and retried up to `BACKGROUND_JOBS_MAX_ATTEMPTS`; exhausted jobs are marked `failed` without crashing the API.

The opt-in in-process worker handles notification and deadline-reminder jobs. It is disabled by default and can be enabled with `BACKGROUND_JOBS_ENABLED=true`. Polling, retry, and shutdown behavior are controlled by the `BACKGROUND_JOBS_*` settings in `.env.example`. Redis is not required. Existing assignment, activity, team, project, and comment notifications remain synchronous and immediately visible; deadline reminders are scheduled in the task transaction and deduplicated when processed. Report and AI job names are reserved hooks only and do not implement those features.

Apply the Phase 10 schema before enabling the worker:
```bash
alembic upgrade head
```

## 🤖 AI Features (Phase 12)

AI is optional and disabled unless `AI_ENABLED=true` and the provider settings in `.env.example` are configured. The application uses a small provider interface with an OpenAI-compatible HTTP adapter; tests use a fake provider and never make external calls. Missing configuration returns a controlled `503` response.

Authenticated users can use:

- `POST /ai/tasks/from-text` to turn natural language into a validated task created through the existing task service. Optional `project_id` and `assignee_id` overrides still pass the normal project, role, and assignment checks.
- `POST /ai/tasks/{task_id}/summary` to summarize the authorized task, comments, status, priority, and activity.
- `POST /ai/tasks/{task_id}/priority-suggestion` to receive a priority recommendation and explanation without changing the stored task.

Task authorization runs before task data is assembled for the provider. AI requests are synchronous in this phase because no AI-result persistence model was added; the existing Phase 10 job architecture remains available for future persisted asynchronous results.

## 📎 File Attachments (Phase 13)

Attachments are authorized through the existing task access rules and stored as metadata in the `attachments` table. File content uses the `StorageProvider` interface with a local filesystem implementation for development and tests. The configured storage root is controlled by `ATTACHMENT_STORAGE_ROOT`; server-generated keys are used instead of client-provided paths, so path traversal is rejected.

Available endpoints:

- `POST /tasks/{task_id}/attachments` uploads a supported text, CSV, PDF, PNG, or JPEG file.
- `GET /tasks/{task_id}/attachments` lists attachment metadata.
- `GET /tasks/{task_id}/attachments/{attachment_id}` downloads attachment content.
- `DELETE /tasks/{task_id}/attachments/{attachment_id}` deletes metadata and stored content.

`ATTACHMENT_MAX_FILE_SIZE_BYTES` controls the upload limit. Filename, extension, and content type must agree. Storage is completed before metadata is committed; failed database writes trigger best-effort content cleanup, and successful metadata deletion removes the stored object. Object storage providers can be added behind the same interface without changing task authorization or API contracts.

## 📝 Comments and Activity

Comments belong to tasks and inherit the task's project/team authorization. Authors may edit or delete their own comments. Managers and admins may moderate comments when they can access the task.

The append-only activity log records task creation, updates, deletion, assignment and project changes, comment creation/update/deletion, and team/project membership changes. Each event stores its actor, action, entity type and ID, timestamp, optional task reference, and structured JSON metadata. There are no API endpoints for editing or deleting activity records.

### Advanced Task Queries

`GET /tasks` supports `limit`, `offset`, `status`, `priority`, `assignee_id`, `project_id`, `deadline_before`, `deadline_after`, `search`, `sort_by`, and `sort_order`. Results retain the existing JSON list response shape. Project-linked tasks are visible only to authorized project members, project owners, team managers, or admins.

Task creation and updates support `project_id` and `assignee_id`. Project assignees must be project members, and assignment/reassignment requires project management scope, a global manager for unscoped tasks, or admin access.

## 🔐 Role-Based Access Control

Authentication identifies the current user through the existing JWT dependency. Authorization is handled separately by reusable role dependencies.

| Role | Permissions |
|---|---|
| `MEMBER` | Create tasks; view, update, and delete tasks they create or are assigned to |
| `MANAGER` | Member task permissions plus access to the current flat task scope and user listing |
| `ADMIN` | Manager permissions plus role changes for users |

Role values are stored as lowercase database values (`member`, `manager`, `admin`) while the application exposes uppercase role names through `UserRole`. Registration never accepts a role field, and only an authenticated admin can change a persisted role.

Team and project authorization is scoped. Team owners and team members can view their teams; team managers and owners can manage them. Projects belong to one team, and only project members, project owners, team managers, or admins can view them. Project creation and membership changes require team or project management scope. A user must be a team member before joining a project.

### Authentication Tokens

`POST /auth/login` returns a short-lived access token and a longer-lived opaque refresh token. Access tokens include issuer, audience, type, issued-at, expiration, and unique ID claims. Refresh tokens are generated with secure randomness and only their SHA-256 digests are stored in the database.

`POST /auth/refresh` rotates the refresh token. The presented token is immediately revoked. Reuse of a revoked token invalidates the user's active refresh sessions. `POST /auth/logout` revokes the supplied refresh token; access tokens remain valid only until their configured expiry.

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

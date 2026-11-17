# TaskMaster

TaskMaster is a task-management API built with Python, FastAPI, and
PostgreSQL.

It supports:

- User registration and login
- User profiles
- Projects and project members
- Tasks, assignments, status, filtering, and search
- Comments and file attachments
- Project invitations
- Secure logout
- Real-time task notifications over WebSockets

AI features are an optional future extension.

## Real-time notifications

After logging in, connect a WebSocket client using the returned access token:

```text
ws://localhost:8001/notifications/ws?token=ACCESS_TOKEN
```

The server sends JSON notifications when a task is assigned or updated, a
comment is added, or a project invitation is created. Missed notifications
can be retrieved with `GET /notifications?unread_only=true`; mark one as read
with `POST /notifications/{notification_id}/read`.

The WebSocket connection authenticates the access token and remains open while
the user is online. A notification has this shape:

```json
{
  "id": 1,
  "user_id": 2,
  "task_id": 10,
  "event_type": "task_assigned",
  "payload": {
    "task_id": 10,
    "project_id": 4,
    "title": "Prepare release notes"
  },
  "read_at": null,
  "created_at": "2026-11-17T14:05:00+00:00"
}
```

For local development on port `8000`, use:

```text
ws://localhost:8000/notifications/ws?token=ACCESS_TOKEN
```

The following browser example opens a connection and prints incoming events:

```javascript
const token = "ACCESS_TOKEN";
const socket = new WebSocket(
  `ws://localhost:8001/notifications/ws?token=${encodeURIComponent(token)}`
);

socket.onopen = () => console.log("Connected to notifications");
socket.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log(notification.event_type, notification);
};
socket.onclose = () => console.log("Disconnected from notifications");
socket.onerror = (error) => console.error("WebSocket error", error);
```

### Notification REST endpoints

List all notifications:

```bash
curl http://localhost:8001/notifications \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

List only unread notifications:

```bash
curl "http://localhost:8001/notifications?unread_only=true" \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

Mark a notification as read:

```bash
curl -X POST http://localhost:8001/notifications/1/read \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

Replace `ACCESS_TOKEN` with the `access_token` returned by
`POST /auth/login`. Notifications are stored in PostgreSQL, so notifications
created while a user is offline can be retrieved later through the REST
endpoint.

## Start the application

From this folder, run:

```bash
docker compose up --build
```

The API is available at:

```text
http://localhost:8001
```

Check that it is running:

```bash
curl http://localhost:8001/health
```

Open the interactive API documentation in your browser:

```text
http://localhost:8001/docs
```

Stop the application with `Ctrl+C`.

To delete the local database and start fresh:

```bash
docker compose down -v
```

## Local Python setup

Docker is the easiest way to run the complete application. If you want to
develop Python code locally, create a virtual environment:

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

With PostgreSQL running, apply migrations:

```bash
export DATABASE_URL=postgresql://taskmaster:taskmaster@localhost:5433/taskmaster
python scripts/migrate.py
```

Start the local API:

```bash
uvicorn app.main:app --reload --port 8000
```

## Simple API example

The examples below use `curl`. Run them one at a time.

### 1. Create an account

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"asha@example.com","password":"correct horse battery","name":"Asha"}'
```

The response contains the new user's `id`. Copy it if you need it later.

### 2. Log in

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"asha@example.com","password":"correct horse battery"}'
```

The response contains an `access_token`. Copy that token and use it below
instead of `YOUR_TOKEN`.

Example authorization header:

```text
Authorization: Bearer YOUR_TOKEN
```

### 3. View and update your profile

```bash
curl http://localhost:8001/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

```bash
curl -X PATCH http://localhost:8001/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Asha Rao"}'
```

### 4. Create a project

```bash
curl -X POST http://localhost:8001/projects \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Website launch","description":"Launch planning"}'
```

Copy the returned project `id` and use it instead of `PROJECT_ID`.

### 5. Create a task

```bash
curl -X POST http://localhost:8001/projects/PROJECT_ID/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Prepare release notes","description":"Write the first draft"}'
```

Copy the returned task `id` and use it instead of `TASK_ID`.

### 6. View your assigned tasks

```bash
curl http://localhost:8001/tasks/assigned-to-me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 7. Mark a task as completed

```bash
curl -X PATCH http://localhost:8001/projects/PROJECT_ID/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed"}'
```

### 8. Invite a team member

First register another user and copy that user's `id`.

```bash
curl -X POST http://localhost:8001/projects/PROJECT_ID/invitations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":OTHER_USER_ID}'
```

Log in as the invited user, then accept the invitation using the invitation
`id` from the previous response:

```bash
curl -X POST http://localhost:8001/projects/invitations/INVITATION_ID/accept \
  -H "Authorization: Bearer OTHER_USER_TOKEN"
```

### 9. Assign a task

```bash
curl -X PATCH http://localhost:8001/projects/PROJECT_ID/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignee_id":OTHER_USER_ID}'
```

### 10. Filter and search tasks

Filter by status:

```bash
curl "http://localhost:8001/projects/PROJECT_ID/tasks?status=completed" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Search by title or description:

```bash
curl "http://localhost:8001/projects/PROJECT_ID/tasks?search=release" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 11. Add a comment and upload a file

Add a comment:

```bash
curl -X POST http://localhost:8001/projects/PROJECT_ID/tasks/TASK_ID/comments \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body":"Please review this task."}'
```

Create a small file and upload it:

```bash
echo "Task notes" > notes.txt

curl -X POST http://localhost:8001/projects/PROJECT_ID/tasks/TASK_ID/attachments/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@notes.txt"
```

### 12. Log out

```bash
curl -X POST http://localhost:8001/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

After logout, the token can no longer be used.

## Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Log in |
| GET | `/auth/me` | View your profile |
| PATCH | `/auth/me` | Update your profile |
| POST | `/auth/logout` | Log out |
| POST | `/projects` | Create a project |
| POST | `/projects/{id}/invitations` | Invite a member |
| POST | `/projects/invitations/{id}/accept` | Accept an invitation |
| POST | `/projects/{id}/tasks` | Create a task |
| GET | `/tasks/assigned-to-me` | View assigned tasks |
| PATCH | `/projects/{id}/tasks/{task_id}` | Update a task |
| GET | `/projects/{id}/tasks` | Filter or search tasks |
| POST | `/projects/{id}/tasks/{task_id}/comments` | Add a comment |
| POST | `/projects/{id}/tasks/{task_id}/attachments/upload` | Upload a file |

## Design choices

- Passwords are hashed with Argon2.
- JWT tokens expire and are checked against database sessions.
- Users must belong to a project before using its tasks.
- PostgreSQL stores application data and attachment metadata.
- Uploaded files are stored locally for development.
- Production should use object storage, file-size limits, malware scanning,
  rate limiting, and stronger secret management.

## Future work

- WebSocket or Server-Sent Events notifications
- AI-generated task descriptions and summaries
- Pagination and audit history
- Automated tests and continuous integration

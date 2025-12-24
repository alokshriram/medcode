# MedCode - Running Instructions

## Prerequisites

- Docker and Docker Compose installed
- Node.js installed (for frontend)
- Python 3.11+ with virtual environment (for backend)

## Database Setup

### Start PostgreSQL Database

```bash
docker compose up -d db
```

Wait a few seconds for the database to be ready:

```bash
docker compose logs db --tail 10
```

Look for: `database system is ready to accept connections`

### Reset Database (Clean Slate)

To completely reset the database and start fresh:

```bash
docker compose down -v
docker compose up -d db
```

The `-v` flag removes the PostgreSQL data volume, giving you a clean database.

### Apply Migrations

From the root directory:

```bash
cd backend
source .venv/bin/activate
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/medcode alembic upgrade head
cd ..
```

## Starting the Servers

### Backend Server

From the root directory:

```bash
cd backend
source .venv/bin/activate
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/medcode uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's running:

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### Frontend Server

In a new terminal, from the root directory:

```bash
cd frontend
VITE_API_URL=http://localhost:8000/api/v1 npm run dev
```

The frontend will be available at http://localhost:3000

## Quick Start (All Steps)

```bash
# 1. Reset and start database
docker compose down -v
docker compose up -d db
sleep 8

# 2. Apply migrations
cd backend
source .venv/bin/activate
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/medcode alembic upgrade head

# 3. Start backend (in background or separate terminal)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/medcode uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# 4. Start frontend (in separate terminal)
cd ../frontend
VITE_API_URL=http://localhost:8000/api/v1 npm run dev
```

## Accessing the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

**Important**: Use `localhost` URLs (not `127.0.0.1`) - OAuth is registered with `localhost`.

## Stopping Services

### Stop Frontend/Backend
Press `Ctrl+C` in the respective terminal.

### Stop Database
```bash
docker compose down
```

### Stop Database and Remove Data
```bash
docker compose down -v
```

## Troubleshooting

### Database Connection Issues
Ensure the database is running and healthy:
```bash
docker compose ps
docker compose logs db
```

### Port Already in Use
Kill existing processes on the port:
```bash
# For backend (port 8000)
lsof -ti:8000 | xargs kill -9

# For frontend (port 3000)
lsof -ti:3000 | xargs kill -9
```

### Permission Issues with init-db.sql
```bash
chmod 644 scripts/init-db.sql
```

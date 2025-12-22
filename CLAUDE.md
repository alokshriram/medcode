# MedCode - Project Guidelines

## Project Overview

MedCode is a medical coding web application that provides tools for medical coders and coding administrators to manage workflows, enhance productivity through AI-powered features, and maintain coding accuracy.

### Core Capabilities
- **Workflow Management**: Task assignment, status tracking, and workload management for coding teams
- **Medical Record Processing**: Document ingestion, categorization, and AI-powered summarization
- **Code Catalog Management**: ICD-10 and CPT code catalogs with search and update mechanisms
- **Productivity Tools**: Streamlined interfaces for efficient medical coding

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript |
| State Management | React Query (server state), useState/useContext (client state) |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| Cache | Redis (backend caching) |
| Authentication | Google Auth + JWT tokens |
| Containerization | Docker |
| Target Deployment | AWS or Azure (optimize for local dev first) |

## Architecture Principles

### Bounded Contexts (Domain-Driven Design)

The application is organized around bounded contexts. Each context has:
- Its own PostgreSQL schema
- Dedicated API path prefix
- Clear domain boundaries

**Current Bounded Contexts:**

| Context | DB Schema | API Path | Description |
|---------|-----------|----------|-------------|
| Coding Workflow | `workflow` | `/api/v1/workflow/` | Task management, assignments, status tracking |
| Encounters | `encounters` | `/api/v1/encounters/` | HL7 ingestion, patient/encounter aggregation, clinical data correlation |
| Medical Records | `records` | `/api/v1/records/` | Codable snapshots, AI summarization, document management |
| Code Catalogs | `catalogs` | `/api/v1/catalogs/` | ICD-10, CPT code management and search |
| Users/Auth | `users` | `/api/v1/users/` | Identity, roles, permissions |

**Data Flow:** HL7 → `encounters` (raw clinical aggregation) → `records` (codable snapshots) → `workflow` (coding work items)

When adding new features:
1. Identify which bounded context it belongs to
2. If it doesn't fit existing contexts, evaluate if a new context is needed
3. Keep cross-context dependencies minimal and explicit

### Backend for Frontend (BFF)

- Path: `/api/v1/bff/`
- Purpose: Orchestration layer when frontend needs data from multiple bounded contexts
- **No persistence** - BFF does not have its own database tables
- Calls internal domain services and aggregates responses
- Keeps frontend API calls simple

### API Design

- **Versioning**: URL path versioning (`/api/v1/`, `/api/v2/`)
- **Authentication**: All endpoints require valid JWT tokens (except health checks)
- **Simple APIs**: Frontend should call straightforward endpoints; complexity lives in BFF or backend services
- **REST conventions**: Follow standard HTTP methods (GET, POST, PUT, PATCH, DELETE)

## Repository Structure

```
medcode/                          # Monorepo root
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── core/                # Shared utilities, config, security
│   │   ├── domains/             # Bounded contexts
│   │   │   ├── encounters/      # HL7 ingestion, clinical aggregation
│   │   │   ├── workflow/
│   │   │   │   ├── models.py    # SQLAlchemy models
│   │   │   │   ├── schemas.py   # Pydantic schemas
│   │   │   │   ├── router.py    # API routes
│   │   │   │   └── service.py   # Business logic
│   │   │   ├── records/
│   │   │   ├── catalogs/
│   │   │   └── users/
│   │   └── bff/                 # Backend for Frontend orchestration
│   ├── tests/
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                 # API client and React Query hooks
│   │   ├── components/          # Reusable UI components
│   │   ├── features/            # Feature-specific components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── pages/               # Route pages
│   │   └── utils/               # Utilities
│   ├── package.json
│   └── Dockerfile
├── docs/
│   └── pdd/                     # Product Design Decisions
├── docker-compose.yml           # Local development orchestration
├── .env.example
├── CLAUDE.md                    # This file
└── .clinerules                  # Code style guidelines
```

## Database Guidelines

### Schema Organization
- Each bounded context owns its schema
- Cross-schema references should be by ID only (no foreign keys across schemas)
- Use UUIDs for primary keys to support distributed systems

### Migration Strategy
- Use Alembic for all schema changes
- **Backward compatibility is critical** (CI/CD deployment)
- For breaking changes:
  1. Add new columns/tables first (nullable or with defaults)
  2. Deploy application changes
  3. Migrate data
  4. Remove old columns in a later migration
- Never drop columns in the same release that stops using them

### Data Model Changes Checklist
- [ ] Is this change backward compatible?
- [ ] Can the previous application version still work with this schema?
- [ ] Are new columns nullable or have sensible defaults?
- [ ] Is there a data migration needed?

## Testing Strategy

### Backend Testing
- Use pytest for all tests
- Write tests as you build features (not after)
- Test categories:
  - **Unit tests**: Business logic in service layer
  - **Integration tests**: API endpoints with test database
  - **Contract tests**: Ensure API responses match schemas
- Tests serve as safety net during refactoring

### Frontend Testing
- Use Jest and React Testing Library
- Focus on user interactions and flows
- Test critical paths: authentication, workflow operations, code lookups

## Security & Compliance

### HIPAA Considerations
- **PHI (Protected Health Information)** must be handled with care
- All data at rest must be encrypted
- All data in transit must use HTTPS/TLS
- Audit logging for access to patient data
- Role-based access control (RBAC) for data access
- No PHI in logs, error messages, or URLs
- Session timeout for inactive users

### Authentication & Authorization
- Google Auth for identity provider
- JWT tokens for API authentication
- Validate JWT on every request
- Implement role-based permissions (coder, admin, supervisor)
- Token refresh mechanism

### Security Checklist
- [ ] No secrets in code or version control
- [ ] Environment variables for all configuration
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (use SQLAlchemy ORM)
- [ ] CORS configured appropriately
- [ ] Rate limiting on public endpoints

## Development Workflow

### Local Development
```bash
# Start all services
docker-compose up

# Backend only
docker-compose up backend db redis

# Frontend only (connects to backend)
cd frontend && npm run dev
```

### Adding a New Feature
1. Identify the bounded context
2. Design the data model (consider backward compatibility)
3. Write the migration
4. Implement the API endpoint with tests
5. Implement the frontend integration
6. Update documentation if needed

### Code Review Focus
- Does it respect bounded context boundaries?
- Is the data model change backward compatible?
- Are there tests covering the new functionality?
- Are HIPAA/security considerations addressed?
- Is the code following the style guide in `.clinerules`?

## AI/ML Integration

*Decision deferred* - Architecture should accommodate future AI/ML features:
- Medical record summarization
- Document categorization
- Code suggestion/validation

When implementing:
- Consider a separate bounded context for AI services
- Design for async processing (medical records can be large)
- Plan for model versioning and updates

## Product Design Decisions

Detailed product design decisions are documented in `docs/pdd/`:
- [PDD-001: HL7 Ingestion and Codable Encounters](docs/pdd/PDD-001-hl7-ingestion-and-codable-encounters.md)

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Initial | React Query for server state | Built-in caching ideal for code catalog lookups; handles loading/error states; reduces boilerplate |
| Initial | Monorepo structure | Simplifies development workflow; shared tooling; atomic commits across stack |
| Initial | PostgreSQL schemas for bounded contexts | Clear data ownership; supports future service extraction if needed |
| Initial | BFF without persistence | Clean separation; orchestration only; avoids data duplication |
| 2025-12-21 | New `encounters` bounded context | Separates raw HL7/clinical aggregation from higher-level records; see PDD-001 |
| 2025-12-21 | Snapshot model for coding | Coders work against point-in-time snapshots for audit/consistency; see PDD-001 |

# Testing Guidance

## Philosophy

### Unit Tests Pin Behavior

Unit tests are the primary mechanism for:
- Documenting expected behavior
- Catching regressions during refactoring
- Providing fast feedback during development

### The 80/20 Rule

Focus testing effort where it matters most:

- **Test key scenarios**: Happy paths, critical error cases, edge cases that have caused bugs
- **Don't test trivial code**: Getters, setters, simple mappings
- **Don't test framework behavior**: Trust that FastAPI routes work, React renders components

### What to Test

| Priority | What | Why |
|----------|------|-----|
| High | Business logic in services | Core value, complex, error-prone |
| High | Data transformations | Easy to get wrong, hard to debug |
| Medium | API contracts | Catch breaking changes |
| Medium | Complex UI interactions | User-facing, regression-prone |
| Low | Simple CRUD operations | Low complexity, framework-handled |
| Skip | Configuration, constants | No logic to test |

---

## Unit Testing

### Structure: Arrange-Act-Assert

```python
def test_task_assignment_updates_status():
    # Arrange
    task = Task(id=uuid4(), status=TaskStatus.PENDING)
    coder = User(id=uuid4(), role=Role.CODER)

    # Act
    result = assign_task(task, coder)

    # Assert
    assert result.status == TaskStatus.ASSIGNED
    assert result.assigned_to == coder.id
```

### Naming Convention

Test names should describe the scenario and expected outcome:

```python
# Pattern: test_<unit>_<scenario>_<expected_outcome>

def test_create_snapshot_with_valid_encounter_returns_snapshot():
    ...

def test_create_snapshot_with_missing_encounter_raises_not_found():
    ...

def test_assign_task_to_coder_at_capacity_raises_capacity_error():
    ...
```

### Test One Thing

Each test should verify one behavior:

```python
# Bad: Testing multiple behaviors
def test_task_creation():
    task = create_task(title="Review", priority=Priority.HIGH)
    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.priority == Priority.HIGH
    assert task.created_at is not None
    # What exactly failed if this test fails?

# Good: Focused tests
def test_create_task_assigns_pending_status():
    task = create_task(title="Review")
    assert task.status == TaskStatus.PENDING

def test_create_task_preserves_priority():
    task = create_task(title="Review", priority=Priority.HIGH)
    assert task.priority == Priority.HIGH
```

### Mocking Guidelines

- Mock external dependencies (databases, APIs, file systems)
- Don't mock the unit under test
- Prefer fakes over mocks when the fake is simple

```python
# Good: Mock external service
def test_encounter_service_handles_hl7_parse_error(mocker):
    mocker.patch(
        "app.domains.encounters.hl7_parser.parse",
        side_effect=HL7ParseError("Invalid message")
    )

    with pytest.raises(IngestionError):
        encounter_service.ingest_message(invalid_hl7)

# Avoid: Mocking too much internal behavior
def test_service_with_everything_mocked(mocker):
    mocker.patch.object(service, "validate")
    mocker.patch.object(service, "transform")
    mocker.patch.object(service, "save")
    # This test doesn't actually test anything meaningful
```

---

## Integration Testing

### Purpose

Integration tests verify that components work together correctly:
- API endpoints with database
- Service layer with real dependencies
- Frontend with mocked API responses

### Test Database Setup

Use a dedicated test database with proper isolation:

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.config import settings

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(settings.TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a fresh database session for each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
```

### API Integration Tests

```python
from fastapi.testclient import TestClient

def test_create_task_endpoint(client: TestClient, db_session, auth_headers):
    # Seed required data
    coder = create_test_user(db_session, role=Role.CODER)

    response = client.post(
        "/api/v1/workflow/tasks",
        json={"title": "Review encounter", "assigned_to": str(coder.id)},
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Review encounter"
    assert data["status"] == "pending"
```

---

## Data Seeding and Cleanup

### Principles

1. **Each test seeds its own data**: Don't rely on data from other tests
2. **Tests clean up after themselves**: Use transactions that rollback
3. **Use factories for test data**: Don't duplicate object creation

### Test Data Factories

```python
# tests/factories.py
from uuid import uuid4
from app.domains.users.models import User, Role
from app.domains.workflow.models import Task, TaskStatus

def create_test_user(
    db_session,
    *,
    email: str = None,
    role: Role = Role.CODER
) -> User:
    user = User(
        id=uuid4(),
        email=email or f"test-{uuid4()}@example.com",
        role=role
    )
    db_session.add(user)
    db_session.flush()
    return user

def create_test_task(
    db_session,
    *,
    title: str = "Test Task",
    status: TaskStatus = TaskStatus.PENDING,
    assigned_to: User = None
) -> Task:
    task = Task(
        id=uuid4(),
        title=title,
        status=status,
        assigned_to_id=assigned_to.id if assigned_to else None
    )
    db_session.add(task)
    db_session.flush()
    return task
```

### Transaction-Based Cleanup

Wrap each test in a transaction that rolls back:

```python
@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    # Automatic cleanup - rollback everything
    session.close()
    transaction.rollback()
    connection.close()
```

---

## Test-Specific API Routes

### When to Use

Create test-only endpoints when you need to:
- Seed complex data states for E2E tests
- Reset database state between test runs
- Trigger time-based events manually (e.g., "expire all sessions")

### Implementation

```python
# app/testing/router.py
from fastapi import APIRouter, Depends
from app.core.config import settings

router = APIRouter(prefix="/api/test", tags=["testing"])

def require_test_mode():
    """Ensure test endpoints only work in test/dev environments."""
    if settings.ENVIRONMENT == "production":
        raise HTTPException(403, "Test endpoints disabled in production")

@router.post("/seed/workflow-scenario", dependencies=[Depends(require_test_mode)])
async def seed_workflow_scenario(
    scenario: WorkflowScenario,
    db: Session = Depends(get_db)
):
    """Seed database with a specific workflow scenario for testing."""
    if scenario == WorkflowScenario.CODER_WITH_FULL_QUEUE:
        coder = create_coder_with_max_tasks(db)
        return {"coder_id": str(coder.id)}
    # ... other scenarios

@router.post("/reset", dependencies=[Depends(require_test_mode)])
async def reset_test_data(db: Session = Depends(get_db)):
    """Clear all test data from the database."""
    # Only delete data created by tests (e.g., with specific markers)
    db.execute("DELETE FROM workflow.tasks WHERE title LIKE 'TEST:%'")
    db.commit()
    return {"status": "reset complete"}
```

### Registration

Only register test routes in non-production environments:

```python
# app/main.py
from app.core.config import settings

app = FastAPI()

# Always register domain routes
app.include_router(workflow_router)
app.include_router(encounters_router)

# Only register test routes in development/test
if settings.ENVIRONMENT in ("development", "test"):
    from app.testing.router import router as test_router
    app.include_router(test_router)
```

---

## Test Organization

### Directory Structure

```
tests/
├── conftest.py              # Shared fixtures
├── factories.py             # Test data factories
├── unit/
│   ├── domains/
│   │   ├── workflow/
│   │   │   ├── test_service.py
│   │   │   └── test_models.py
│   │   └── encounters/
│   │       └── test_hl7_parser.py
│   └── core/
│       └── test_security.py
├── integration/
│   ├── api/
│   │   ├── test_workflow_endpoints.py
│   │   └── test_encounters_endpoints.py
│   └── services/
│       └── test_encounter_ingestion.py
└── e2e/                     # End-to-end tests (if needed)
    └── test_coding_workflow.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/domains/workflow/test_service.py

# Run tests matching pattern
pytest -k "test_task_assignment"

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

---

## Frontend Testing

### Component Testing

```typescript
// WorkflowList.test.tsx
import { render, screen } from '@testing-library/react';
import { WorkflowList } from './WorkflowList';

describe('WorkflowList', () => {
  it('renders task titles', () => {
    const tasks = [
      { id: '1', title: 'Review encounter A' },
      { id: '2', title: 'Review encounter B' },
    ];

    render(<WorkflowList tasks={tasks} />);

    expect(screen.getByText('Review encounter A')).toBeInTheDocument();
    expect(screen.getByText('Review encounter B')).toBeInTheDocument();
  });

  it('shows empty state when no tasks', () => {
    render(<WorkflowList tasks={[]} />);

    expect(screen.getByText('No tasks available')).toBeInTheDocument();
  });
});
```

### Hook Testing

```typescript
// useWorkflow.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useWorkflowTasks } from './useWorkflow';

const wrapper = ({ children }) => (
  <QueryClientProvider client={new QueryClient()}>
    {children}
  </QueryClientProvider>
);

describe('useWorkflowTasks', () => {
  it('fetches and returns tasks', async () => {
    const { result } = renderHook(() => useWorkflowTasks(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(2);
  });
});
```

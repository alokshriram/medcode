# Coding Guidance

## Language & Framework Standards

### Backend: Python + FastAPI

- **Python 3.11+** with type hints everywhere
- **FastAPI** for API endpoints
- **SQLAlchemy 2.0** with async support for database operations
- **Pydantic** for request/response validation
- **Alembic** for database migrations

### Frontend: TypeScript + React

- **TypeScript** in strict mode—no `any` types
- **React 18+** with functional components and hooks
- **React Query** for server state management
- **CSS Modules** or **Tailwind** for styling

---

## Clean Code Principles

### Write Code for Humans

Code is read far more often than it's written. Optimize for readability:

```python
# Bad
def proc(d, f):
    return [x for x in d if f(x)]

# Good
def filter_items(items: list[Item], predicate: Callable[[Item], bool]) -> list[Item]:
    return [item for item in items if predicate(item)]
```

### Naming Conventions

**Python:**
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `SCREAMING_SNAKE_CASE` for constants
- Prefix private methods with `_`

**TypeScript:**
- `camelCase` for functions, variables
- `PascalCase` for components, types, interfaces
- `SCREAMING_SNAKE_CASE` for constants

### Be Idiomatic

Write code that looks natural in its language:

```python
# Pythonic
if items:
    process(items)

names = [user.name for user in users if user.active]

with open(path) as f:
    content = f.read()
```

```typescript
// Idiomatic TypeScript/React
const ActiveUsers = ({ users }: { users: User[] }) => {
  const activeUsers = users.filter(user => user.isActive);

  return (
    <ul>
      {activeUsers.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
};
```

---

## DRY Principle (Don't Repeat Yourself)

### When to Abstract

Abstract when you see **three or more** instances of the same pattern. Two instances might be coincidence.

```python
# Before: Repeated validation logic
@router.post("/tasks")
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    if not current_user.can_create_tasks:
        raise HTTPException(403, "Not authorized")
    # ...

@router.post("/assignments")
async def create_assignment(assignment: AssignmentCreate, db: Session = Depends(get_db)):
    if not current_user.can_create_assignments:
        raise HTTPException(403, "Not authorized")
    # ...

# After: Extracted dependency
def require_permission(permission: str):
    def checker(current_user: User = Depends(get_current_user)):
        if not current_user.has_permission(permission):
            raise HTTPException(403, "Not authorized")
        return current_user
    return Depends(checker)

@router.post("/tasks")
async def create_task(
    task: TaskCreate,
    user: User = require_permission("create_tasks")
):
    # ...
```

### When NOT to Abstract

- Don't create abstractions for hypothetical future use
- Don't abstract things that are similar but serve different purposes
- Duplication is better than the wrong abstraction

---

## Keep Methods and Files Short

### Method Length

- Aim for methods under **20 lines**
- If a method needs a comment explaining a section, extract that section
- Each method should do **one thing**

```python
# Too long - doing multiple things
def process_encounter(encounter_data: dict) -> Encounter:
    # Validate
    if not encounter_data.get("patient_id"):
        raise ValueError("Missing patient_id")
    if not encounter_data.get("date"):
        raise ValueError("Missing date")
    # ... 10 more validation lines

    # Transform
    patient = get_patient(encounter_data["patient_id"])
    # ... 15 more transformation lines

    # Save
    encounter = Encounter(**transformed_data)
    db.add(encounter)
    # ... more save logic

    return encounter

# Better - single responsibility per method
def process_encounter(encounter_data: dict) -> Encounter:
    validated = validate_encounter_data(encounter_data)
    transformed = transform_to_encounter(validated)
    return save_encounter(transformed)
```

### File Length

- Aim for files under **300 lines**
- If a file grows large, it's doing too much
- Split by responsibility, not arbitrarily

### Signs You Need to Split

- Multiple unrelated classes in one file
- Scrolling extensively to find things
- Imports from many different domains
- File name is too generic (e.g., `utils.py`, `helpers.ts`)

---

## Refactor As You Go

### The Boy Scout Rule

Leave code better than you found it. When working in a file:

- Fix obvious issues you encounter
- Improve names that are unclear
- Extract methods that are too long
- Remove dead code

### Refactoring Triggers

Refactor when you notice:
- **Duplication**: Same code in multiple places
- **Long methods**: Hard to understand at a glance
- **Deep nesting**: More than 3 levels of indentation
- **Feature envy**: Method uses more data from another class than its own
- **Primitive obsession**: Using primitives instead of small objects

### Safe Refactoring

1. Ensure tests exist for the code you're changing
2. Make small, incremental changes
3. Run tests after each change
4. Commit frequently

---

## Conventional Commits

Use structured commit messages for clear history and automated tooling.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks (deps, config) |
| `style` | Formatting, whitespace (no code change) |
| `perf` | Performance improvement |

### Scope

Use the domain or component name:

```
feat(workflow): add task assignment endpoint
fix(encounters): handle duplicate HL7 messages
refactor(catalogs): extract code search logic
test(users): add auth integration tests
```

### Examples

```
feat(workflow): add bulk task assignment

Allows supervisors to assign multiple tasks to a coder
in a single operation.

Closes #123
```

```
fix(encounters): prevent duplicate snapshot creation

Added idempotency check using encounter_id + version.
```

```
refactor(bff): extract encounter aggregation logic

Moved complex aggregation from router to dedicated service
for better testability.
```

---

## Code Organization

### Backend Structure

```
domains/
└── workflow/
    ├── __init__.py
    ├── models.py      # SQLAlchemy models (data structure)
    ├── schemas.py     # Pydantic schemas (API contracts)
    ├── router.py      # FastAPI routes (thin, delegates to service)
    ├── service.py     # Business logic (testable, no HTTP concerns)
    └── repository.py  # Data access (optional, for complex queries)
```

### Frontend Structure

```
features/
└── workflow/
    ├── index.ts              # Public exports
    ├── WorkflowList.tsx      # Components
    ├── WorkflowDetail.tsx
    ├── useWorkflow.ts        # Custom hooks
    ├── workflowApi.ts        # API calls
    └── workflow.types.ts     # TypeScript types
```

### Import Order

**Python:**
```python
# Standard library
import os
from datetime import datetime

# Third-party
from fastapi import APIRouter
from sqlalchemy.orm import Session

# Local
from app.core.config import settings
from app.domains.workflow.service import WorkflowService
```

**TypeScript:**
```typescript
// React
import { useState, useEffect } from 'react';

// Third-party
import { useQuery } from '@tanstack/react-query';

// Local
import { WorkflowApi } from './workflowApi';
import type { Workflow } from './workflow.types';
```

# Architecture Guidance

## Core Principles

### Loosely Coupled, Strongly Cohesive

Design systems where:
- **High cohesion within domains**: Related functionality lives together. A domain should fully own its data, business rules, and operations.
- **Low coupling between domains**: Domains communicate through well-defined interfaces, not shared internals. Changes in one domain should not ripple through others.

### Domain-Driven Design (DDD)

1. **Bounded Contexts**: Each domain has clear boundaries. The same concept (e.g., "User") may have different representations in different contexts—this is intentional.

2. **Ubiquitous Language**: Use domain terminology consistently within each bounded context. Code should read like the domain experts speak.

3. **Aggregates**: Group related entities that change together. The aggregate root is the only entry point for modifications.

4. **Domain Events**: When something significant happens in a domain, emit an event. Other domains can react without tight coupling.

---

## API-First Strategy

### Design Before Implementation

1. **Define contracts first**: Write OpenAPI/Swagger specs before implementing endpoints
2. **Version from day one**: Use URL versioning (`/api/v1/`, `/api/v2/`)
3. **Design for clients**: APIs should be intuitive for frontend developers

### Keep Client Code Simple

- Clients should not need to understand backend complexity
- Aggregate data server-side when the client needs data from multiple sources
- Return exactly what the client needs—no over-fetching, no under-fetching
- Use consistent response shapes and error formats

### API Design Rules

```
GET    /resources          → List resources
GET    /resources/{id}     → Get single resource
POST   /resources          → Create resource
PUT    /resources/{id}     → Full update
PATCH  /resources/{id}     → Partial update
DELETE /resources/{id}     → Delete resource
```

- Use nouns for resources, not verbs
- Use query parameters for filtering, sorting, pagination
- Return appropriate HTTP status codes

---

## Domain Isolation

### Each Domain Owns Its Data

- Domains have their own database schema
- No direct foreign keys across schema boundaries
- Cross-domain references use IDs only
- Each domain can evolve its data model independently

### Communication Between Domains

**Synchronous (when immediate consistency is required):**
- Internal service calls within the same process
- Use dependency injection for testability

**Asynchronous (when eventual consistency is acceptable):**
- Domain events via message queues
- Better for decoupling and resilience

### Anti-Corruption Layer (ACL)

When integrating with external systems or legacy code:
- Create a translation layer at the boundary
- Keep external concepts out of your domain model
- The ACL adapts external data to your domain's language

---

## Orchestration Domain

### When to Use Orchestration

Create an orchestration layer (BFF or dedicated orchestrator) when:
- A user action requires coordination across multiple domains
- The frontend needs aggregated data from several sources
- Complex workflows span domain boundaries

### RPC-Style Semantics for Orchestration

For orchestration endpoints, RPC-style naming is acceptable:

```
POST /api/v1/bff/submit-coding-review
POST /api/v1/bff/assign-work-items
POST /api/v1/bff/complete-encounter-workflow
```

### Orchestration Rules

1. **No persistence**: Orchestrators coordinate, they don't own data
2. **Thin logic**: Business rules live in domains, not orchestrators
3. **Compensating actions**: Plan for partial failures in multi-step operations
4. **Idempotency**: Orchestrated operations must be safely retryable

---

## Idempotency Guarantees

### Why Idempotency Matters

Networks fail. Clients retry. Without idempotency, retries cause duplicate operations.

### Implementation Strategies

1. **Idempotency Keys**
   - Clients provide a unique key with each request
   - Server stores results keyed by this value
   - Repeated requests return the cached result

   ```python
   @app.post("/api/v1/workflow/tasks")
   async def create_task(
       task: TaskCreate,
       idempotency_key: str = Header(None)
   ):
       if idempotency_key:
           cached = await get_cached_result(idempotency_key)
           if cached:
               return cached
       # Process and cache result
   ```

2. **Natural Idempotency**
   - Design operations to be naturally idempotent when possible
   - `PUT` with full resource state is idempotent by nature
   - Use upserts where appropriate

3. **Database Constraints**
   - Unique constraints prevent duplicate records
   - Use `INSERT ... ON CONFLICT` patterns

### Idempotency Checklist

- [ ] Can this endpoint be safely retried?
- [ ] Are side effects (emails, notifications) guarded against duplicates?
- [ ] Is there a mechanism to detect duplicate requests?

---

## Performance and Latency

### Design for Performance

1. **Minimize round trips**
   - Batch operations where possible
   - Return related data in single requests (within reason)
   - Use pagination for large datasets

2. **Async where appropriate**
   - Long-running operations should be async
   - Return immediately with a job/task ID
   - Provide status polling or webhooks

3. **Caching strategy**
   - Cache at the right layer (HTTP, application, database)
   - Use Redis for frequently accessed, rarely changed data
   - Cache invalidation must be explicit and correct

### Database Performance

1. **Index thoughtfully**
   - Index columns used in WHERE, JOIN, ORDER BY
   - Don't over-index—writes become slower
   - Use EXPLAIN to understand query plans

2. **Query patterns**
   - Avoid N+1 queries (use eager loading)
   - Select only needed columns for read-heavy paths
   - Use database-level pagination

### Latency Budgets

Think about latency at each layer:

```
Total request budget: 200ms
├── Network (client → server): 20ms
├── Authentication/middleware: 10ms
├── Business logic: 50ms
├── Database queries: 100ms
└── Response serialization: 20ms
```

- Set alerts when latency exceeds targets
- Profile slow endpoints regularly
- Optimize the critical path first

---

## Architecture Decision Records

When making significant architectural decisions:

1. Document the decision and rationale
2. Record alternatives considered
3. Note trade-offs accepted
4. Update when circumstances change

Keep these in `docs/adr/` or the decisions log in `CLAUDE.md`.

```markdown
# AGENTS.md — Cloud Persistence API Guidelines

## Purpose
This document defines how AI assistants and contributors must design, modify, and extend the **ProjectPlanning Cloud Persistence API** (FastAPI + PostgreSQL).

It governs **architecture**, **coding standards**, **layering**, and **documentation requirements**.

➡️ **Any change to the API MUST also update `API_DOCUMENTATION.md`.  
No PR is accepted without this.**

For detailed endpoints, schemas, and models, refer to:  
**`API_DOCUMENTATION.md`**

---

## 1. High-Level Architecture

```

Proxy API (8000) ───►  Cloud Persistence API (8001) ───► PostgreSQL (5433)
(Orchestration)            (Persistence Only)            (Storage)

````

- Cloud API stores data and exposes a REST interface.
- Proxy API handles orchestration + Bonita BPM.
- Cloud API must **never depend on Bonita** — it only stores references.

---

## 2. Tech Stack (Required)

- **FastAPI** (async)
- **Python 3.12+**
- **SQLAlchemy 2.0 async**
- **PostgreSQL 15+**
- **Alembic** for migrations
- **Pydantic v2**
- **JWT authentication**
- **Docker + docker-compose**

---

## 3. Architectural Rules

### 3.1 Mandatory Layering

**API Layer**
- Route definitions  
- Request/response validation  
- Auth checks  
- Zero business logic  

**Service Layer**
- Business rules  
- Database queries  
- Domain validations  
- Must not commit transactions  

**Model Layer**
- SQLAlchemy ORM models  
- UUID primary keys  
- Timestamp fields  
- Relationship definitions  

**Schema Layer**
- Pydantic schemas  
- Input/output contracts  
- Never expose sensitive fields  

---

## 4. Coding Standards

### 4.1 Conventions
- **Fully async** (no sync functions)
- **UUIDs everywhere** (`uuid4()`)
- **Cascade deletes defined explicitly**
- **Use eager loading** (`selectinload`) to avoid N+1
- **Environment variables for secrets**
- **Always create Alembic migrations**
- **Update `API_DOCUMENTATION.md` for ANY API change**

### 4.2 Anti-Patterns (Forbidden)
❌ Sync database operations  
❌ Business logic inside endpoints  
❌ Direct DB operations inside endpoints  
❌ Hardcoded secrets  
❌ Skipping migrations  
❌ Returning ORM models directly  

---

## 5. Feature Workflow

### Step 1 — Model
- Create/modify SQLAlchemy model  
- Add relationships + cascades  
- Add timestamps  

### Step 2 — Schemas
- Define `Create`, `Update`, `Response` schemas  
- Public response must hide sensitive fields  

### Step 3 — Service
- CRUD operations  
- Business rules  
- No commits  

### Step 4 — Endpoints
- Define routes under `/api/v1/...`  
- Apply auth dependencies  
- Use Pydantic for I/O  
- Call service layer only  

### Step 5 — Migration
```bash
uv run alembic revision --autogenerate -m "Description"
uv run alembic upgrade head
````

### Step 6 — Documentation (Mandatory)

Every API change must update:

* `API_DOCUMENTATION.md`

  * Endpoints
  * Request/response bodies
  * Model diagrams if needed

If documentation is missing → reject the PR.

---

## 6. API Contract Governance

All resource paths must follow:

```
/api/v1/<resource>/
/api/v1/<resource>/{id}
```

* **PATCH** for partial updates
* **PUT** only when replacing the entire resource
* Sensitive fields must never appear in responses

---

## 7. Repository Structure (Simplified)

```
app/
  api/
    v1/
      endpoints/
      router.py
    deps/
  services/
  models/
  schemas/
  core/
  db/
```

---

## 8. Testing Requirements

All new features must include tests:

* Happy paths
* 404/403/422 cases
* Authentication behavior
* Cascade delete integrity
* Validation errors

---

## 9. Required Business Behavior

### Accepting an Oferta

When an oferta is accepted:

1. `oferta.estado → aceptada`
2. `pedido.estado → completado`
3. Other ofertas remain `pendiente`
4. Must occur within a single DB transaction

---

**End of AGENTS.md**

```
```

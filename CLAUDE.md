# ProjectPlanning Cloud Persistence API

## Project Overview

**FastAPI Cloud Persistence API** - Handles all database operations for the ProjectPlanning system. This is a standalone REST API with PostgreSQL that stores project data, user authentication, and offers. It's called by the Proxy API for orchestration.

### Architecture

```
┌─────────────────────┐
│  Proxy API          │  (Orchestration & Bonita BPM integration)
│  (Port 8000)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Cloud API          │  ◄── This API (Port 8001)
│  (Persistence)      │  (Authentication, Projects, Offers)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PostgreSQL         │  (Data Storage)
│  (Port 5433)        │
└─────────────────────┘
```

### Tech Stack

- **Framework:** FastAPI with async/await
- **Package Manager:** uv (modern Python package manager)
- **Python:** 3.12+
- **Database:** PostgreSQL 15+ with asyncpg driver
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Authentication:** JWT (access + refresh tokens), bcrypt password hashing
- **Deployment:** Docker + docker-compose

### Current Features

1. **Authentication** (`/api/v1/auth/*`)
   - User registration (MEMBER/COUNCIL roles)
   - Login (access + refresh tokens)
   - Token refresh
   - Password hashing with bcrypt

2. **Projects** (`/api/v1/projects/*`)
   - CRUD operations for projects with nested etapas and pedidos
   - User ownership (user_id FK)
   - Bonita BPM tracking (case_id, process_instance_id)
   - Cascade deletes

3. **Pedidos** (`/api/v1/pedidos/*`, `/api/v1/projects/{id}/pedidos`)
   - Add pedidos to existing projects
   - List pedidos with optional estado filter
   - Delete pedidos (cascades to ofertas)
   - Pedido states (pendiente, completado)
   - Automatically marked completado when oferta accepted

4. **Offers** (`/api/v1/ofertas/*`)
   - Users can submit offers for specific pedidos
   - Offer states (pendiente, aceptada, rechazada)
   - Accepting oferta marks pedido as completado
   - Linked to user and pedido

---

## Domain Model

### Database Schema

#### **users**
User accounts with authentication and role-based access.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Auto-generated |
| email | String(255) | UNIQUE, NOT NULL | Login email |
| password | String(255) | NOT NULL | Bcrypt hashed password |
| ong | String(255) | NOT NULL | Organization name |
| nombre | String(255) | NOT NULL | First name |
| apellido | String(255) | NOT NULL | Last name |
| role | UserRole | NOT NULL, default=MEMBER | COUNCIL or MEMBER |
| created_at | DateTime(TZ) | NOT NULL, auto | Creation timestamp |
| updated_at | DateTime(TZ) | NOT NULL, auto | Update timestamp |

**Relationships:**
- `proyectos` → One-to-Many with Proyecto (CASCADE DELETE)
- `ofertas` → One-to-Many with Oferta (CASCADE DELETE)

---

#### **proyectos**
Main project table with metadata and Bonita tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Auto-generated |
| user_id | UUID | FK(users.id), NOT NULL | Project owner |
| titulo | String(200) | NOT NULL | Project title |
| descripcion | Text | NOT NULL | Project description |
| tipo | String(100) | NOT NULL | Project type |
| pais | String(100) | NOT NULL | Country |
| provincia | String(100) | NOT NULL | Province/State |
| ciudad | String(100) | NOT NULL | City |
| barrio | String(100) | NULLABLE | Neighborhood |
| estado | EstadoProyecto | NOT NULL, default=pendiente | Project status |
| bonita_case_id | String(100) | NULLABLE | Bonita case ID (set later) |
| bonita_process_instance_id | Integer | NULLABLE | Bonita process instance ID |
| created_at | DateTime(TZ) | NOT NULL, auto | Creation timestamp |
| updated_at | DateTime(TZ) | NOT NULL, auto | Update timestamp |

**Relationships:**
- `user` → Many-to-One with User
- `etapas` → One-to-Many with Etapa (CASCADE DELETE)

---

#### **etapas**
Project stages/phases with date ranges.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Auto-generated |
| proyecto_id | UUID | FK(proyectos.id), NOT NULL | Parent project |
| nombre | String(200) | NOT NULL | Stage name |
| descripcion | Text | NOT NULL | Stage description |
| fecha_inicio | Date | NOT NULL | Start date |
| fecha_fin | Date | NOT NULL | End date |

**Relationships:**
- `proyecto` → Many-to-One with Proyecto
- `pedidos` → One-to-Many with Pedido (CASCADE DELETE)

---

#### **pedidos**
Coverage requests within etapas (economic, materials, labor, transport, equipment).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Auto-generated |
| etapa_id | UUID | FK(etapas.id), NOT NULL | Parent stage |
| tipo | TipoPedido | NOT NULL | Request type |
| descripcion | Text | NOT NULL | Request description |
| estado | EstadoPedido | NOT NULL, default=pendiente | Pedido status |
| monto | Float | NULLABLE | Amount (for economico) |
| moneda | String(10) | NULLABLE | Currency code |
| cantidad | Integer | NULLABLE | Quantity (for materiales/etc) |
| unidad | String(50) | NULLABLE | Unit of measurement |

**Relationships:**
- `etapa` → Many-to-One with Etapa
- `ofertas` → One-to-Many with Oferta (CASCADE DELETE)

---

#### **ofertas**
User-submitted offers to cover specific pedidos.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Auto-generated |
| pedido_id | UUID | FK(pedidos.id), NOT NULL | Target pedido |
| user_id | UUID | FK(users.id), NOT NULL | Offer creator |
| monto_ofrecido | Float | NULLABLE | Offered amount |
| descripcion | Text | NOT NULL | Offer description |
| estado | EstadoOferta | NOT NULL, default=pendiente | Offer status |
| created_at | DateTime(TZ) | NOT NULL, auto | Creation timestamp |
| updated_at | DateTime(TZ) | NOT NULL, auto | Update timestamp |

**Relationships:**
- `pedido` → Many-to-One with Pedido
- `user` → Many-to-One with User

---

### Enums

**UserRole:**
- `COUNCIL` - Council member with elevated privileges
- `MEMBER` - Regular member

**EstadoProyecto:**
- `pendiente` - Created and seeking financing
- `en_ejecucion` - Project is being executed
- `finalizado` - Work completed and closed

**TipoPedido:**
- `economico` - Economic/financial request
- `materiales` - Materials request
- `mano_obra` - Labor request
- `transporte` - Transport request
- `equipamiento` - Equipment request

**EstadoPedido:**
- `PENDIENTE` - Pedido without accepted oferta
- `COMPROMETIDO` - Oferta accepted, awaiting fulfillment
- `COMPLETADO` - Pedido fulfilled

**EstadoEtapa:**
- `pendiente` - Awaiting funding
- `financiada` - All pedidos comprometido/completado
- `en_ejecucion` - Stage is in execution
- `completada` - Stage finished

**EstadoOferta:**
- `pendiente` - Pending review
- `aceptada` - Accepted
- `rechazada` - Rejected

---

## Architecture Patterns

### Folder Structure

```
app/
├── main.py                    # FastAPI app, CORS, routers
├── config.py                  # Pydantic Settings (env vars)
│
├── api/
│   ├── v1/
│   │   ├── router.py          # Main v1 router
│   │   └── endpoints/         # Route handlers (auth, projects, pedidos, ofertas)
│   └── deps/
│       └── auth.py            # Auth dependencies (get_current_user)
│
├── models/                    # SQLAlchemy ORM models
│   ├── user.py
│   ├── proyecto.py
│   ├── etapa.py
│   ├── pedido.py
│   └── oferta.py
│
├── schemas/                   # Pydantic schemas (request/response)
│   ├── user.py
│   ├── proyecto.py
│   ├── etapa.py
│   ├── pedido.py
│   └── oferta.py
│
├── services/                  # Business logic layer
│   ├── user_service.py
│   ├── proyecto_service.py
│   ├── pedido_service.py
│   └── oferta_service.py
│
├── core/
│   └── security.py            # JWT & password hashing
│
└── db/
    ├── base.py                # SQLAlchemy Base
    └── session.py             # Async session management
```

### Layer Responsibilities

**API Layer** ([app/api/v1/endpoints/](app/api/v1/endpoints/))
- Route definitions and HTTP handling
- Request validation (via Pydantic schemas)
- Response formatting
- Authentication/authorization checks
- Minimal business logic

**Service Layer** ([app/services/](app/services/))
- Business logic and orchestration
- Database operations (CRUD)
- Transaction management
- Domain rules enforcement

**Model Layer** ([app/models/](app/models/))
- SQLAlchemy ORM definitions
- Database schema representation
- Relationships and constraints

**Schema Layer** ([app/schemas/](app/schemas/))
- Pydantic models for API contracts
- Request validation rules
- Response serialization

---

## Development Guidelines

### Key Conventions

1. **All IDs are UUIDs** - Generated server-side using `uuid.uuid4()`
2. **Async/Await Everywhere** - All DB operations are async
3. **Auto Timestamps** - Use `server_default=func.now()` and `onupdate=func.now()`
4. **Cascade Deletes** - Parent deletion cascades to children
5. **JWT Authentication** - Access tokens (15 min) + Refresh tokens (1 day)
6. **Service Pattern** - Business logic in service layer, not endpoints
7. **Type Hints** - Use SQLAlchemy 2.0 `Mapped[]` annotations

### Common Patterns

#### UUID Primary Keys
```python
from uuid import UUID, uuid4
from sqlalchemy.dialects.postgresql import UUID as PGUUID

id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), primary_key=True, default=uuid4
)
```

#### Timestamps
```python
from sqlalchemy import DateTime, func

created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), nullable=False
)
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
)
```

#### Relationships with Cascade
```python
# Parent side (Proyecto)
etapas: Mapped[List["Etapa"]] = relationship(
    back_populates="proyecto", cascade="all, delete-orphan", lazy="joined"
)

# Child side (Etapa)
proyecto: Mapped["Proyecto"] = relationship(back_populates="etapas")
```

#### Async Database Session
```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

async def endpoint(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model))
    await db.commit()
```

#### Protected Endpoints
```python
from app.api.deps.auth import get_current_user
from app.models.user import User

async def endpoint(current_user: User = Depends(get_current_user)):
    # current_user is automatically loaded from JWT token
    pass
```

### Anti-Patterns to Avoid

❌ **Don't use sync database operations** - Always use async/await
❌ **Don't forget `joinedload()`** - Prevent N+1 queries with eager loading
❌ **Don't put business logic in endpoints** - Use service layer
❌ **Don't commit in service layer** - Let caller control transactions
❌ **Don't hardcode secrets** - Use environment variables
❌ **Don't skip migrations** - Always create Alembic migrations for schema changes
❌ **Don't expose password hashes** - Use Pydantic schemas to filter sensitive fields

---

## Quick Reference

### Common Commands

```bash
# Install dependencies
uv sync

# Run development server (auto-reload)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Create new migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Docker: Start services
docker-compose up --build

# Docker: Stop and clean
docker-compose down -v
```

### Environment Variables

Create `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql://projectplanning:projectplanning123@localhost:5432/projectplanning_cloud

# API
API_V1_PREFIX=/api/v1
PROJECT_NAME=ProjectPlanning Cloud Persistence API

# CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Security (CHANGE IN PRODUCTION!)
JWT_SECRET_KEY=your-super-secret-access-key-here
JWT_REFRESH_SECRET_KEY=your-super-secret-refresh-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=1440
```

### Adding a New Feature Checklist

When adding a new feature (e.g., "Comments on Projects"):

1. **Model** - Create SQLAlchemy model in [app/models/](app/models/)
   - Define table schema with UUID PK
   - Add relationships with cascade deletes
   - Include timestamps

2. **Schema** - Create Pydantic schemas in [app/schemas/](app/schemas/)
   - `CommentCreate` - For POST requests (no IDs)
   - `CommentResponse` - For responses (with IDs, timestamps)
   - `CommentUpdate` - For PATCH requests (all optional)

3. **Service** - Create service in [app/services/](app/services/)
   - CRUD operations (create, get, update, delete, list)
   - Business logic and validation
   - Database queries with proper eager loading

4. **Endpoint** - Create endpoint in [app/api/v1/endpoints/](app/api/v1/endpoints/)
   - Route handlers with HTTP methods
   - Request/response type annotations
   - Authentication dependencies
   - Call service layer

5. **Router** - Register in [app/api/v1/router.py](app/api/v1/router.py)
   ```python
   from app.api.v1.endpoints import comments
   api_router.include_router(comments.router, tags=["comments"])
   ```

6. **Migration** - Generate Alembic migration
   ```bash
   uv run alembic revision --autogenerate -m "Add comments table"
   uv run alembic upgrade head
   ```

7. **Test** - Add tests in [tests/](tests/)
   - Happy path scenarios
   - Error cases (404, 403, 422)
   - Authentication checks

### API Documentation

Once running, access interactive API docs:
- **Swagger UI:** http://localhost:8001/docs
- **OpenAPI JSON:** http://localhost:8001/openapi.json

### Current API Endpoints

**Authentication:**
```
POST   /api/v1/auth/register       → Register new user
POST   /api/v1/auth/login          → Login (get tokens)
POST   /api/v1/auth/refresh        → Refresh access token
```

**Projects:**
```
POST   /api/v1/projects            → Create project (with nested etapas/pedidos)
GET    /api/v1/projects/{id}       → Get project with all data
PATCH  /api/v1/projects/{id}       → Update project (Bonita info, etc)
DELETE /api/v1/projects/{id}       → Delete project (cascade)
```

**Pedidos:**
```
POST   /api/v1/projects/{project_id}/etapas/{etapa_id}/pedidos
       → Create pedido for existing etapa

GET    /api/v1/projects/{project_id}/pedidos?estado={pendiente|completado}
       → List all pedidos for a project (optional filter)

DELETE /api/v1/pedidos/{pedido_id}
       → Delete pedido (cascade to ofertas)
```

**Ofertas:**
```
POST   /api/v1/pedidos/{pedido_id}/ofertas
       → Create oferta for pedido

GET    /api/v1/pedidos/{pedido_id}/ofertas
       → List all ofertas for pedido (with user info)

POST   /api/v1/ofertas/{oferta_id}/accept
       → Accept oferta (marks pedido as completado)

POST   /api/v1/ofertas/{oferta_id}/reject
       → Reject oferta
```

### Business Logic: Accepting Ofertas

When a project owner accepts an oferta:
1. Oferta estado → `aceptada`
2. Pedido estado → `completado` (automatically)
3. Other ofertas for the same pedido remain `pendiente`

---

## Design Decisions

### Why Async SQLAlchemy?
- Better performance for I/O-bound operations
- Non-blocking database queries
- Native FastAPI async support
- Scales better with concurrent requests

### Why UUIDs?
- Globally unique across services
- No sequential ID exposure (better security)
- Works well in distributed systems
- No collision risk

### Why Service Layer?
- Separates business logic from HTTP handling
- Easier to test (mock dependencies)
- Reusable across multiple endpoints
- Cleaner code organization

### Why JWT?
- Stateless authentication
- Short-lived access tokens (15 min) + long-lived refresh tokens (1 day)
- No session storage needed
- Works across distributed services

---

**End of Documentation**

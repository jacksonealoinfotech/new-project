# Step-by-Step Feature Development Guide

This guide walks you through adding a new domain feature (e.g., an `organizations` module) to the repository without modifying global infrastructure.

---

### Step 1: Create the Feature Directory
Create `app/modules/<feature_name>/` containing:
```
app/modules/organizations/
├── __init__.py
├── models.py
├── schemas.py
├── repository.py
├── service.py
├── dependencies.py
└── router.py
```

---

### Step 2: Define Persistence Models
In `models.py`, inherit from `Base` and mixins:
```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
```

---

### Step 3: Register Model in Alembic & Generate Migration
Import the new model in `alembic/env.py` and run:
```bash
make migration m="add_organizations_table"
make migrate
```

---

### Step 4: Define Pydantic Schemas
In `schemas.py`:
```python
from pydantic import Field
from app.common.schemas import BaseSchema, IDSchema, TimestampSchema


class OrgCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=255)


class OrgUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=255)


class OrgResponse(IDSchema, TimestampSchema, OrgCreate):
    pass
```

---

### Step 5: Implement Repository
In `repository.py`:
```python
from app.repositories.base import BaseRepository
from .models import Organization


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session):
        super().__init__(model=Organization, session=session)
```

---

### Step 6: Implement Service & Transaction Ownership
In `service.py`:
```python
from app.db.transaction import in_transaction
from .models import Organization
from .repository import OrganizationRepository


class OrganizationService:
    def __init__(self, session):
        self.session = session
        self.repo = OrganizationRepository(session)

    async def create_org(self, data):
        async with in_transaction(self.session):
            org = Organization(name=data.name)
            return await self.repo.create(org)
```

---

### Step 7: Create Router & Wire Dependencies
In `router.py`:
```python
from fastapi import APIRouter, Depends, status
from app.modules.auth.dependencies import get_current_active_user
from .schemas import OrgCreate, OrgResponse
from .service import OrganizationService
from .dependencies import get_org_service

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("/", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrgCreate,
    current_user=Depends(get_current_active_user),
    service: OrganizationService = Depends(get_org_service),
):
    org = await service.create_org(data)
    return OrgResponse.model_validate(org)
```

---

### Step 8: Register Router in `app/api/v1/router.py`
```python
from app.modules.organizations.router import router as orgs_router

v1_router.include_router(orgs_router)
```

---

### Step 9: Add Automated Tests
Create `tests/api/test_organizations.py` and run:
```bash
make check
```
All linting, typing, and tests will automatically run across the new module!

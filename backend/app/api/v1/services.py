"""
Services API endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentAdmin, CurrentUser, DbSession
from app.models.service import Service
from app.models.user import UserRole
from app.schemas.service import (
    ServiceCreate,
    ServiceListResponse,
    ServiceResponse,
    ServiceUpdate,
)

router = APIRouter()


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    db: DbSession,
    current_user: CurrentAdmin,
    service_in: ServiceCreate,
) -> Service:
    """Create a new service (admin only)."""
    service = Service(
        name=service_in.name,
        code=service_in.code,
        category=service_in.category,
        description=service_in.description,
        price=service_in.price,
        tax_rate=service_in.tax_rate,
        duration_minutes=service_in.duration_minutes,
        clinic_id=service_in.clinic_id,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)

    return service


@router.get("/", response_model=list[ServiceListResponse])
async def list_services(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID | None = None,
    category: str | None = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[Service]:
    """List services with optional filters."""
    query = select(Service)

    if clinic_id:
        if (
            current_user.role != UserRole.ADMIN.value
            and current_user.clinic_id != clinic_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        query = query.where(Service.clinic_id == clinic_id)
    elif current_user.role != UserRole.ADMIN.value and current_user.clinic_id:
        query = query.where(Service.clinic_id == current_user.clinic_id)

    if category:
        query = query.where(Service.category == category)

    if active_only:
        query = query.where(Service.is_active == True)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return list(result.scalars().all())


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    db: DbSession,
    current_user: CurrentUser,
    service_id: UUID,
) -> Service:
    """Get a specific service."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != service.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return service


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    db: DbSession,
    current_user: CurrentAdmin,
    service_id: UUID,
    service_in: ServiceUpdate,
) -> Service:
    """Update a service (admin only)."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    update_data = service_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)

    await db.commit()
    await db.refresh(service)

    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    db: DbSession,
    current_user: CurrentAdmin,
    service_id: UUID,
) -> None:
    """Deactivate a service (admin only)."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    service.is_active = False
    await db.commit()

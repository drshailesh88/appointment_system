"""
Invoices API endpoints.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.doctor import Doctor
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.patient import Patient
from app.models.service import Service
from app.models.user import UserRole
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceItemResponse,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceSummary,
    InvoiceUpdate,
)

router = APIRouter()


async def generate_invoice_number(db, clinic_id: UUID) -> str:
    """Generate unique invoice number."""
    # Format: INV-YYYYMMDD-XXXX
    today = date.today()
    prefix = f"INV-{today.strftime('%Y%m%d')}"

    # Get count for today
    result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.invoice_number.like(f"{prefix}%"),
            Invoice.clinic_id == clinic_id,
        )
    )
    count = result.scalar() or 0

    return f"{prefix}-{count + 1:04d}"


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    db: DbSession,
    current_user: CurrentUser,
    invoice_in: InvoiceCreate,
) -> Invoice:
    """Create a new invoice."""
    # Verify access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != invoice_in.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Verify patient exists
    patient_result = await db.execute(
        select(Patient).where(Patient.id == invoice_in.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Generate invoice number
    invoice_number = await generate_invoice_number(db, invoice_in.clinic_id)

    # Create invoice
    invoice = Invoice(
        invoice_number=invoice_number,
        patient_id=invoice_in.patient_id,
        doctor_id=invoice_in.doctor_id,
        clinic_id=invoice_in.clinic_id,
        invoice_date=invoice_in.invoice_date,
        due_date=invoice_in.due_date,
        notes=invoice_in.notes,
        discount_amount=invoice_in.discount_amount,
        discount_reason=invoice_in.discount_reason,
        gstin=invoice_in.gstin,
        status=InvoiceStatus.PENDING.value,
    )

    # Add items and calculate totals
    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")

    for item_in in invoice_in.items:
        item_subtotal = item_in.unit_price * item_in.quantity
        item_tax = item_subtotal * (item_in.tax_rate / 100)

        item = InvoiceItem(
            description=item_in.description,
            quantity=item_in.quantity,
            unit_price=item_in.unit_price,
            tax_rate=item_in.tax_rate,
            subtotal=item_subtotal,
            tax_amount=item_tax,
            total=item_subtotal + item_tax,
            service_id=item_in.service_id,
            hsn_code=item_in.hsn_code,
        )
        invoice.items.append(item)

        subtotal += item_subtotal
        tax_total += item_tax

    invoice.subtotal = subtotal
    invoice.tax_amount = tax_total
    invoice.total_amount = subtotal + tax_total - invoice_in.discount_amount

    # Split GST (18% = 9% CGST + 9% SGST for intra-state)
    invoice.cgst_amount = tax_total / 2
    invoice.sgst_amount = tax_total / 2

    db.add(invoice)
    await db.commit()

    # Reload with relationships for response
    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.patient),
            selectinload(Invoice.doctor),
        )
        .where(Invoice.id == invoice.id)
    )
    invoice = result.scalar_one()

    return invoice


@router.get("/", response_model=list[InvoiceListResponse])
async def list_invoices(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID | None = None,
    patient_id: UUID | None = None,
    status_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List invoices with filters."""
    query = (
        select(Invoice)
        .options(selectinload(Invoice.patient))
    )

    if clinic_id:
        if (
            current_user.role != UserRole.ADMIN.value
            and current_user.clinic_id != clinic_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        query = query.where(Invoice.clinic_id == clinic_id)
    elif current_user.role != UserRole.ADMIN.value and current_user.clinic_id:
        query = query.where(Invoice.clinic_id == current_user.clinic_id)

    if patient_id:
        query = query.where(Invoice.patient_id == patient_id)

    if status_filter:
        query = query.where(Invoice.status == status_filter)

    if date_from:
        query = query.where(Invoice.invoice_date >= date_from)

    if date_to:
        query = query.where(Invoice.invoice_date <= date_to)

    query = (
        query.order_by(Invoice.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    invoices = result.scalars().all()

    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "patient_id": inv.patient_id,
            "patient_name": inv.patient.full_name if inv.patient else "Unknown",
            "total_amount": inv.total_amount,
            "paid_amount": inv.paid_amount,
            "balance_due": inv.balance_due,
            "status": inv.status,
            "invoice_date": inv.invoice_date,
            "due_date": inv.due_date,
        }
        for inv in invoices
    ]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    db: DbSession,
    current_user: CurrentUser,
    invoice_id: UUID,
) -> Invoice:
    """Get a specific invoice."""
    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.patient),
            selectinload(Invoice.doctor),
        )
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != invoice.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    db: DbSession,
    current_user: CurrentUser,
    invoice_id: UUID,
    invoice_in: InvoiceUpdate,
) -> Invoice:
    """Update an invoice."""
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != invoice.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Can't update paid or cancelled invoices
    if invoice.status in [InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update invoice with status: {invoice.status}",
        )

    update_data = invoice_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(invoice, field, value.value)
        else:
            setattr(invoice, field, value)

    # Recalculate total if discount changed
    if "discount_amount" in update_data:
        invoice.total_amount = (
            invoice.subtotal + invoice.tax_amount - invoice.discount_amount
        )

    await db.commit()

    # Reload with relationships for response
    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.patient),
            selectinload(Invoice.doctor),
        )
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one()

    return invoice


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    db: DbSession,
    current_user: CurrentUser,
    invoice_id: UUID,
    reason: str | None = None,
) -> Invoice:
    """Cancel an invoice."""
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if invoice.status == InvoiceStatus.PAID.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a paid invoice",
        )

    invoice.status = InvoiceStatus.CANCELLED.value
    invoice.is_cancelled = True
    invoice.cancellation_reason = reason

    await db.commit()

    # Reload with relationships for response
    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.patient),
            selectinload(Invoice.doctor),
        )
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one()

    return invoice


@router.get("/summary/clinic/{clinic_id}", response_model=InvoiceSummary)
async def get_invoice_summary(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """Get invoice summary for a clinic."""
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    query = select(Invoice).where(
        Invoice.clinic_id == clinic_id,
        Invoice.is_cancelled == False,
    )

    if date_from:
        query = query.where(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.where(Invoice.invoice_date <= date_to)

    result = await db.execute(query)
    invoices = result.scalars().all()

    total_amount = sum(inv.total_amount for inv in invoices)
    paid_amount = sum(inv.paid_amount for inv in invoices)
    pending_amount = total_amount - paid_amount

    today = date.today()
    overdue_count = sum(
        1 for inv in invoices
        if inv.due_date and inv.due_date < today and inv.balance_due > 0
    )

    return {
        "total_invoices": len(invoices),
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "pending_amount": pending_amount,
        "overdue_count": overdue_count,
    }

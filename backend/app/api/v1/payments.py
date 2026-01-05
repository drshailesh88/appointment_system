"""
Payments API endpoints.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.user import UserRole
from app.schemas.payment import (
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    PaymentSummary,
    PaymentUpdate,
    RefundRequest,
)

router = APIRouter()


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    db: DbSession,
    current_user: CurrentUser,
    payment_in: PaymentCreate,
) -> Payment:
    """Record a payment."""
    # Get invoice
    result = await db.execute(
        select(Invoice).where(Invoice.id == payment_in.invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != invoice.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Can't pay cancelled invoice
    if invoice.status == InvoiceStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pay a cancelled invoice",
        )

    # Check if payment exceeds balance
    if payment_in.amount > invoice.balance_due:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount exceeds balance due: ₹{invoice.balance_due}",
        )

    payment = Payment(
        invoice_id=payment_in.invoice_id,
        amount=payment_in.amount,
        payment_method=payment_in.payment_method.value,
        status=PaymentStatus.COMPLETED.value,
        payment_date=payment_in.payment_date,
        transaction_id=payment_in.transaction_id,
        receipt_number=payment_in.receipt_number,
        upi_transaction_id=payment_in.upi_transaction_id,
        upi_vpa=payment_in.upi_vpa,
        notes=payment_in.notes,
        collected_by=payment_in.collected_by or current_user.name,
    )
    db.add(payment)

    # Update invoice
    invoice.paid_amount += payment_in.amount

    if invoice.paid_amount >= invoice.total_amount:
        invoice.status = InvoiceStatus.PAID.value
    elif invoice.paid_amount > 0:
        invoice.status = InvoiceStatus.PARTIALLY_PAID.value

    await db.commit()

    # Reload with relationships for response
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.invoice))
        .where(Payment.id == payment.id)
    )
    payment = result.scalar_one()

    return payment


@router.get("/", response_model=list[PaymentListResponse])
async def list_payments(
    db: DbSession,
    current_user: CurrentUser,
    invoice_id: UUID | None = None,
    payment_method: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List payments with filters."""
    query = (
        select(Payment)
        .options(selectinload(Payment.invoice))
    )

    if current_user.role != UserRole.ADMIN.value and current_user.clinic_id:
        query = query.join(Invoice).where(Invoice.clinic_id == current_user.clinic_id)

    if invoice_id:
        query = query.where(Payment.invoice_id == invoice_id)

    if payment_method:
        query = query.where(Payment.payment_method == payment_method)

    if date_from:
        query = query.where(Payment.payment_date >= date_from)

    if date_to:
        query = query.where(Payment.payment_date <= date_to)

    query = (
        query.order_by(Payment.payment_date.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    payments = result.scalars().all()

    return [
        {
            "id": p.id,
            "invoice_id": p.invoice_id,
            "invoice_number": p.invoice.invoice_number if p.invoice else None,
            "amount": p.amount,
            "payment_method": p.payment_method,
            "status": p.status,
            "payment_date": p.payment_date,
            "receipt_number": p.receipt_number,
        }
        for p in payments
    ]


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    db: DbSession,
    current_user: CurrentUser,
    payment_id: UUID,
) -> Payment:
    """Get a specific payment."""
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.invoice))
        .where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    # Check access via invoice
    if (
        current_user.role != UserRole.ADMIN.value
        and payment.invoice
        and current_user.clinic_id != payment.invoice.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return payment


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
    db: DbSession,
    current_user: CurrentUser,
    payment_id: UUID,
    refund_in: RefundRequest,
) -> Payment:
    """Process a refund."""
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.invoice))
        .where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    if payment.status != PaymentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only refund completed payments",
        )

    max_refund = payment.amount - payment.refund_amount
    if refund_in.amount > max_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount exceeds available: ₹{max_refund}",
        )

    payment.refund_amount += refund_in.amount
    payment.refund_reason = refund_in.reason
    payment.refund_date = datetime.now(timezone.utc)

    if payment.refund_amount >= payment.amount:
        payment.status = PaymentStatus.REFUNDED.value
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED.value

    # Update invoice
    if payment.invoice:
        payment.invoice.paid_amount -= refund_in.amount
        if payment.invoice.paid_amount <= 0:
            payment.invoice.status = InvoiceStatus.PENDING.value
        elif payment.invoice.paid_amount < payment.invoice.total_amount:
            payment.invoice.status = InvoiceStatus.PARTIALLY_PAID.value

    await db.commit()

    # Reload with relationships for response
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.invoice))
        .where(Payment.id == payment_id)
    )
    payment = result.scalar_one()

    return payment


@router.get("/summary/clinic/{clinic_id}", response_model=PaymentSummary)
async def get_payment_summary(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """Get payment summary for a clinic."""
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    query = (
        select(Payment)
        .join(Invoice)
        .where(
            Invoice.clinic_id == clinic_id,
            Payment.status.in_([
                PaymentStatus.COMPLETED.value,
                PaymentStatus.PARTIALLY_REFUNDED.value,
            ]),
        )
    )

    if date_from:
        query = query.where(Payment.payment_date >= date_from)
    if date_to:
        query = query.where(Payment.payment_date <= date_to)

    result = await db.execute(query)
    payments = result.scalars().all()

    total_collected = Decimal("0.00")
    cash_collected = Decimal("0.00")
    upi_collected = Decimal("0.00")
    card_collected = Decimal("0.00")
    refunded = Decimal("0.00")

    for p in payments:
        net = p.amount - p.refund_amount
        total_collected += net
        refunded += p.refund_amount

        if p.payment_method == PaymentMethod.CASH.value:
            cash_collected += net
        elif p.payment_method == PaymentMethod.UPI.value:
            upi_collected += net
        elif p.payment_method == PaymentMethod.CARD.value:
            card_collected += net

    # Get pending amount from invoices
    pending_result = await db.execute(
        select(Invoice).where(
            Invoice.clinic_id == clinic_id,
            Invoice.status.in_([
                InvoiceStatus.PENDING.value,
                InvoiceStatus.PARTIALLY_PAID.value,
            ]),
        )
    )
    pending_invoices = pending_result.scalars().all()
    pending_amount = sum(inv.balance_due for inv in pending_invoices)

    return {
        "total_collected": total_collected,
        "cash_collected": cash_collected,
        "upi_collected": upi_collected,
        "card_collected": card_collected,
        "pending_amount": pending_amount,
        "refunded_amount": refunded,
        "transaction_count": len(payments),
    }

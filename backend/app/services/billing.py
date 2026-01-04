"""
Billing service for invoice and GST calculations.
"""

from decimal import Decimal
from enum import Enum
from typing import Any

from app.models.invoice import Invoice, InvoiceItem


class GSTType(str, Enum):
    """GST calculation type."""

    INTRA_STATE = "intra_state"  # CGST + SGST
    INTER_STATE = "inter_state"  # IGST
    EXEMPT = "exempt"            # No GST


# Healthcare service HSN/SAC codes
HEALTHCARE_HSN_CODES = {
    "consultation": "9993",
    "diagnostic": "9993",
    "surgery": "9993",
    "hospital": "9993",
    "ambulance": "9994",
    "lab_test": "9993",
    "imaging": "9993",  # X-ray, CT, MRI, etc.
}

# GST exempt services (under Section 12 of CGST Act)
GST_EXEMPT_SERVICES = {
    "hospital_room_charges",  # Below Rs 5000 per day
    "diagnostic_tests_prescribed",  # Pathological or diagnostic tests
    "transportation_patient",  # Transport of patient in ambulance
}

# Standard GST rate for healthcare services (most are exempt, but some attract GST)
STANDARD_GST_RATE = Decimal("18.00")  # 18% = 9% CGST + 9% SGST (or 18% IGST)


class BillingService:
    """Service for billing calculations and GST compliance."""

    @staticmethod
    def calculate_gst(
        amount: Decimal,
        clinic_state: str,
        patient_state: str,
        is_exempt: bool = False,
        custom_rate: Decimal | None = None,
    ) -> dict[str, Decimal]:
        """
        Calculate GST based on state and exemption status.

        Args:
            amount: Taxable amount (before tax)
            clinic_state: Clinic's state code (e.g., "MH" for Maharashtra)
            patient_state: Patient's state code
            is_exempt: Whether service is GST exempt
            custom_rate: Custom GST rate (if different from standard)

        Returns:
            Dictionary with CGST, SGST, IGST amounts and total tax
        """
        if is_exempt:
            return {
                "cgst": Decimal("0.00"),
                "sgst": Decimal("0.00"),
                "igst": Decimal("0.00"),
                "total_tax": Decimal("0.00"),
                "gst_type": GSTType.EXEMPT.value,
            }

        gst_rate = custom_rate or STANDARD_GST_RATE

        # Intra-state: CGST + SGST (each half of total rate)
        if clinic_state.upper() == patient_state.upper():
            half_rate = gst_rate / 2
            cgst = (amount * half_rate / 100).quantize(Decimal("0.01"))
            sgst = cgst  # Equal split
            igst = Decimal("0.00")
            gst_type = GSTType.INTRA_STATE.value
        # Inter-state: IGST (full rate)
        else:
            cgst = Decimal("0.00")
            sgst = Decimal("0.00")
            igst = (amount * gst_rate / 100).quantize(Decimal("0.01"))
            gst_type = GSTType.INTER_STATE.value

        total_tax = cgst + sgst + igst

        return {
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,
            "total_tax": total_tax,
            "gst_type": gst_type,
            "gst_rate": gst_rate,
        }

    @staticmethod
    def calculate_invoice_totals(
        items: list[InvoiceItem],
        clinic_state: str,
        patient_state: str,
        discount_amount: Decimal = Decimal("0.00"),
    ) -> dict[str, Any]:
        """
        Calculate invoice totals with GST breakdown.

        Args:
            items: List of invoice items
            clinic_state: Clinic's state code
            patient_state: Patient's state code
            discount_amount: Discount to apply on subtotal

        Returns:
            Dictionary with subtotal, tax breakdown, and total
        """
        subtotal = sum(item.subtotal for item in items)

        # Apply discount to subtotal
        taxable_amount = subtotal - discount_amount
        if taxable_amount < 0:
            taxable_amount = Decimal("0.00")

        # Calculate GST
        # Note: In healthcare, most services are exempt, but we calculate
        # based on item tax_rate if specified
        total_cgst = Decimal("0.00")
        total_sgst = Decimal("0.00")
        total_igst = Decimal("0.00")
        total_tax = Decimal("0.00")

        for item in items:
            if item.tax_rate > 0:
                item_taxable = item.subtotal * (taxable_amount / subtotal) if subtotal > 0 else Decimal("0.00")

                gst_calc = BillingService.calculate_gst(
                    amount=item_taxable,
                    clinic_state=clinic_state,
                    patient_state=patient_state,
                    custom_rate=item.tax_rate,
                )

                total_cgst += gst_calc["cgst"]
                total_sgst += gst_calc["sgst"]
                total_igst += gst_calc["igst"]
                total_tax += gst_calc["total_tax"]

        total_amount = taxable_amount + total_tax

        return {
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "taxable_amount": taxable_amount,
            "cgst_amount": total_cgst,
            "sgst_amount": total_sgst,
            "igst_amount": total_igst,
            "tax_amount": total_tax,
            "total_amount": total_amount,
            "gst_type": GSTType.INTRA_STATE.value if clinic_state.upper() == patient_state.upper() else GSTType.INTER_STATE.value,
        }

    @staticmethod
    def calculate_insurance_split(
        total_amount: Decimal,
        copay_percentage: Decimal = Decimal("0.00"),
        deductible: Decimal = Decimal("0.00"),
        approved_amount: Decimal | None = None,
    ) -> dict[str, Decimal]:
        """
        Calculate patient vs insurance portions of a bill.

        Args:
            total_amount: Total invoice amount
            copay_percentage: Patient's copay percentage (e.g., 10%)
            deductible: Deductible amount patient must pay first
            approved_amount: Amount approved by insurance (if known)

        Returns:
            Dictionary with patient_portion, insurance_portion, and breakdown
        """
        # Patient pays deductible first
        patient_deductible = min(deductible, total_amount)
        remaining_after_deductible = total_amount - patient_deductible

        # Calculate copay on remaining amount
        patient_copay = (remaining_after_deductible * copay_percentage / 100).quantize(Decimal("0.01"))

        # Insurance portion (before approval)
        potential_insurance_portion = remaining_after_deductible - patient_copay

        # If insurance has approved a specific amount
        if approved_amount is not None:
            actual_insurance_portion = min(approved_amount, potential_insurance_portion)
            patient_additional = potential_insurance_portion - actual_insurance_portion
        else:
            actual_insurance_portion = potential_insurance_portion
            patient_additional = Decimal("0.00")

        # Total patient portion
        patient_portion = patient_deductible + patient_copay + patient_additional

        return {
            "patient_portion": patient_portion,
            "insurance_portion": actual_insurance_portion,
            "patient_deductible": patient_deductible,
            "patient_copay": patient_copay,
            "patient_additional": patient_additional,
            "total_amount": total_amount,
        }

    @staticmethod
    def get_hsn_code(service_type: str) -> str:
        """
        Get HSN/SAC code for a service type.

        Args:
            service_type: Type of service (consultation, diagnostic, etc.)

        Returns:
            HSN/SAC code
        """
        return HEALTHCARE_HSN_CODES.get(service_type.lower(), "9993")

    @staticmethod
    def is_service_exempt(service_type: str, amount: Decimal | None = None) -> bool:
        """
        Check if a service is GST exempt.

        Args:
            service_type: Type of service
            amount: Service amount (for threshold checks like room charges)

        Returns:
            True if service is exempt from GST
        """
        service_lower = service_type.lower()

        # Check explicit exemptions
        if service_lower in GST_EXEMPT_SERVICES:
            # Hospital room charges exempt only if < Rs 5000/day
            if service_lower == "hospital_room_charges" and amount:
                return amount < Decimal("5000.00")
            return True

        return False

    @staticmethod
    def format_gst_invoice_data(invoice: Invoice, clinic: Any, patient: Any) -> dict[str, Any]:
        """
        Format invoice data for GST-compliant PDF generation.

        Args:
            invoice: Invoice object
            clinic: Clinic object
            patient: Patient object

        Returns:
            Dictionary with formatted invoice data for PDF
        """
        return {
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.strftime("%d-%b-%Y"),
            "due_date": invoice.due_date.strftime("%d-%b-%Y") if invoice.due_date else None,

            # Clinic details
            "clinic_name": clinic.name,
            "clinic_address": clinic.address,
            "clinic_city": clinic.city,
            "clinic_state": clinic.state,
            "clinic_pincode": clinic.pincode,
            "clinic_gstin": invoice.gstin or clinic.gstin if hasattr(clinic, 'gstin') else None,
            "clinic_phone": clinic.phone if hasattr(clinic, 'phone') else None,

            # Patient details
            "patient_name": patient.full_name,
            "patient_address": patient.address,
            "patient_city": patient.city,
            "patient_state": patient.state,
            "patient_pincode": patient.pincode,
            "patient_phone": patient.phone,

            # Invoice items
            "items": [
                {
                    "sr_no": idx + 1,
                    "description": item.description,
                    "hsn_code": item.hsn_code or "9993",
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "taxable_value": float(item.subtotal),
                    "tax_rate": float(item.tax_rate),
                    "tax_amount": float(item.tax_amount),
                    "total": float(item.total),
                }
                for idx, item in enumerate(invoice.items)
            ],

            # Totals
            "subtotal": float(invoice.subtotal),
            "discount_amount": float(invoice.discount_amount),
            "discount_reason": invoice.discount_reason,
            "taxable_amount": float(invoice.subtotal - invoice.discount_amount),

            # GST breakdown
            "cgst_amount": float(invoice.cgst_amount),
            "sgst_amount": float(invoice.sgst_amount),
            "igst_amount": float(invoice.igst_amount),
            "total_tax": float(invoice.tax_amount),

            # Is intra-state or inter-state
            "is_intra_state": invoice.igst_amount == 0,

            # Final amounts
            "total_amount": float(invoice.total_amount),
            "paid_amount": float(invoice.paid_amount),
            "balance_due": float(invoice.balance_due),

            # Status
            "status": invoice.status,
            "notes": invoice.notes,
        }

    @staticmethod
    def validate_gstin(gstin: str) -> bool:
        """
        Validate GSTIN format.

        Format: 2 digits (state code) + 10 alphanumeric (PAN) + 1 alphanumeric + Z + 1 alphanumeric
        Example: 27AABCT1234F1Z5

        Args:
            gstin: GSTIN string to validate

        Returns:
            True if valid format
        """
        if not gstin or len(gstin) != 15:
            return False

        # Check format: 2 digits + 10 alphanumeric + 1 alphanumeric + Z + 1 alphanumeric
        import re
        pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        return bool(re.match(pattern, gstin.upper()))

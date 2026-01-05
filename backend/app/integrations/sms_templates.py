"""
SMS Templates for MSG91 (DLT Compliant).

All templates must be registered with DLT (Distributed Ledger Technology)
for TRAI compliance in India.

IMPORTANT: Replace template_id values with actual DLT registered template IDs
before going to production.

DLT Registration Process:
1. Login to MSG91 dashboard
2. Navigate to DLT section
3. Submit templates with variables
4. Get approval from telecom operator
5. Copy template IDs here

Variables in templates use {VAR} format for MSG91.
"""

from enum import Enum
from typing import Dict, List


class MessageType(str, Enum):
    """Types of SMS messages."""

    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_CANCELLATION = "appointment_cancellation"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"
    OTP = "otp"
    WELCOME = "welcome"
    PAYMENT_RECEIPT = "payment_receipt"
    WAITLIST_NOTIFICATION = "waitlist_notification"
    SLOT_OFFER = "slot_offer"
    PRESCRIPTION_READY = "prescription_ready"
    LAB_REPORT_READY = "lab_report_ready"


class SMSTemplate:
    """SMS template with DLT compliance."""

    def __init__(
        self,
        template_id: str,
        template: str,
        variables: List[str],
        category: str = "transactional",
        description: str = "",
    ):
        """
        Initialize SMS template.

        Args:
            template_id: DLT registered template ID
            template: Template text with {VAR} placeholders
            variables: List of variable names in order
            category: Template category (transactional/promotional)
            description: Template description
        """
        self.template_id = template_id
        self.template = template
        self.variables = variables
        self.category = category
        self.description = description

    def format(self, **kwargs) -> str:
        """
        Format template with variables.

        Args:
            **kwargs: Variable values

        Returns:
            Formatted message
        """
        return self.template.format(**kwargs)

    def get_msg91_vars(self, **kwargs) -> Dict[str, str]:
        """
        Get MSG91 format variables (VAR1, VAR2, etc).

        Args:
            **kwargs: Variable values

        Returns:
            Dict with VAR1, VAR2, etc.
        """
        msg91_vars = {}
        for i, var_name in enumerate(self.variables, 1):
            if var_name in kwargs:
                msg91_vars[f"VAR{i}"] = str(kwargs[var_name])
        return msg91_vars


# DLT Registered Templates
# IMPORTANT: Replace these template IDs with your actual DLT registered IDs

TEMPLATES = {
    MessageType.APPOINTMENT_CONFIRMATION: SMSTemplate(
        template_id="1107170557711953593",  # Replace with actual DLT template ID
        template=(
            "Dear {patient_name}, your appointment with Dr. {doctor_name} is confirmed "
            "for {date} at {time}. Token No: {token}. Clinic: {clinic_name}. - DocAssist"
        ),
        variables=["patient_name", "doctor_name", "date", "time", "token", "clinic_name"],
        category="transactional",
        description="Appointment confirmation message",
    ),
    MessageType.APPOINTMENT_REMINDER: SMSTemplate(
        template_id="1107170557720342197",  # Replace with actual DLT template ID
        template=(
            "Reminder: Your appointment with Dr. {doctor_name} is tomorrow at {time}. "
            "Please arrive 10 minutes early. Call {clinic_phone} for any queries. - DocAssist"
        ),
        variables=["doctor_name", "time", "clinic_phone"],
        category="transactional",
        description="Appointment reminder (24 hours before)",
    ),
    MessageType.APPOINTMENT_CANCELLATION: SMSTemplate(
        template_id="1107170557728730798",  # Replace with actual DLT template ID
        template=(
            "Your appointment with Dr. {doctor_name} on {date} at {time} has been cancelled. "
            "Reason: {reason}. Please reschedule if needed. - DocAssist"
        ),
        variables=["doctor_name", "date", "time", "reason"],
        category="transactional",
        description="Appointment cancellation notification",
    ),
    MessageType.APPOINTMENT_RESCHEDULED: SMSTemplate(
        template_id="1107170557737119399",  # Replace with actual DLT template ID
        template=(
            "Your appointment has been rescheduled. New date: {new_date}, Time: {new_time}. "
            "Dr. {doctor_name}. Token: {token}. - DocAssist"
        ),
        variables=["new_date", "new_time", "doctor_name", "token"],
        category="transactional",
        description="Appointment rescheduled notification",
    ),
    MessageType.OTP: SMSTemplate(
        template_id="1107170557745508000",  # Replace with actual DLT template ID
        template=(
            "{otp} is your One-Time Password (OTP) for DocAssist. "
            "Valid for {validity} minutes. Do not share this with anyone. - DocAssist"
        ),
        variables=["otp", "validity"],
        category="transactional",
        description="OTP for patient authentication",
    ),
    MessageType.WELCOME: SMSTemplate(
        template_id="1107170557753896601",  # Replace with actual DLT template ID
        template=(
            "Welcome to {clinic_name}! Your registration is successful. "
            "Download the DocAssist app to book appointments easily. - DocAssist"
        ),
        variables=["clinic_name"],
        category="transactional",
        description="Welcome message for new patients",
    ),
    MessageType.PAYMENT_RECEIPT: SMSTemplate(
        template_id="1107170557762285202",  # Replace with actual DLT template ID
        template=(
            "Payment received: Rs. {amount} for Invoice #{invoice_number}. "
            "Receipt sent to your email. Thank you! - {clinic_name}"
        ),
        variables=["amount", "invoice_number", "clinic_name"],
        category="transactional",
        description="Payment receipt confirmation",
    ),
    MessageType.WAITLIST_NOTIFICATION: SMSTemplate(
        template_id="1107170557770673803",  # Replace with actual DLT template ID
        template=(
            "Good news! A slot is available with Dr. {doctor_name} on {date} at {time}. "
            "Reply YES to book or call {clinic_phone}. - DocAssist"
        ),
        variables=["doctor_name", "date", "time", "clinic_phone"],
        category="transactional",
        description="Waitlist slot available notification",
    ),
    MessageType.SLOT_OFFER: SMSTemplate(
        template_id="1107170557779062404",  # Replace with actual DLT template ID
        template=(
            "Slot available: Dr. {doctor_name} has an opening on {date} at {time}. "
            "Book now! Call {clinic_phone} or use the app. - DocAssist"
        ),
        variables=["doctor_name", "date", "time", "clinic_phone"],
        category="promotional",
        description="Promotional slot availability message",
    ),
    MessageType.PRESCRIPTION_READY: SMSTemplate(
        template_id="1107170557787451005",  # Replace with actual DLT template ID
        template=(
            "Your prescription is ready. Visit {clinic_name} to collect or "
            "download from the app. Patient: {patient_name}. - DocAssist"
        ),
        variables=["clinic_name", "patient_name"],
        category="transactional",
        description="Prescription ready for collection",
    ),
    MessageType.LAB_REPORT_READY: SMSTemplate(
        template_id="1107170557795839606",  # Replace with actual DLT template ID
        template=(
            "Your lab report is ready. Available in the DocAssist app. "
            "Patient: {patient_name}. For queries, call {clinic_phone}. - DocAssist"
        ),
        variables=["patient_name", "clinic_phone"],
        category="transactional",
        description="Lab report ready notification",
    ),
}


def get_template(message_type: MessageType) -> SMSTemplate:
    """
    Get SMS template by type.

    Args:
        message_type: Type of message

    Returns:
        SMSTemplate instance

    Raises:
        KeyError: If template not found
    """
    return TEMPLATES[message_type]


def format_message(message_type: MessageType, **kwargs) -> tuple[str, str]:
    """
    Format SMS message with variables.

    Args:
        message_type: Type of message
        **kwargs: Variable values

    Returns:
        Tuple of (formatted_message, template_id)

    Raises:
        KeyError: If template not found
    """
    template = get_template(message_type)
    message = template.format(**kwargs)
    return message, template.template_id


def get_msg91_payload(message_type: MessageType, **kwargs) -> Dict:
    """
    Get MSG91 API payload for template.

    Args:
        message_type: Type of message
        **kwargs: Variable values

    Returns:
        Dict with MSG91 API payload
    """
    template = get_template(message_type)
    return {
        "template_id": template.template_id,
        **template.get_msg91_vars(**kwargs),
    }


# DLT Entity ID - Replace with your registered entity ID
DLT_ENTITY_ID = "1101234567890123456"  # Example format

# Sender IDs - Must be DLT registered
SENDER_IDS = {
    "transactional": "DOCAST",  # 6 characters, DLT registered
    "promotional": "DOCPRO",  # 6 characters, DLT registered
}

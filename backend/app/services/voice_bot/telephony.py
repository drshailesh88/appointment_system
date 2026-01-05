"""
Telephony integration using Twilio.

Phase 18: Voice Bot / Phone Automation

Handles:
- Incoming/outbound call management
- TwiML generation for Twilio
- Call status updates
- WebSocket connection for real-time audio streaming
"""

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class TelephonyService:
    """Telephony service using Twilio."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        phone_number: str,
        webhook_url: str,
    ):
        """
        Initialize telephony service.

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            phone_number: Twilio phone number
            webhook_url: Public webhook URL for callbacks
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.phone_number = phone_number
        self.webhook_url = webhook_url
        self._client = None

    @property
    def client(self):
        """Get or create Twilio client (lazy loading)."""
        if self._client is None:
            try:
                from twilio.rest import Client

                self._client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized")
            except ImportError:
                logger.error("Twilio library not installed. Install with: pip install twilio")
                raise
        return self._client

    def generate_twiml_connect(self, call_sid: str) -> str:
        """
        Generate TwiML to connect call to WebSocket for real-time audio streaming.

        Args:
            call_sid: Twilio call SID

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import Connect, VoiceResponse

            response = VoiceResponse()

            # Connect to our WebSocket for bidirectional audio streaming
            connect = Connect()
            connect.stream(
                url=f"{self.webhook_url}/api/v1/voice-bot/ws/{call_sid}",
                track="both_tracks",  # Inbound + outbound audio
            )
            response.append(connect)

            return str(response)

        except ImportError:
            logger.error("Twilio library not installed")
            raise

    def generate_twiml_say(self, message: str, language: str = "en") -> str:
        """
        Generate TwiML to speak a message (fallback if WebSocket unavailable).

        Args:
            message: Message to speak
            language: Language code

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse

            response = VoiceResponse()

            # Map language codes to Twilio voices
            voice_map = {
                "hi": "Polly.Aditi",  # Hindi
                "en": "Polly.Raveena",  # Indian English
                "ta": "Polly.Aditi",  # Use Hindi voice for Tamil (best available)
                "te": "Polly.Aditi",  # Use Hindi voice for Telugu
            }

            voice = voice_map.get(language, "Polly.Raveena")

            response.say(message, voice=voice, language=language)

            return str(response)

        except ImportError:
            logger.error("Twilio library not installed")
            raise

    async def initiate_outbound_call(
        self,
        to_number: str,
        clinic_id: UUID,
        purpose: str = "appointment_reminder",
        appointment_id: Optional[UUID] = None,
    ) -> dict:
        """
        Initiate outbound call (e.g., appointment reminder).

        Args:
            to_number: Phone number to call (E.164 format)
            clinic_id: Clinic ID
            purpose: Call purpose
            appointment_id: Optional appointment ID

        Returns:
            Call information dict
        """
        try:
            # Format phone number (ensure +91 prefix for India)
            if not to_number.startswith("+"):
                to_number = f"+91{to_number}"

            # Create call
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=f"{self.webhook_url}/api/v1/voice-bot/outbound-handler",
                status_callback=f"{self.webhook_url}/api/v1/voice-bot/status",
                status_callback_event=[
                    "initiated",
                    "ringing",
                    "answered",
                    "completed",
                ],
                status_callback_method="POST",
            )

            logger.info(f"Outbound call initiated: {call.sid} to {to_number}")

            return {
                "call_sid": call.sid,
                "status": call.status,
                "to_number": to_number,
                "from_number": self.phone_number,
            }

        except Exception as e:
            logger.error(f"Error initiating outbound call: {e}", exc_info=True)
            raise

    async def end_call(self, call_sid: str) -> bool:
        """
        End an active call.

        Args:
            call_sid: Twilio call SID

        Returns:
            True if successful
        """
        try:
            call = self.client.calls(call_sid).update(status="completed")
            logger.info(f"Call ended: {call_sid}")
            return True

        except Exception as e:
            logger.error(f"Error ending call: {e}", exc_info=True)
            return False

    async def get_call_status(self, call_sid: str) -> Optional[dict]:
        """
        Get call status from Twilio.

        Args:
            call_sid: Twilio call SID

        Returns:
            Call status dict or None
        """
        try:
            call = self.client.calls(call_sid).fetch()

            return {
                "call_sid": call.sid,
                "status": call.status,
                "duration": call.duration,
                "start_time": call.start_time,
                "end_time": call.end_time,
                "from_number": call.from_,
                "to_number": call.to,
                "direction": call.direction,
            }

        except Exception as e:
            logger.error(f"Error fetching call status: {e}", exc_info=True)
            return None

    def validate_twilio_request(
        self,
        url: str,
        params: dict,
        signature: str,
    ) -> bool:
        """
        Validate that a request came from Twilio.

        Args:
            url: Full URL of the request
            params: Request parameters
            signature: X-Twilio-Signature header value

        Returns:
            True if valid
        """
        try:
            from twilio.request_validator import RequestValidator

            validator = RequestValidator(self.auth_token)
            return validator.validate(url, params, signature)

        except Exception as e:
            logger.error(f"Error validating Twilio request: {e}", exc_info=True)
            return False


class ExotelService:
    """
    Alternative telephony service using Exotel (India-focused).

    Exotel is a popular alternative to Twilio for Indian market.
    https://exotel.com
    """

    def __init__(
        self,
        api_key: str,
        api_token: str,
        account_sid: str,
        phone_number: str,
        webhook_url: str,
    ):
        """Initialize Exotel service."""
        self.api_key = api_key
        self.api_token = api_token
        self.account_sid = account_sid
        self.phone_number = phone_number
        self.webhook_url = webhook_url
        self.base_url = f"https://api.exotel.com/v1/Accounts/{account_sid}"

    async def initiate_outbound_call(
        self,
        to_number: str,
        clinic_id: UUID,
        purpose: str = "appointment_reminder",
    ) -> dict:
        """
        Initiate outbound call via Exotel.

        Args:
            to_number: Phone number to call
            clinic_id: Clinic ID
            purpose: Call purpose

        Returns:
            Call information dict
        """
        try:
            import httpx

            # Format numbers (Exotel uses Indian format)
            if to_number.startswith("+91"):
                to_number = to_number[3:]

            url = f"{self.base_url}/Calls/connect.json"

            data = {
                "From": self.phone_number,
                "To": to_number,
                "CallerId": self.phone_number,
                "Url": f"{self.webhook_url}/api/v1/voice-bot/exotel-handler",
                "StatusCallback": f"{self.webhook_url}/api/v1/voice-bot/exotel-status",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=(self.api_key, self.api_token),
                )

                if response.status_code == 200:
                    result = response.json()
                    call_data = result.get("Call", {})

                    logger.info(f"Exotel call initiated: {call_data.get('Sid')}")

                    return {
                        "call_sid": call_data.get("Sid"),
                        "status": call_data.get("Status"),
                        "to_number": to_number,
                        "from_number": self.phone_number,
                    }
                else:
                    logger.error(f"Exotel API error: {response.status_code} - {response.text}")
                    raise Exception(f"Exotel API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Error initiating Exotel call: {e}", exc_info=True)
            raise

    # Add other Exotel methods as needed...


def get_telephony_service(provider: str = "twilio", **kwargs) -> TelephonyService | ExotelService:
    """
    Factory function to get telephony service.

    Args:
        provider: "twilio" or "exotel"
        **kwargs: Provider-specific configuration

    Returns:
        Telephony service instance
    """
    if provider == "twilio":
        return TelephonyService(
            account_sid=kwargs["account_sid"],
            auth_token=kwargs["auth_token"],
            phone_number=kwargs["phone_number"],
            webhook_url=kwargs["webhook_url"],
        )
    elif provider == "exotel":
        return ExotelService(
            api_key=kwargs["api_key"],
            api_token=kwargs["api_token"],
            account_sid=kwargs["account_sid"],
            phone_number=kwargs["phone_number"],
            webhook_url=kwargs["webhook_url"],
        )
    else:
        raise ValueError(f"Unknown telephony provider: {provider}")

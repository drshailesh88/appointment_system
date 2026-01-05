# Phase 18: Voice Bot / Phone Automation

## Status: PARTIAL
## Completion: 40%

## Overview

Phone-based automation using Twilio for incoming/outbound call management, TwiML generation, call status tracking, and WebSocket streaming for real-time audio processing.

## Implemented Components

- [x] Telephony service using Twilio (file: backend/app/services/voice_bot/telephony.py)
- [x] TwiML generation for call handling
- [x] WebSocket connection for real-time audio streaming
- [x] Call status tracking
- [x] Bidirectional audio (inbound + outbound)

## Missing Components

- [ ] API endpoints for voice bot
- [ ] Call recording management
- [ ] Voice agent logic (appointment booking via phone)
- [ ] Speech-to-text integration with Whisper
- [ ] Text-to-speech integration with Chatterbox
- [ ] Natural language understanding for phone bookings
- [ ] Call analytics and reporting
- [ ] Database models for calls
- [ ] Test coverage

## Key Files

### Backend
- backend/app/services/voice_bot/telephony.py - Twilio integration
- backend/app/api/v1/voice_bot.py - Voice bot API (partial)
- backend/app/schemas/voice_bot.py - Pydantic schemas (partial)

## Features

### Telephony Service
- Initialize Twilio client (lazy loading)
- Generate TwiML for WebSocket streaming
- Generate TwiML for voice messages (fallback)
- Initiate outbound calls
- Handle incoming calls
- Call status tracking

### TwiML Generation
- Connect calls to WebSocket for real-time streaming
- Both tracks (inbound + outbound audio)
- Fallback voice messages if WebSocket unavailable
- Gather digits (IVR menus)
- Call forwarding

### WebSocket Streaming
- Bidirectional audio streaming
- Real-time speech processing
- Stream both caller and callee audio
- Connection to backend WebSocket endpoint

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Telephony Provider | Twilio | Call management |
| Protocol | TwiML | Call control XML |
| Streaming | WebSocket | Real-time audio |
| STT | Whisper (planned) | Speech-to-text |
| TTS | Chatterbox (planned) | Text-to-speech |

## Call Flow

### Incoming Call
1. Patient calls clinic phone number
2. Twilio receives call, sends webhook to backend
3. Backend generates TwiML to connect to WebSocket
4. WebSocket established for bidirectional audio
5. Audio streamed to Whisper for transcription
6. NLU processes intent (book appointment, check status, etc.)
7. Response generated and sent to TTS (Chatterbox)
8. Audio response streamed back to caller
9. Call ends or transfers to human if needed

### Outbound Call
1. System triggers outbound call (reminder, follow-up)
2. Backend initiates call via Twilio API
3. Patient answers
4. Pre-recorded or dynamic message played
5. Optional IVR menu (press 1 to confirm, etc.)
6. Call ends or connects to live agent

## API Endpoints

To be implemented:
- POST /api/v1/voice-bot/webhook/incoming - Handle incoming call
- POST /api/v1/voice-bot/webhook/status - Call status updates
- WS /api/v1/voice-bot/ws/{call_sid} - WebSocket for audio streaming
- POST /api/v1/voice-bot/outbound - Initiate outbound call
- GET /api/v1/voice-bot/calls - List call history
- GET /api/v1/voice-bot/calls/{id} - Get call details
- POST /api/v1/voice-bot/calls/{id}/recording - Get recording

## Configuration

### Environment Variables
```bash
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+91XXXXXXXXXX
TWILIO_WEBHOOK_URL=https://your-domain.com/api/v1/voice-bot/webhook
```

### Twilio Setup
1. Create Twilio account
2. Purchase phone number
3. Configure webhook URLs
4. Set up authentication

## Integration with Existing Systems

### Phase 1 Voice Agent
- Reuse Whisper STT (already implemented)
- Reuse Chatterbox TTS (already implemented)
- Extend NLU for phone context

### Phase 16 AI Assistant
- Share conversation logic
- Function calling for appointment booking
- Context management

## Use Cases

### Automated Appointment Booking
```
Caller: "I want to book an appointment with Dr. Sharma"
Bot: "Sure! I can help you with that. What date works for you?"
Caller: "Tomorrow at 3 PM"
Bot: "Let me check... Dr. Sharma has a slot at 3:30 PM. Should I book it?"
Caller: "Yes"
Bot: "Great! What's your name?"
Caller: "Ramesh Kumar"
Bot: "Your appointment is confirmed for tomorrow at 3:30 PM with Dr. Sharma. You'll receive an SMS confirmation."
```

### Appointment Reminders
```
Bot: "Hello! This is a reminder about your appointment with Dr. Sharma tomorrow at 3:30 PM. Press 1 to confirm, 2 to reschedule, or 3 to cancel."
Patient: [Presses 1]
Bot: "Thank you! Your appointment is confirmed. See you tomorrow."
```

### After-Hours Calls
```
Bot: "Thank you for calling Dr. Sharma's clinic. We're currently closed. Our hours are Monday to Saturday, 9 AM to 6 PM. Would you like to book an appointment? Press 1 for yes."
```

## Future Enhancements

### Phase 18.1: Full Voice Agent
- [ ] Complete NLU for phone bookings
- [ ] Multi-turn conversation handling
- [ ] Sentiment analysis
- [ ] Call transfer to human

### Phase 18.2: Advanced Features
- [ ] Multi-language support (23 Indian languages)
- [ ] Call recording and transcription
- [ ] Voicemail handling
- [ ] Call queueing
- [ ] Hold music

### Phase 18.3: Analytics
- [ ] Call volume analytics
- [ ] Booking conversion rate
- [ ] Average handle time
- [ ] Customer satisfaction scoring

### Phase 18.4: IVR Menus
- [ ] Custom IVR flows
- [ ] Department routing
- [ ] Business hours handling
- [ ] Holiday messages

## Testing

Not yet implemented. Need to add:
- Twilio webhook tests (using mocks)
- TwiML generation tests
- Call flow tests
- WebSocket connection tests

## Deployment

Requires:
1. Twilio account setup
2. Public webhook URL (ngrok for testing)
3. Environment configuration
4. Database migration
5. WebSocket server setup

## Security Considerations

- Verify Twilio signatures on webhooks
- Secure WebSocket connections (wss://)
- Encrypt call recordings
- HIPAA compliance for medical conversations
- Rate limiting on API endpoints

## Competitive Advantage

vs **Practo**:
- ✅ Phone booking (Practo is web/app only)
- ✅ Automated reminders
- ✅ After-hours availability

vs **HealthPlix**:
- ✅ Voice bot for appointment management
- ✅ Multi-language phone support

vs **PM Cardio**:
- ✅ Automated phone system
- ✅ Better patient accessibility

---

**Status:** 🔄 PARTIAL (Basic telephony implemented, voice agent logic pending)
**Priority:** Medium
**Next Steps:** Integrate with Whisper/Chatterbox, implement booking logic
**Estimated Completion:** 4-5 weeks
**Dependencies:** Phase 1 (Voice Agent), Phase 16 (AI Assistant)

# DocAssist Patient Booking Portal

Public-facing web portal for patients to find and book appointments with doctors.

## Features

- 🔍 **Doctor Discovery** - Search doctors by specialization and location
- 📅 **Real-time Slot Booking** - View and book available appointment slots
- 📱 **OTP Authentication** - Secure phone-based login for patients
- 📋 **Appointment Management** - View, manage, and cancel appointments
- 🎨 **Modern UI** - Clean, responsive design with Tailwind CSS

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **API**: REST API (FastAPI backend)
- **Authentication**: OTP-based (JWT tokens)

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running at `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Update NEXT_PUBLIC_API_URL in .env.local if needed
```

### Development

```bash
# Run development server
npm run dev

# Open http://localhost:3000 in browser
```

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Environment Variables

The `.env.local` file contains:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Project Structure

```
web/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx           # Home page
│   │   ├── doctors/           # Doctor listing & detail pages
│   │   └── appointments/      # Appointment management pages
│   ├── components/            # Reusable React components
│   │   ├── DoctorCard.tsx    # Doctor preview card
│   │   ├── SlotPicker.tsx    # Appointment slot selector
│   │   ├── OTPVerification.tsx # OTP login component
│   │   └── AppointmentCard.tsx # Appointment display card
│   └── lib/
│       └── api-client.ts      # Backend API client
├── public/                    # Static assets
└── package.json
```

## Pages

### Home (`/`)
- Hero section with search
- Quick access to popular specializations
- Feature highlights

### Doctors Listing (`/doctors`)
- Browse all available doctors
- Filter by specialization and city
- Click to view doctor details

### Doctor Detail (`/doctors/[id]`)
- Doctor profile and bio
- Clinic information
- Slot picker for booking
- Patient details form

### Appointments (`/appointments`)
- OTP login required
- View all appointments
- Filter by status
- Cancel appointments

### Appointment Detail (`/appointments/[id]`)
- Full appointment details
- Token number
- Cancel option (if scheduled)

## API Integration

The frontend communicates with the backend using the `apiClient` service:

```typescript
import { apiClient } from '@/lib/api-client';

// List doctors
const doctors = await apiClient.listDoctors({ specialization: 'Cardiology' });

// Get doctor details
const doctor = await apiClient.getDoctor(doctorId);

// Get available slots
const slots = await apiClient.getDoctorSlots(doctorId, '2026-01-05');

// Send OTP
await apiClient.sendOTP(phone);

// Verify OTP
await apiClient.verifyOTP(phone, otpCode);

// Book appointment
const appointment = await apiClient.bookAppointment(bookingData);

// Get my appointments
const appointments = await apiClient.getMyAppointments();
```

## Authentication Flow

1. Patient enters phone number
2. OTP sent via SMS
3. Patient enters OTP code
4. Backend verifies and returns JWT token
5. Token stored in localStorage
6. Token sent with authenticated requests

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Docker

```bash
# Build image
docker build -t docassist-web .

# Run container
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://api:8000/api/v1 docassist-web
```

## Development Guidelines

- Use TypeScript for all components
- Follow Next.js App Router conventions
- Use Tailwind for styling (no custom CSS)
- Keep components small and focused
- Handle loading and error states
- Mobile-first responsive design

## Future Enhancements

- [ ] Embeddable booking widget
- [ ] Online payment integration
- [ ] Patient medical history view
- [ ] Lab results display
- [ ] Prescription downloads
- [ ] Multi-language support

## License

Part of DocAssist Practice Manager - see main project LICENSE

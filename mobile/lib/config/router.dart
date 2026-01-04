import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/login_screen.dart';
import '../features/dashboard/presentation/dashboard_screen.dart';
import '../features/appointments/presentation/appointments_screen.dart';
import '../features/appointments/presentation/appointment_detail_screen.dart';
import '../features/appointments/presentation/book_appointment_screen.dart';
import '../features/patients/presentation/patients_screen.dart';
import '../features/patients/presentation/patient_detail_screen.dart';
import '../features/doctors/presentation/doctors_screen.dart';
import '../features/settings/presentation/settings_screen.dart';
import '../features/analytics/presentation/analytics_screen.dart';
import '../features/waitlist/presentation/waitlist_screen.dart';
import '../features/settings/presentation/integrations/whatsapp_settings_screen.dart';
import '../features/settings/presentation/integrations/voice_settings_screen.dart';
import '../core/providers/auth_provider.dart';

/// Router provider
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);

  return GoRouter(
    initialLocation: '/login',
    debugLogDiagnostics: true,
    redirect: (context, state) {
      final isLoggedIn = authState.isAuthenticated;
      final isLoginRoute = state.matchedLocation == '/login';

      if (!isLoggedIn && !isLoginRoute) {
        return '/login';
      }

      if (isLoggedIn && isLoginRoute) {
        return '/dashboard';
      }

      return null;
    },
    routes: [
      // Auth Routes
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginScreen(),
      ),

      // Main App Shell
      ShellRoute(
        builder: (context, state, child) => MainShell(child: child),
        routes: [
          // Dashboard
          GoRoute(
            path: '/dashboard',
            name: 'dashboard',
            builder: (context, state) => const DashboardScreen(),
          ),

          // Appointments
          GoRoute(
            path: '/appointments',
            name: 'appointments',
            builder: (context, state) => const AppointmentsScreen(),
            routes: [
              GoRoute(
                path: 'book',
                name: 'book-appointment',
                builder: (context, state) => const BookAppointmentScreen(),
              ),
              GoRoute(
                path: ':id',
                name: 'appointment-detail',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return AppointmentDetailScreen(appointmentId: id);
                },
              ),
            ],
          ),

          // Patients
          GoRoute(
            path: '/patients',
            name: 'patients',
            builder: (context, state) => const PatientsScreen(),
            routes: [
              GoRoute(
                path: ':id',
                name: 'patient-detail',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return PatientDetailScreen(patientId: id);
                },
              ),
            ],
          ),

          // Doctors
          GoRoute(
            path: '/doctors',
            name: 'doctors',
            builder: (context, state) => const DoctorsScreen(),
          ),

          // Analytics
          GoRoute(
            path: '/analytics',
            name: 'analytics',
            builder: (context, state) => const AnalyticsScreen(),
          ),

          // Waitlist
          GoRoute(
            path: '/waitlist',
            name: 'waitlist',
            builder: (context, state) => const WaitlistScreen(),
          ),

          // Settings
          GoRoute(
            path: '/settings',
            name: 'settings',
            builder: (context, state) => const SettingsScreen(),
            routes: [
              GoRoute(
                path: 'whatsapp',
                name: 'whatsapp-settings',
                builder: (context, state) => const WhatsAppSettingsScreen(),
              ),
              GoRoute(
                path: 'voice',
                name: 'voice-settings',
                builder: (context, state) => const VoiceSettingsScreen(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

/// Main app shell with bottom navigation
class MainShell extends StatelessWidget {
  final Widget child;

  const MainShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _calculateSelectedIndex(context),
        onTap: (index) => _onItemTapped(index, context),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.calendar_today_outlined),
            activeIcon: Icon(Icons.calendar_today),
            label: 'Appointments',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.people_outlined),
            activeIcon: Icon(Icons.people),
            label: 'Patients',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings_outlined),
            activeIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }

  int _calculateSelectedIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith('/dashboard')) return 0;
    if (location.startsWith('/appointments')) return 1;
    if (location.startsWith('/patients')) return 2;
    if (location.startsWith('/settings')) return 3;
    return 0;
  }

  void _onItemTapped(int index, BuildContext context) {
    switch (index) {
      case 0:
        context.goNamed('dashboard');
        break;
      case 1:
        context.goNamed('appointments');
        break;
      case 2:
        context.goNamed('patients');
        break;
      case 3:
        context.goNamed('settings');
        break;
    }
  }
}

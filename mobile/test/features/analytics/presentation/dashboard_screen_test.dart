import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';

import 'package:docassist_mobile/features/analytics/presentation/analytics_screen.dart';
import 'package:docassist_mobile/core/providers/analytics_provider.dart';

// Mock classes
class MockAnalyticsNotifier extends Mock implements AnalyticsNotifier {}

void main() {
  late MockAnalyticsNotifier mockNotifier;

  setUp(() {
    mockNotifier = MockAnalyticsNotifier();
  });

  Widget createWidgetUnderTest({
    required AnalyticsState state,
  }) {
    return ProviderScope(
      overrides: [
        analyticsProvider.overrideWith((ref) => mockNotifier),
      ],
      child: const MaterialApp(
        home: AnalyticsScreen(),
      ),
    );
  }

  group('AnalyticsScreen Widget Tests', () {
    testWidgets('displays loading indicator when state is loading',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(isLoading: true),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(isLoading: true),
      ));

      // Assert
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('displays app bar with title', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(isLoading: false),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Analytics'), findsOneWidget);
      expect(find.byType(AppBar), findsOneWidget);
    });

    testWidgets('displays period selector in app bar',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(isLoading: false),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('This Month'), findsOneWidget);
      expect(find.byIcon(Icons.arrow_drop_down), findsOneWidget);
    });

    testWidgets('shows period options when period selector is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(isLoading: false),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(PopupMenuButton<String>));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Today'), findsOneWidget);
      expect(find.text('This Week'), findsOneWidget);
      expect(find.text('This Month'), findsNWidgets(2)); // One in menu, one in button
      expect(find.text('This Quarter'), findsOneWidget);
      expect(find.text('This Year'), findsOneWidget);
    });

    testWidgets('displays appointment statistics section',
        (WidgetTester tester) async {
      // Arrange
      final appointmentStats = AppointmentStats(
        total: 100,
        completed: 80,
        cancelled: 15,
        noShow: 5,
        scheduled: 20,
        completionRate: 80.0,
        cancellationRate: 15.0,
        noShowRate: 5.0,
      );

      when(() => mockNotifier.state).thenReturn(
        AnalyticsState(
          isLoading: false,
          appointmentStats: appointmentStats,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: AnalyticsState(
          isLoading: false,
          appointmentStats: appointmentStats,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Appointment Statistics'), findsOneWidget);
      expect(find.text('Total'), findsOneWidget);
      expect(find.text('100'), findsOneWidget);
      expect(find.text('Completed'), findsOneWidget);
      expect(find.text('80'), findsOneWidget);
      expect(find.text('Cancelled'), findsOneWidget);
      expect(find.text('15'), findsOneWidget);
      expect(find.text('No Show'), findsOneWidget);
      expect(find.text('5'), findsOneWidget);
    });

    testWidgets('displays appointment statistics with percentages',
        (WidgetTester tester) async {
      // Arrange
      final appointmentStats = AppointmentStats(
        total: 100,
        completed: 80,
        cancelled: 15,
        noShow: 5,
        scheduled: 20,
        completionRate: 80.0,
        cancellationRate: 15.0,
        noShowRate: 5.0,
      );

      when(() => mockNotifier.state).thenReturn(
        AnalyticsState(
          isLoading: false,
          appointmentStats: appointmentStats,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: AnalyticsState(
          isLoading: false,
          appointmentStats: appointmentStats,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('80.0%'), findsOneWidget);
      expect(find.text('15.0%'), findsOneWidget);
      expect(find.text('5.0%'), findsOneWidget);
    });

    testWidgets('displays revenue section', (WidgetTester tester) async {
      // Arrange
      final revenueStats = RevenueStats(
        totalRevenue: 150000.0,
        collected: 120000.0,
        pending: 30000.0,
        refunded: 0.0,
        collectionRate: 80.0,
        averageInvoice: 1500.0,
      );

      when(() => mockNotifier.state).thenReturn(
        AnalyticsState(
          isLoading: false,
          revenueStats: revenueStats,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: AnalyticsState(
          isLoading: false,
          revenueStats: revenueStats,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Revenue'), findsOneWidget);
      expect(find.text('Total Revenue'), findsOneWidget);
      expect(find.text('₹150000'), findsOneWidget);
      expect(find.text('80.0% collected'), findsOneWidget);
    });

    testWidgets('displays revenue breakdown', (WidgetTester tester) async {
      // Arrange
      final revenueStats = RevenueStats(
        totalRevenue: 150000.0,
        collected: 120000.0,
        pending: 30000.0,
        refunded: 0.0,
        collectionRate: 80.0,
        averageInvoice: 1500.0,
      );

      when(() => mockNotifier.state).thenReturn(
        AnalyticsState(
          isLoading: false,
          revenueStats: revenueStats,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: AnalyticsState(
          isLoading: false,
          revenueStats: revenueStats,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Collected'), findsOneWidget);
      expect(find.text('₹120000'), findsOneWidget);
      expect(find.text('Pending'), findsOneWidget);
      expect(find.text('₹30000'), findsOneWidget);
      expect(find.text('Avg Invoice'), findsOneWidget);
      expect(find.text('₹1500'), findsOneWidget);
    });

    testWidgets('displays doctor utilization section',
        (WidgetTester tester) async {
      // Arrange
      final doctors = [
        DoctorUtilization(
          doctorId: '1',
          doctorName: 'Sharma',
          totalSlots: 100,
          bookedSlots: 85,
          completedAppointments: 80,
          utilizationRate: 85.0,
          averageDuration: 15.0,
          revenueGenerated: 120000.0,
        ),
        DoctorUtilization(
          doctorId: '2',
          doctorName: 'Patel',
          totalSlots: 100,
          bookedSlots: 60,
          completedAppointments: 55,
          utilizationRate: 60.0,
          averageDuration: 20.0,
          revenueGenerated: 82500.0,
        ),
      ];

      when(() => mockNotifier.state).thenReturn(
        AnalyticsState(
          isLoading: false,
          doctorUtilization: doctors,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: AnalyticsState(
          isLoading: false,
          doctorUtilization: doctors,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Doctor Utilization'), findsOneWidget);
      expect(find.text('Dr. Sharma'), findsOneWidget);
      expect(find.text('Dr. Patel'), findsOneWidget);
      expect(find.text('80 appointments completed'), findsOneWidget);
      expect(find.text('55 appointments completed'), findsOneWidget);
      expect(find.text('85%'), findsOneWidget);
      expect(find.text('60%'), findsOneWidget);
    });

    testWidgets('displays daily trend chart', (WidgetTester tester) async {
      // Arrange
      final dailyTrend = [
        DailyMetric(
          date: DateTime(2024, 1, 1),
          appointments: 10,
          revenue: 15000.0,
          newPatients: 3,
        ),
        DailyMetric(
          date: DateTime(2024, 1, 2),
          appointments: 15,
          revenue: 22500.0,
          newPatients: 5,
        ),
        DailyMetric(
          date: DateTime(2024, 1, 3),
          appointments: 12,
          revenue: 18000.0,
          newPatients: 4,
        ),
      ];

      when(() => mockNotifier.state).thenReturn(
        AnalyticsState(
          isLoading: false,
          dailyTrend: dailyTrend,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: AnalyticsState(
          isLoading: false,
          dailyTrend: dailyTrend,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Daily Trend'), findsOneWidget);
      expect(find.text('10'), findsOneWidget);
      expect(find.text('15'), findsOneWidget);
      expect(find.text('12'), findsOneWidget);
    });

    testWidgets('displays "No data available" when stats are null',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(
          isLoading: false,
          appointmentStats: null,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(
          isLoading: false,
          appointmentStats: null,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('No data available'), findsOneWidget);
    });

    testWidgets('displays "No revenue data" when revenue is null',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(
          isLoading: false,
          revenueStats: null,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(
          isLoading: false,
          revenueStats: null,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('No revenue data'), findsOneWidget);
    });

    testWidgets('displays "No doctor data" when doctor list is empty',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(
          isLoading: false,
          doctorUtilization: [],
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(
          isLoading: false,
          doctorUtilization: [],
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('No doctor data'), findsOneWidget);
    });

    testWidgets('displays "No trend data" when trend list is empty',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(
          isLoading: false,
          dailyTrend: [],
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(
          isLoading: false,
          dailyTrend: [],
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('No trend data'), findsOneWidget);
    });

    testWidgets('supports pull-to-refresh', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(isLoading: false),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Perform pull-to-refresh gesture
      await tester.drag(
        find.byType(RefreshIndicator),
        const Offset(0, 300),
      );
      await tester.pumpAndSettle();

      // Assert
      verify(() => mockNotifier.loadDashboard('month')).called(greaterThan(1));
    });

    testWidgets('changes period and reloads data', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(isLoading: false),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Open period selector
      await tester.tap(find.byType(PopupMenuButton<String>));
      await tester.pumpAndSettle();

      // Select "This Week"
      await tester.tap(find.text('This Week'));
      await tester.pumpAndSettle();

      // Assert
      verify(() => mockNotifier.loadDashboard('week')).called(1);
    });

    testWidgets('displays correct stat tile icons',
        (WidgetTester tester) async {
      // Arrange
      final appointmentStats = AppointmentStats(
        total: 100,
        completed: 80,
        cancelled: 15,
        noShow: 5,
        scheduled: 20,
        completionRate: 80.0,
        cancellationRate: 15.0,
        noShowRate: 5.0,
      );

      when(() => mockNotifier.state).thenReturn(
        AnalyticsState(
          isLoading: false,
          appointmentStats: appointmentStats,
        ),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: AnalyticsState(
          isLoading: false,
          appointmentStats: appointmentStats,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byIcon(Icons.calendar_today), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
      expect(find.byIcon(Icons.cancel), findsOneWidget);
      expect(find.byIcon(Icons.person_off), findsOneWidget);
    });

    testWidgets('calls loadDashboard on initialization',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const AnalyticsState(isLoading: false),
      );
      when(() => mockNotifier.loadDashboard(any()))
          .thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const AnalyticsState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      verify(() => mockNotifier.loadDashboard('month')).called(1);
    });
  });
}

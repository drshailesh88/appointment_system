import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';

import 'package:docassist_mobile/features/telemedicine/presentation/waiting_room_screen.dart';
import 'package:docassist_mobile/core/providers/telemedicine_provider.dart';
import 'package:docassist_mobile/core/models/consultation.dart';

// Mock classes
class MockTelemedicineNotifier extends Mock
    implements TelemedicineNotifier {}

void main() {
  late MockTelemedicineNotifier mockNotifier;

  setUp(() {
    mockNotifier = MockTelemedicineNotifier();
  });

  Widget createWidgetUnderTest({
    required TelemedicineState state,
  }) {
    return ProviderScope(
      overrides: [
        telemedicineProvider.overrideWith((ref) => mockNotifier),
      ],
      child: MaterialApp(
        home: WaitingRoomScreen(
          consultationId: 'test-consultation-id',
          appointmentId: 'test-appointment-id',
        ),
      ),
    );
  }

  group('WaitingRoomScreen Widget Tests', () {
    testWidgets('displays loading indicator when state is loading',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: true),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: true),
      ));

      // Assert
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('displays waiting room content when loaded',
        (WidgetTester tester) async {
      // Arrange
      final waitingStatus = WaitingRoomStatus(
        status: 'waiting',
        position: 3,
        estimatedWaitMinutes: 15,
        patientJoinedAt: DateTime.now(),
      );

      when(() => mockNotifier.state).thenReturn(
        TelemedicineState(
          isLoading: false,
          waitingRoomStatus: waitingStatus,
        ),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: TelemedicineState(
          isLoading: false,
          waitingRoomStatus: waitingStatus,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Please wait'), findsOneWidget);
      expect(find.text('You are #3 in the queue'), findsOneWidget);
      expect(find.text('~15 minutes'), findsOneWidget);
      expect(find.text('Leave Waiting Room'), findsOneWidget);
    });

    testWidgets('displays queue position correctly when patient is next',
        (WidgetTester tester) async {
      // Arrange
      final waitingStatus = WaitingRoomStatus(
        status: 'waiting',
        position: 1,
        estimatedWaitMinutes: 5,
        patientJoinedAt: DateTime.now(),
      );

      when(() => mockNotifier.state).thenReturn(
        TelemedicineState(
          isLoading: false,
          waitingRoomStatus: waitingStatus,
        ),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: TelemedicineState(
          isLoading: false,
          waitingRoomStatus: waitingStatus,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text("You're next!"), findsOneWidget);
    });

    testWidgets('displays waiting animation', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byIcon(Icons.video_call), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('displays tips while waiting', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Tips while you wait'), findsOneWidget);
      expect(find.text('Keep your device charged'), findsOneWidget);
      expect(
          find.text('Ensure you have a stable internet connection'),
          findsOneWidget);
      expect(find.text('Find a quiet, well-lit place for the call'),
          findsOneWidget);
      expect(find.text('Have your medical reports ready if needed'),
          findsOneWidget);
    });

    testWidgets('shows cancel confirmation dialog when leave button is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Leave Waiting Room'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Leave Waiting Room?'), findsOneWidget);
      expect(
          find.text(
              'Are you sure you want to leave the waiting room? You will lose your place in the queue.'),
          findsOneWidget);
      expect(find.text('No, Stay'), findsOneWidget);
      expect(find.text('Yes, Leave'), findsOneWidget);
    });

    testWidgets('dismisses dialog when "No, Stay" is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Leave Waiting Room'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('No, Stay'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Leave Waiting Room?'), findsNothing);
      expect(find.text('Please wait'), findsOneWidget);
    });

    testWidgets('has correct app bar', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Waiting Room'), findsOneWidget);
      expect(find.byType(AppBar), findsOneWidget);
    });

    testWidgets('displays estimated wait time in hours when > 60 minutes',
        (WidgetTester tester) async {
      // Arrange
      final waitingStatus = WaitingRoomStatus(
        status: 'waiting',
        position: 5,
        estimatedWaitMinutes: 90,
        patientJoinedAt: DateTime.now(),
      );

      when(() => mockNotifier.state).thenReturn(
        TelemedicineState(
          isLoading: false,
          waitingRoomStatus: waitingStatus,
        ),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: TelemedicineState(
          isLoading: false,
          waitingRoomStatus: waitingStatus,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('~2 hour(s)'), findsOneWidget);
    });

    testWidgets('displays all queue info cards', (WidgetTester tester) async {
      // Arrange
      final waitingStatus = WaitingRoomStatus(
        status: 'waiting',
        position: 2,
        estimatedWaitMinutes: 10,
        patientJoinedAt: DateTime.now(),
      );

      when(() => mockNotifier.state).thenReturn(
        TelemedicineState(
          isLoading: false,
          waitingRoomStatus: waitingStatus,
        ),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: TelemedicineState(
          isLoading: false,
          waitingRoomStatus: waitingStatus,
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byIcon(Icons.people), findsOneWidget);
      expect(find.byIcon(Icons.access_time), findsOneWidget);
      expect(find.text('Estimated wait time'), findsOneWidget);
    });

    testWidgets('calls joinWaitingRoom on initialization',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.joinWaitingRoom(
            any(),
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      verify(() => mockNotifier.joinWaitingRoom(
            'test-consultation-id',
            deviceType: any(named: 'deviceType'),
            connectionType: any(named: 'connectionType'),
          )).called(1);
    });
  });
}

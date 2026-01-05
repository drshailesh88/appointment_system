import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';

import 'package:docassist_mobile/features/telemedicine/presentation/consultation_screen.dart';
import 'package:docassist_mobile/core/providers/telemedicine_provider.dart';

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
        home: ConsultationScreen(
          consultationId: 'test-consultation-id',
          roomUrl: 'https://meet.jitsi.si/test-room',
          jwtToken: 'test-jwt-token',
          roomName: 'TestRoom123',
        ),
      ),
    );
  }

  group('ConsultationScreen Widget Tests', () {
    testWidgets('displays video call placeholder',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Video Consultation'), findsOneWidget);
      expect(find.text('Room: TestRoom123'), findsOneWidget);
      expect(find.byIcon(Icons.video_call), findsOneWidget);
    });

    testWidgets('displays Jitsi integration message',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(
          find.textContaining('Jitsi Meet SDK Integration Required'),
          findsOneWidget);
    });

    testWidgets('displays all control buttons', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Mute'), findsOneWidget);
      expect(find.text('Camera'), findsOneWidget);
      expect(find.text('End'), findsOneWidget);
      expect(find.text('Chat'), findsOneWidget);
      expect(find.text('More'), findsOneWidget);
    });

    testWidgets('displays correct control icons', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byIcon(Icons.mic_off), findsOneWidget);
      expect(find.byIcon(Icons.videocam_off), findsOneWidget);
      expect(find.byIcon(Icons.call_end), findsOneWidget);
      expect(find.byIcon(Icons.chat), findsOneWidget);
      expect(find.byIcon(Icons.more_vert), findsOneWidget);
    });

    testWidgets('shows more options bottom sheet when More is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('More'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Recording'), findsOneWidget);
      expect(find.text('Switch Camera'), findsOneWidget);
      expect(find.text('Share Screen'), findsOneWidget);
    });

    testWidgets('shows recording consent dialog from more options',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Open more options
      await tester.tap(find.text('More'));
      await tester.pumpAndSettle();

      // Tap recording option
      await tester.tap(find.text('Recording'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Request Recording'), findsOneWidget);
      expect(find.textContaining('Recording this consultation requires consent'),
          findsOneWidget);
      expect(find.text('No'), findsOneWidget);
      expect(find.text('Yes, I Consent'), findsOneWidget);
    });

    testWidgets('shows end call confirmation dialog when End is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.endConsultation(
            any(),
            connectionQuality: any(named: 'connectionQuality'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('End Consultation?'), findsOneWidget);
      expect(
          find.text('Are you sure you want to end this consultation?'),
          findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('End Call'), findsOneWidget);
    });

    testWidgets('dismisses end call dialog when Cancel is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('End Consultation?'), findsNothing);
      expect(find.text('Video Consultation'), findsOneWidget);
    });

    testWidgets('shows rating dialog after ending call',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.endConsultation(
            any(),
            connectionQuality: any(named: 'connectionQuality'),
          )).thenAnswer((_) async => true);
      when(() => mockNotifier.submitRating(any(), any()))
          .thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // End the call
      await tester.tap(find.text('End'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End Call'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Rate Consultation'), findsOneWidget);
      expect(find.text('How was your consultation experience?'),
          findsOneWidget);
      expect(find.byIcon(Icons.star), findsNWidgets(5));
    });

    testWidgets('rating dialog has Skip and Submit buttons',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.endConsultation(
            any(),
            connectionQuality: any(named: 'connectionQuality'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End Call'));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Skip'), findsOneWidget);
      expect(find.text('Submit'), findsOneWidget);
    });

    testWidgets('can select different star ratings',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.endConsultation(
            any(),
            connectionQuality: any(named: 'connectionQuality'),
          )).thenAnswer((_) async => true);
      when(() => mockNotifier.submitRating(any(), any()))
          .thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End Call'));
      await tester.pumpAndSettle();

      // Find all star buttons (both filled and empty)
      final starButtons = find.byType(IconButton);

      // Tap the third star (for 3-star rating)
      await tester.tap(starButtons.at(2));
      await tester.pumpAndSettle();

      // Assert - should see 3 filled stars and 2 empty stars
      expect(find.byIcon(Icons.star), findsNWidgets(3));
      expect(find.byIcon(Icons.star_border), findsNWidgets(2));
    });

    testWidgets('calls endConsultation when End Call is confirmed',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.endConsultation(
            any(),
            connectionQuality: any(named: 'connectionQuality'),
          )).thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End Call'));
      await tester.pumpAndSettle();

      // Assert
      verify(() => mockNotifier.endConsultation(
            'test-consultation-id',
            connectionQuality: any(named: 'connectionQuality'),
          )).called(1);
    });

    testWidgets('submits rating when Submit is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );
      when(() => mockNotifier.endConsultation(
            any(),
            connectionQuality: any(named: 'connectionQuality'),
          )).thenAnswer((_) async => true);
      when(() => mockNotifier.submitRating(any(), any()))
          .thenAnswer((_) async => true);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('End Call'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Submit'));
      await tester.pumpAndSettle();

      // Assert
      verify(() => mockNotifier.submitRating('test-consultation-id', 5))
          .called(1);
    });

    testWidgets('has black background for video screen',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Assert
      final scaffold = tester.widget<Scaffold>(find.byType(Scaffold));
      expect(scaffold.backgroundColor, Colors.black);
    });

    testWidgets('prevents back navigation with confirmation',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const TelemedicineState(isLoading: false),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const TelemedicineState(isLoading: false),
      ));
      await tester.pumpAndSettle();

      // Try to pop the route (back button)
      final NavigatorState navigator = tester.state(find.byType(Navigator));
      navigator.pop();
      await tester.pumpAndSettle();

      // Assert - should show confirmation dialog
      expect(find.text('End Consultation?'), findsOneWidget);
    });
  });
}

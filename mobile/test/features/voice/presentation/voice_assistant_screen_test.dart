import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';

import 'package:docassist_mobile/core/providers/voice_booking_provider.dart';

// Mock classes
class MockVoiceBookingNotifier extends Mock implements VoiceBookingNotifier {}

// Voice Assistant Screen (we'll create a simple one for testing)
class VoiceAssistantScreen extends ConsumerWidget {
  const VoiceAssistantScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final voiceState = ref.watch(voiceBookingProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Voice Assistant'),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.language),
            onSelected: (value) {},
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'en', child: Text('English')),
              const PopupMenuItem(value: 'hi', child: Text('Hindi')),
              const PopupMenuItem(value: 'mr', child: Text('Marathi')),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // Voice animation
                  _VoiceAnimation(isActive: voiceState.isActive),
                  const SizedBox(height: 24),

                  // Status text
                  if (voiceState.status == VoiceBookingStatus.listening)
                    const Text('Listening...', style: TextStyle(fontSize: 18)),
                  if (voiceState.status == VoiceBookingStatus.processing)
                    const Text('Processing...', style: TextStyle(fontSize: 18)),
                  if (voiceState.status == VoiceBookingStatus.responding)
                    const Text('Responding...', style: TextStyle(fontSize: 18)),

                  const SizedBox(height: 16),

                  // Transcript
                  if (voiceState.transcript != null) ...[
                    Card(
                      color: Colors.blue[50],
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('You said:',
                                style: TextStyle(fontWeight: FontWeight.bold)),
                            const SizedBox(height: 8),
                            Text(voiceState.transcript!),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Response
                  if (voiceState.response != null) ...[
                    Card(
                      color: Colors.green[50],
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Assistant:',
                                style: TextStyle(fontWeight: FontWeight.bold)),
                            const SizedBox(height: 8),
                            Text(voiceState.response!),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Error
                  if (voiceState.hasError) ...[
                    Card(
                      color: Colors.red[50],
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          children: [
                            const Icon(Icons.error, color: Colors.red),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                voiceState.errorMessage ?? 'An error occurred',
                                style: const TextStyle(color: Colors.red),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Quick phrases
                  if (voiceState.status == VoiceBookingStatus.idle) ...[
                    const Text('Try saying:',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    ...voiceBookingSuggestions.map((suggestion) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Chip(
                            label: Text(suggestion),
                            avatar: const Icon(Icons.mic, size: 16),
                          ),
                        )),
                  ],
                ],
              ),
            ),
          ),

          // Control buttons
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 8,
                ),
              ],
            ),
            child: SafeArea(
              top: false,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (voiceState.isActive)
                    ElevatedButton.icon(
                      onPressed: () {
                        ref.read(voiceBookingProvider.notifier).cancel();
                      },
                      icon: const Icon(Icons.close),
                      label: const Text('Cancel'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        foregroundColor: Colors.white,
                      ),
                    )
                  else
                    FloatingActionButton.large(
                      onPressed: () {
                        ref.read(voiceBookingProvider.notifier).startListening();
                      },
                      child: const Icon(Icons.mic, size: 32),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _VoiceAnimation extends StatelessWidget {
  final bool isActive;

  const _VoiceAnimation({required this.isActive});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 150,
      height: 150,
      decoration: BoxDecoration(
        color: isActive ? Colors.blue[100] : Colors.grey[200],
        shape: BoxShape.circle,
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          if (isActive)
            const CircularProgressIndicator(
              strokeWidth: 3,
              valueColor: AlwaysStoppedAnimation<Color>(Colors.blue),
            ),
          Icon(
            Icons.mic,
            size: 64,
            color: isActive ? Colors.blue[700] : Colors.grey[600],
          ),
        ],
      ),
    );
  }
}

void main() {
  late MockVoiceBookingNotifier mockNotifier;

  setUp(() {
    mockNotifier = MockVoiceBookingNotifier();
  });

  Widget createWidgetUnderTest({
    required VoiceBookingState state,
  }) {
    return ProviderScope(
      overrides: [
        voiceBookingProvider.overrideWith((ref) => mockNotifier),
      ],
      child: const MaterialApp(
        home: VoiceAssistantScreen(),
      ),
    );
  }

  group('VoiceAssistantScreen Widget Tests', () {
    testWidgets('displays app bar with title', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(),
      ));

      // Assert
      expect(find.text('Voice Assistant'), findsOneWidget);
      expect(find.byType(AppBar), findsOneWidget);
    });

    testWidgets('displays language selector in app bar',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(),
      ));

      // Assert
      expect(find.byIcon(Icons.language), findsOneWidget);
    });

    testWidgets('shows language options when selector is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(),
      ));

      await tester.tap(find.byIcon(Icons.language));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('English'), findsOneWidget);
      expect(find.text('Hindi'), findsOneWidget);
      expect(find.text('Marathi'), findsOneWidget);
    });

    testWidgets('displays microphone button when idle',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.idle),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.idle),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.byIcon(Icons.mic), findsNWidgets(2)); // One in FAB, one in animation
    });

    testWidgets('displays cancel button when active',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.listening),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.listening),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.byIcon(Icons.close), findsOneWidget);
    });

    testWidgets('displays listening status when listening',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.listening),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.listening),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Listening...'), findsOneWidget);
    });

    testWidgets('displays processing status when processing',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.processing),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.processing),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Processing...'), findsOneWidget);
    });

    testWidgets('displays responding status when responding',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.responding),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.responding),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Responding...'), findsOneWidget);
    });

    testWidgets('displays transcript when available',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(
          status: VoiceBookingStatus.processing,
          transcript: 'Book an appointment with Dr. Sharma',
        ),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(
          status: VoiceBookingStatus.processing,
          transcript: 'Book an appointment with Dr. Sharma',
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('You said:'), findsOneWidget);
      expect(find.text('Book an appointment with Dr. Sharma'), findsOneWidget);
    });

    testWidgets('displays response when available',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(
          status: VoiceBookingStatus.responding,
          transcript: 'Book an appointment with Dr. Sharma',
          response: 'I have booked your appointment for tomorrow at 10 AM',
        ),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(
          status: VoiceBookingStatus.responding,
          transcript: 'Book an appointment with Dr. Sharma',
          response: 'I have booked your appointment for tomorrow at 10 AM',
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Assistant:'), findsOneWidget);
      expect(find.text('I have booked your appointment for tomorrow at 10 AM'),
          findsOneWidget);
    });

    testWidgets('displays error message when error occurs',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(
          status: VoiceBookingStatus.error,
          errorMessage: 'Network connection failed',
        ),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(
          status: VoiceBookingStatus.error,
          errorMessage: 'Network connection failed',
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byIcon(Icons.error), findsOneWidget);
      expect(find.text('Network connection failed'), findsOneWidget);
    });

    testWidgets('displays quick phrase suggestions when idle',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.idle),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.idle),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Try saying:'), findsOneWidget);
      expect(find.text('Book an appointment for tomorrow'), findsOneWidget);
      expect(find.text('Schedule a follow-up with Dr. Sharma'), findsOneWidget);
      expect(find.text('Cancel my appointment on Monday'), findsOneWidget);
    });

    testWidgets('displays active voice animation when listening',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.listening),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.listening),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('displays inactive voice animation when idle',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.idle),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.idle),
      ));
      await tester.pumpAndSettle();

      // Assert - No circular progress when idle
      expect(find.byType(CircularProgressIndicator), findsNothing);
    });

    testWidgets('calls startListening when microphone button is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.idle),
      );
      when(() => mockNotifier.startListening()).thenAnswer((_) async => {});

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.idle),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Assert
      verify(() => mockNotifier.startListening()).called(1);
    });

    testWidgets('calls cancel when cancel button is tapped',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.listening),
      );
      when(() => mockNotifier.cancel()).thenReturn(null);

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.listening),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      // Assert
      verify(() => mockNotifier.cancel()).called(1);
    });

    testWidgets('displays suggestion chips', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(status: VoiceBookingStatus.idle),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(status: VoiceBookingStatus.idle),
      ));
      await tester.pumpAndSettle();

      // Assert
      expect(find.byType(Chip), findsNWidgets(voiceBookingSuggestions.length));
    });

    testWidgets('transcript card has correct styling',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(
          status: VoiceBookingStatus.processing,
          transcript: 'Test transcript',
        ),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(
          status: VoiceBookingStatus.processing,
          transcript: 'Test transcript',
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      final transcriptCard = tester.widget<Card>(
        find.ancestor(
          of: find.text('You said:'),
          matching: find.byType(Card),
        ),
      );
      expect(transcriptCard.color, Colors.blue[50]);
    });

    testWidgets('response card has correct styling',
        (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(
          status: VoiceBookingStatus.responding,
          response: 'Test response',
        ),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(
          status: VoiceBookingStatus.responding,
          response: 'Test response',
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      final responseCard = tester.widget<Card>(
        find.ancestor(
          of: find.text('Assistant:'),
          matching: find.byType(Card),
        ),
      );
      expect(responseCard.color, Colors.green[50]);
    });

    testWidgets('error card has correct styling', (WidgetTester tester) async {
      // Arrange
      when(() => mockNotifier.state).thenReturn(
        const VoiceBookingState(
          status: VoiceBookingStatus.error,
          errorMessage: 'Test error',
        ),
      );

      // Act
      await tester.pumpWidget(createWidgetUnderTest(
        state: const VoiceBookingState(
          status: VoiceBookingStatus.error,
          errorMessage: 'Test error',
        ),
      ));
      await tester.pumpAndSettle();

      // Assert
      final errorCard = tester.widget<Card>(
        find.ancestor(
          of: find.text('Test error'),
          matching: find.byType(Card),
        ),
      );
      expect(errorCard.color, Colors.red[50]);
    });
  });
}

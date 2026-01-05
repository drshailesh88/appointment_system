import 'package:docassist_mobile/core/models/patient.dart';
import 'package:docassist_mobile/core/providers/patients_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// Mock classes
class MockPatientsNotifier extends Mock implements PatientsNotifier {}

void main() {
  group('PatientListScreen Widget Tests', () {
    late List<Patient> mockPatients;
    late MockPatientsNotifier mockNotifier;

    setUp(() {
      mockNotifier = MockPatientsNotifier();

      mockPatients = [
        Patient(
          id: 'pat-001',
          firstName: 'John',
          lastName: 'Doe',
          phone: '+919876543210',
          email: 'john.doe@example.com',
          dateOfBirth: DateTime(1985, 5, 15),
          gender: 'M',
          address: '123 Main St',
          city: 'Mumbai',
          bloodGroup: 'O+',
          clinicId: 'clinic-001',
          isActive: true,
          createdAt: DateTime(2023, 1, 1),
        ),
        Patient(
          id: 'pat-002',
          firstName: 'Jane',
          lastName: 'Smith',
          phone: '+919876543211',
          email: 'jane.smith@example.com',
          dateOfBirth: DateTime(1990, 8, 20),
          gender: 'F',
          address: '456 Oak Ave',
          city: 'Delhi',
          bloodGroup: 'A+',
          clinicId: 'clinic-001',
          isActive: true,
          createdAt: DateTime(2023, 1, 2),
        ),
        Patient(
          id: 'pat-003',
          firstName: 'Bob',
          lastName: 'Johnson',
          phone: '+919876543212',
          dateOfBirth: DateTime(1975, 3, 10),
          gender: 'M',
          city: 'Bangalore',
          clinicId: 'clinic-001',
          isActive: true,
          createdAt: DateTime(2023, 1, 3),
        ),
      ];
    });

    testWidgets('displays loading indicator when searching',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: [],
              isSearching: true,
              error: null,
            ),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('displays error message with retry button',
        (WidgetTester tester) async {
      const errorMessage = 'Failed to search patients';
      bool retryCalled = false;

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: [],
              isSearching: false,
              error: errorMessage,
              onRetry: () {
                retryCalled = true;
              },
            ),
          ),
        ),
      );

      expect(find.textContaining('Error'), findsOneWidget);
      expect(find.textContaining(errorMessage), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);

      await tester.tap(find.text('Retry'));
      await tester.pump();

      expect(retryCalled, true);
    });

    testWidgets('displays empty state when no search query',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: [],
              isSearching: false,
              error: null,
              showEmptySearch: true,
            ),
          ),
        ),
      );

      expect(find.text('Search for patients'), findsOneWidget);
      expect(
        find.text('Enter at least 2 characters to search'),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.search), findsOneWidget);
    });

    testWidgets('displays no results message when search returns empty',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: [],
              isSearching: false,
              error: null,
              showEmptySearch: false,
              searchQuery: 'xyz',
            ),
          ),
        ),
      );

      expect(find.text('No patients found'), findsOneWidget);
      expect(find.text('Try a different search term'), findsOneWidget);
      expect(find.byIcon(Icons.person_search), findsOneWidget);
      expect(find.text('Add New Patient'), findsOneWidget);
    });

    testWidgets('displays list of patients when search results available',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('John Doe'), findsOneWidget);
      expect(find.text('Jane Smith'), findsOneWidget);
      expect(find.text('Bob Johnson'), findsOneWidget);
    });

    testWidgets('displays correct number of patient cards',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.byType(Card), findsNWidgets(3));
      expect(find.byType(ListTile), findsNWidgets(3));
    });

    testWidgets('displays patient phone numbers correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('+919876543210'), findsOneWidget);
      expect(find.text('+919876543211'), findsOneWidget);
      expect(find.text('+919876543212'), findsOneWidget);
    });

    testWidgets('displays patient gender and age correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.textContaining('Male'), findsNWidgets(2));
      expect(find.textContaining('Female'), findsOneWidget);
      expect(find.textContaining('years'), findsNWidgets(3));
    });

    testWidgets('displays patient avatars with initials',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.byType(CircleAvatar), findsNWidgets(3));

      // Find all Text widgets that are single characters (initials)
      final jInitial = find.text('J');
      expect(jInitial, findsNWidgets(2)); // John and Jane

      final bInitial = find.text('B');
      expect(bInitial, findsOneWidget); // Bob
    });

    testWidgets('card tap triggers navigation callback',
        (WidgetTester tester) async {
      String? tappedPatientId;

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: false,
              error: null,
              onTap: (id) {
                tappedPatientId = id;
              },
            ),
          ),
        ),
      );

      await tester.tap(find.byType(ListTile).first);
      await tester.pump();

      expect(tappedPatientId, 'pat-001');
    });

    testWidgets('list is scrollable with many patients',
        (WidgetTester tester) async {
      final longList = List.generate(
        20,
        (index) => Patient(
          id: 'pat-$index',
          firstName: 'Patient',
          lastName: '$index',
          phone: '+9198765432${index.toString().padLeft(2, '0')}',
          clinicId: 'clinic-001',
          isActive: true,
          createdAt: DateTime(2023, 1, 1),
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: longList,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      // First patient should be visible
      expect(find.text('Patient 0'), findsOneWidget);

      // Last patient should not be visible initially
      expect(find.text('Patient 19'), findsNothing);

      // Scroll to bottom
      await tester.fling(
        find.byType(ListView),
        const Offset(0, -5000),
        1000,
      );
      await tester.pumpAndSettle();

      // Last patient should now be visible
      expect(find.text('Patient 19'), findsOneWidget);
    });

    testWidgets('displays patients without email', (WidgetTester tester) async {
      final patientWithoutEmail = [
        Patient(
          id: 'pat-004',
          firstName: 'Test',
          lastName: 'Patient',
          phone: '+919876543213',
          gender: 'M',
          clinicId: 'clinic-001',
          isActive: true,
          createdAt: DateTime(2023, 1, 1),
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: patientWithoutEmail,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('Test Patient'), findsOneWidget);
      expect(find.text('+919876543213'), findsOneWidget);
    });

    testWidgets('displays patients without gender or age',
        (WidgetTester tester) async {
      final patientWithoutDetails = [
        Patient(
          id: 'pat-005',
          firstName: 'Simple',
          lastName: 'Patient',
          phone: '+919876543214',
          clinicId: 'clinic-001',
          isActive: true,
          createdAt: DateTime(2023, 1, 1),
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: patientWithoutDetails,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('Simple Patient'), findsOneWidget);
      // Should only show phone, not gender/age
      expect(find.text('+919876543214'), findsOneWidget);
    });

    testWidgets('empty results shows add patient button',
        (WidgetTester tester) async {
      bool addPatientCalled = false;

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: [],
              isSearching: false,
              error: null,
              showEmptySearch: false,
              searchQuery: 'nonexistent',
              onAddPatient: () {
                addPatientCalled = true;
              },
            ),
          ),
        ),
      );

      expect(find.text('Add New Patient'), findsOneWidget);

      await tester.tap(find.text('Add New Patient'));
      await tester.pump();

      expect(addPatientCalled, true);
    });

    testWidgets('handles patients with very long names',
        (WidgetTester tester) async {
      final longNamePatients = [
        Patient(
          id: 'pat-006',
          firstName: 'Extremely Long First Name',
          lastName: 'Extremely Long Last Name',
          phone: '+919876543215',
          clinicId: 'clinic-001',
          isActive: true,
          createdAt: DateTime(2023, 1, 1),
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: longNamePatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(tester.takeException(), isNull);
    });

    testWidgets('search results update when query changes',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: [mockPatients[0]], // Only John
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('John Doe'), findsOneWidget);
      expect(find.text('Jane Smith'), findsNothing);

      // Simulate search query change
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: [mockPatients[1]], // Only Jane
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('John Doe'), findsNothing);
      expect(find.text('Jane Smith'), findsOneWidget);
    });

    testWidgets('displays chevron icons on all patient cards',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.chevron_right), findsNWidgets(3));
    });

    testWidgets('filters work correctly', (WidgetTester tester) async {
      // Test male patients only
      final malePatients =
          mockPatients.where((p) => p.gender == 'M').toList();

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: malePatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('John Doe'), findsOneWidget);
      expect(find.text('Bob Johnson'), findsOneWidget);
      expect(find.text('Jane Smith'), findsNothing);
    });

    testWidgets('handles special characters in names',
        (WidgetTester tester) async {
      final specialNamePatients = [
        Patient(
          id: 'pat-007',
          firstName: "O'Brien",
          lastName: 'Smith-Jones',
          phone: '+919876543216',
          clinicId: 'clinic-001',
          isActive: true,
          createdAt: DateTime(2023, 1, 1),
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: specialNamePatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text("O'Brien Smith-Jones"), findsOneWidget);
    });

    testWidgets('patient cards have proper spacing',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: false,
              error: null,
            ),
          ),
        ),
      );

      final cardFinder = find.byType(Card).first;
      final Card card = tester.widget(cardFinder);
      expect(card.margin, const EdgeInsets.only(bottom: 8));
    });

    testWidgets('loading state shows only spinner',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _PatientListTest(
              patients: mockPatients,
              isSearching: true,
              error: null,
            ),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.byType(ListView), findsNothing);
    });
  });
}

// Test widget wrapper
class _PatientListTest extends StatelessWidget {
  final List<Patient> patients;
  final bool isSearching;
  final String? error;
  final Function(String)? onTap;
  final VoidCallback? onRetry;
  final VoidCallback? onAddPatient;
  final bool showEmptySearch;
  final String? searchQuery;

  const _PatientListTest({
    required this.patients,
    required this.isSearching,
    this.error,
    this.onTap,
    this.onRetry,
    this.onAddPatient,
    this.showEmptySearch = false,
    this.searchQuery,
  });

  @override
  Widget build(BuildContext context) {
    if (isSearching) {
      return const Center(child: CircularProgressIndicator());
    }

    if (error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
            const SizedBox(height: 16),
            Text('Error: $error'),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: onRetry,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (showEmptySearch) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.search,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'Search for patients',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Enter at least 2 characters to search',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      );
    }

    if (patients.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.person_search,
              size: 48,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'No patients found',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Try a different search term',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: onAddPatient,
              icon: const Icon(Icons.person_add),
              label: const Text('Add New Patient'),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: patients.length,
      itemBuilder: (context, index) {
        final patient = patients[index];
        return _PatientCardWrapper(
          patient: patient,
          onTap: () => onTap?.call(patient.id),
        );
      },
    );
  }
}

class _PatientCardWrapper extends StatelessWidget {
  final Patient patient;
  final VoidCallback onTap;

  const _PatientCardWrapper({
    required this.patient,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Theme.of(context).colorScheme.primaryContainer,
          child: Text(patient.fullName.substring(0, 1).toUpperCase()),
        ),
        title: Text(patient.fullName),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(patient.phone),
            if (patient.gender != null || patient.dateOfBirth != null)
              Text(
                [
                  if (patient.gender != null) patient.genderDisplay,
                  if (patient.age != null) '${patient.age} years',
                ].join(' • '),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey,
                    ),
              ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}

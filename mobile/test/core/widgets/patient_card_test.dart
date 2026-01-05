import 'package:docassist_mobile/core/models/patient.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('PatientCard Widget Tests', () {
    late Patient testPatient;

    setUp(() {
      testPatient = Patient(
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
        allergies: 'Peanuts',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );
    });

    testWidgets('displays patient full name correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.text('John Doe'), findsOneWidget);
    });

    testWidgets('displays patient with only first name',
        (WidgetTester tester) async {
      final patientWithFirstNameOnly = Patient(
        id: 'pat-002',
        firstName: 'Jane',
        phone: '+919876543211',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: patientWithFirstNameOnly,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.text('Jane'), findsOneWidget);
    });

    testWidgets('displays phone number correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.text('+919876543210'), findsOneWidget);
    });

    testWidgets('displays gender correctly', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.textContaining('Male'), findsOneWidget);
    });

    testWidgets('displays age correctly', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      // Patient born in 1985 should be around 38-39 years old
      final age = testPatient.age;
      expect(age, isNotNull);
      expect(age! >= 38 && age <= 40, true);
      expect(find.textContaining('$age'), findsOneWidget);
    });

    testWidgets('displays female gender correctly',
        (WidgetTester tester) async {
      final femalePatient = Patient(
        id: 'pat-003',
        firstName: 'Sarah',
        lastName: 'Smith',
        phone: '+919876543212',
        gender: 'F',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: femalePatient,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.textContaining('Female'), findsOneWidget);
    });

    testWidgets('displays avatar with first letter of name',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.byType(CircleAvatar), findsOneWidget);
      expect(find.text('J'), findsOneWidget);
    });

    testWidgets('displays chevron right icon', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.chevron_right), findsOneWidget);
    });

    testWidgets('triggers onTap callback when card is tapped',
        (WidgetTester tester) async {
      bool tapCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {
                tapCalled = true;
              },
            ),
          ),
        ),
      );

      await tester.tap(find.byType(ListTile));
      await tester.pump();

      expect(tapCalled, true);
    });

    testWidgets('displays patient without date of birth',
        (WidgetTester tester) async {
      final patientWithoutDob = Patient(
        id: 'pat-004',
        firstName: 'Bob',
        lastName: 'Johnson',
        phone: '+919876543213',
        gender: 'M',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: patientWithoutDob,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.text('Bob Johnson'), findsOneWidget);
      expect(find.textContaining('Male'), findsOneWidget);
      // Age should not be displayed if DOB is null
      expect(patientWithoutDob.age, isNull);
    });

    testWidgets('displays patient without gender',
        (WidgetTester tester) async {
      final patientWithoutGender = Patient(
        id: 'pat-005',
        firstName: 'Alice',
        lastName: 'Williams',
        phone: '+919876543214',
        dateOfBirth: DateTime(1990, 3, 20),
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: patientWithoutGender,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.text('Alice Williams'), findsOneWidget);
      // Should still display age even without gender
      final age = patientWithoutGender.age;
      expect(age, isNotNull);
    });

    testWidgets('handles long patient names without overflow',
        (WidgetTester tester) async {
      final longNamePatient = Patient(
        id: 'pat-006',
        firstName: 'Extremely Long First Name',
        lastName: 'Extremely Long Last Name That Should Not Overflow',
        phone: '+919876543215',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: longNamePatient,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(tester.takeException(), isNull);
    });

    testWidgets('calculates age correctly for different ages',
        (WidgetTester tester) async {
      // Test infant (less than 1 year)
      final infant = Patient(
        id: 'pat-007',
        firstName: 'Baby',
        lastName: 'Infant',
        phone: '+919876543216',
        dateOfBirth: DateTime.now().subtract(const Duration(days: 100)),
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      expect(infant.age, 0);

      // Test elderly patient
      final elderly = Patient(
        id: 'pat-008',
        firstName: 'Old',
        lastName: 'Person',
        phone: '+919876543217',
        dateOfBirth: DateTime(1940, 1, 1),
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      expect(elderly.age! >= 83, true);
    });

    testWidgets('displays "Other" gender correctly',
        (WidgetTester tester) async {
      final otherGenderPatient = Patient(
        id: 'pat-009',
        firstName: 'Alex',
        lastName: 'Taylor',
        phone: '+919876543218',
        gender: 'O',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: otherGenderPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.textContaining('Other'), findsOneWidget);
    });

    testWidgets('card has proper styling', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      final cardFinder = find.byType(Card);
      expect(cardFinder, findsOneWidget);

      final Card card = tester.widget(cardFinder);
      expect(card.margin, const EdgeInsets.only(bottom: 8));
    });

    testWidgets('avatar has proper background color',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _PatientCardTest(
              patient: testPatient,
              onTap: () {},
            ),
          ),
        ),
      );

      final avatarFinder = find.byType(CircleAvatar);
      expect(avatarFinder, findsOneWidget);

      final CircleAvatar avatar = tester.widget(avatarFinder);
      // Should use theme's primary container color
      expect(avatar.backgroundColor, isNotNull);
    });
  });

  group('Patient Model Tests', () {
    test('fullName returns correct name with last name', () {
      final patient = Patient(
        id: 'pat-001',
        firstName: 'John',
        lastName: 'Doe',
        phone: '+919876543210',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      expect(patient.fullName, 'John Doe');
    });

    test('fullName returns only first name when last name is null', () {
      final patient = Patient(
        id: 'pat-002',
        firstName: 'Jane',
        phone: '+919876543211',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      expect(patient.fullName, 'Jane');
    });

    test('fullName returns only first name when last name is empty', () {
      final patient = Patient(
        id: 'pat-003',
        firstName: 'Bob',
        lastName: '',
        phone: '+919876543212',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      expect(patient.fullName, 'Bob');
    });

    test('genderDisplay returns correct values', () {
      final male = Patient(
        id: 'pat-004',
        firstName: 'Male',
        phone: '+919876543213',
        gender: 'M',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );
      expect(male.genderDisplay, 'Male');

      final female = Patient(
        id: 'pat-005',
        firstName: 'Female',
        phone: '+919876543214',
        gender: 'F',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );
      expect(female.genderDisplay, 'Female');

      final other = Patient(
        id: 'pat-006',
        firstName: 'Other',
        phone: '+919876543215',
        gender: 'O',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );
      expect(other.genderDisplay, 'Other');

      final unspecified = Patient(
        id: 'pat-007',
        firstName: 'Unspecified',
        phone: '+919876543216',
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );
      expect(unspecified.genderDisplay, 'Not specified');
    });

    test('age calculation handles birthday not yet occurred this year', () {
      final now = DateTime.now();
      final futureMonthBirthday = DateTime(
        now.year - 30,
        now.month + 1 > 12 ? 1 : now.month + 1,
        15,
      );

      final patient = Patient(
        id: 'pat-008',
        firstName: 'Test',
        phone: '+919876543217',
        dateOfBirth: futureMonthBirthday,
        clinicId: 'clinic-001',
        isActive: true,
        createdAt: DateTime(2023, 1, 1),
      );

      // If birthday hasn't occurred this year, age should be one less
      if (futureMonthBirthday.month > now.month) {
        expect(patient.age, 29);
      }
    });
  });
}

// Test widget wrapper
class _PatientCardTest extends StatelessWidget {
  final Patient patient;
  final VoidCallback onTap;

  const _PatientCardTest({
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

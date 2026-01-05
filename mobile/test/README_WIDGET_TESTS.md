# Flutter Widget Tests - DocAssist Practice Manager

This directory contains comprehensive widget tests for the DocAssist Practice Manager mobile application.

## 📋 Test Coverage

### Core Widgets (`test/core/widgets/`)

#### 1. **appointment_card_test.dart**
Tests for the appointment card widget component:
- ✅ Displays patient name correctly
- ✅ Shows appointment time formatting
- ✅ Status badge colors (scheduled, checked-in, completed, cancelled)
- ✅ Chief complaint display
- ✅ Token number display
- ✅ Check-in button functionality
- ✅ Card tap navigation
- ✅ Patient avatar with initials
- ✅ Long name overflow handling

#### 2. **patient_card_test.dart**
Tests for the patient card widget component:
- ✅ Full name display (with/without last name)
- ✅ Phone number display
- ✅ Gender display (Male, Female, Other)
- ✅ Age calculation from date of birth
- ✅ Avatar with first letter
- ✅ Card tap navigation
- ✅ Handles missing data (email, gender, DOB)
- ✅ Special characters in names
- ✅ Model logic tests (fullName, genderDisplay, age)

### Feature Tests (`test/features/`)

#### 3. **appointments/presentation/appointment_list_screen_test.dart**
Tests for the appointments list screen:
- ✅ Loading state with spinner
- ✅ Error state with message
- ✅ Empty state
- ✅ List rendering with data
- ✅ Status filtering
- ✅ Check-in button visibility
- ✅ Check-in callback
- ✅ Pull-to-refresh
- ✅ List scrolling
- ✅ Token number display
- ✅ Chief complaint display
- ✅ Multiple appointments with same status

#### 4. **patients/presentation/patient_list_screen_test.dart**
Tests for the patients list screen:
- ✅ Loading state during search
- ✅ Error state with retry button
- ✅ Empty search state
- ✅ No results message
- ✅ List rendering with search results
- ✅ Patient details display
- ✅ Avatar rendering
- ✅ Card tap navigation
- ✅ List scrolling
- ✅ Add patient button
- ✅ Filter functionality
- ✅ Special characters handling

## 🚀 Running Tests

### Run All Widget Tests
```bash
cd /home/user/appointment_system/mobile
flutter test
```

### Run Specific Test File
```bash
# Appointment card tests
flutter test test/core/widgets/appointment_card_test.dart

# Patient card tests
flutter test test/core/widgets/patient_card_test.dart

# Appointment list screen tests
flutter test test/features/appointments/presentation/appointment_list_screen_test.dart

# Patient list screen tests
flutter test test/features/patients/presentation/patient_list_screen_test.dart
```

### Run Tests with Coverage
```bash
flutter test --coverage
```

### Run Tests in Watch Mode
```bash
flutter test --watch
```

### Run Specific Test Group
```bash
flutter test --name "AppointmentCard"
flutter test --name "PatientCard"
```

## 📦 Dependencies

The following test dependencies are included in `pubspec.yaml`:

```yaml
dev_dependencies:
  flutter_test:
    sdk: flutter
  mocktail: ^1.0.1  # For mocking
```

## 🏗️ Test Structure

Each test file follows this structure:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

void main() {
  group('Widget Name Tests', () {
    late MockDependency mockDependency;

    setUp(() {
      // Setup before each test
      mockDependency = MockDependency();
    });

    testWidgets('should display something', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(home: TestWidget()),
      );

      // Act & Assert
      expect(find.text('Expected Text'), findsOneWidget);
    });
  });
}
```

## 🧪 Test Patterns Used

### 1. **Widget Testing**
- Use `testWidgets()` for widget tests
- `WidgetTester` for interacting with widgets
- `pumpWidget()` to render widgets
- `pumpAndSettle()` for animations

### 2. **Finding Widgets**
- `find.text('text')` - Find by text
- `find.byType(Widget)` - Find by widget type
- `find.byIcon(Icons.icon)` - Find by icon
- `find.byKey(Key('key'))` - Find by key

### 3. **Assertions**
- `expect(finder, findsOneWidget)` - Exactly one widget
- `expect(finder, findsNothing)` - No widgets
- `expect(finder, findsNWidgets(n))` - Exactly n widgets
- `expect(finder, findsWidgets)` - At least one widget

### 4. **Interactions**
- `await tester.tap(finder)` - Tap widget
- `await tester.enterText(finder, 'text')` - Enter text
- `await tester.fling(finder, offset, speed)` - Scroll gesture
- `await tester.pump()` - Rebuild widgets

### 5. **Mocking with Mocktail**
- Create mock classes extending `Mock`
- Use `when()` for stubbing
- Use `verify()` for verification

## 📝 Test Data

Test files include factory methods and helper classes for creating test data:

### Appointment Test Data
```dart
final testAppointment = Appointment(
  id: 'apt-001',
  patientName: 'John Doe',
  doctorName: 'Dr. Smith',
  scheduledStart: DateTime.now(),
  status: 'scheduled',
  // ... other fields
);
```

### Patient Test Data
```dart
final testPatient = Patient(
  id: 'pat-001',
  firstName: 'John',
  lastName: 'Doe',
  phone: '+919876543210',
  // ... other fields
);
```

## 🎯 Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Clear Names**: Use descriptive test names
3. **Arrange-Act-Assert**: Follow AAA pattern
4. **Mock External Dependencies**: Use mocktail for providers
5. **Test Edge Cases**: Handle null, empty, and error states
6. **Use ProviderScope**: Wrap widgets for Riverpod testing

## 🐛 Common Issues

### Issue: "No Material widget found"
**Solution**: Wrap widget in `MaterialApp`
```dart
await tester.pumpWidget(
  MaterialApp(home: YourWidget()),
);
```

### Issue: "RenderFlex overflowed"
**Solution**: Wrap in `SingleChildScrollView` or use bounded constraints
```dart
await tester.pumpWidget(
  MaterialApp(
    home: Scaffold(
      body: SizedBox(
        width: 400,
        height: 600,
        child: YourWidget(),
      ),
    ),
  ),
);
```

### Issue: "Null check operator used on a null value"
**Solution**: Ensure all required providers are overridden
```dart
ProviderScope(
  overrides: [
    yourProvider.overrideWith((ref) => mockNotifier),
  ],
  child: YourWidget(),
)
```

## 📊 Test Coverage Goals

Target coverage metrics:
- **Overall**: > 80%
- **Core Widgets**: > 90%
- **Feature Screens**: > 75%
- **Critical Paths**: 100%

## 🔍 Code Quality Checks

Run these before committing:

```bash
# Format code
flutter format lib/ test/

# Analyze code
flutter analyze

# Run tests
flutter test

# Generate coverage
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
open coverage/html/index.html
```

## 📚 Additional Resources

- [Flutter Testing Documentation](https://docs.flutter.dev/testing)
- [Widget Testing Guide](https://docs.flutter.dev/cookbook/testing/widget/introduction)
- [Mocktail Package](https://pub.dev/packages/mocktail)
- [Riverpod Testing](https://riverpod.dev/docs/essentials/testing)

## 🚧 Future Enhancements

Planned test additions:
- [ ] Integration tests for complete user flows
- [ ] Golden tests for visual regression
- [ ] Performance tests for list scrolling
- [ ] Accessibility tests (semantics)
- [ ] Internationalization tests

---

**Last Updated**: 2026-01-05
**Test Files**: 4 new widget test files
**Total Test Cases**: 100+ comprehensive tests

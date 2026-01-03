/// Patient model
class Patient {
  final String id;
  final String firstName;
  final String? lastName;
  final String phone;
  final String? email;
  final DateTime? dateOfBirth;
  final String? gender;
  final String? address;
  final String? city;
  final String? bloodGroup;
  final String? allergies;
  final String clinicId;
  final bool isActive;
  final DateTime createdAt;

  Patient({
    required this.id,
    required this.firstName,
    this.lastName,
    required this.phone,
    this.email,
    this.dateOfBirth,
    this.gender,
    this.address,
    this.city,
    this.bloodGroup,
    this.allergies,
    required this.clinicId,
    required this.isActive,
    required this.createdAt,
  });

  factory Patient.fromJson(Map<String, dynamic> json) {
    return Patient(
      id: json['id'],
      firstName: json['first_name'],
      lastName: json['last_name'],
      phone: json['phone'],
      email: json['email'],
      dateOfBirth: json['date_of_birth'] != null
          ? DateTime.parse(json['date_of_birth'])
          : null,
      gender: json['gender'],
      address: json['address'],
      city: json['city'],
      bloodGroup: json['blood_group'],
      allergies: json['allergies'],
      clinicId: json['clinic_id'],
      isActive: json['is_active'] ?? true,
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  String get fullName {
    if (lastName != null && lastName!.isNotEmpty) {
      return '$firstName $lastName';
    }
    return firstName;
  }

  int? get age {
    if (dateOfBirth == null) return null;
    final now = DateTime.now();
    int years = now.year - dateOfBirth!.year;
    if (now.month < dateOfBirth!.month ||
        (now.month == dateOfBirth!.month && now.day < dateOfBirth!.day)) {
      years--;
    }
    return years;
  }

  String get genderDisplay {
    switch (gender) {
      case 'M':
        return 'Male';
      case 'F':
        return 'Female';
      case 'O':
        return 'Other';
      default:
        return gender ?? 'Not specified';
    }
  }
}

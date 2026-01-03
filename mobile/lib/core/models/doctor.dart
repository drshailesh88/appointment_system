/// Doctor model
class Doctor {
  final String id;
  final String name;
  final String? specialization;
  final String? qualification;
  final String? registrationNumber;
  final int? experienceYears;
  final String? phone;
  final String? email;
  final String clinicId;
  final double consultationFee;
  final double? followupFee;
  final int slotDuration;
  final Map<String, dynamic>? workingHours;
  final String? photoUrl;
  final List<String>? languages;
  final bool isActive;
  final bool acceptingNewPatients;

  Doctor({
    required this.id,
    required this.name,
    this.specialization,
    this.qualification,
    this.registrationNumber,
    this.experienceYears,
    this.phone,
    this.email,
    required this.clinicId,
    required this.consultationFee,
    this.followupFee,
    required this.slotDuration,
    this.workingHours,
    this.photoUrl,
    this.languages,
    required this.isActive,
    required this.acceptingNewPatients,
  });

  factory Doctor.fromJson(Map<String, dynamic> json) {
    return Doctor(
      id: json['id'],
      name: json['name'],
      specialization: json['specialization'],
      qualification: json['qualification'],
      registrationNumber: json['registration_number'],
      experienceYears: json['experience_years'],
      phone: json['phone'],
      email: json['email'],
      clinicId: json['clinic_id'],
      consultationFee: (json['consultation_fee'] ?? 500).toDouble(),
      followupFee: json['followup_fee']?.toDouble(),
      slotDuration: json['slot_duration'] ?? 15,
      workingHours: json['working_hours'],
      photoUrl: json['photo_url'],
      languages: json['languages'] != null
          ? List<String>.from(json['languages'])
          : null,
      isActive: json['is_active'] ?? true,
      acceptingNewPatients: json['accepting_new_patients'] ?? true,
    );
  }

  String get feeDisplay => '₹${consultationFee.toStringAsFixed(0)}';

  String get experienceDisplay {
    if (experienceYears == null) return '';
    return '$experienceYears years';
  }
}

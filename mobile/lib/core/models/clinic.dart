/// Clinic model for multi-location practices
///
/// Represents a physical clinic location within an organization.
class Clinic {
  final String id;
  final String name;
  final String organizationId;
  final String? code;
  final String? description;
  final String address;
  final String city;
  final String state;
  final String postalCode;
  final String country;
  final String? phone;
  final String? email;
  final String? website;
  final double? latitude;
  final double? longitude;
  final bool isActive;
  final Map<String, dynamic>? settings;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Computed fields
  final String? organizationName;
  final int staffCount;
  final int patientCount;

  Clinic({
    required this.id,
    required this.name,
    required this.organizationId,
    this.code,
    this.description,
    required this.address,
    required this.city,
    required this.state,
    required this.postalCode,
    this.country = 'India',
    this.phone,
    this.email,
    this.website,
    this.latitude,
    this.longitude,
    required this.isActive,
    this.settings,
    required this.createdAt,
    required this.updatedAt,
    this.organizationName,
    this.staffCount = 0,
    this.patientCount = 0,
  });

  factory Clinic.fromJson(Map<String, dynamic> json) {
    return Clinic(
      id: json['id'],
      name: json['name'],
      organizationId: json['organization_id'],
      code: json['code'],
      description: json['description'],
      address: json['address'],
      city: json['city'],
      state: json['state'],
      postalCode: json['postal_code'],
      country: json['country'] ?? 'India',
      phone: json['phone'],
      email: json['email'],
      website: json['website'],
      latitude: json['latitude']?.toDouble(),
      longitude: json['longitude']?.toDouble(),
      isActive: json['is_active'],
      settings: json['settings'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      organizationName: json['organization_name'],
      staffCount: json['staff_count'] ?? 0,
      patientCount: json['patient_count'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'organization_id': organizationId,
      'code': code,
      'description': description,
      'address': address,
      'city': city,
      'state': state,
      'postal_code': postalCode,
      'country': country,
      'phone': phone,
      'email': email,
      'website': website,
      'latitude': latitude,
      'longitude': longitude,
      'is_active': isActive,
      'settings': settings,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'organization_name': organizationName,
      'staff_count': staffCount,
      'patient_count': patientCount,
    };
  }

  Clinic copyWith({
    String? id,
    String? name,
    String? organizationId,
    String? code,
    String? description,
    String? address,
    String? city,
    String? state,
    String? postalCode,
    String? country,
    String? phone,
    String? email,
    String? website,
    double? latitude,
    double? longitude,
    bool? isActive,
    Map<String, dynamic>? settings,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? organizationName,
    int? staffCount,
    int? patientCount,
  }) {
    return Clinic(
      id: id ?? this.id,
      name: name ?? this.name,
      organizationId: organizationId ?? this.organizationId,
      code: code ?? this.code,
      description: description ?? this.description,
      address: address ?? this.address,
      city: city ?? this.city,
      state: state ?? this.state,
      postalCode: postalCode ?? this.postalCode,
      country: country ?? this.country,
      phone: phone ?? this.phone,
      email: email ?? this.email,
      website: website ?? this.website,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      isActive: isActive ?? this.isActive,
      settings: settings ?? this.settings,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      organizationName: organizationName ?? this.organizationName,
      staffCount: staffCount ?? this.staffCount,
      patientCount: patientCount ?? this.patientCount,
    );
  }

  /// Get full address as single string
  String get fullAddress {
    return '$address, $city, $state $postalCode';
  }

  /// Check if clinic has location coordinates
  bool get hasCoordinates {
    return latitude != null && longitude != null;
  }
}

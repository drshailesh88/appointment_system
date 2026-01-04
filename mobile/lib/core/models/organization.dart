/// Organization model for multi-location practice groups
///
/// Represents a parent organization that can manage multiple clinics.
class Organization {
  final String id;
  final String name;
  final String slug;
  final String? description;
  final String ownerUserId;
  final String subscriptionTier;
  final String? subscriptionExpiresAt;
  final int maxClinics;
  final int maxUsers;
  final String? logoUrl;
  final String primaryColor;
  final String? email;
  final String? phone;
  final String? website;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Computed fields
  final int clinicCount;
  final int userCount;

  Organization({
    required this.id,
    required this.name,
    required this.slug,
    this.description,
    required this.ownerUserId,
    required this.subscriptionTier,
    this.subscriptionExpiresAt,
    required this.maxClinics,
    required this.maxUsers,
    this.logoUrl,
    required this.primaryColor,
    this.email,
    this.phone,
    this.website,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
    this.clinicCount = 0,
    this.userCount = 0,
  });

  factory Organization.fromJson(Map<String, dynamic> json) {
    return Organization(
      id: json['id'],
      name: json['name'],
      slug: json['slug'],
      description: json['description'],
      ownerUserId: json['owner_user_id'],
      subscriptionTier: json['subscription_tier'],
      subscriptionExpiresAt: json['subscription_expires_at'],
      maxClinics: json['max_clinics'],
      maxUsers: json['max_users'],
      logoUrl: json['logo_url'],
      primaryColor: json['primary_color'],
      email: json['email'],
      phone: json['phone'],
      website: json['website'],
      isActive: json['is_active'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      clinicCount: json['clinic_count'] ?? 0,
      userCount: json['user_count'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'slug': slug,
      'description': description,
      'owner_user_id': ownerUserId,
      'subscription_tier': subscriptionTier,
      'subscription_expires_at': subscriptionExpiresAt,
      'max_clinics': maxClinics,
      'max_users': maxUsers,
      'logo_url': logoUrl,
      'primary_color': primaryColor,
      'email': email,
      'phone': phone,
      'website': website,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'clinic_count': clinicCount,
      'user_count': userCount,
    };
  }

  Organization copyWith({
    String? id,
    String? name,
    String? slug,
    String? description,
    String? ownerUserId,
    String? subscriptionTier,
    String? subscriptionExpiresAt,
    int? maxClinics,
    int? maxUsers,
    String? logoUrl,
    String? primaryColor,
    String? email,
    String? phone,
    String? website,
    bool? isActive,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? clinicCount,
    int? userCount,
  }) {
    return Organization(
      id: id ?? this.id,
      name: name ?? this.name,
      slug: slug ?? this.slug,
      description: description ?? this.description,
      ownerUserId: ownerUserId ?? this.ownerUserId,
      subscriptionTier: subscriptionTier ?? this.subscriptionTier,
      subscriptionExpiresAt: subscriptionExpiresAt ?? this.subscriptionExpiresAt,
      maxClinics: maxClinics ?? this.maxClinics,
      maxUsers: maxUsers ?? this.maxUsers,
      logoUrl: logoUrl ?? this.logoUrl,
      primaryColor: primaryColor ?? this.primaryColor,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      website: website ?? this.website,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      clinicCount: clinicCount ?? this.clinicCount,
      userCount: userCount ?? this.userCount,
    );
  }
}

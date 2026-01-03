/// User model
class User {
  final String id;
  final String? name;
  final String? email;
  final String? phone;
  final String role;
  final String? clinicId;
  final String? avatarUrl;

  User({
    required this.id,
    this.name,
    this.email,
    this.phone,
    required this.role,
    this.clinicId,
    this.avatarUrl,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      name: json['name'],
      email: json['email'],
      phone: json['phone'],
      role: json['role'],
      clinicId: json['clinic_id'],
      avatarUrl: json['avatar_url'],
    );
  }

  bool get isAdmin => role == 'admin';
  bool get isDoctor => role == 'doctor';
  bool get isReceptionist => role == 'receptionist';
}

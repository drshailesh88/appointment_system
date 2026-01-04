/// Insurance models for patient insurance and verification

/// Patient insurance information
class PatientInsurance {
  final String id;
  final String patientId;
  final String providerName;
  final String policyNumber;
  final String? groupNumber;
  final String insuranceType;
  final String? planName;
  final DateTime? coverageStartDate;
  final DateTime? coverageEndDate;
  final bool isPrimary;
  final String? subscriberName;
  final String? subscriberRelationship;
  final String? tpaName;
  final String? tpaId;
  final bool cashlessEnabled;
  final String? networkType;
  final double? copayAmount;
  final double? deductibleAmount;
  final double? outOfPocketMax;
  final Map<String, dynamic>? additionalInfo;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;

  PatientInsurance({
    required this.id,
    required this.patientId,
    required this.providerName,
    required this.policyNumber,
    this.groupNumber,
    required this.insuranceType,
    this.planName,
    this.coverageStartDate,
    this.coverageEndDate,
    required this.isPrimary,
    this.subscriberName,
    this.subscriberRelationship,
    this.tpaName,
    this.tpaId,
    required this.cashlessEnabled,
    this.networkType,
    this.copayAmount,
    this.deductibleAmount,
    this.outOfPocketMax,
    this.additionalInfo,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  factory PatientInsurance.fromJson(Map<String, dynamic> json) {
    return PatientInsurance(
      id: json['id'],
      patientId: json['patient_id'],
      providerName: json['provider_name'],
      policyNumber: json['policy_number'],
      groupNumber: json['group_number'],
      insuranceType: json['insurance_type'],
      planName: json['plan_name'],
      coverageStartDate: json['coverage_start_date'] != null
          ? DateTime.parse(json['coverage_start_date'])
          : null,
      coverageEndDate: json['coverage_end_date'] != null
          ? DateTime.parse(json['coverage_end_date'])
          : null,
      isPrimary: json['is_primary'] ?? false,
      subscriberName: json['subscriber_name'],
      subscriberRelationship: json['subscriber_relationship'],
      tpaName: json['tpa_name'],
      tpaId: json['tpa_id'],
      cashlessEnabled: json['cashless_enabled'] ?? false,
      networkType: json['network_type'],
      copayAmount: json['copay_amount'] != null
          ? (json['copay_amount'] as num).toDouble()
          : null,
      deductibleAmount: json['deductible_amount'] != null
          ? (json['deductible_amount'] as num).toDouble()
          : null,
      outOfPocketMax: json['out_of_pocket_max'] != null
          ? (json['out_of_pocket_max'] as num).toDouble()
          : null,
      additionalInfo: json['additional_info'],
      isActive: json['is_active'] ?? true,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'patient_id': patientId,
      'provider_name': providerName,
      'policy_number': policyNumber,
      'group_number': groupNumber,
      'insurance_type': insuranceType,
      'plan_name': planName,
      'coverage_start_date': coverageStartDate?.toIso8601String(),
      'coverage_end_date': coverageEndDate?.toIso8601String(),
      'is_primary': isPrimary,
      'subscriber_name': subscriberName,
      'subscriber_relationship': subscriberRelationship,
      'tpa_name': tpaName,
      'tpa_id': tpaId,
      'cashless_enabled': cashlessEnabled,
      'network_type': networkType,
      'copay_amount': copayAmount,
      'deductible_amount': deductibleAmount,
      'out_of_pocket_max': outOfPocketMax,
      'additional_info': additionalInfo,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  bool get isExpired {
    if (coverageEndDate == null) return false;
    return coverageEndDate!.isBefore(DateTime.now());
  }

  bool get isExpiringSoon {
    if (coverageEndDate == null) return false;
    final daysUntilExpiry =
        coverageEndDate!.difference(DateTime.now()).inDays;
    return daysUntilExpiry > 0 && daysUntilExpiry <= 30;
  }

  String get insuranceTypeDisplay {
    switch (insuranceType) {
      case 'health':
        return 'Health';
      case 'dental':
        return 'Dental';
      case 'vision':
        return 'Vision';
      case 'accident':
        return 'Accident';
      case 'critical_illness':
        return 'Critical Illness';
      default:
        return insuranceType;
    }
  }

  String get subscriberRelationshipDisplay {
    switch (subscriberRelationship) {
      case 'self':
        return 'Self';
      case 'spouse':
        return 'Spouse';
      case 'parent':
        return 'Parent';
      case 'child':
        return 'Child';
      case 'other':
        return 'Other';
      default:
        return subscriberRelationship ?? 'Not specified';
    }
  }
}

/// Insurance list item (minimal info)
class InsuranceListItem {
  final String id;
  final String providerName;
  final String policyNumber;
  final String insuranceType;
  final bool isPrimary;
  final bool isActive;
  final DateTime? coverageEndDate;
  final DateTime? lastVerified;

  InsuranceListItem({
    required this.id,
    required this.providerName,
    required this.policyNumber,
    required this.insuranceType,
    required this.isPrimary,
    required this.isActive,
    this.coverageEndDate,
    this.lastVerified,
  });

  factory InsuranceListItem.fromJson(Map<String, dynamic> json) {
    return InsuranceListItem(
      id: json['id'],
      providerName: json['provider_name'],
      policyNumber: json['policy_number'],
      insuranceType: json['insurance_type'],
      isPrimary: json['is_primary'] ?? false,
      isActive: json['is_active'] ?? true,
      coverageEndDate: json['coverage_end_date'] != null
          ? DateTime.parse(json['coverage_end_date'])
          : null,
      lastVerified: json['last_verified'] != null
          ? DateTime.parse(json['last_verified'])
          : null,
    );
  }
}

/// Coverage details
class CoverageDetails {
  final String? planName;
  final String? coverageLevel;
  final String? networkStatus;
  final List<String>? coveredServices;
  final List<String>? excludedServices;
  final double? maxCoverageAmount;
  final double? remainingCoverage;

  CoverageDetails({
    this.planName,
    this.coverageLevel,
    this.networkStatus,
    this.coveredServices,
    this.excludedServices,
    this.maxCoverageAmount,
    this.remainingCoverage,
  });

  factory CoverageDetails.fromJson(Map<String, dynamic> json) {
    return CoverageDetails(
      planName: json['plan_name'],
      coverageLevel: json['coverage_level'],
      networkStatus: json['network_status'],
      coveredServices: json['covered_services'] != null
          ? List<String>.from(json['covered_services'])
          : null,
      excludedServices: json['excluded_services'] != null
          ? List<String>.from(json['excluded_services'])
          : null,
      maxCoverageAmount: json['max_coverage_amount'] != null
          ? (json['max_coverage_amount'] as num).toDouble()
          : null,
      remainingCoverage: json['remaining_coverage'] != null
          ? (json['remaining_coverage'] as num).toDouble()
          : null,
    );
  }
}

/// Copay information
class CopayInfo {
  final double? amount;
  final double? percentage;
  final String? description;
  final String? appliesTo;

  CopayInfo({
    this.amount,
    this.percentage,
    this.description,
    this.appliesTo,
  });

  factory CopayInfo.fromJson(Map<String, dynamic> json) {
    return CopayInfo(
      amount:
          json['amount'] != null ? (json['amount'] as num).toDouble() : null,
      percentage: json['percentage'] != null
          ? (json['percentage'] as num).toDouble()
          : null,
      description: json['description'],
      appliesTo: json['applies_to'],
    );
  }
}

/// Deductible information
class DeductibleInfo {
  final double? totalDeductible;
  final double? remainingDeductible;
  final double? metAmount;
  final double? familyDeductible;
  final DateTime? resetDate;

  DeductibleInfo({
    this.totalDeductible,
    this.remainingDeductible,
    this.metAmount,
    this.familyDeductible,
    this.resetDate,
  });

  factory DeductibleInfo.fromJson(Map<String, dynamic> json) {
    return DeductibleInfo(
      totalDeductible: json['total_deductible'] != null
          ? (json['total_deductible'] as num).toDouble()
          : null,
      remainingDeductible: json['remaining_deductible'] != null
          ? (json['remaining_deductible'] as num).toDouble()
          : null,
      metAmount: json['met_amount'] != null
          ? (json['met_amount'] as num).toDouble()
          : null,
      familyDeductible: json['family_deductible'] != null
          ? (json['family_deductible'] as num).toDouble()
          : null,
      resetDate: json['reset_date'] != null
          ? DateTime.parse(json['reset_date'])
          : null,
    );
  }
}

/// Insurance verification result
class VerificationResult {
  final String id;
  final String insuranceId;
  final DateTime verifiedAt;
  final String? verifiedBy;
  final String status;
  final bool? isEligible;
  final DateTime? eligibilityStartDate;
  final DateTime? eligibilityEndDate;
  final CoverageDetails? coverageDetails;
  final CopayInfo? copayInfo;
  final DeductibleInfo? deductibleInfo;
  final Map<String, dynamic>? benefits;
  final String? limitations;
  final String? errorMessage;
  final DateTime? expiresAt;

  VerificationResult({
    required this.id,
    required this.insuranceId,
    required this.verifiedAt,
    this.verifiedBy,
    required this.status,
    this.isEligible,
    this.eligibilityStartDate,
    this.eligibilityEndDate,
    this.coverageDetails,
    this.copayInfo,
    this.deductibleInfo,
    this.benefits,
    this.limitations,
    this.errorMessage,
    this.expiresAt,
  });

  factory VerificationResult.fromJson(Map<String, dynamic> json) {
    return VerificationResult(
      id: json['id'],
      insuranceId: json['insurance_id'],
      verifiedAt: DateTime.parse(json['verified_at']),
      verifiedBy: json['verified_by'],
      status: json['status'],
      isEligible: json['is_eligible'],
      eligibilityStartDate: json['eligibility_start_date'] != null
          ? DateTime.parse(json['eligibility_start_date'])
          : null,
      eligibilityEndDate: json['eligibility_end_date'] != null
          ? DateTime.parse(json['eligibility_end_date'])
          : null,
      coverageDetails: json['coverage_details'] != null
          ? CoverageDetails.fromJson(json['coverage_details'])
          : null,
      copayInfo: json['copay_info'] != null
          ? CopayInfo.fromJson(json['copay_info'])
          : null,
      deductibleInfo: json['deductible_info'] != null
          ? DeductibleInfo.fromJson(json['deductible_info'])
          : null,
      benefits: json['benefits'],
      limitations: json['limitations'],
      errorMessage: json['error_message'],
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'])
          : null,
    );
  }

  bool get isSuccess => status == 'success';
  bool get isFailed => status == 'failed';
  bool get isPending => status == 'pending';
  bool get isExpired =>
      expiresAt != null && expiresAt!.isBefore(DateTime.now());
}

/// Insurance provider
class InsuranceProvider {
  final String code;
  final String name;
  final String country;
  final bool supportsVerification;
  final bool supportsClaims;
  final bool tpaRequired;
  final String? documentationUrl;

  InsuranceProvider({
    required this.code,
    required this.name,
    required this.country,
    required this.supportsVerification,
    required this.supportsClaims,
    required this.tpaRequired,
    this.documentationUrl,
  });

  factory InsuranceProvider.fromJson(Map<String, dynamic> json) {
    return InsuranceProvider(
      code: json['code'],
      name: json['name'],
      country: json['country'] ?? 'IN',
      supportsVerification: json['supports_verification'] ?? false,
      supportsClaims: json['supports_claims'] ?? false,
      tpaRequired: json['tpa_required'] ?? false,
      documentationUrl: json['documentation_url'],
    );
  }
}

/// TPA (Third-Party Administrator)
class TPA {
  final String code;
  final String name;
  final String country;

  TPA({
    required this.code,
    required this.name,
    required this.country,
  });

  factory TPA.fromJson(Map<String, dynamic> json) {
    return TPA(
      code: json['code'],
      name: json['name'],
      country: json['country'] ?? 'IN',
    );
  }
}

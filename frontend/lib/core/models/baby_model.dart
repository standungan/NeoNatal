class ParentInfo {
  final String? motherName;
  final String? fatherName;
  final String? motherPhone;
  final String? motherMedicalHistory;
  final String? birthHistory;
  final String? deliveryHistory;
  final String? additionalNotes;

  const ParentInfo({
    this.motherName,
    this.fatherName,
    this.motherPhone,
    this.motherMedicalHistory,
    this.birthHistory,
    this.deliveryHistory,
    this.additionalNotes,
  });

  factory ParentInfo.fromJson(Map<String, dynamic> j) => ParentInfo(
        motherName: j['mother_name'],
        fatherName: j['father_name'],
        motherPhone: j['mother_phone'],
        motherMedicalHistory: j['mother_medical_history'],
        birthHistory: j['birth_history'],
        deliveryHistory: j['delivery_history'],
        additionalNotes: j['additional_notes'],
      );

  Map<String, dynamic> toJson() => {
        'mother_name': motherName,
        'father_name': fatherName,
        'mother_phone': motherPhone,
        'mother_medical_history': motherMedicalHistory,
        'birth_history': birthHistory,
        'delivery_history': deliveryHistory,
        'additional_notes': additionalNotes,
      };
}

class AssignmentInfo {
  final String incubatorId;
  final String incubatorNo;
  final String? location;
  final DateTime assignedAt;
  final String? assignedByName;

  const AssignmentInfo({
    required this.incubatorId,
    required this.incubatorNo,
    this.location,
    required this.assignedAt,
    this.assignedByName,
  });

  factory AssignmentInfo.fromJson(Map<String, dynamic> j) => AssignmentInfo(
        incubatorId: j['incubator_id'],
        incubatorNo: j['incubator_no'],
        location: j['location'],
        assignedAt: DateTime.parse(j['assigned_at']),
        assignedByName: j['assigned_by_name'],
      );
}

class BabyDetail {
  final String babyId;
  final String babyName;
  final String gender;
  final DateTime birthDate;
  final double? birthWeight;
  final double? birthLength;
  final int? gestationalAge;
  final String? birthType;
  final String? clinicalNotes;
  final bool isActive;
  final int ageInDays;
  final ParentInfo? parent;
  final AssignmentInfo? currentAssignment;

  const BabyDetail({
    required this.babyId,
    required this.babyName,
    required this.gender,
    required this.birthDate,
    this.birthWeight,
    this.birthLength,
    this.gestationalAge,
    this.birthType,
    this.clinicalNotes,
    required this.isActive,
    required this.ageInDays,
    this.parent,
    this.currentAssignment,
  });

  factory BabyDetail.fromJson(Map<String, dynamic> j) => BabyDetail(
        babyId: j['baby_id'],
        babyName: j['baby_name'],
        gender: j['gender'],
        birthDate: DateTime.parse(j['birth_date']),
        birthWeight: j['birth_weight'] != null
            ? double.parse(j['birth_weight'].toString())
            : null,
        birthLength: j['birth_length'] != null
            ? double.parse(j['birth_length'].toString())
            : null,
        gestationalAge: j['gestational_age'],
        birthType: j['birth_type'],
        clinicalNotes: j['clinical_notes'],
        isActive: j['is_active'] ?? true,
        ageInDays: j['age_in_days'] ?? 0,
        parent: j['parent'] != null ? ParentInfo.fromJson(j['parent']) : null,
        currentAssignment: j['current_assignment'] != null
            ? AssignmentInfo.fromJson(j['current_assignment'])
            : null,
      );
}

class IncubatorOption {
  final String incubatorId;
  final String incubatorNo;
  final String? location;

  const IncubatorOption({
    required this.incubatorId,
    required this.incubatorNo,
    this.location,
  });

  factory IncubatorOption.fromJson(Map<String, dynamic> j) => IncubatorOption(
        incubatorId: j['incubator_id'],
        incubatorNo: j['incubator_no'],
        location: j['location'],
      );

  @override
  String toString() =>
      'Inkubator $incubatorNo${location != null ? ' - $location' : ''}';
}

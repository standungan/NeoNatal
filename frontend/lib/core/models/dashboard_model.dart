class DashboardStats {
  final int total;
  final int terisi;
  final int kosong;
  final int warning;
  final int tidakTersedia;

  const DashboardStats({
    required this.total,
    required this.terisi,
    required this.kosong,
    required this.warning,
    required this.tidakTersedia,
  });

  factory DashboardStats.fromJson(Map<String, dynamic> j) => DashboardStats(
        total: j['total'],
        terisi: j['terisi'],
        kosong: j['kosong'],
        warning: j['warning'],
        tidakTersedia: j['tidak_tersedia'],
      );
}

class BabySummary {
  final String babyId;
  final String babyName;
  final int ageInDays;
  final double? birthWeight;

  const BabySummary({
    required this.babyId,
    required this.babyName,
    required this.ageInDays,
    this.birthWeight,
  });

  factory BabySummary.fromJson(Map<String, dynamic> j) => BabySummary(
        babyId: j['baby_id'],
        babyName: j['baby_name'],
        ageInDays: j['age_in_days'],
        birthWeight: j['birth_weight'] != null
            ? double.parse(j['birth_weight'].toString())
            : null,
      );
}

class LatestVitals {
  final double? suhuBayi;
  final int? heartRate;
  final double? spo2;
  final DateTime observationTime;
  final String vitalStatus; // "normal" | "warning"

  const LatestVitals({
    this.suhuBayi,
    this.heartRate,
    this.spo2,
    required this.observationTime,
    required this.vitalStatus,
  });

  factory LatestVitals.fromJson(Map<String, dynamic> j) => LatestVitals(
        suhuBayi: j['suhu_bayi'] != null
            ? double.parse(j['suhu_bayi'].toString())
            : null,
        heartRate: j['heart_rate'],
        spo2: j['spo2'] != null ? double.parse(j['spo2'].toString()) : null,
        observationTime: DateTime.parse(j['observation_time']),
        vitalStatus: j['vital_status'] ?? 'normal',
      );
}

class IncubatorDashboardItem {
  final String incubatorId;
  final String incubatorNo;
  final String? location;
  final String status;
  final BabySummary? currentBaby;
  final LatestVitals? latestVitals;

  const IncubatorDashboardItem({
    required this.incubatorId,
    required this.incubatorNo,
    this.location,
    required this.status,
    this.currentBaby,
    this.latestVitals,
  });

  factory IncubatorDashboardItem.fromJson(Map<String, dynamic> j) =>
      IncubatorDashboardItem(
        incubatorId: j['incubator_id'],
        incubatorNo: j['incubator_no'],
        location: j['location'],
        status: j['status'],
        currentBaby: j['current_baby'] != null
            ? BabySummary.fromJson(j['current_baby'])
            : null,
        latestVitals: j['latest_vitals'] != null
            ? LatestVitals.fromJson(j['latest_vitals'])
            : null,
      );
}

class DashboardData {
  final DashboardStats stats;
  final List<IncubatorDashboardItem> incubators;

  const DashboardData({required this.stats, required this.incubators});

  factory DashboardData.fromJson(Map<String, dynamic> j) => DashboardData(
        stats: DashboardStats.fromJson(j['stats']),
        incubators: (j['incubators'] as List)
            .map((e) => IncubatorDashboardItem.fromJson(e))
            .toList(),
      );
}

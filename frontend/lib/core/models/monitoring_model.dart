class MonitoringRecord {
  final String monitoringId;
  final String babyId;
  final String? recorderName;
  final DateTime observationTime;
  final double? suhuBayi;
  final double? suhuInkubator;
  final int? heartRate;
  final double? spo2;
  final int? expressionScore;
  final int? movementScore;
  final String? catatan;
  final String? fotoUrl;
  final String vitalStatus;

  const MonitoringRecord({
    required this.monitoringId,
    required this.babyId,
    this.recorderName,
    required this.observationTime,
    this.suhuBayi,
    this.suhuInkubator,
    this.heartRate,
    this.spo2,
    this.expressionScore,
    this.movementScore,
    this.catatan,
    this.fotoUrl,
    this.vitalStatus = 'normal',
  });

  factory MonitoringRecord.fromJson(Map<String, dynamic> j) => MonitoringRecord(
        monitoringId: j['monitoring_id'],
        babyId: j['baby_id'],
        recorderName: j['recorder_name'],
        observationTime: DateTime.parse(j['observation_time']),
        suhuBayi: j['suhu_bayi'] != null
            ? double.parse(j['suhu_bayi'].toString())
            : null,
        suhuInkubator: j['suhu_inkubator'] != null
            ? double.parse(j['suhu_inkubator'].toString())
            : null,
        heartRate: j['heart_rate'],
        spo2: j['spo2'] != null ? double.parse(j['spo2'].toString()) : null,
        expressionScore: j['expression_score'],
        movementScore: j['movement_score'],
        catatan: j['catatan'],
        fotoUrl: j['foto_url'],
        vitalStatus: j['vital_status'] ?? 'normal',
      );
}

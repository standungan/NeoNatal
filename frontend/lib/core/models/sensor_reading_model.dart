// Telemetry sample from an incubator's IoT device (updates03).
//
// Every metric is nullable and a null is MEANINGFUL: the sensor had nothing to
// report — probe off the baby, DHT22 read failure — which is not the same as
// zero. Charts must break the line rather than plot a 0 or skip the gap.

class SensorReading {
  final String readingId;
  final String incubatorId;
  final String? babyId;
  final DateTime recordedAt;
  final double? suhuBayi;
  final double? suhuInkubator;
  final double? kelembapanInkubator;
  final int? heartRate;
  final double? spo2;
  final int? respiratoryRate;
  final String source;

  const SensorReading({
    required this.readingId,
    required this.incubatorId,
    required this.babyId,
    required this.recordedAt,
    required this.suhuBayi,
    required this.suhuInkubator,
    required this.kelembapanInkubator,
    required this.heartRate,
    required this.spo2,
    required this.respiratoryRate,
    required this.source,
  });

  /// Numeric fields arrive as JSON numbers, but parse defensively: Pydantic
  /// serialises Decimal as a *string* unless a field serializer says otherwise,
  /// and that difference is invisible until arithmetic silently misbehaves.
  static double? _num(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  static int? _int(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toInt();
    return int.tryParse(v.toString());
  }

  factory SensorReading.fromJson(Map<String, dynamic> j) => SensorReading(
        readingId: j['reading_id'] as String,
        incubatorId: j['incubator_id'] as String,
        babyId: j['baby_id'] as String?,
        recordedAt: DateTime.parse(j['recorded_at'] as String).toLocal(),
        suhuBayi: _num(j['suhu_bayi']),
        suhuInkubator: _num(j['suhu_inkubator']),
        kelembapanInkubator: _num(j['kelembapan_inkubator']),
        heartRate: _int(j['heart_rate']),
        spo2: _num(j['spo2']),
        respiratoryRate: _int(j['respiratory_rate']),
        source: (j['source'] ?? 'sensor') as String,
      );

  /// Value for a metric key, so one chart widget can serve every panel.
  double? metric(String key) => switch (key) {
        'suhu_bayi' => suhuBayi,
        'suhu_inkubator' => suhuInkubator,
        'kelembapan_inkubator' => kelembapanInkubator,
        'heart_rate' => heartRate?.toDouble(),
        'spo2' => spo2,
        'respiratory_rate' => respiratoryRate?.toDouble(),
        _ => null,
      };
}

/// One metric's alert bounds, from GET /incubators/{id}/thresholds.
class ThresholdMetric {
  final String key;
  final String label;
  final String unit;
  final double? min;
  final double? max;

  const ThresholdMetric({
    required this.key,
    required this.label,
    required this.unit,
    required this.min,
    required this.max,
  });

  factory ThresholdMetric.fromJson(Map<String, dynamic> j) => ThresholdMetric(
        key: j['key'] as String,
        label: j['label'] as String,
        unit: (j['unit'] ?? '') as String,
        min: SensorReading._num(j['min']),
        max: SensorReading._num(j['max']),
      );
}

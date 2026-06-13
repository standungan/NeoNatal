class InvolvementRecord {
  final String involvementId;
  final String babyId;
  final String? recorderName;
  final DateTime observationTime;
  final int? durasiMenyusui;
  final int? durasiInteraksi;
  final String? catatan;
  final int? skorKeterlibatan;
  final String? skorKategori;
  final String? kondisiBayi;

  const InvolvementRecord({
    required this.involvementId,
    required this.babyId,
    this.recorderName,
    required this.observationTime,
    this.durasiMenyusui,
    this.durasiInteraksi,
    this.catatan,
    this.skorKeterlibatan,
    this.skorKategori,
    this.kondisiBayi,
  });

  factory InvolvementRecord.fromJson(Map<String, dynamic> j) =>
      InvolvementRecord(
        involvementId: j['involvement_id'],
        babyId: j['baby_id'],
        recorderName: j['recorder_name'],
        observationTime: DateTime.parse(j['observation_time']),
        durasiMenyusui: j['durasi_menyusui'],
        durasiInteraksi: j['durasi_interaksi'],
        catatan: j['catatan'],
        skorKeterlibatan: j['skor_keterlibatan'],
        skorKategori: j['skor_kategori'],
        kondisiBayi: j['kondisi_bayi'],
      );
}

class InvolvementSummary {
  final int totalSessions;
  final double? avgSkor;
  final double? avgDurasiMenyusui;
  final double? avgDurasiInteraksi;
  final int? latestSkor;
  final String? latestKategori;

  const InvolvementSummary({
    required this.totalSessions,
    this.avgSkor,
    this.avgDurasiMenyusui,
    this.avgDurasiInteraksi,
    this.latestSkor,
    this.latestKategori,
  });

  factory InvolvementSummary.fromJson(Map<String, dynamic> j) =>
      InvolvementSummary(
        totalSessions: j['total_sessions'] ?? 0,
        avgSkor: j['avg_skor'] != null
            ? double.parse(j['avg_skor'].toString())
            : null,
        avgDurasiMenyusui: j['avg_durasi_menyusui'] != null
            ? double.parse(j['avg_durasi_menyusui'].toString())
            : null,
        avgDurasiInteraksi: j['avg_durasi_interaksi'] != null
            ? double.parse(j['avg_durasi_interaksi'].toString())
            : null,
        latestSkor: j['latest_skor'],
        latestKategori: j['latest_kategori'],
      );
}

/// Client-side score preview — mirrors backend formula exactly
int previewScore(int? menyusui, int? interaksi) {
  final m = menyusui ?? 0;
  final i = interaksi ?? 0;
  final mPts = (m * 2).clamp(0, 60);
  final iPts = (i * 40 / 60).round().clamp(0, 40);
  return mPts + iPts;
}

String scoreCategory(int score) {
  if (score >= 76) return 'Sangat Baik';
  if (score >= 51) return 'Baik';
  if (score >= 26) return 'Sedang';
  return 'Rendah';
}

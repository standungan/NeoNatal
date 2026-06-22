class InvolvementRecord {
  final String involvementId;
  final String babyId;
  final String? recorderName;
  final DateTime observationTime;
  final int? durasiMenyusui;
  final int? durasiInteraksi;
  // Pillar 8 sub-domains (0–4 each)
  final int? presenceScore;
  final int? physicalInteractionScore;
  final int? feedingParticipationScore;
  final int? careParticipationScore;
  final int? knowledgeScore;
  final int? communicationScore;
  final int? emotionalReadinessScore;
  final int? dischargeReadinessScore;
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
    this.presenceScore,
    this.physicalInteractionScore,
    this.feedingParticipationScore,
    this.careParticipationScore,
    this.knowledgeScore,
    this.communicationScore,
    this.emotionalReadinessScore,
    this.dischargeReadinessScore,
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
        presenceScore: j['presence_score'],
        physicalInteractionScore: j['physical_interaction_score'],
        feedingParticipationScore: j['feeding_participation_score'],
        careParticipationScore: j['care_participation_score'],
        knowledgeScore: j['knowledge_score'],
        communicationScore: j['communication_score'],
        emotionalReadinessScore: j['emotional_readiness_score'],
        dischargeReadinessScore: j['discharge_readiness_score'],
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

/// Client-side Parent Engagement Index preview — mirrors backend formula.
/// 8 Pillar-8 domains, each 0–4 (max raw = 32) → PEI = round(sum / 32 * 100).
int previewScore(List<int?> domainScores) {
  final raw = domainScores.fold<int>(0, (sum, v) => sum + (v ?? 0));
  return (raw / 32 * 100).round();
}

String scoreCategory(int score) {
  if (score >= 76) return 'Sangat Baik';
  if (score >= 51) return 'Baik';
  if (score >= 26) return 'Sedang';
  return 'Rendah';
}

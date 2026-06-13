import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';
import 'package:neonatal_care/core/widgets/status_badge.dart';
import 'package:url_launcher/url_launcher.dart';

final _reportProvider =
    FutureProvider.autoDispose.family<Map<String, dynamic>, String>(
  (ref, babyId) async {
    final res = await ApiClient().dio.get(ApiEndpoints.report(babyId));
    return res.data as Map<String, dynamic>;
  },
);

class ReportScreen extends ConsumerWidget {
  final String babyId;
  const ReportScreen({super.key, required this.babyId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reportAsync = ref.watch(_reportProvider(babyId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Laporan & Riwayat Bayi'),
        actions: [
          IconButton(
            icon: const Icon(Icons.picture_as_pdf),
            tooltip: 'Export PDF',
            onPressed: () => _exportPdf(babyId),
          ),
        ],
      ),
      body: reportAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (data) {
          final baby = data['baby'] as Map<String, dynamic>;
          final monitoring = (data['monitoring_history'] as List)
              .cast<Map<String, dynamic>>();
          final involvement = data['involvement_summary'] as Map<String, dynamic>;

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(_reportProvider(babyId)),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _BabyHeader(baby: baby),
                  const SizedBox(height: 12),
                  if (baby['latest_vitals'] != null)
                    _LatestVitalsCard(
                        vitals: baby['latest_vitals'] as Map<String, dynamic>),
                  const SizedBox(height: 12),
                  _InvolvementCard(summary: involvement),
                  const SizedBox(height: 12),
                  _MonitoringHistoryCard(records: monitoring),
                  const SizedBox(height: 12),
                  _VitalsChartCard(records: monitoring),
                  const SizedBox(height: 12),
                  _ExportCard(babyId: babyId),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Future<void> _exportPdf(String babyId) async {
    final token = await ApiClient().getToken();
    final url =
        '${ApiEndpoints.baseUrl}${ApiEndpoints.reportPdf(babyId)}?token=$token';
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

class _BabyHeader extends StatelessWidget {
  final Map<String, dynamic> baby;
  const _BabyHeader({required this.baby});

  @override
  Widget build(BuildContext context) {
    final assignment = baby['current_assignment'] as Map<String, dynamic>?;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha:0.1),
                  shape: BoxShape.circle),
              child: const Icon(Icons.child_care,
                  color: AppColors.primary, size: 28),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(baby['baby_name'],
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
                  Text(
                    'Hari ke-${baby['age_in_days']}  •  '
                    '${baby['birth_weight'] != null ? '${baby['birth_weight']} gram' : '-'}  •  '
                    '${baby['gender'] == 'laki_laki' ? 'Laki-laki' : 'Perempuan'}',
                    style: const TextStyle(fontSize: 12, color: AppColors.inkMuted),
                  ),
                  if (assignment != null)
                    Text('Inkubator ${assignment['incubator_no']}',
                        style: const TextStyle(
                            fontSize: 12, color: AppColors.primary)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LatestVitalsCard extends StatelessWidget {
  final Map<String, dynamic> vitals;
  const _LatestVitalsCard({required this.vitals});

  @override
  Widget build(BuildContext context) {
    final isWarning = vitals['vital_status'] == 'warning';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('Kondisi Terkini',
                    style: TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 15)),
                const Spacer(),
                VitalStatusDot(vitals['vital_status'] ?? 'normal'),
                const SizedBox(width: 6),
                Text(isWarning ? 'Perhatian' : 'Normal',
                    style: TextStyle(
                        color: isWarning ? AppColors.warning : AppColors.normal,
                        fontWeight: FontWeight.w600,
                        fontSize: 13)),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                _VitalTile('Suhu Bayi',       '${vitals['suhu_bayi'] ?? '-'} °C'),
                _VitalTile('Suhu Inkubator',  '${vitals['suhu_inkubator'] ?? '-'} °C'),
                _VitalTile('Heart Rate',      '${vitals['heart_rate'] ?? '-'} bpm'),
                _VitalTile('SpO2',            '${vitals['spo2'] ?? '-'} %'),
                _VitalTile('Ekspresi',        '${vitals['expression_score'] ?? '-'} / 5'),
                _VitalTile('Gerakan',         '${vitals['movement_score'] ?? '-'} / 5'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _VitalTile extends StatelessWidget {
  final String label;
  final String value;
  const _VitalTile(this.label, this.value);

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          children: [
            Text(label,
                style: const TextStyle(
                    fontSize: 11, color: AppColors.inkMuted)),
            const SizedBox(height: 3),
            Text(value,
                style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 13,
                    color: AppColors.ink)),
          ],
        ),
      );
}

class _InvolvementCard extends StatelessWidget {
  final Map<String, dynamic> summary;
  const _InvolvementCard({required this.summary});

  @override
  Widget build(BuildContext context) {
    final skor = summary['latest_skor'];
    final kategori = summary['latest_kategori'] ?? '-';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Keterlibatan Orang Tua',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 12),
            Row(
              children: [
                Text(
                  skor != null ? '$skor' : '-',
                  style: const TextStyle(
                      fontSize: 36,
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary),
                ),
                if (skor != null)
                  const Text(' / 100',
                      style: TextStyle(fontSize: 18, color: AppColors.inkMuted)),
                const SizedBox(width: 12),
                Chip(
                  label: Text(kategori),
                  backgroundColor: AppColors.primary.withValues(alpha:0.1),
                  labelStyle: const TextStyle(color: AppColors.primary),
                ),
              ],
            ),
            Text(
              'Total sesi: ${summary['total_sessions']}  •  '
              'Rata-rata: ${summary['avg_skor']?.toStringAsFixed(1) ?? '-'}',
              style: const TextStyle(color: AppColors.inkMuted, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _MonitoringHistoryCard extends StatelessWidget {
  final List<Map<String, dynamic>> records;
  const _MonitoringHistoryCard({required this.records});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Riwayat Monitoring (${records.length} entri)',
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 12),
            if (records.isEmpty)
              const Text('Belum ada data monitoring.',
                  style: TextStyle(color: AppColors.inkMuted))
            else
              ...records.take(10).map((r) => _MonitoringRow(r)),
          ],
        ),
      ),
    );
  }
}

class _MonitoringRow extends StatelessWidget {
  final Map<String, dynamic> r;
  const _MonitoringRow(this.r);

  @override
  Widget build(BuildContext context) {
    final time = DateFormat('dd/MM/yyyy HH:mm')
        .format(DateTime.parse(r['observation_time']));
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Expanded(
              flex: 3,
              child: Text(time,
                  style: const TextStyle(fontSize: 12, color: AppColors.inkMuted))),
          Expanded(child: Text('${r['suhu_bayi'] ?? '-'}°C',
              style: const TextStyle(fontSize: 12))),
          Expanded(child: Text('${r['heart_rate'] ?? '-'} bpm',
              style: const TextStyle(fontSize: 12))),
          Expanded(child: Text('${r['spo2'] ?? '-'}%',
              style: const TextStyle(fontSize: 12))),
          VitalStatusDot(r['vital_status'] ?? 'normal'),
        ],
      ),
    );
  }
}

// ── Vitals Chart ─────────────────────────────────────────────────────────────

class _VitalsChartCard extends StatelessWidget {
  final List<Map<String, dynamic>> records;
  const _VitalsChartCard({required this.records});

  @override
  Widget build(BuildContext context) {
    if (records.isEmpty) return const SizedBox.shrink();

    // records come newest-first from API — reverse for chronological order
    final sorted = records.reversed.toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Grafik Tren Vital',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 4),
            Row(
              children: [
                Container(width: 16, height: 2, color: Colors.green.shade400),
                const SizedBox(width: 4),
                const Text('Batas normal',
                    style: TextStyle(fontSize: 10, color: AppColors.inkMuted)),
              ],
            ),
            const SizedBox(height: 16),
            _ChartSection(
              title: 'Suhu Bayi (°C)',
              color: Colors.orange,
              data: sorted,
              valueKey: 'suhu_bayi',
              minY: 34,
              maxY: 40,
              normalMin: 36.0,
              normalMax: 37.5,
            ),
            const SizedBox(height: 20),
            _ChartSection(
              title: 'Heart Rate (bpm)',
              color: AppColors.abnormal,
              data: sorted,
              valueKey: 'heart_rate',
              minY: 70,
              maxY: 200,
              normalMin: 100,
              normalMax: 160,
            ),
            const SizedBox(height: 20),
            _ChartSection(
              title: 'SpO2 (%)',
              color: AppColors.primary,
              data: sorted,
              valueKey: 'spo2',
              minY: 80,
              maxY: 100,
              normalMin: 93,
              normalMax: 100,
            ),
          ],
        ),
      ),
    );
  }
}

class _ChartSection extends StatelessWidget {
  final String title;
  final Color color;
  final List<Map<String, dynamic>> data;
  final String valueKey;
  final double minY;
  final double maxY;
  final double normalMin;
  final double normalMax;

  const _ChartSection({
    required this.title,
    required this.color,
    required this.data,
    required this.valueKey,
    required this.minY,
    required this.maxY,
    required this.normalMin,
    required this.normalMax,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(width: 10, height: 10,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
            const SizedBox(width: 6),
            Text(title,
                style: TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w600, color: color)),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 160,
          child: _LineChart(
            data: data,
            valueKey: valueKey,
            color: color,
            minY: minY,
            maxY: maxY,
            normalMin: normalMin,
            normalMax: normalMax,
          ),
        ),
      ],
    );
  }
}

class _LineChart extends StatelessWidget {
  final List<Map<String, dynamic>> data;
  final String valueKey;
  final Color color;
  final double minY;
  final double maxY;
  final double normalMin;
  final double normalMax;

  const _LineChart({
    required this.data,
    required this.valueKey,
    required this.color,
    required this.minY,
    required this.maxY,
    required this.normalMin,
    required this.normalMax,
  });

  @override
  Widget build(BuildContext context) {
    final spots = <FlSpot>[];
    for (var i = 0; i < data.length; i++) {
      final v = data[i][valueKey];
      if (v != null) {
        spots.add(FlSpot(i.toDouble(), double.parse(v.toString())));
      }
    }

    if (spots.length < 2) {
      return const Center(
        child: Text('Butuh minimal 2 data untuk menampilkan grafik',
            style: TextStyle(color: AppColors.inkMuted, fontSize: 13)),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(top: 16, right: 12, bottom: 4),
      child: LineChart(
        LineChartData(
          minY: minY,
          maxY: maxY,
          clipData: const FlClipData.all(),
          extraLinesData: ExtraLinesData(
            horizontalLines: [
              HorizontalLine(
                y: normalMin,
                color: Colors.green.shade300,
                strokeWidth: 1,
                dashArray: [6, 4],
              ),
              HorizontalLine(
                y: normalMax,
                color: Colors.green.shade300,
                strokeWidth: 1,
                dashArray: [6, 4],
              ),
            ],
          ),
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) =>
                FlLine(color: Colors.grey.shade200, strokeWidth: 1),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 38,
                getTitlesWidget: (v, _) => Text(
                  v.toStringAsFixed(0),
                  style: const TextStyle(fontSize: 10, color: AppColors.inkMuted),
                ),
              ),
            ),
            bottomTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            topTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              curveSmoothness: 0.3,
              color: color,
              barWidth: 2.5,
              dotData: FlDotData(
                show: spots.length <= 12,
                getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
                  radius: 3,
                  color: color,
                  strokeWidth: 1.5,
                  strokeColor: Colors.white,
                ),
              ),
              belowBarData: BarAreaData(
                show: true,
                color: color.withValues(alpha: 0.08),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ExportCard extends StatelessWidget {
  final String babyId;
  const _ExportCard({required this.babyId});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Export & Cetak',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              icon: const Icon(Icons.picture_as_pdf),
              label: const Text('Export PDF'),
              onPressed: () async {
                final token = await ApiClient().getToken();
                final url =
                    '${ApiEndpoints.baseUrl}${ApiEndpoints.reportPdf(babyId)}?token=$token';
                final uri = Uri.parse(url);
                if (await canLaunchUrl(uri)) {
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/models/sensor_reading_model.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';
import 'package:neonatal_care/features/incubator/providers/sensor_readings_provider.dart';

/// Live sensor trends for one incubator, as small multiples.
///
/// Mirrors the web dashboard's decisions, for the same reasons:
///  * one metric, one unit, one axis per panel — never a dual-axis plot, where
///    the crossing point of two lines is an artefact of the two scales;
///  * skin and air temperature are separate panels but share a y-range, so a
///    0.3 °C wobble cannot look like a 3 °C swing;
///  * a null BREAKS the line. Skipping null spots (as the report screen does)
///    would draw straight through a period where the probe was off the baby,
///    inventing readings that were never taken.
class SensorChartCard extends ConsumerWidget {
  final String incubatorId;
  const SensorChartCard({super.key, required this.incubatorId});

  static const _panels = <_PanelSpec>[
    _PanelSpec('Suhu Bayi', '°C', 'suhu_bayi', scaleGroup: 'celsius'),
    _PanelSpec('Suhu Inkubator', '°C', 'suhu_inkubator', scaleGroup: 'celsius'),
    _PanelSpec('Detak Jantung', 'bpm', 'heart_rate'),
    _PanelSpec('SpO₂', '%', 'spo2'),
    _PanelSpec('Kelembapan', '%', 'kelembapan_inkubator'),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final readingsAsync = ref.watch(sensorReadingsProvider(incubatorId));
    final thresholds =
        ref.watch(incubatorThresholdsProvider(incubatorId)).valueOrNull ??
            const <ThresholdMetric>[];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: readingsAsync.when(
          loading: () => const SizedBox(
            height: 120,
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (e, _) => _Frame(
            child: Text('Gagal memuat data sensor: $e',
                style: const TextStyle(fontSize: 12.5, color: AppColors.abnormal)),
          ),
          data: (rows) {
            if (rows.isEmpty) {
              return const _Frame(
                child: Text(
                  'Belum ada data sensor untuk inkubator ini. Grafik muncul '
                  'otomatis setelah perangkat mulai mengirim.',
                  style: TextStyle(fontSize: 12.5, color: AppColors.inkMuted),
                ),
              );
            }

            final domains = _sharedDomains(rows, thresholds);

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Tren Sensor',
                        style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 15,
                            color: AppColors.ink)),
                    Text('${rows.length} pembacaan',
                        style: const TextStyle(
                            fontSize: 11.5, color: AppColors.inkMuted)),
                  ],
                ),
                const SizedBox(height: 12),
                for (final p in _panels) ...[
                  _Panel(
                    spec: p,
                    rows: rows,
                    threshold: thresholds
                        .where((t) => t.key == p.metricKey)
                        .firstOrNull,
                    domain: p.scaleGroup == null ? null : domains[p.scaleGroup],
                  ),
                  const SizedBox(height: 16),
                ],
                const Text(
                  'Garis terputus berarti sensor tidak mengirim nilai saat itu '
                  '— misalnya probe lepas dari bayi. Itu bukan nilai nol.',
                  style: TextStyle(fontSize: 11, color: AppColors.inkMuted),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  /// One y-range per scale group, covering every panel in it plus its band.
  static Map<String, ({double min, double max})> _sharedDomains(
    List<SensorReading> rows,
    List<ThresholdMetric> thresholds,
  ) {
    final out = <String, ({double min, double max})>{};
    for (final group in _panels
        .map((p) => p.scaleGroup)
        .whereType<String>()
        .toSet()) {
      final vals = <double>[];
      for (final p in _panels.where((p) => p.scaleGroup == group)) {
        for (final r in rows) {
          final v = r.metric(p.metricKey);
          if (v != null) vals.add(v);
        }
        final t = thresholds.where((t) => t.key == p.metricKey).firstOrNull;
        if (t?.min != null) vals.add(t!.min!);
        if (t?.max != null) vals.add(t!.max!);
      }
      if (vals.isEmpty) continue;
      final lo = vals.reduce((a, b) => a < b ? a : b);
      final hi = vals.reduce((a, b) => a > b ? a : b);
      final pad = ((hi - lo) * 0.12).clamp(0.5, double.infinity);
      out[group] = (min: lo - pad, max: hi + pad);
    }
    return out;
  }
}

class _PanelSpec {
  final String title;
  final String unit;
  final String metricKey;
  final String? scaleGroup;
  const _PanelSpec(this.title, this.unit, this.metricKey, {this.scaleGroup});
}

class _Frame extends StatelessWidget {
  final Widget child;
  const _Frame({required this.child});

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Tren Sensor',
              style: TextStyle(
                  fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
          const SizedBox(height: 8),
          child,
        ],
      );
}

class _Panel extends StatelessWidget {
  final _PanelSpec spec;
  final List<SensorReading> rows;
  final ThresholdMetric? threshold;
  final ({double min, double max})? domain;

  const _Panel({
    required this.spec,
    required this.rows,
    required this.threshold,
    required this.domain,
  });

  @override
  Widget build(BuildContext context) {
    // FlSpot.nullSpot is fl_chart's documented way to break a line. Building the
    // list positionally (rather than skipping nulls, as report_screen does) is
    // what makes a gap render as a gap.
    final spots = <FlSpot>[];
    double? lo, hi;
    for (var i = 0; i < rows.length; i++) {
      final v = rows[i].metric(spec.metricKey);
      if (v == null) {
        spots.add(FlSpot.nullSpot);
      } else {
        spots.add(FlSpot(i.toDouble(), v));
        lo = (lo == null || v < lo) ? v : lo;
        hi = (hi == null || v > hi) ? v : hi;
      }
    }

    final loV = lo;
    final hiV = hi;
    final hasAny = loV != null && hiV != null;
    final latest = rows.reversed
        .map((r) => r.metric(spec.metricKey))
        .firstWhere((v) => v != null, orElse: () => null);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('${spec.title} (${spec.unit})',
                style: const TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                    color: AppColors.ink)),
            Text(
              latest == null ? '—' : _fmt(latest),
              style: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w800,
                  color: latest == null ? AppColors.inkMuted : AppColors.ink),
            ),
          ],
        ),
        const SizedBox(height: 6),
        SizedBox(
          height: 130,
          child: hasAny
              ? LineChart(_chartData(spots, lo!, hi!))
              : Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    'Sensor belum mengirim nilai untuk ${spec.title}.',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        fontSize: 11.5, color: AppColors.inkMuted),
                  ),
                ),
        ),
      ],
    );
  }

  static String _fmt(double v) =>
      v == v.roundToDouble() ? v.toStringAsFixed(0) : v.toStringAsFixed(1);

  LineChartData _chartData(List<FlSpot> spots, double dataLo, double dataHi) {
    // A panel with no scaleGroup takes its range from the data alone, so a flat
    // series - every reading identical, which is normal for heart rate and SpO2
    // between events - collapses to the 0.5 floor below. The threshold band then
    // spans far wider than that window and covers the plot edge to edge, which
    // reads as a solid grey block rather than a chart. Fold the band into the
    // range exactly as _sharedDomains already does for grouped panels, so the
    // reading is shown sitting inside its normal range instead.
    var lo = dataLo;
    var hi = dataHi;
    if (domain == null) {
      for (final bound in [threshold?.min, threshold?.max]) {
        if (bound == null) continue;
        if (bound < lo) lo = bound;
        if (bound > hi) hi = bound;
      }
    }

    final pad = ((hi - lo) * 0.12).clamp(0.5, double.infinity);
    final minY = domain?.min ?? (lo - pad);
    final maxY = domain?.max ?? (hi + pad);
    final step = (maxY - minY) / 4;

    return LineChartData(
      minY: minY,
      maxY: maxY,
      minX: 0,
      maxX: (rows.length - 1).toDouble(),
      clipData: const FlClipData.all(),
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: step,
        getDrawingHorizontalLine: (_) =>
            const FlLine(color: Color(0xFFEEF2F7), strokeWidth: 1),
      ),
      borderData: FlBorderData(show: false),
      // Normal-range band from the incubator's own thresholds, so admin
      // overrides are reflected without any extra wiring.
      rangeAnnotations: RangeAnnotations(
        horizontalRangeAnnotations: [
          if (threshold?.min != null || threshold?.max != null)
            HorizontalRangeAnnotation(
              y1: threshold?.min ?? minY,
              y2: threshold?.max ?? maxY,
              color: const Color(0xFF94A3B8).withValues(alpha: 0.10),
            ),
        ],
      ),
      titlesData: FlTitlesData(
        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 38,
            interval: step,
            // Tanpa interval yang tetap, fl_chart menandai tepi bawah sumbu
            // sekaligus tick pertama; pada rentang sempit keduanya jatuh nyaris
            // di titik yang sama dan angkanya bertumpuk ('26.0' menimpa '25.7').
            // Kedua tepi dilewati, tersisa tiga label yang berjarak sama.
            getTitlesWidget: (v, meta) {
              if (v <= minY + step * 0.05 || v >= maxY - step * 0.05) {
                return const SizedBox.shrink();
              }
              return Text(
                _fmt(v),
                style: const TextStyle(fontSize: 9.5, color: AppColors.inkMuted),
              );
            },
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 22,
            // Dibagi atas jarak antar-titik terjauh, bukan jumlah baris, supaya
            // tick terakhir jatuh tepat pada bacaan terbaru - jam yang paling
            // ingin dilihat orang.
            interval: ((rows.length - 1) / 3).clamp(1, double.infinity),
            getTitlesWidget: (v, meta) {
              final i = v.round();
              if (i < 0 || i >= rows.length) return const SizedBox.shrink();
              // Label paling kanan berpusat tepat di tepi kanvas, jadi separuhnya
              // terpotong ('07:31:14' tinggal '07:31:14...'). fitInside menggeser
              // label tepi ke dalam alih-alih memotongnya.
              return SideTitleWidget(
                axisSide: meta.axisSide,
                space: 4,
                fitInside:
                    SideTitleFitInsideData.fromTitleMeta(meta, distanceFromEdge: 0),
                child: Text(
                  DateFormat('HH:mm:ss').format(rows[i].recordedAt),
                  style: const TextStyle(fontSize: 9, color: AppColors.inkMuted),
                ),
              );
            },
          ),
        ),
      ),
      lineTouchData: LineTouchData(
        touchTooltipData: LineTouchTooltipData(
          getTooltipItems: (touched) => touched
              .map((t) => LineTooltipItem(
                    '${_fmt(t.y)} ${spec.unit}\n'
                    '${DateFormat('HH:mm:ss').format(rows[t.x.round()].recordedAt)}',
                    const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w600),
                  ))
              .toList(),
        ),
      ),
      lineBarsData: [
        LineChartBarData(
          spots: spots,
          isCurved: true,
          curveSmoothness: 0.2,
          color: AppColors.primary,
          barWidth: 2,
          // A lone reading between nulls has no line to draw, so show its point
          // — otherwise a probe that reads once every few minutes renders
          // nothing at all.
          dotData: FlDotData(
            show: true,
            checkToShowDot: (spot, _) {
              final i = spot.x.round();
              bool has(int k) =>
                  k >= 0 && k < spots.length && !spots[k].isNull();
              return !has(i - 1) && !has(i + 1);
            },
            getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
              radius: 2.5,
              color: AppColors.primary,
              strokeWidth: 0,
            ),
          ),
          belowBarData: BarAreaData(show: false),
        ),
      ],
    );
  }
}

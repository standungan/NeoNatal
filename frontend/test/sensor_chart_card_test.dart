// Widget tests for the IoT sensor chart (updates03 P3).
//
// The chart only mounts behind a login, so these drive it directly with the
// exact payload shape the API returns — including the case that matters most:
// null metrics, which must break the line rather than be skipped or plotted
// as zero.

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:neonatal_care/core/models/sensor_reading_model.dart';
import 'package:neonatal_care/features/incubator/providers/sensor_readings_provider.dart';
import 'package:neonatal_care/features/incubator/widgets/sensor_chart_card.dart';

const _incId = 'bbbbbbbb-0002-0002-0002-000000000001';

/// A reading as the API actually serves it: Decimal fields are JSON numbers
/// (a field_serializer makes them so), heart_rate is a plain int, and any of
/// them may be null.
Map<String, dynamic> _row({
  required int i,
  num? suhuBayi,
  num? suhuInkubator,
  num? kelembapan,
  int? heartRate,
  num? spo2,
}) =>
    {
      'reading_id': 'r$i',
      'incubator_id': _incId,
      'baby_id': 'cccccccc-0003-0003-0003-000000000001',
      'recorded_at':
          DateTime.utc(2026, 9, 1, 10, 0, i % 60).toIso8601String(),
      'suhu_bayi': suhuBayi,
      'suhu_inkubator': suhuInkubator,
      'kelembapan_inkubator': kelembapan,
      'heart_rate': heartRate,
      'spo2': spo2,
      'respiratory_rate': null,
      'source': 'sensor',
    };

List<ThresholdMetric> _thresholds() => [
      const ThresholdMetric(
          key: 'suhu_bayi', label: 'Suhu Bayi', unit: '°C', min: 36.0, max: 37.5),
      const ThresholdMetric(
          key: 'suhu_inkubator',
          label: 'Suhu Inkubator',
          unit: '°C',
          min: 34.0,
          max: 36.0),
      const ThresholdMetric(
          key: 'heart_rate', label: 'HR', unit: 'bpm', min: 100, max: 160),
    ];

Widget _harness(List<SensorReading> rows, {List<ThresholdMetric>? thresholds}) =>
    ProviderScope(
      overrides: [
        sensorReadingsProvider(_incId).overrideWith((ref) => Stream.value(rows)),
        incubatorThresholdsProvider(_incId)
            .overrideWith((ref) async => thresholds ?? _thresholds()),
      ],
      child: const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: SensorChartCard(incubatorId: _incId),
          ),
        ),
      ),
    );

void main() {
  test('parses the API payload, including nulls and numeric types', () {
    final r = SensorReading.fromJson(
        _row(i: 1, suhuBayi: 36.8, kelembapan: 55, heartRate: null, spo2: null));
    expect(r.suhuBayi, 36.8);
    expect(r.kelembapanInkubator, 55.0);
    expect(r.heartRate, isNull, reason: 'null must survive as null, not 0');
    expect(r.spo2, isNull);
    expect(r.metric('suhu_bayi'), 36.8);
    expect(r.metric('heart_rate'), isNull);
  });

  test('parses Decimal-as-string defensively', () {
    // Pydantic serialises Decimal as a STRING unless a field serializer says
    // otherwise. If that serializer is ever removed, the chart must not silently
    // receive unusable values.
    final r = SensorReading.fromJson({
      ..._row(i: 1),
      'suhu_bayi': '36.9',
      'kelembapan_inkubator': '52.00',
    });
    expect(r.suhuBayi, 36.9);
    expect(r.kelembapanInkubator, 52.0);
  });

  testWidgets('renders one panel per metric', (tester) async {
    final rows = List.generate(
      10,
      (i) => SensorReading.fromJson(_row(
        i: i,
        suhuBayi: 36.5 + i * 0.1,
        suhuInkubator: 34.2 + i * 0.1,
        kelembapan: 55,
        heartRate: 130 + i,
        spo2: 97,
      )),
    );

    await tester.pumpWidget(_harness(rows));
    await tester.pumpAndSettle();

    expect(find.text('Tren Sensor'), findsOneWidget);
    expect(find.text('Suhu Bayi (°C)'), findsOneWidget);
    expect(find.text('Suhu Inkubator (°C)'), findsOneWidget);
    expect(find.text('Detak Jantung (bpm)'), findsOneWidget);
    expect(find.text('SpO₂ (%)'), findsOneWidget);
    expect(find.text('Kelembapan (%)'), findsOneWidget);
    expect(find.byType(LineChart), findsNWidgets(5));
  });

  testWidgets('a null metric breaks the line instead of being skipped',
      (tester) async {
    // Every metric present so all five panels draw a chart — a panel with no
    // data renders a message instead, which would shift the indices below.
    // Probe off in the middle: readings 3 and 4 have no HR.
    final rows = List.generate(8, (i) {
      final off = i == 3 || i == 4;
      return SensorReading.fromJson(_row(
        i: i,
        suhuBayi: 36.5,
        suhuInkubator: 34.5,
        kelembapan: 55,
        spo2: 97,
        heartRate: off ? null : 130 + i,
      ));
    });

    await tester.pumpWidget(_harness(rows));
    await tester.pumpAndSettle();

    final charts = tester.widgetList<LineChart>(find.byType(LineChart)).toList();
    // Panels are in declaration order; Detak Jantung is the third.
    final hr = charts[2].data.lineBarsData.single.spots;

    expect(hr.length, rows.length,
        reason: 'one entry per reading — gaps are positional, not removed');
    expect(hr[3].isNull(), isTrue, reason: 'missing reading must be a nullSpot');
    expect(hr[4].isNull(), isTrue);
    expect(hr[2].isNull(), isFalse);
    expect(hr.where((s) => !s.isNull()).any((s) => s.y == 0), isFalse,
        reason: 'a gap must never be plotted as zero');
  });

  testWidgets('the two temperature panels share one y-range', (tester) async {
    // Skin temp barely moves; air temp swings. On independent scales the skin
    // wobble would look as large as the air swing.
    final rows = List.generate(
      10,
      (i) => SensorReading.fromJson(_row(
        i: i,
        suhuBayi: 36.5 + (i.isEven ? 0.1 : 0.0),
        suhuInkubator: 30.0 + i.toDouble(),
      )),
    );

    await tester.pumpWidget(_harness(rows));
    await tester.pumpAndSettle();

    final charts = tester.widgetList<LineChart>(find.byType(LineChart)).toList();
    final skin = charts[0].data;
    final air = charts[1].data;

    expect(skin.minY, air.minY);
    expect(skin.maxY, air.maxY);
  });

  testWidgets('a panel with no data says so rather than drawing an empty grid',
      (tester) async {
    final rows = List.generate(
      5,
      (i) => SensorReading.fromJson(_row(i: i, suhuBayi: 36.5)),
    );

    await tester.pumpWidget(_harness(rows));
    await tester.pumpAndSettle();

    expect(find.textContaining('Sensor belum mengirim nilai untuk Detak Jantung'),
        findsOneWidget);
    expect(find.textContaining('Sensor belum mengirim nilai untuk SpO₂'),
        findsOneWidget);
    // Suhu Bayi has data, so it draws.
    expect(find.byType(LineChart), findsWidgets);
  });

  testWidgets('empty response shows guidance, not a broken chart',
      (tester) async {
    await tester.pumpWidget(_harness(const []));
    await tester.pumpAndSettle();

    expect(find.textContaining('Belum ada data sensor'), findsOneWidget);
    expect(find.byType(LineChart), findsNothing);
  });
}

import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/sensor_reading_model.dart';

/// How many samples the chart keeps on screen (~6 min at the firmware's 3 s cadence).
const int kReadingWindow = 120;

/// Live sensor readings for one incubator, oldest first.
///
/// Polling rather than the SSE stream the web dashboard uses: `dio`'s streaming
/// response does not work on Flutter **web**, which is how this app is run today,
/// so a stream here would work on device and silently fail in Chrome. At the
/// firmware's 3 s cadence, refetching on the same interval is visually identical.
/// The SSE endpoint exists (`ApiEndpoints.incubatorStream`) for when this is
/// native-only.
final sensorReadingsProvider = StreamProvider.autoDispose
    .family<List<SensorReading>, String>((ref, incubatorId) async* {
  Future<List<SensorReading>> fetch() async {
    final res = await ApiClient().dio.get(
          ApiEndpoints.incubatorReadings(incubatorId),
          queryParameters: {'limit': kReadingWindow},
        );
    return (res.data as List)
        .map((e) => SensorReading.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  yield await fetch();

  // Ticks are skipped rather than queued if a request is slow, so a stalled
  // network cannot build a backlog of requests that all land at once.
  var inFlight = false;
  await for (final _ in Stream.periodic(const Duration(seconds: 3))) {
    if (inFlight) continue;
    inFlight = true;
    try {
      yield await fetch();
    } catch (_) {
      // A dropped poll is not an error worth tearing the chart down for — the
      // next tick recovers, and the previous data stays on screen meanwhile.
    } finally {
      inFlight = false;
    }
  }
});

/// Per-incubator alert bounds. Fetched once; admins change these rarely.
final incubatorThresholdsProvider = FutureProvider.autoDispose
    .family<List<ThresholdMetric>, String>((ref, incubatorId) async {
  final res =
      await ApiClient().dio.get(ApiEndpoints.incubatorThresholds(incubatorId));
  final metrics = (res.data['metrics'] as List?) ?? const [];
  return metrics
      .map((e) => ThresholdMetric.fromJson(e as Map<String, dynamic>))
      .toList();
});

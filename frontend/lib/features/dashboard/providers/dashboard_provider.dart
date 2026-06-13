import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/dashboard_model.dart';

final dashboardProvider =
    FutureProvider.autoDispose<DashboardData>((ref) async {
  final res = await ApiClient().dio.get(ApiEndpoints.dashboard);
  return DashboardData.fromJson(res.data);
});

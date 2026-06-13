import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

final _auditProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) async {
    final res = await ApiClient()
        .dio
        .get(ApiEndpoints.auditLogs, queryParameters: {'limit': 200});
    return (res.data as List).cast<Map<String, dynamic>>();
  },
);

class AuditLogScreen extends ConsumerWidget {
  const AuditLogScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final logsAsync = ref.watch(_auditProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Audit Log'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(_auditProvider),
          ),
        ],
      ),
      body: logsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Gagal memuat: $e')),
        data: (logs) {
          if (logs.isEmpty) {
            return const Center(
              child: Text('Belum ada aktivitas tercatat.',
                  style: TextStyle(color: AppColors.inkMuted)),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(_auditProvider),
            child: ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: logs.length,
              separatorBuilder: (_, __) => const SizedBox(height: 6),
              itemBuilder: (_, i) => _LogTile(log: logs[i]),
            ),
          );
        },
      ),
    );
  }
}

class _LogTile extends StatelessWidget {
  final Map<String, dynamic> log;
  const _LogTile({required this.log});

  @override
  Widget build(BuildContext context) {
    final action = log['action'] as String? ?? '-';
    final color = _actionColor(action);
    final time = log['created_at'] != null
        ? DateFormat('dd/MM/yyyy HH:mm:ss')
            .format(DateTime.parse(log['created_at']).toLocal())
        : '-';

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              margin: const EdgeInsets.only(top: 2),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(action,
                  style: TextStyle(
                      fontSize: 11,
                      color: color,
                      fontWeight: FontWeight.w700)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(log['user_name'] ?? 'Sistem',
                      style: const TextStyle(
                          fontWeight: FontWeight.w600, fontSize: 13)),
                  if (log['table_name'] != null)
                    Text(
                      'Tabel: ${log['table_name']}'
                      '${log['ip_address'] != null ? '  •  IP: ${log['ip_address']}' : ''}',
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.inkMuted),
                    ),
                  const SizedBox(height: 2),
                  Text(time,
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.inkMuted)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _actionColor(String action) {
    final a = action.toLowerCase();
    if (a.contains('delete') || a.contains('deactivate')) {
      return AppColors.abnormal;
    }
    if (a.contains('create')) return AppColors.normal;
    if (a.contains('update') || a.contains('reset')) return AppColors.warning;
    return AppColors.primary;
  }
}

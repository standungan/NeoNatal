import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/baby_model.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';
import 'package:neonatal_care/core/widgets/status_badge.dart';

// ── Providers (must live at top level, not inside build) ──────────────────────

final _incubatorDetailProvider =
    FutureProvider.autoDispose.family<Map<String, dynamic>, String>(
  (ref, incubatorId) async {
    final res = await ApiClient().dio.get(ApiEndpoints.incubator(incubatorId));
    return res.data as Map<String, dynamic>;
  },
);

final _babyDetailProvider =
    FutureProvider.autoDispose.family<BabyDetail, String>(
  (ref, babyId) async {
    final res = await ApiClient().dio.get(ApiEndpoints.baby(babyId));
    return BabyDetail.fromJson(res.data);
  },
);

// ── Screen ────────────────────────────────────────────────────────────────────

class IncubatorDetailScreen extends ConsumerWidget {
  final String incubatorId;
  const IncubatorDetailScreen({super.key, required this.incubatorId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dataAsync = ref.watch(_incubatorDetailProvider(incubatorId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Detail Inkubator'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(_incubatorDetailProvider(incubatorId)),
          ),
        ],
      ),
      body: dataAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Error: $e'),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () =>
                    ref.invalidate(_incubatorDetailProvider(incubatorId)),
                child: const Text('Coba Lagi'),
              ),
            ],
          ),
        ),
        data: (inc) {
          final baby = inc['current_baby'] as Map<String, dynamic>?;
          final babyId = baby?['baby_id'] as String?;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _IncubatorInfoCard(inc: inc),
                const SizedBox(height: 12),
                if (babyId != null)
                  _BabyInfoCard(babyId: babyId)
                else
                  _EmptyBabyCard(incubatorNo: inc['incubator_no'] as String),
                const SizedBox(height: 12),
                if (babyId != null) _ActionMenu(babyId: babyId),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ── Sub-widgets ───────────────────────────────────────────────────────────────

class _IncubatorInfoCard extends StatelessWidget {
  final Map<String, dynamic> inc;
  const _IncubatorInfoCard({required this.inc});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha:0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(
                child: Text(
                  inc['incubator_no'] as String,
                  style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary),
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Inkubator ${inc['incubator_no']}',
                    style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: AppColors.ink),
                  ),
                  if (inc['location'] != null)
                    Text(inc['location'] as String,
                        style: const TextStyle(color: AppColors.inkMuted)),
                ],
              ),
            ),
            StatusBadge(inc['status'] as String),
          ],
        ),
      ),
    );
  }
}

class _BabyInfoCard extends ConsumerWidget {
  final String babyId;
  const _BabyInfoCard({required this.babyId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final babyAsync = ref.watch(_babyDetailProvider(babyId));

    return babyAsync.when(
      loading: () => const Card(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Center(child: CircularProgressIndicator()),
        ),
      ),
      error: (e, _) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text('Error memuat data bayi: $e'),
        ),
      ),
      data: (baby) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.child_care, color: AppColors.primary),
                  const SizedBox(width: 8),
                  Text(
                    'Informasi Bayi',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const Divider(height: 16),
              _kv('Nama', baby.babyName),
              _kv('Jenis Kelamin',
                  baby.gender == 'laki_laki' ? 'Laki-laki' : 'Perempuan'),
              _kv('Tanggal Lahir',
                  DateFormat('dd MMM yyyy').format(baby.birthDate)),
              _kv('Usia', '${baby.ageInDays} hari'),
              _kv('Berat Lahir',
                  baby.birthWeight != null ? '${baby.birthWeight} gram' : '-'),
              if (baby.currentAssignment != null) ...[
                _kv('Inkubator',
                    'No. ${baby.currentAssignment!.incubatorNo}'
                    '${baby.currentAssignment!.location != null ? ' — ${baby.currentAssignment!.location}' : ''}'),
                _kv(
                  'Tanggal Masuk',
                  DateFormat('dd MMM yyyy HH:mm')
                      .format(baby.currentAssignment!.assignedAt),
                ),
                if (baby.currentAssignment!.assignedByName != null)
                  _kv('Perawat', baby.currentAssignment!.assignedByName!),
              ],
              if (baby.parent != null) ...[
                const Divider(height: 16),
                _kv('Nama Ibu', baby.parent!.motherName ?? '-'),
                _kv('Nama Ayah', baby.parent!.fatherName ?? '-'),
                _kv('Telepon', baby.parent!.motherPhone ?? '-'),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _kv(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 120,
              child: Text(label,
                  style: const TextStyle(
                      color: AppColors.inkMuted, fontSize: 13)),
            ),
            Expanded(
              child: Text(value,
                  style: const TextStyle(fontWeight: FontWeight.w500)),
            ),
          ],
        ),
      );
}

class _EmptyBabyCard extends StatelessWidget {
  final String incubatorNo;
  const _EmptyBabyCard({required this.incubatorNo});

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              const Icon(Icons.bed_outlined, size: 40, color: AppColors.kosong),
              const SizedBox(height: 8),
              Text('Inkubator $incubatorNo kosong',
                  style: const TextStyle(
                      color: AppColors.inkMuted, fontWeight: FontWeight.w600)),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                icon: const Icon(Icons.add),
                label: const Text('Register Bayi Baru'),
                onPressed: () => context.push('/baby/register'),
              ),
            ],
          ),
        ),
      );
}

class _ActionMenu extends StatelessWidget {
  final String babyId;
  const _ActionMenu({required this.babyId});

  @override
  Widget build(BuildContext context) {
    const actions = [
      ('Monitoring',        Icons.monitor_heart,  AppColors.primary),
      ('Keterlibatan OT',   Icons.people,          AppColors.normal),
      ('Lihat Laporan',     Icons.bar_chart,       Color(0xFF8B5CF6)),
    ];

    final routes = [
      '/baby/$babyId/monitoring',
      '/baby/$babyId/involvement',
      '/baby/$babyId/report',
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Menu Aksi',
                style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                    color: AppColors.ink)),
            const SizedBox(height: 14),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: List.generate(actions.length, (i) {
                final (label, icon, color) = actions[i];
                return InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => context.push(routes[i]),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 6),
                    child: Column(
                      children: [
                        Container(
                          width: 54,
                          height: 54,
                          decoration: BoxDecoration(
                            color: color.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(15),
                          ),
                          child: Icon(icon, color: color, size: 26),
                        ),
                        const SizedBox(height: 7),
                        Text(label,
                            style: const TextStyle(
                                fontSize: 11.5,
                                fontWeight: FontWeight.w600,
                                color: AppColors.ink),
                            textAlign: TextAlign.center),
                      ],
                    ),
                  ),
                );
              }),
            ),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/dashboard_model.dart';
import 'package:neonatal_care/core/providers/auth_provider.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';
import 'package:neonatal_care/core/widgets/stat_card.dart';
import 'package:neonatal_care/core/widgets/status_badge.dart';
import 'package:neonatal_care/features/dashboard/providers/dashboard_provider.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final dashAsync = ref.watch(dashboardProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Selamat datang,',
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: AppColors.inkMuted)),
            Text(auth.token?.fullName ?? '',
                style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    color: AppColors.ink)),
          ],
        ),
        actions: [
          if (auth.role == 'admin')
            PopupMenuButton<String>(
              icon: const Icon(Icons.admin_panel_settings),
              tooltip: 'Menu Admin',
              onSelected: (v) => context.push(v),
              itemBuilder: (_) => const [
                PopupMenuItem(
                  value: '/admin/users',
                  child: ListTile(
                    leading: Icon(Icons.people),
                    title: Text('Manajemen Pengguna'),
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
                PopupMenuItem(
                  value: '/admin/audit-logs',
                  child: ListTile(
                    leading: Icon(Icons.history),
                    title: Text('Audit Log'),
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ],
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(dashboardProvider),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
      floatingActionButton: auth.role == 'admin'
          ? FloatingActionButton.extended(
              onPressed: () => showDialog(
                context: context,
                builder: (_) => _AddIncubatorDialog(
                  onSuccess: () => ref.invalidate(dashboardProvider),
                ),
              ),
              icon: const Icon(Icons.add),
              label: const Text('Tambah Inkubator'),
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            )
          : null,
      body: dashAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.wifi_off, size: 48, color: AppColors.kosong),
              const SizedBox(height: 12),
              Text('Gagal memuat data: $e'),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => ref.invalidate(dashboardProvider),
                child: const Text('Coba Lagi'),
              ),
            ],
          ),
        ),
        data: (data) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(dashboardProvider),
          child: CustomScrollView(
            slivers: [
              SliverToBoxAdapter(child: _StatsRow(stats: data.stats)),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
                sliver: SliverToBoxAdapter(
                  child: Row(
                    children: [
                      const Text(
                        'Daftar Inkubator',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                          color: AppColors.ink,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.10),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          '${data.incubators.length}',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: AppColors.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                sliver: SliverList.builder(
                  itemCount: data.incubators.length,
                  itemBuilder: (_, i) =>
                      _IncubatorCard(item: data.incubators[i]),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 80)),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  final DashboardStats stats;
  const _StatsRow({required this.stats});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Row(
        children: [
          Expanded(child: StatCard(label: 'Total',   count: stats.total,   color: AppColors.primary, icon: Icons.devices_outlined)),
          const SizedBox(width: 10),
          Expanded(child: StatCard(label: 'Terisi',  count: stats.terisi,  color: AppColors.accent,  icon: Icons.baby_changing_station)),
          const SizedBox(width: 10),
          Expanded(child: StatCard(label: 'Kosong',  count: stats.kosong,  color: AppColors.kosong,  icon: Icons.check_circle_outline)),
          const SizedBox(width: 10),
          Expanded(child: StatCard(label: 'Warning', count: stats.warning, color: AppColors.warning, icon: Icons.warning_amber_rounded)),
        ],
      ),
    );
  }
}

class _IncubatorCard extends ConsumerWidget {
  final IncubatorDashboardItem item;
  const _IncubatorCard({required this.item});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final baby = item.currentBaby;
    final vitals = item.latestVitals;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: () => context.push('/incubator/${item.incubatorId}'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Center(
                      child: Text(
                        item.incubatorNo,
                        style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                            color: AppColors.primary),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          baby?.babyName ?? 'Belum ada pasien',
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14.5,
                            color: baby == null
                                ? AppColors.inkMuted
                                : AppColors.ink,
                          ),
                        ),
                        if (item.location != null)
                          Text(item.location!,
                              style: const TextStyle(
                                  fontSize: 12, color: AppColors.inkMuted)),
                      ],
                    ),
                  ),
                  StatusBadge(item.status),
                ],
              ),
              if (vitals != null) ...[
                const Divider(height: 16),
                Row(
                  children: [
                    _VitalChip(
                        label: 'Suhu',
                        value: '${vitals.suhuBayi?.toStringAsFixed(1) ?? '-'}°C',
                        isWarning: vitals.vitalStatus == 'warning'),
                    const SizedBox(width: 8),
                    _VitalChip(
                        label: 'HR',
                        value: '${vitals.heartRate ?? '-'} bpm',
                        isWarning: vitals.vitalStatus == 'warning'),
                    const SizedBox(width: 8),
                    _VitalChip(
                        label: 'SpO2',
                        value: '${vitals.spo2?.toStringAsFixed(0) ?? '-'}%',
                        isWarning: vitals.vitalStatus == 'warning'),
                  ],
                ),
              ] else if (baby == null) ...[
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  icon: const Icon(Icons.add, size: 16),
                  label: const Text('Register Bayi'),
                  onPressed: () => context.push('/baby/register'),
                  style: OutlinedButton.styleFrom(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    textStyle: const TextStyle(fontSize: 12),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _VitalChip extends StatelessWidget {
  final String label;
  final String value;
  final bool isWarning;
  const _VitalChip(
      {required this.label, required this.value, required this.isWarning});

  @override
  Widget build(BuildContext context) {
    final color = isWarning ? AppColors.warning : AppColors.ink;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: (isWarning ? AppColors.warning : AppColors.kosong)
            .withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(9),
      ),
      child: Column(
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 10, color: AppColors.inkMuted)),
          Text(value,
              style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: color)),
        ],
      ),
    );
  }
}

// ── Add Incubator Dialog (admin only) ─────────────────────────────────────────

class _AddIncubatorDialog extends StatefulWidget {
  final VoidCallback onSuccess;
  const _AddIncubatorDialog({required this.onSuccess});

  @override
  State<_AddIncubatorDialog> createState() => _AddIncubatorDialogState();
}

class _AddIncubatorDialogState extends State<_AddIncubatorDialog> {
  final _formKey    = GlobalKey<FormState>();
  final _noCtrl     = TextEditingController();
  final _locationCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _noCtrl.dispose();
    _locationCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });
    try {
      await ApiClient().dio.post(ApiEndpoints.incubators, data: {
        'incubator_no': _noCtrl.text.trim(),
        if (_locationCtrl.text.trim().isNotEmpty)
          'location': _locationCtrl.text.trim(),
      });
      if (mounted) {
        Navigator.of(context).pop();
        widget.onSuccess();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Inkubator berhasil ditambahkan'),
            backgroundColor: AppColors.normal,
          ),
        );
      }
    } catch (e) {
      setState(() { _loading = false; _error = 'Gagal menyimpan: $e'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Tambah Inkubator Baru'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _noCtrl,
              decoration: const InputDecoration(labelText: 'Nomor Inkubator *'),
              validator: (v) =>
                  v == null || v.trim().isEmpty ? 'Wajib diisi' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _locationCtrl,
              decoration: const InputDecoration(labelText: 'Lokasi (opsional)'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!,
                  style: const TextStyle(color: AppColors.abnormal, fontSize: 13)),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _loading ? null : () => Navigator.of(context).pop(),
          child: const Text('Batal'),
        ),
        ElevatedButton(
          onPressed: _loading ? null : _submit,
          style: ElevatedButton.styleFrom(minimumSize: const Size(80, 40)),
          child: _loading
              ? const SizedBox(
                  height: 16, width: 16,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white))
              : const Text('Simpan'),
        ),
      ],
    );
  }
}

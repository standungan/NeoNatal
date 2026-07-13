import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/aksi_model.dart';
import 'package:neonatal_care/core/models/scoring.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';
import 'package:neonatal_care/core/widgets/score_chips.dart';

/// Menu Aksi — Pilar 8 "Kolaborasi Interprofesional" (6 items, 0–3).
class AksiScreen extends ConsumerStatefulWidget {
  final String babyId;
  const AksiScreen({super.key, required this.babyId});

  @override
  ConsumerState<AksiScreen> createState() => _AksiScreenState();
}

class _AksiScreenState extends ConsumerState<AksiScreen> {
  final _formKey = GlobalKey<FormState>();
  DateTime _obsTime = DateTime.now();

  final Map<String, int> _scores = {};
  final _catatanCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _catatanCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ApiClient().dio.post(
        ApiEndpoints.aksi(widget.babyId),
        data: {
          'observation_time': _obsTime.toIso8601String(),
          'scores': _scores,
          'catatan':
              _catatanCtrl.text.trim().isEmpty ? null : _catatanCtrl.text.trim(),
        },
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Kolaborasi interprofesional berhasil disimpan'),
          backgroundColor: AppColors.normal,
        ));
        context.pop();
      }
    } catch (e) {
      setState(() => _error = 'Gagal menyimpan: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final total = _scores.values.fold<int>(0, (s, v) => s + v);
    final pct = percentageFor(total, kAksiMaxTotal);
    final category = categoryFor(pct);
    final scoreColor = categoryColor(category);
    final alarms = kAksiItems
        .where((it) => _scores[it[0]] != null && _scores[it[0]]! <= 1)
        .toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Kolaborasi Interprofesional')),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const _SectionTitle('Waktu Observasi'),
              GestureDetector(
                onTap: () async {
                  final d = await showDatePicker(
                    context: context,
                    initialDate: _obsTime,
                    firstDate: DateTime(2020),
                    lastDate: DateTime.now(),
                  );
                  if (d != null && mounted) setState(() => _obsTime = d);
                },
                child: InputDecorator(
                  decoration: const InputDecoration(
                      suffixIcon: Icon(Icons.calendar_today)),
                  child: Text(DateFormat('dd/MM/yyyy').format(_obsTime)),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Menu Aksi — Kolaborasi Interprofesional. Nilai tiap item 0–3 '
                '(0 = penyimpangan berat · 1 = sedang · 2 = ringan · 3 = sesuai standar).',
                style: TextStyle(fontSize: 11.5, color: AppColors.inkMuted),
              ),
              const SizedBox(height: 18),

              // ── 6 Pillar-8 items ────────────────────────────────────────
              for (var i = 0; i < kAksiItems.length; i++)
                _ItemTile(
                  index: i + 1,
                  title: kAksiItems[i][1],
                  value: _scores[kAksiItems[i][0]],
                  onChanged: (v) =>
                      setState(() => _scores[kAksiItems[i][0]] = v),
                ),
              const SizedBox(height: 8),

              // live score preview
              const _SectionTitle('Ringkasan Skor (Otomatis)'),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: scoreColor.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: scoreColor.withValues(alpha: 0.2)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          '${pct.toStringAsFixed(1)}%',
                          style: TextStyle(
                              fontSize: 38,
                              fontWeight: FontWeight.w800,
                              color: scoreColor),
                        ),
                        const SizedBox(width: 16),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 4),
                          decoration: BoxDecoration(
                            color: scoreColor,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(category,
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text('$total / $kAksiMaxTotal poin',
                        style: const TextStyle(
                            fontSize: 12, color: AppColors.inkMuted)),
                    if (alarms.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Text('⚠ ${alarms.length} item perlu perhatian (skor 0–1)',
                          style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                              color: AppColors.abnormal)),
                      for (final a in alarms)
                        Text('• ${a[1]}',
                            style: const TextStyle(
                                fontSize: 11.5, color: AppColors.ink)),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 20),

              const _SectionTitle('Catatan (Opsional)'),
              TextFormField(
                controller: _catatanCtrl,
                maxLines: 3,
                decoration: const InputDecoration(
                    hintText: 'Catatan kolaborasi & handover...'),
              ),

              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: AppColors.abnormal)),
              ],
              const SizedBox(height: 24),

              ElevatedButton(
                onPressed: (_loading || _scores.isEmpty) ? null : _submit,
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Text('Simpan Aksi'),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}

/// One instrument item: number + text + 0–3 chip selector.
class _ItemTile extends StatelessWidget {
  final int index;
  final String title;
  final int? value;
  final ValueChanged<int> onChanged;

  const _ItemTile({
    required this.index,
    required this.title,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 11,
                backgroundColor: AppColors.primary,
                child: Text('$index',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w700)),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(title,
                    style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 13.5,
                        color: AppColors.ink)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ScoreChips(value: value, min: 0, max: 3, onChanged: onChanged),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          children: [
            Container(
              width: 4,
              height: 16,
              decoration: BoxDecoration(
                color: AppColors.primary,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
            const SizedBox(width: 8),
            Text(text,
                style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14.5,
                    color: AppColors.ink)),
          ],
        ),
      );
}

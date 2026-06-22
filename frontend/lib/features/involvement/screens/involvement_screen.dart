import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/involvement_model.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';
import 'package:neonatal_care/core/widgets/score_chips.dart';

class InvolvementScreen extends ConsumerStatefulWidget {
  final String babyId;
  const InvolvementScreen({super.key, required this.babyId});

  @override
  ConsumerState<InvolvementScreen> createState() => _InvolvementScreenState();
}

class _InvolvementScreenState extends ConsumerState<InvolvementScreen> {
  final _formKey = GlobalKey<FormState>();
  DateTime _obsTime = DateTime.now();

  // Pillar 8 sub-domain ratings (0–4)
  int? _presence;
  int? _physical;
  int? _feeding;
  int? _care;
  int? _knowledge;
  int? _communication;
  int? _emotional;
  int? _discharge;

  // Optional supplementary durations
  final _menyusuiCtrl  = TextEditingController();
  final _interaksiCtrl = TextEditingController();
  final _catatanCtrl   = TextEditingController();
  String? _kondisiBayi;
  bool _loading = false;
  String? _error;

  List<int?> get _domains =>
      [_presence, _physical, _feeding, _care, _knowledge, _communication, _emotional, _discharge];

  int get _liveScore => previewScore(_domains);

  @override
  void dispose() {
    _menyusuiCtrl.dispose();
    _interaksiCtrl.dispose();
    _catatanCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });
    try {
      await ApiClient().dio.post(
        ApiEndpoints.involvement(widget.babyId),
        data: {
          'observation_time': _obsTime.toIso8601String(),
          'durasi_menyusui': int.tryParse(_menyusuiCtrl.text),
          'durasi_interaksi': int.tryParse(_interaksiCtrl.text),
          'presence_score': _presence,
          'physical_interaction_score': _physical,
          'feeding_participation_score': _feeding,
          'care_participation_score': _care,
          'knowledge_score': _knowledge,
          'communication_score': _communication,
          'emotional_readiness_score': _emotional,
          'discharge_readiness_score': _discharge,
          'catatan': _catatanCtrl.text.trim().isEmpty ? null : _catatanCtrl.text.trim(),
          'kondisi_bayi': _kondisiBayi,
        },
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Keterlibatan orang tua berhasil disimpan'),
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
    final score = _liveScore;
    final category = scoreCategory(score);
    final scoreColor = score >= 76
        ? AppColors.normal
        : score >= 51
            ? AppColors.primary
            : score >= 26
                ? AppColors.warning
                : AppColors.tidakTersedia;

    return Scaffold(
      appBar: AppBar(title: const Text('Keterlibatan Orang Tua')),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // date time
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
                  decoration: const InputDecoration(suffixIcon: Icon(Icons.calendar_today)),
                  child: Text(DateFormat('dd/MM/yyyy').format(_obsTime)),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Nilai tiap domain 0–4  (0 = tidak ada · 1 = minimal · 2 = kadang · 3 = sering · 4 = konsisten)',
                style: TextStyle(fontSize: 11.5, color: AppColors.inkMuted),
              ),
              const SizedBox(height: 18),

              // ── Pillar 8 domains ────────────────────────────────────────
              _DomainTile(
                index: 1,
                title: 'Kehadiran',
                subtitle: 'Frekuensi & durasi kunjungan',
                value: _presence,
                onChanged: (v) => setState(() => _presence = v),
                extra: TextFormField(
                  controller: _interaksiCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                      labelText: 'Durasi kunjungan (opsional)', suffixText: 'menit'),
                ),
              ),
              _DomainTile(
                index: 2,
                title: 'Interaksi Fisik',
                subtitle: 'Sentuhan lembut, menggendong, perawatan kanguru',
                value: _physical,
                onChanged: (v) => setState(() => _physical = v),
              ),
              _DomainTile(
                index: 3,
                title: 'Partisipasi Menyusui',
                subtitle: 'Menyusui langsung / pemberian ASI perah',
                value: _feeding,
                onChanged: (v) => setState(() => _feeding = v),
                extra: TextFormField(
                  controller: _menyusuiCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                      labelText: 'Durasi menyusui (opsional)', suffixText: 'menit'),
                ),
              ),
              _DomainTile(
                index: 4,
                title: 'Partisipasi Perawatan',
                subtitle: 'Ganti popok, kebersihan, menenangkan bayi',
                value: _care,
                onChanged: (v) => setState(() => _care = v),
              ),
              _DomainTile(
                index: 5,
                title: 'Pengetahuan',
                subtitle: 'Pemahaman kondisi & rencana perawatan bayi',
                value: _knowledge,
                onChanged: (v) => setState(() => _knowledge = v),
              ),
              _DomainTile(
                index: 6,
                title: 'Komunikasi',
                subtitle: 'Keterlibatan saat diskusi klinis',
                value: _communication,
                onChanged: (v) => setState(() => _communication = v),
              ),
              _DomainTile(
                index: 7,
                title: 'Kesiapan Emosional',
                subtitle: 'Tingkat kecemasan & kepercayaan diri',
                value: _emotional,
                onChanged: (v) => setState(() => _emotional = v),
              ),
              _DomainTile(
                index: 8,
                title: 'Kesiapan Pulang',
                subtitle: 'Kompetensi perawatan & kesadaran darurat',
                value: _discharge,
                onChanged: (v) => setState(() => _discharge = v),
              ),
              const SizedBox(height: 8),

              // live PEI preview
              const _SectionTitle('Parent Engagement Index (Otomatis)'),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: scoreColor.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: scoreColor.withValues(alpha: 0.2)),
                ),
                child: Row(
                  children: [
                    Text(
                      '$score',
                      style: TextStyle(
                          fontSize: 42,
                          fontWeight: FontWeight.w800,
                          color: scoreColor),
                    ),
                    const Text(' / 100',
                        style: TextStyle(fontSize: 20, color: AppColors.inkMuted)),
                    const SizedBox(width: 16),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      decoration: BoxDecoration(
                        color: scoreColor,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(category,
                          style: const TextStyle(
                              color: Colors.white, fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '0–25 Rendah  |  26–50 Sedang  |  51–75 Baik  |  76–100 Sangat Baik',
                style: TextStyle(fontSize: 11, color: AppColors.inkMuted),
              ),
              const SizedBox(height: 20),

              // kondisi bayi
              const _SectionTitle('Kondisi Bayi Saat Interaksi'),
              DropdownButtonFormField<String>(
                initialValue: _kondisiBayi,
                hint: const Text('Pilih kondisi bayi'),
                decoration: const InputDecoration(),
                items: const [
                  DropdownMenuItem(value: 'Tenang', child: Text('Tenang')),
                  DropdownMenuItem(value: 'Aktif',  child: Text('Aktif')),
                  DropdownMenuItem(value: 'Rewel',  child: Text('Rewel')),
                  DropdownMenuItem(value: 'Tidur',  child: Text('Tidur')),
                ],
                onChanged: (v) => setState(() => _kondisiBayi = v),
              ),
              const SizedBox(height: 20),

              // notes
              const _SectionTitle('Catatan (Opsional)'),
              TextFormField(
                controller: _catatanCtrl,
                maxLines: 3,
                decoration: const InputDecoration(
                    hintText: 'Catatan aktivitas dan interaksi orang tua...'),
              ),

              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: AppColors.abnormal)),
              ],
              const SizedBox(height: 24),

              ElevatedButton(
                onPressed: _loading ? null : _submit,
                child: _loading
                    ? const SizedBox(
                        height: 20, width: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Text('Simpan Keterlibatan'),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}

/// One Pillar-8 sub-domain: title + subtitle + 0–4 chip selector + optional field.
class _DomainTile extends StatelessWidget {
  final int index;
  final String title;
  final String subtitle;
  final int? value;
  final ValueChanged<int> onChanged;
  final Widget? extra;

  const _DomainTile({
    required this.index,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
    this.extra,
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
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                            color: AppColors.ink)),
                    Text(subtitle,
                        style: const TextStyle(
                            fontSize: 11.5, color: AppColors.inkMuted)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ScoreChips(value: value, min: 0, max: 4, onChanged: onChanged),
          if (extra != null) ...[
            const SizedBox(height: 12),
            extra!,
          ],
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

import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';
import 'package:neonatal_care/core/widgets/score_chips.dart';

class MonitoringScreen extends ConsumerStatefulWidget {
  final String babyId;
  const MonitoringScreen({super.key, required this.babyId});

  @override
  ConsumerState<MonitoringScreen> createState() => _MonitoringScreenState();
}

class _MonitoringScreenState extends ConsumerState<MonitoringScreen> {
  final _formKey = GlobalKey<FormState>();
  DateTime _obsTime = DateTime.now();

  final _suhuBayiCtrl   = TextEditingController();
  final _suhuIncCtrl    = TextEditingController();
  final _kelembapanCtrl = TextEditingController();
  final _hrCtrl         = TextEditingController();
  final _rrCtrl         = TextEditingController();
  final _spo2Ctrl       = TextEditingController();
  final _sleepDurCtrl   = TextEditingController();
  final _agitationCtrl  = TextEditingController();
  final _catatanCtrl    = TextEditingController();

  int? _expressionScore;
  int? _movementScore;
  int? _painScore;
  int? _sleepQuality;
  XFile? _photo;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [
      _suhuBayiCtrl, _suhuIncCtrl, _kelembapanCtrl, _hrCtrl, _rrCtrl, _spo2Ctrl,
      _sleepDurCtrl, _agitationCtrl, _catatanCtrl,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickPhoto() async {
    final img = await ImagePicker().pickImage(
        source: ImageSource.gallery, imageQuality: 80, maxWidth: 1200);
    if (img != null) setState(() => _photo = img);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });
    try {
      final res = await ApiClient().dio.post(
        ApiEndpoints.monitoring(widget.babyId),
        data: {
          'observation_time': _obsTime.toIso8601String(),
          'suhu_bayi': _suhuBayiCtrl.text.isNotEmpty ? double.parse(_suhuBayiCtrl.text) : null,
          'suhu_inkubator': _suhuIncCtrl.text.isNotEmpty ? double.parse(_suhuIncCtrl.text) : null,
          'kelembapan_inkubator': _kelembapanCtrl.text.isNotEmpty ? double.parse(_kelembapanCtrl.text) : null,
          'heart_rate': _hrCtrl.text.isNotEmpty ? int.parse(_hrCtrl.text) : null,
          'respiratory_rate': _rrCtrl.text.isNotEmpty ? int.parse(_rrCtrl.text) : null,
          'spo2': _spo2Ctrl.text.isNotEmpty ? double.parse(_spo2Ctrl.text) : null,
          'expression_score': _expressionScore,
          'movement_score': _movementScore,
          'pain_score': _painScore,
          'sleep_duration_min': _sleepDurCtrl.text.isNotEmpty ? int.parse(_sleepDurCtrl.text) : null,
          'sleep_quality': _sleepQuality,
          'agitation_episodes': _agitationCtrl.text.isNotEmpty ? int.parse(_agitationCtrl.text) : null,
          'catatan': _catatanCtrl.text.trim().isEmpty ? null : _catatanCtrl.text.trim(),
        },
      );

      // upload photo if selected
      if (_photo != null) {
        final monitoringId = res.data['monitoring_id'];
        final formData = FormData.fromMap({
          'file': await MultipartFile.fromFile(_photo!.path,
              filename: _photo!.name),
        });
        await ApiClient()
            .dio
            .post(ApiEndpoints.photoUpload(monitoringId), data: formData);
      }

      if (mounted) {
        final status = res.data['vital_status'];
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(status == 'warning'
              ? '⚠ Data monitoring disimpan — ada vital di luar batas normal'
              : 'Data monitoring berhasil disimpan'),
          backgroundColor:
              status == 'warning' ? AppColors.warning : AppColors.normal,
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
    return Scaffold(
      appBar: AppBar(title: const Text('Monitoring Bayi')),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // date time picker
              const _SectionTitle('Tanggal & Waktu Observasi'),
              GestureDetector(
                onTap: () async {
                  final d = await showDatePicker(
                    context: context,
                    initialDate: _obsTime,
                    firstDate: DateTime(2020),
                    lastDate: DateTime.now(),
                  );
                  if (d == null || !context.mounted) return;
                  final t = await showTimePicker(
                    context: context,
                    initialTime: TimeOfDay.fromDateTime(_obsTime),
                  );
                  if (t != null) {
                    setState(() => _obsTime =
                        DateTime(d.year, d.month, d.day, t.hour, t.minute));
                  }
                },
                child: InputDecorator(
                  decoration: const InputDecoration(
                      suffixIcon: Icon(Icons.calendar_today)),
                  child: Text(DateFormat('dd/MM/yyyy HH:mm').format(_obsTime)),
                ),
              ),
              const SizedBox(height: 20),

              const _SectionTitle('Tanda Vital'),
              Row(children: [
                Expanded(child: TextFormField(
                  controller: _suhuBayiCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Suhu Bayi (°C)'),
                )),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(
                  controller: _suhuIncCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Suhu Inkubator (°C)'),
                )),
              ]),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(child: TextFormField(
                  controller: _hrCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Heart Rate (bpm)'),
                )),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(
                  controller: _rrCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Respiratory Rate (/mnt)'),
                )),
              ]),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(child: TextFormField(
                  controller: _spo2Ctrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'SpO2 (%)'),
                )),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(
                  controller: _kelembapanCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Kelembapan Inkubator (%)'),
                )),
              ]),
              const SizedBox(height: 20),

              const _SectionTitle('Expression Score (1–5)'),
              ScoreChips(
                value: _expressionScore,
                onChanged: (v) => setState(() => _expressionScore = v),
              ),
              const SizedBox(height: 20),

              const _SectionTitle('Movement Score (1–5)'),
              ScoreChips(
                value: _movementScore,
                onChanged: (v) => setState(() => _movementScore = v),
              ),
              const SizedBox(height: 20),

              // ── Pillar 6: Pain & Stress ──────────────────────────────────
              const _SectionTitle('Skor Nyeri / NIPS (0–7)'),
              ScoreChips(
                value: _painScore,
                min: 0,
                max: 7,
                onChanged: (v) => setState(() => _painScore = v),
              ),
              const SizedBox(height: 6),
              const Text('0 = tidak nyeri  •  ≥ 4 = perlu perhatian',
                  style: TextStyle(fontSize: 11, color: AppColors.inkMuted)),
              const SizedBox(height: 20),

              // ── Pillar 5: Sleep & Comfort ────────────────────────────────
              const _SectionTitle('Tidur & Kenyamanan'),
              Row(children: [
                Expanded(child: TextFormField(
                  controller: _sleepDurCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                      labelText: 'Durasi Tidur', suffixText: 'menit'),
                )),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(
                  controller: _agitationCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Episode Gelisah'),
                )),
              ]),
              const SizedBox(height: 14),
              const Text('Kualitas Tidur (1–5)',
                  style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                      color: AppColors.inkMuted)),
              const SizedBox(height: 8),
              ScoreChips(
                value: _sleepQuality,
                onChanged: (v) => setState(() => _sleepQuality = v),
              ),
              const SizedBox(height: 20),

              const _SectionTitle('Catatan Observasi (Opsional)'),
              TextFormField(
                controller: _catatanCtrl,
                maxLines: 3,
                decoration: const InputDecoration(
                    hintText: 'Masukkan catatan observasi...',
                    alignLabelWithHint: true),
              ),
              const SizedBox(height: 20),

              const _SectionTitle('Foto (Opsional)'),
              GestureDetector(
                onTap: _pickPhoto,
                child: Container(
                  height: 130,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: _photo != null
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(14),
                          child: Image.file(File(_photo!.path), fit: BoxFit.cover),
                        )
                      : const Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.add_photo_alternate_outlined,
                                size: 34, color: AppColors.inkMuted),
                            SizedBox(height: 8),
                            Text('Klik untuk upload foto',
                                style: TextStyle(
                                    color: AppColors.inkMuted,
                                    fontWeight: FontWeight.w500)),
                          ],
                        ),
                ),
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
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Simpan Monitoring'),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
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

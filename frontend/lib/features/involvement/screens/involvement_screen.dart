import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/involvement_model.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

class InvolvementScreen extends ConsumerStatefulWidget {
  final String babyId;
  const InvolvementScreen({super.key, required this.babyId});

  @override
  ConsumerState<InvolvementScreen> createState() => _InvolvementScreenState();
}

class _InvolvementScreenState extends ConsumerState<InvolvementScreen> {
  final _formKey = GlobalKey<FormState>();
  DateTime _obsTime = DateTime.now();

  final _menyusuiCtrl  = TextEditingController();
  final _interaksiCtrl = TextEditingController();
  final _catatanCtrl   = TextEditingController();
  String? _kondisiBayi;
  bool _loading = false;
  String? _error;

  int get _liveScore => previewScore(
        int.tryParse(_menyusuiCtrl.text),
        int.tryParse(_interaksiCtrl.text),
      );

  @override
  void initState() {
    super.initState();
    _menyusuiCtrl.addListener(() => setState(() {}));
    _interaksiCtrl.addListener(() => setState(() {}));
  }

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
              const Text('Waktu Observasi',
                  style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14.5,
                      color: AppColors.ink)),
              const SizedBox(height: 8),
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
              const SizedBox(height: 20),

              // durations
              const Text('1. Durasi Aktivitas',
                  style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14.5,
                      color: AppColors.ink)),
              const SizedBox(height: 10),
              Row(children: [
                Expanded(child: TextFormField(
                  controller: _menyusuiCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Durasi Menyusui',
                    suffixText: 'menit',
                  ),
                )),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(
                  controller: _interaksiCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Durasi Interaksi',
                    suffixText: 'menit',
                  ),
                )),
              ]),
              const SizedBox(height: 16),

              // notes
              const Text('2. Catatan (Opsional)',
                  style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14.5,
                      color: AppColors.ink)),
              const SizedBox(height: 8),
              TextFormField(
                controller: _catatanCtrl,
                maxLines: 3,
                decoration: const InputDecoration(
                    hintText: 'Catatan aktivitas dan interaksi orang tua...'),
              ),
              const SizedBox(height: 20),

              // live score preview
              const Text('3. Skor Keterlibatan (Otomatis)',
                  style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14.5,
                      color: AppColors.ink)),
              const SizedBox(height: 10),
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
                        style:
                            TextStyle(fontSize: 20, color: AppColors.inkMuted)),
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
              ),
              const SizedBox(height: 8),
              const Text(
                '0–25 Rendah  |  26–50 Sedang  |  51–75 Baik  |  76–100 Sangat Baik',
                style: TextStyle(fontSize: 11, color: AppColors.inkMuted),
              ),
              const SizedBox(height: 20),

              // kondisi bayi
              const Text('4. Kondisi Bayi Saat Interaksi',
                  style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14.5,
                      color: AppColors.ink)),
              const SizedBox(height: 8),
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

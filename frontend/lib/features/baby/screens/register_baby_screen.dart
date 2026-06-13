// ignore_for_file: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/baby_model.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

final _availableIncubatorsProvider =
    FutureProvider.autoDispose<List<IncubatorOption>>((ref) async {
  final res = await ApiClient().dio.get(ApiEndpoints.incubatorsAvailable);
  return (res.data as List).map((e) => IncubatorOption.fromJson(e)).toList();
});

class RegisterBabyScreen extends ConsumerStatefulWidget {
  const RegisterBabyScreen({super.key});

  @override
  ConsumerState<RegisterBabyScreen> createState() => _RegisterBabyScreenState();
}

class _RegisterBabyScreenState extends ConsumerState<RegisterBabyScreen> {
  final _pageCtrl = PageController();
  int _step = 0;

  // step 1 — baby
  final _babyNameCtrl = TextEditingController();
  String _gender = 'laki_laki';
  DateTime? _birthDate;
  final _birthWeightCtrl = TextEditingController();
  final _birthLengthCtrl = TextEditingController();
  final _gestCtrl = TextEditingController();

  // step 2 — parent
  final _motherCtrl = TextEditingController();
  final _fatherCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _medHistCtrl = TextEditingController();

  // step 3 — incubator
  IncubatorOption? _selectedIncubator;

  bool _loading = false;
  String? _error;

  final _step1Key = GlobalKey<FormState>();
  final _step2Key = GlobalKey<FormState>();

  @override
  void dispose() {
    _pageCtrl.dispose();
    for (final c in [
      _babyNameCtrl, _birthWeightCtrl, _birthLengthCtrl, _gestCtrl,
      _motherCtrl, _fatherCtrl, _phoneCtrl, _medHistCtrl
    ]) { c.dispose(); }
    super.dispose();
  }

  void _next() {
    if (_step == 0 && !_step1Key.currentState!.validate()) return;
    if (_step == 1 && !_step2Key.currentState!.validate()) return;
    if (_step < 2) {
      setState(() => _step++);
      _pageCtrl.nextPage(
          duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
    } else {
      _submit();
    }
  }

  void _back() {
    if (_step > 0) {
      setState(() => _step--);
      _pageCtrl.previousPage(
          duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
    } else {
      context.pop();
    }
  }

  Future<void> _submit() async {
    if (_selectedIncubator == null) {
      setState(() => _error = 'Pilih inkubator terlebih dahulu');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      await ApiClient().dio.post(ApiEndpoints.babies, data: {
        'baby_name': _babyNameCtrl.text.trim(),
        'gender': _gender,
        'birth_date': DateFormat('yyyy-MM-dd').format(_birthDate!),
        'birth_weight': _birthWeightCtrl.text.isNotEmpty
            ? double.parse(_birthWeightCtrl.text)
            : null,
        'birth_length': _birthLengthCtrl.text.isNotEmpty
            ? double.parse(_birthLengthCtrl.text)
            : null,
        'gestational_age': _gestCtrl.text.isNotEmpty
            ? int.parse(_gestCtrl.text)
            : null,
        'parent': {
          'mother_name': _motherCtrl.text.trim(),
          'father_name': _fatherCtrl.text.trim(),
          'mother_phone': _phoneCtrl.text.trim(),
          'mother_medical_history': _medHistCtrl.text.trim(),
        },
        'incubator_id': _selectedIncubator!.incubatorId,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Bayi berhasil didaftarkan'),
              backgroundColor: AppColors.normal),
        );
        context.go('/dashboard');
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
      appBar: AppBar(
        title: const Text('Registrasi Bayi Baru'),
        leading: IconButton(
            icon: const Icon(Icons.arrow_back), onPressed: _back),
      ),
      body: Column(
        children: [
          _StepIndicator(current: _step),
          Expanded(
            child: PageView(
              controller: _pageCtrl,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                _Step1BabyInfo(
                    formKey: _step1Key,
                    nameCtrl: _babyNameCtrl,
                    gender: _gender,
                    birthDate: _birthDate,
                    weightCtrl: _birthWeightCtrl,
                    lengthCtrl: _birthLengthCtrl,
                    gestCtrl: _gestCtrl,
                    onGenderChanged: (v) => setState(() => _gender = v),
                    onDatePicked: (d) => setState(() => _birthDate = d)),
                _Step2ParentInfo(
                    formKey: _step2Key,
                    motherCtrl: _motherCtrl,
                    fatherCtrl: _fatherCtrl,
                    phoneCtrl: _phoneCtrl,
                    medHistCtrl: _medHistCtrl),
                _Step3Incubator(
                    selected: _selectedIncubator,
                    onSelected: (v) => setState(() => _selectedIncubator = v)),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(_error!,
                  style: const TextStyle(color: AppColors.abnormal)),
            ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: ElevatedButton(
              onPressed: _loading ? null : _next,
              child: _loading
                  ? const SizedBox(
                      height: 20, width: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : Text(_step < 2 ? 'Lanjut' : 'Simpan & Tempatkan Bayi'),
            ),
          ),
        ],
      ),
    );
  }
}

class _StepIndicator extends StatelessWidget {
  final int current;
  const _StepIndicator({required this.current});
  static const labels = ['Informasi Bayi', 'Informasi Orang Tua', 'Penempatan Inkubator'];

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: List.generate(labels.length, (i) {
          final active = i == current;
          final done = i < current;
          const inactive = Color(0xFFCBD5E1);
          final color = done || active ? AppColors.primary : inactive;
          return Expanded(
            child: Row(
              children: [
                if (i > 0) Expanded(child: Container(height: 2, color: done ? AppColors.primary : AppColors.border)),
                Column(
                  children: [
                    CircleAvatar(
                      radius: 15,
                      backgroundColor: color,
                      child: done
                          ? const Icon(Icons.check, color: Colors.white, size: 14)
                          : Text('${i + 1}',
                              style: TextStyle(
                                  color: active || done ? Colors.white : AppColors.inkMuted,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(height: 4),
                    Text(labels[i],
                        style: TextStyle(
                            fontSize: 10,
                            color: active ? AppColors.primary : AppColors.inkMuted,
                            fontWeight: active ? FontWeight.w700 : FontWeight.w500),
                        textAlign: TextAlign.center),
                  ],
                ),
              ],
            ),
          );
        }),
      ),
    );
  }
}

class _Step1BabyInfo extends StatelessWidget {
  final GlobalKey<FormState> formKey;
  final TextEditingController nameCtrl, weightCtrl, lengthCtrl, gestCtrl;
  final String gender;
  final DateTime? birthDate;
  final ValueChanged<String> onGenderChanged;
  final ValueChanged<DateTime> onDatePicked;

  const _Step1BabyInfo({
    required this.formKey, required this.nameCtrl, required this.gender,
    required this.birthDate, required this.weightCtrl, required this.lengthCtrl,
    required this.gestCtrl, required this.onGenderChanged, required this.onDatePicked,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('1. Informasi Bayi',
                style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                    color: AppColors.ink)),
            const SizedBox(height: 16),
            TextFormField(
              controller: nameCtrl,
              decoration: const InputDecoration(labelText: 'Nama Bayi *'),
              validator: (v) => v == null || v.isEmpty ? 'Wajib diisi' : null,
            ),
            const SizedBox(height: 12),
            const Text('Jenis Kelamin *',
                style: TextStyle(fontSize: 13, color: AppColors.inkMuted)),
            Row(
              children: [
                Expanded(
                  child: RadioListTile<String>(
                    value: 'laki_laki', groupValue: gender,
                    title: const Text('Laki-laki', style: TextStyle(fontSize: 13)),
                    onChanged: (v) => onGenderChanged(v!),
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
                Expanded(
                  child: RadioListTile<String>(
                    value: 'perempuan', groupValue: gender,
                    title: const Text('Perempuan', style: TextStyle(fontSize: 13)),
                    onChanged: (v) => onGenderChanged(v!),
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            GestureDetector(
              onTap: () async {
                final d = await showDatePicker(
                  context: context,
                  initialDate: DateTime.now(),
                  firstDate: DateTime(2020),
                  lastDate: DateTime.now(),
                );
                if (d != null) onDatePicked(d);
              },
              child: InputDecorator(
                decoration: const InputDecoration(
                  labelText: 'Tanggal Lahir *',
                  suffixIcon: Icon(Icons.calendar_today),
                ),
                child: Text(
                  birthDate != null
                      ? DateFormat('dd MMM yyyy').format(birthDate!)
                      : 'Pilih tanggal',
                  style: TextStyle(
                      color: birthDate == null ? AppColors.inkMuted : AppColors.ink),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(child: TextFormField(
                  controller: weightCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Berat Lahir (gram)'),
                )),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(
                  controller: lengthCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Panjang (cm)'),
                )),
              ],
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: gestCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Usia Gestasi (minggu)'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Step2ParentInfo extends StatelessWidget {
  final GlobalKey<FormState> formKey;
  final TextEditingController motherCtrl, fatherCtrl, phoneCtrl, medHistCtrl;

  const _Step2ParentInfo({
    required this.formKey, required this.motherCtrl, required this.fatherCtrl,
    required this.phoneCtrl, required this.medHistCtrl,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('2. Informasi Orang Tua',
                style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                    color: AppColors.ink)),
            const SizedBox(height: 16),
            TextFormField(controller: motherCtrl, decoration: const InputDecoration(labelText: 'Nama Ibu')),
            const SizedBox(height: 12),
            TextFormField(controller: fatherCtrl, decoration: const InputDecoration(labelText: 'Nama Ayah')),
            const SizedBox(height: 12),
            TextFormField(
              controller: phoneCtrl,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Nomor Telepon Ibu'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: medHistCtrl,
              maxLines: 3,
              decoration: const InputDecoration(
                  labelText: 'Riwayat Kesehatan Ibu', alignLabelWithHint: true),
            ),
          ],
        ),
      ),
    );
  }
}

class _Step3Incubator extends ConsumerWidget {
  final IncubatorOption? selected;
  final ValueChanged<IncubatorOption?> onSelected;

  const _Step3Incubator({required this.selected, required this.onSelected});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listAsync = ref.watch(_availableIncubatorsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('3. Penempatan Inkubator',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 16),
          listAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('Error: $e'),
            data: (options) => options.isEmpty
                ? const Text('Tidak ada inkubator yang tersedia.',
                    style: TextStyle(color: AppColors.abnormal))
                : DropdownButtonFormField<IncubatorOption>(
                    value: selected,
                    hint: const Text('Pilih Inkubator'),
                    decoration: const InputDecoration(labelText: 'Inkubator *'),
                    items: options
                        .map((o) => DropdownMenuItem(
                            value: o, child: Text(o.toString())))
                        .toList(),
                    onChanged: onSelected,
                  ),
          ),
        ],
      ),
    );
  }
}

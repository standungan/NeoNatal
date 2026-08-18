// ignore_for_file: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/baby_model.dart';
import 'package:neonatal_care/core/models/intake_options.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

final _availableIncubatorsProvider =
    FutureProvider.autoDispose<List<IncubatorOption>>((ref) async {
  final res = await ApiClient().dio.get(ApiEndpoints.incubatorsAvailable);
  return (res.data as List).map((e) => IncubatorOption.fromJson(e)).toList();
});

class DoctorOption {
  final String id;
  final String fullName;
  const DoctorOption(this.id, this.fullName);
  factory DoctorOption.fromJson(Map<String, dynamic> j) =>
      DoctorOption(j['id'] as String, j['full_name'] as String);
}

final _doctorsProvider =
    FutureProvider.autoDispose<List<DoctorOption>>((ref) async {
  final res = await ApiClient().dio.get(ApiEndpoints.usersDoctors);
  return (res.data as List)
      .map((e) => DoctorOption.fromJson(e as Map<String, dynamic>))
      .toList();
});

class RegisterBabyScreen extends ConsumerStatefulWidget {
  const RegisterBabyScreen({super.key});

  @override
  ConsumerState<RegisterBabyScreen> createState() => _RegisterBabyScreenState();
}

class _RegisterBabyScreenState extends ConsumerState<RegisterBabyScreen> {
  final _pageCtrl = PageController();
  int _step = 0;
  static const _stepLabels = ['Bayi', 'Orang Tua', 'Ibu A–C', 'Ibu D–E', 'Registrasi'];

  // ── step 1: identitas bayi ──
  final _babyNameCtrl = TextEditingController();
  String _gender = 'laki_laki';
  DateTime? _birthDate;
  TimeOfDay? _jamLahir;
  final _birthWeightCtrl = TextEditingController();
  final _birthLengthCtrl = TextEditingController();
  final _gestCtrl = TextEditingController();
  final _lingkarKepalaCtrl = TextEditingController();
  final _lingkarDadaCtrl = TextEditingController();
  String? _golDarahBayi;
  final _noRmBayiCtrl = TextEditingController();
  final _birthTypeCtrl = TextEditingController();
  final _usiaMasukCtrl = TextEditingController();
  final _clinicalNotesCtrl = TextEditingController();

  // ── step 2: orang tua ──
  final _motherCtrl = TextEditingController();
  final _fatherCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _medHistCtrl = TextEditingController();

  // ── step 3: rekam medis ibu A–C ──
  final _noRmIbuCtrl = TextEditingController();
  final _umurIbuCtrl = TextEditingController();
  String? _pendidikan;
  final _pekerjaanCtrl = TextEditingController();
  final _alamatCtrl = TextEditingController();
  String? _golDarahIbu;
  final _kehamilanKeCtrl = TextEditingController();
  final _jmlHidupCtrl = TextEditingController();
  bool _riwayatAbortus = false, _riwayatPrematur = false, _riwayatBblr = false, _riwayatMeninggal = false;
  final _usiaKehamilanCtrl = TextEditingController();
  String? _jenisKehamilan;
  bool _ancRutin = false;
  final _jmlAncCtrl = TextEditingController();
  bool _hipertensi = false, _preeklamsia = false, _dm = false, _infeksi = false,
      _perdarahan = false, _kpd = false, _merokok = false, _paparanAsap = false,
      _alkohol = false, _obatTertentu = false;
  final _obatKetCtrl = TextEditingController();

  // ── step 4: rekam medis ibu D–E ──
  DateTime? _tglPersalinan;
  String? _jenisPersalinan;
  final _tempatCtrl = TextEditingController();
  final _indikasiPrematur = <String>{};
  final _indikasiLainnyaCtrl = TextEditingController();
  final _komplikasi = <String>{};
  final _komplikasiLainnyaCtrl = TextEditingController();
  final _apgar1Ctrl = TextEditingController();
  final _apgar5Ctrl = TextEditingController();
  String? _kondisiUmum;
  bool _masihDirawat = false, _komplikasiPostpartum = false,
      _dapatBerjalan = false, _dapatMenyusui = false;

  // ── step 5: registrasi & inkubator ──
  final _rumahSakitCtrl = TextEditingController();
  final _ruangNicuCtrl = TextEditingController();
  DoctorOption? _selectedDoctor;
  IncubatorOption? _selectedIncubator;

  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _pageCtrl.dispose();
    for (final c in [
      _babyNameCtrl, _birthWeightCtrl, _birthLengthCtrl, _gestCtrl, _lingkarKepalaCtrl,
      _lingkarDadaCtrl, _noRmBayiCtrl, _birthTypeCtrl, _usiaMasukCtrl, _clinicalNotesCtrl,
      _motherCtrl, _fatherCtrl, _phoneCtrl, _medHistCtrl, _noRmIbuCtrl, _umurIbuCtrl,
      _pekerjaanCtrl, _alamatCtrl, _kehamilanKeCtrl, _jmlHidupCtrl, _usiaKehamilanCtrl,
      _jmlAncCtrl, _obatKetCtrl, _tempatCtrl, _indikasiLainnyaCtrl, _komplikasiLainnyaCtrl,
      _apgar1Ctrl, _apgar5Ctrl, _rumahSakitCtrl, _ruangNicuCtrl,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  // ── payload helpers ──
  String? _s(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();
  int? _i(TextEditingController c) => int.tryParse(c.text.trim());
  double? _d(TextEditingController c) => double.tryParse(c.text.trim());
  String _two(int n) => n.toString().padLeft(2, '0');

  void _next() {
    if (_step == 0) {
      if (_babyNameCtrl.text.trim().isEmpty || _birthDate == null) {
        setState(() => _error = 'Nama bayi & tanggal lahir wajib diisi');
        return;
      }
    }
    setState(() => _error = null);
    if (_step < _stepLabels.length - 1) {
      setState(() => _step++);
      _pageCtrl.nextPage(duration: const Duration(milliseconds: 280), curve: Curves.easeInOut);
    } else {
      _submit();
    }
  }

  void _back() {
    if (_step > 0) {
      setState(() => _step--);
      _pageCtrl.previousPage(duration: const Duration(milliseconds: 280), curve: Curves.easeInOut);
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
      final maternal = {
        'no_rm_ibu': _s(_noRmIbuCtrl),
        'umur_ibu': _i(_umurIbuCtrl),
        'pendidikan': _pendidikan,
        'pekerjaan': _s(_pekerjaanCtrl),
        'alamat': _s(_alamatCtrl),
        'golongan_darah': _golDarahIbu,
        'kehamilan_ke': _i(_kehamilanKeCtrl),
        'jumlah_persalinan_hidup': _i(_jmlHidupCtrl),
        'riwayat_abortus': _riwayatAbortus,
        'riwayat_prematur': _riwayatPrematur,
        'riwayat_bblr': _riwayatBblr,
        'riwayat_bayi_meninggal': _riwayatMeninggal,
        'usia_kehamilan_lahir': _i(_usiaKehamilanCtrl),
        'jenis_kehamilan': _jenisKehamilan,
        'anc_rutin': _ancRutin,
        'jumlah_anc': _i(_jmlAncCtrl),
        'hipertensi_kehamilan': _hipertensi,
        'preeklamsia': _preeklamsia,
        'diabetes_gestasional': _dm,
        'infeksi_hamil': _infeksi,
        'perdarahan_hamil': _perdarahan,
        'ketuban_pecah_dini': _kpd,
        'merokok': _merokok,
        'paparan_asap_rokok': _paparanAsap,
        'konsumsi_alkohol': _alkohol,
        'obat_tertentu': _obatTertentu,
        'obat_tertentu_ket': _s(_obatKetCtrl),
        'tanggal_persalinan':
            _tglPersalinan != null ? DateFormat('yyyy-MM-dd').format(_tglPersalinan!) : null,
        'jenis_persalinan': _jenisPersalinan,
        'tempat_persalinan': _s(_tempatCtrl),
        'indikasi_prematur': _indikasiPrematur.isEmpty ? null : _indikasiPrematur.toList(),
        'indikasi_prematur_lainnya': _s(_indikasiLainnyaCtrl),
        'komplikasi_persalinan': _komplikasi.isEmpty ? null : _komplikasi.toList(),
        'komplikasi_lainnya': _s(_komplikasiLainnyaCtrl),
        'apgar_menit_1': _i(_apgar1Ctrl),
        'apgar_menit_5': _i(_apgar5Ctrl),
        'kondisi_umum': _kondisiUmum,
        'masih_dirawat': _masihDirawat,
        'komplikasi_postpartum': _komplikasiPostpartum,
        'dapat_berjalan': _dapatBerjalan,
        'dapat_menyusui': _dapatMenyusui,
      };

      await ApiClient().dio.post(ApiEndpoints.babies, data: {
        'baby_name': _babyNameCtrl.text.trim(),
        'gender': _gender,
        'birth_date': DateFormat('yyyy-MM-dd').format(_birthDate!),
        'birth_weight': _d(_birthWeightCtrl),
        'birth_length': _d(_birthLengthCtrl),
        'gestational_age': _i(_gestCtrl),
        'birth_type': _s(_birthTypeCtrl),
        'clinical_notes': _s(_clinicalNotesCtrl),
        'no_rm_bayi': _s(_noRmBayiCtrl),
        'jam_lahir': _jamLahir != null
            ? '${_two(_jamLahir!.hour)}:${_two(_jamLahir!.minute)}:00'
            : null,
        'usia_masuk_nicu_jam': _i(_usiaMasukCtrl),
        'lingkar_kepala': _d(_lingkarKepalaCtrl),
        'lingkar_dada': _d(_lingkarDadaCtrl),
        'golongan_darah': _golDarahBayi,
        'parent': {
          'mother_name': _s(_motherCtrl),
          'father_name': _s(_fatherCtrl),
          'mother_phone': _s(_phoneCtrl),
          'mother_medical_history': _s(_medHistCtrl),
        },
        'maternal': maternal,
        'incubator_id': _selectedIncubator!.incubatorId,
        'rumah_sakit': _s(_rumahSakitCtrl),
        'ruang_nicu': _s(_ruangNicuCtrl),
        'dpjp_id': _selectedDoctor?.id,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Bayi berhasil didaftarkan'),
          backgroundColor: AppColors.normal,
        ));
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
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: _back),
      ),
      body: Column(
        children: [
          _indicator(),
          Expanded(
            child: PageView(
              controller: _pageCtrl,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                _stepBaby(),
                _stepParent(),
                _stepMaternalABC(),
                _stepMaternalDE(),
                _stepRegistration(),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(_error!, style: const TextStyle(color: AppColors.abnormal)),
            ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: ElevatedButton(
              onPressed: _loading ? null : _next,
              child: _loading
                  ? const SizedBox(
                      height: 20, width: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : Text(_step < _stepLabels.length - 1 ? 'Lanjut' : 'Simpan & Tempatkan Bayi'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _indicator() => Container(
        color: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Langkah ${_step + 1} dari ${_stepLabels.length}: ${_stepLabels[_step]}',
                style: const TextStyle(
                    fontWeight: FontWeight.w700, fontSize: 13, color: AppColors.primary)),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: (_step + 1) / _stepLabels.length,
                minHeight: 6,
                backgroundColor: const Color(0xFFE2E8F0),
                valueColor: const AlwaysStoppedAnimation(AppColors.primary),
              ),
            ),
          ],
        ),
      );

  // ── shared field builders ──
  Widget _title(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
      );
  Widget _sub(String t) => Padding(
        padding: const EdgeInsets.only(top: 14, bottom: 6),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppColors.primary)),
      );
  Widget _tf(TextEditingController c, String label, {TextInputType? kb, int maxLines = 1}) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextFormField(
          controller: c, keyboardType: kb, maxLines: maxLines,
          decoration: InputDecoration(labelText: label),
        ),
      );
  Widget _dd(String label, String? value, List<(String, String)> options, ValueChanged<String?> onChanged) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: DropdownButtonFormField<String>(
          initialValue: value,
          decoration: InputDecoration(labelText: label),
          items: options.map((o) => DropdownMenuItem(value: o.$1, child: Text(o.$2))).toList(),
          onChanged: onChanged,
        ),
      );
  Widget _ddBlood(String label, String? value, ValueChanged<String?> onChanged) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: DropdownButtonFormField<String>(
          initialValue: value,
          decoration: InputDecoration(labelText: label),
          items: kBloodTypes.map((b) => DropdownMenuItem(value: b, child: Text(b))).toList(),
          onChanged: onChanged,
        ),
      );
  Widget _yn(String label, bool value, ValueChanged<bool> onChanged) => SwitchListTile(
        contentPadding: EdgeInsets.zero,
        dense: true,
        title: Text(label, style: const TextStyle(fontSize: 13)),
        value: value,
        onChanged: onChanged,
      );
  Widget _dateField(String label, DateTime? value, ValueChanged<DateTime> onPicked) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: GestureDetector(
          onTap: () async {
            final d = await showDatePicker(
              context: context, initialDate: value ?? DateTime.now(),
              firstDate: DateTime(2020), lastDate: DateTime.now(),
            );
            if (d != null) onPicked(d);
          },
          child: InputDecorator(
            decoration: InputDecoration(labelText: label, suffixIcon: const Icon(Icons.calendar_today)),
            child: Text(value != null ? DateFormat('dd MMM yyyy').format(value) : 'Pilih tanggal',
                style: TextStyle(color: value == null ? AppColors.inkMuted : AppColors.ink)),
          ),
        ),
      );
  Widget _checklist(List<String> options, Set<String> selected) => Wrap(
        spacing: 6, runSpacing: 6,
        children: options.map((o) {
          final sel = selected.contains(o);
          return FilterChip(
            label: Text(o, style: const TextStyle(fontSize: 11.5)),
            selected: sel,
            onSelected: (v) => setState(() => v ? selected.add(o) : selected.remove(o)),
          );
        }).toList(),
      );

  Widget _page(List<Widget> children) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
      );

  // ── step 1: bayi ──
  Widget _stepBaby() => _page([
        _title('1. Identitas Bayi'),
        _tf(_babyNameCtrl, 'Nama Bayi *'),
        const Text('Jenis Kelamin *', style: TextStyle(fontSize: 13, color: AppColors.inkMuted)),
        Row(children: [
          Expanded(child: RadioListTile<String>(
            value: 'laki_laki', groupValue: _gender, contentPadding: EdgeInsets.zero,
            title: const Text('Laki-laki', style: TextStyle(fontSize: 13)),
            onChanged: (v) => setState(() => _gender = v!))),
          Expanded(child: RadioListTile<String>(
            value: 'perempuan', groupValue: _gender, contentPadding: EdgeInsets.zero,
            title: const Text('Perempuan', style: TextStyle(fontSize: 13)),
            onChanged: (v) => setState(() => _gender = v!))),
        ]),
        _dateField('Tanggal Lahir *', _birthDate, (d) => setState(() => _birthDate = d)),
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: GestureDetector(
            onTap: () async {
              final t = await showTimePicker(context: context, initialTime: _jamLahir ?? TimeOfDay.now());
              if (t != null) setState(() => _jamLahir = t);
            },
            child: InputDecorator(
              decoration: const InputDecoration(labelText: 'Jam Lahir', suffixIcon: Icon(Icons.access_time)),
              child: Text(_jamLahir != null ? _jamLahir!.format(context) : 'Pilih jam',
                  style: TextStyle(color: _jamLahir == null ? AppColors.inkMuted : AppColors.ink)),
            ),
          ),
        ),
        Row(children: [
          Expanded(child: _tf(_birthWeightCtrl, 'Berat Lahir (gram)', kb: TextInputType.number)),
          const SizedBox(width: 12),
          Expanded(child: _tf(_birthLengthCtrl, 'Panjang (cm)', kb: TextInputType.number)),
        ]),
        Row(children: [
          Expanded(child: _tf(_lingkarKepalaCtrl, 'Lingkar Kepala (cm)', kb: TextInputType.number)),
          const SizedBox(width: 12),
          Expanded(child: _tf(_lingkarDadaCtrl, 'Lingkar Dada (cm)', kb: TextInputType.number)),
        ]),
        Row(children: [
          Expanded(child: _tf(_gestCtrl, 'Usia Gestasi (minggu)', kb: TextInputType.number)),
          const SizedBox(width: 12),
          Expanded(child: _tf(_usiaMasukCtrl, 'Usia Masuk NICU (jam)', kb: TextInputType.number)),
        ]),
        _ddBlood('Golongan Darah Bayi', _golDarahBayi, (v) => setState(() => _golDarahBayi = v)),
        _tf(_birthTypeCtrl, 'Jenis Kelahiran (mis. spontan / SC)'),
        _tf(_noRmBayiCtrl, 'No. Rekam Medis Bayi'),
        _tf(_clinicalNotesCtrl, 'Catatan Klinis', maxLines: 2),
      ]);

  // ── step 2: orang tua ──
  Widget _stepParent() => _page([
        _title('2. Informasi Orang Tua'),
        _tf(_motherCtrl, 'Nama Ibu'),
        _tf(_fatherCtrl, 'Nama Ayah'),
        _tf(_phoneCtrl, 'Nomor Telepon Ibu', kb: TextInputType.phone),
        _tf(_medHistCtrl, 'Riwayat Kesehatan Ibu (ringkas)', maxLines: 3),
      ]);

  // ── step 3: rekam medis ibu A–C ──
  Widget _stepMaternalABC() => _page([
        _title('3. Rekam Medis Ibu (A–C)'),
        _sub('A. Identitas Ibu'),
        _tf(_noRmIbuCtrl, 'No. Rekam Medis Ibu'),
        Row(children: [
          Expanded(child: _tf(_umurIbuCtrl, 'Umur Ibu (tahun)', kb: TextInputType.number)),
          const SizedBox(width: 12),
          Expanded(child: _ddBlood('Gol. Darah Ibu', _golDarahIbu, (v) => setState(() => _golDarahIbu = v))),
        ]),
        _dd('Pendidikan', _pendidikan, kPendidikan, (v) => setState(() => _pendidikan = v)),
        _tf(_pekerjaanCtrl, 'Pekerjaan'),
        _tf(_alamatCtrl, 'Alamat', maxLines: 2),
        _sub('B. Riwayat Obstetri'),
        Row(children: [
          Expanded(child: _tf(_kehamilanKeCtrl, 'Kehamilan ke-', kb: TextInputType.number)),
          const SizedBox(width: 12),
          Expanded(child: _tf(_jmlHidupCtrl, 'Persalinan hidup', kb: TextInputType.number)),
        ]),
        _yn('Riwayat abortus', _riwayatAbortus, (v) => setState(() => _riwayatAbortus = v)),
        _yn('Riwayat prematur', _riwayatPrematur, (v) => setState(() => _riwayatPrematur = v)),
        _yn('Riwayat BBLR', _riwayatBblr, (v) => setState(() => _riwayatBblr = v)),
        _yn('Riwayat bayi meninggal', _riwayatMeninggal, (v) => setState(() => _riwayatMeninggal = v)),
        _sub('C. Riwayat Kehamilan Saat Ini'),
        Row(children: [
          Expanded(child: _tf(_usiaKehamilanCtrl, 'Usia kehamilan lahir (mgg)', kb: TextInputType.number)),
          const SizedBox(width: 12),
          Expanded(child: _tf(_jmlAncCtrl, 'Jumlah ANC', kb: TextInputType.number)),
        ]),
        _dd('Jenis Kehamilan', _jenisKehamilan, kJenisKehamilan, (v) => setState(() => _jenisKehamilan = v)),
        _yn('ANC rutin', _ancRutin, (v) => setState(() => _ancRutin = v)),
        _yn('Hipertensi kehamilan', _hipertensi, (v) => setState(() => _hipertensi = v)),
        _yn('Preeklamsia', _preeklamsia, (v) => setState(() => _preeklamsia = v)),
        _yn('Diabetes gestasional', _dm, (v) => setState(() => _dm = v)),
        _yn('Infeksi saat hamil', _infeksi, (v) => setState(() => _infeksi = v)),
        _yn('Perdarahan saat hamil', _perdarahan, (v) => setState(() => _perdarahan = v)),
        _yn('Ketuban pecah dini', _kpd, (v) => setState(() => _kpd = v)),
        _yn('Merokok', _merokok, (v) => setState(() => _merokok = v)),
        _yn('Paparan asap rokok', _paparanAsap, (v) => setState(() => _paparanAsap = v)),
        _yn('Konsumsi alkohol', _alkohol, (v) => setState(() => _alkohol = v)),
        _yn('Konsumsi obat tertentu', _obatTertentu, (v) => setState(() => _obatTertentu = v)),
        if (_obatTertentu) _tf(_obatKetCtrl, 'Keterangan obat'),
      ]);

  // ── step 4: rekam medis ibu D–E ──
  Widget _stepMaternalDE() => _page([
        _title('4. Rekam Medis Ibu (D–E)'),
        _sub('D. Riwayat Persalinan'),
        _dateField('Tanggal Persalinan', _tglPersalinan, (d) => setState(() => _tglPersalinan = d)),
        _dd('Jenis Persalinan', _jenisPersalinan, kJenisPersalinan, (v) => setState(() => _jenisPersalinan = v)),
        _tf(_tempatCtrl, 'Tempat Persalinan'),
        const SizedBox(height: 4),
        const Text('Indikasi Persalinan Prematur', style: TextStyle(fontSize: 12.5, color: AppColors.inkMuted)),
        const SizedBox(height: 6),
        _checklist(kIndikasiPrematur, _indikasiPrematur),
        const SizedBox(height: 8),
        _tf(_indikasiLainnyaCtrl, 'Indikasi lainnya'),
        const SizedBox(height: 4),
        const Text('Komplikasi Persalinan', style: TextStyle(fontSize: 12.5, color: AppColors.inkMuted)),
        const SizedBox(height: 6),
        _checklist(kKomplikasiPersalinan, _komplikasi),
        const SizedBox(height: 8),
        _tf(_komplikasiLainnyaCtrl, 'Komplikasi lainnya'),
        Row(children: [
          Expanded(child: _tf(_apgar1Ctrl, 'APGAR menit 1', kb: TextInputType.number)),
          const SizedBox(width: 12),
          Expanded(child: _tf(_apgar5Ctrl, 'APGAR menit 5', kb: TextInputType.number)),
        ]),
        _sub('E. Kondisi Ibu Setelah Melahirkan'),
        _dd('Kondisi Umum', _kondisiUmum, kKondisiUmum, (v) => setState(() => _kondisiUmum = v)),
        _yn('Masih dirawat', _masihDirawat, (v) => setState(() => _masihDirawat = v)),
        _yn('Komplikasi postpartum', _komplikasiPostpartum, (v) => setState(() => _komplikasiPostpartum = v)),
        _yn('Dapat berjalan', _dapatBerjalan, (v) => setState(() => _dapatBerjalan = v)),
        _yn('Dapat menyusui', _dapatMenyusui, (v) => setState(() => _dapatMenyusui = v)),
      ]);

  // ── step 5: registrasi & inkubator ──
  Widget _stepRegistration() {
    final doctorsAsync = ref.watch(_doctorsProvider);
    final incubatorsAsync = ref.watch(_availableIncubatorsProvider);
    return _page([
      _title('5. Registrasi & Penempatan'),
      _tf(_rumahSakitCtrl, 'Rumah Sakit'),
      _tf(_ruangNicuCtrl, 'Ruang NICU'),
      const SizedBox(height: 4),
      doctorsAsync.when(
        loading: () => const LinearProgressIndicator(),
        error: (e, _) => Text('Gagal memuat dokter: $e', style: const TextStyle(color: AppColors.abnormal)),
        data: (doctors) => DropdownButtonFormField<DoctorOption>(
          initialValue: _selectedDoctor,
          decoration: const InputDecoration(labelText: 'DPJP (Dokter Penanggung Jawab)'),
          items: doctors.map((d) => DropdownMenuItem(value: d, child: Text(d.fullName))).toList(),
          onChanged: (v) => setState(() => _selectedDoctor = v),
        ),
      ),
      const SizedBox(height: 14),
      const Text('Penempatan Inkubator *', style: TextStyle(fontSize: 13, color: AppColors.inkMuted)),
      const SizedBox(height: 6),
      incubatorsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Text('Error: $e', style: const TextStyle(color: AppColors.abnormal)),
        data: (options) => options.isEmpty
            ? const Text('Tidak ada inkubator yang tersedia.',
                style: TextStyle(color: AppColors.abnormal))
            : DropdownButtonFormField<IncubatorOption>(
                initialValue: _selectedIncubator,
                decoration: const InputDecoration(labelText: 'Inkubator *'),
                items: options
                    .map((o) => DropdownMenuItem(value: o, child: Text(o.toString())))
                    .toList(),
                onChanged: (v) => setState(() => _selectedIncubator = v),
              ),
      ),
    ]);
  }
}

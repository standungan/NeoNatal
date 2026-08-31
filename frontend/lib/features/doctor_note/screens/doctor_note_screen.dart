import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/providers/auth_provider.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

/// Previous doctor notes for this baby (newest first).
final _doctorNotesProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, String>((ref, babyId) async {
  final res = await ApiClient().dio.get(ApiEndpoints.doctorNotes(babyId));
  return (res.data as List).cast<Map<String, dynamic>>();
});

/// Observasi Dokter — a doctor writes an observation note for the baby.
/// Writing is dokter-only (enforced by the backend); everyone can read.
class DoctorNoteScreen extends ConsumerStatefulWidget {
  final String babyId;
  const DoctorNoteScreen({super.key, required this.babyId});

  @override
  ConsumerState<DoctorNoteScreen> createState() => _DoctorNoteScreenState();
}

class _DoctorNoteScreenState extends ConsumerState<DoctorNoteScreen> {
  DateTime _obsTime = DateTime.now();
  final _catatanCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _catatanCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ApiClient().dio.post(
        ApiEndpoints.doctorNotes(widget.babyId),
        data: {
          'observation_time': _obsTime.toIso8601String(),
          'catatan': _catatanCtrl.text.trim(),
        },
      );
      if (!mounted) return;
      _catatanCtrl.clear();
      ref.invalidate(_doctorNotesProvider(widget.babyId));
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Catatan dokter berhasil disimpan'),
        backgroundColor: AppColors.normal,
      ));
    } catch (e) {
      setState(() => _error = 'Gagal menyimpan: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDokter = ref.watch(authProvider).role == 'dokter';
    final notesAsync = ref.watch(_doctorNotesProvider(widget.babyId));

    return Scaffold(
      appBar: AppBar(title: const Text('Observasi Dokter')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (isDokter) ...[
              const _SectionTitle('Catatan Baru'),
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
                      labelText: 'Waktu Observasi',
                      suffixIcon: Icon(Icons.calendar_today)),
                  child: Text(DateFormat('dd MMM yyyy').format(_obsTime)),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _catatanCtrl,
                maxLines: 6,
                decoration: const InputDecoration(
                  labelText: 'Catatan Dokter',
                  hintText:
                      'Hasil observasi, penilaian klinis, dan rencana tindak lanjut...',
                  alignLabelWithHint: true,
                ),
                onChanged: (_) => setState(() {}),
              ),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(_error!,
                    style: const TextStyle(color: AppColors.abnormal)),
              ],
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: (_loading || _catatanCtrl.text.trim().isEmpty)
                    ? null
                    : _submit,
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Text('Simpan Catatan'),
              ),
              const SizedBox(height: 24),
            ] else
              Container(
                margin: const EdgeInsets.only(bottom: 20),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: const Text(
                  'Hanya dokter yang dapat menulis catatan observasi. '
                  'Riwayat catatan di bawah bersifat baca-saja.',
                  style: TextStyle(fontSize: 12.5, color: AppColors.inkMuted),
                ),
              ),

            const _SectionTitle('Riwayat Catatan'),
            notesAsync.when(
              loading: () => const Padding(
                padding: EdgeInsets.all(24),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (e, _) => Text('Gagal memuat catatan: $e',
                  style: const TextStyle(color: AppColors.abnormal)),
              data: (notes) => notes.isEmpty
                  ? const Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: Text('Belum ada catatan dokter.',
                          style: TextStyle(color: AppColors.inkMuted)),
                    )
                  : Column(
                      children: notes.map((n) => _NoteCard(note: n)).toList(),
                    ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _NoteCard extends StatelessWidget {
  final Map<String, dynamic> note;
  const _NoteCard({required this.note});

  @override
  Widget build(BuildContext context) {
    final time = note['observation_time'] as String?;
    final when = time != null
        ? DateFormat('dd MMM yyyy HH:mm').format(DateTime.parse(time))
        : '-';
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.medical_information,
                    size: 16, color: AppColors.primary),
                const SizedBox(width: 6),
                Expanded(
                  child: Text('${note['recorder_name'] ?? 'Dokter'}',
                      style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                          color: AppColors.ink)),
                ),
                Text(when,
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.inkMuted)),
              ],
            ),
            const SizedBox(height: 8),
            Text('${note['catatan'] ?? ''}',
                style: const TextStyle(fontSize: 13, color: AppColors.ink)),
          ],
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

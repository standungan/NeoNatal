import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/observation_model.dart';
import 'package:neonatal_care/core/models/scoring.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';
import 'package:neonatal_care/core/widgets/score_chips.dart';

final _observationCatalogProvider =
    FutureProvider.autoDispose<ObservationCatalog>((ref) async {
  final res = await ApiClient().dio.get(ApiEndpoints.observationCatalog);
  return ObservationCatalog.fromJson(res.data as Map<String, dynamic>);
});

/// Monitoring Bayi (Observasi) — 6 pilar / 42 item, tiap item 0–4.
class ObservationScreen extends ConsumerStatefulWidget {
  final String babyId;
  const ObservationScreen({super.key, required this.babyId});

  @override
  ConsumerState<ObservationScreen> createState() => _ObservationScreenState();
}

class _ObservationScreenState extends ConsumerState<ObservationScreen> {
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
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ApiClient().dio.post(
        ApiEndpoints.observation(widget.babyId),
        data: {
          'observation_time': _obsTime.toIso8601String(),
          'scores': _scores,
          'catatan':
              _catatanCtrl.text.trim().isEmpty ? null : _catatanCtrl.text.trim(),
        },
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Observasi berhasil disimpan'),
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
    final catalogAsync = ref.watch(_observationCatalogProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Monitoring Bayi (Observasi)')),
      body: catalogAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('Gagal memuat katalog observasi: $e'),
          ),
        ),
        data: (catalog) {
          final total = _scores.values.fold<int>(0, (s, v) => s + v);
          final pct = percentageFor(total, catalog.maxTotal);
          final category = categoryFor(pct);
          final scoreColor = categoryColor(category);
          final filled = _scores.length;
          final alarms = <ObsCatalogItem>[
            for (final p in catalog.pillars)
              for (final it in p.items)
                if ((_scores[it.itemCode] ?? 99) <= 1) it,
          ];

          return SingleChildScrollView(
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
                const SizedBox(height: 18),

                // ── 6 pillars ──────────────────────────────────────────────
                for (var pi = 0; pi < catalog.pillars.length; pi++)
                  _PillarCard(
                    index: pi + 1,
                    pillar: catalog.pillars[pi],
                    scores: _scores,
                    onChanged: (code, v) => setState(() => _scores[code] = v),
                  ),

                const SizedBox(height: 8),
                const _SectionTitle('Catatan (Opsional)'),
                TextFormField(
                  controller: _catatanCtrl,
                  maxLines: 3,
                  decoration: const InputDecoration(
                      hintText: 'Temuan khusus / catatan observasi...'),
                ),
                const SizedBox(height: 20),

                // ── live summary ───────────────────────────────────────────
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
                          Text('${pct.toStringAsFixed(1)}%',
                              style: TextStyle(
                                  fontSize: 38,
                                  fontWeight: FontWeight.w800,
                                  color: scoreColor)),
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
                      Text(
                          '$total / ${catalog.maxTotal} poin · '
                          '$filled / ${catalog.totalItems} item terisi',
                          style: const TextStyle(
                              fontSize: 12, color: AppColors.inkMuted)),
                      if (alarms.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        Text('⚠ ${alarms.length} item perlu perhatian (skor 0–1)',
                            style: const TextStyle(
                                fontSize: 12.5,
                                fontWeight: FontWeight.w700,
                                color: AppColors.abnormal)),
                        for (final a in alarms.take(8))
                          Text('• ${a.text}',
                              style: const TextStyle(
                                  fontSize: 11.5, color: AppColors.ink)),
                        if (alarms.length > 8)
                          Text('…dan ${alarms.length - 8} lainnya',
                              style: const TextStyle(
                                  fontSize: 11.5, color: AppColors.inkMuted)),
                      ],
                    ],
                  ),
                ),

                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!,
                      style: const TextStyle(color: AppColors.abnormal)),
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
                      : const Text('Simpan Observasi'),
                ),
                const SizedBox(height: 16),
              ],
            ),
          );
        },
      ),
    );
  }
}

/// One pillar: numbered title + running score + scale hint + its items.
class _PillarCard extends StatelessWidget {
  final int index;
  final ObsCatalogPillar pillar;
  final Map<String, int> scores;
  final void Function(String code, int v) onChanged;

  const _PillarCard({
    required this.index,
    required this.pillar,
    required this.scores,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final raw = pillar.items
        .fold<int>(0, (s, it) => s + (scores[it.itemCode] ?? 0));
    final max = pillar.items.length * kMaxPerItem;
    final pct = max == 0 ? 0.0 : raw / max * 100;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('$index. ${pillar.label}',
                      style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 14.5,
                          color: AppColors.ink)),
                ),
                Text('$raw/$max · ${pct.toStringAsFixed(0)}%',
                    style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppColors.inkMuted)),
              ],
            ),
            const SizedBox(height: 4),
            const Text(kScaleHint,
                style: TextStyle(fontSize: 11, color: AppColors.inkMuted)),
            const SizedBox(height: 12),
            for (var i = 0; i < pillar.items.length; i++)
              _ItemTile(
                index: i + 1,
                title: pillar.items[i].text,
                value: scores[pillar.items[i].itemCode],
                onChanged: (v) => onChanged(pillar.items[i].itemCode, v),
              ),
          ],
        ),
      ),
    );
  }
}

/// One instrument item: number + text + 0–4 chip selector.
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
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('$index. $title',
              style: const TextStyle(fontSize: 13, color: AppColors.ink)),
          const SizedBox(height: 8),
          ScoreChips(value: value, min: 0, max: kMaxPerItem, onChanged: onChanged),
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

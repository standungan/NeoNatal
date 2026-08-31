// Flat single-pillar catalog — the shape returned by BOTH
// GET /api/v1/aksi/catalog and GET /api/v1/involvement/catalog:
//
//   { key, label, items: [{item_code, text}], total_items, max_total }
//
// Fetched rather than hardcoded so the items, their wording and the maximum
// score can never drift from the backend catalog that scores them. The 0–4
// scale change already moved max_total from 18 to 24 once; a duplicated Dart
// copy would have silently kept scoring against the old maximum.
//
// Observation has its own model (observation_model.dart) because it nests
// items under 6 pillars; these two are flat.

class PillarCatalogItem {
  final String itemCode;
  final String text;
  const PillarCatalogItem(this.itemCode, this.text);

  factory PillarCatalogItem.fromJson(Map<String, dynamic> j) =>
      PillarCatalogItem(j['item_code'] as String, j['text'] as String);
}

class PillarCatalog {
  final String key;
  final String label;
  final List<PillarCatalogItem> items;
  final int totalItems;
  final int maxTotal;

  const PillarCatalog({
    required this.key,
    required this.label,
    required this.items,
    required this.totalItems,
    required this.maxTotal,
  });

  factory PillarCatalog.fromJson(Map<String, dynamic> j) => PillarCatalog(
        key: j['key'] as String,
        label: j['label'] as String,
        items: (j['items'] as List)
            .map((e) => PillarCatalogItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        totalItems: j['total_items'] as int,
        maxTotal: j['max_total'] as int,
      );
}

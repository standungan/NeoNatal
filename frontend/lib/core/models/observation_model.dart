// Observasi (Monitoring Bayi) — 6 pilar / 42 item, tiap item 0–4.
// Catalog-driven (fetched from GET /observation/catalog) so the 42 items never
// drift from the backend. Shared scoring helpers live in core/models/scoring.dart.

class ObsCatalogItem {
  final String itemCode;
  final String text;
  const ObsCatalogItem(this.itemCode, this.text);

  factory ObsCatalogItem.fromJson(Map<String, dynamic> j) =>
      ObsCatalogItem(j['item_code'] as String, j['text'] as String);
}

class ObsCatalogPillar {
  final String key;
  final String label;
  final List<ObsCatalogItem> items;
  const ObsCatalogPillar({required this.key, required this.label, required this.items});

  factory ObsCatalogPillar.fromJson(Map<String, dynamic> j) => ObsCatalogPillar(
        key: j['key'] as String,
        label: j['label'] as String,
        items: (j['items'] as List)
            .map((e) => ObsCatalogItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class ObservationCatalog {
  final List<ObsCatalogPillar> pillars;
  final int totalItems;
  final int maxTotal;
  const ObservationCatalog({
    required this.pillars,
    required this.totalItems,
    required this.maxTotal,
  });

  factory ObservationCatalog.fromJson(Map<String, dynamic> j) => ObservationCatalog(
        pillars: (j['pillars'] as List)
            .map((e) => ObsCatalogPillar.fromJson(e as Map<String, dynamic>))
            .toList(),
        totalItems: j['total_items'] as int,
        maxTotal: j['max_total'] as int,
      );
}

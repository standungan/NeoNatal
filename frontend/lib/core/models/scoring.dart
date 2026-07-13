import 'package:flutter/material.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

/// Shared scoring helpers for the 8-pillar instrument modules
/// (Monitoring Bayi, Keterlibatan Orang Tua, Menu Aksi) — each item is 0–3.

double percentageFor(int total, int maxTotal) =>
    maxTotal == 0 ? 0 : total / maxTotal * 100;

/// 5-band interpretation shared by every pillar module (0–100%).
String categoryFor(double percentage) {
  if (percentage >= 85) return 'Sangat Baik';
  if (percentage >= 70) return 'Baik';
  if (percentage >= 55) return 'Cukup';
  if (percentage >= 40) return 'Kurang';
  return 'Sangat Kurang';
}

Color categoryColor(String category) {
  switch (category) {
    case 'Sangat Baik':
      return AppColors.normal;
    case 'Baik':
      return AppColors.primary;
    case 'Cukup':
      return const Color(0xFF0EA5E9);
    case 'Kurang':
      return AppColors.warning;
    default:
      return AppColors.abnormal; // Sangat Kurang
  }
}

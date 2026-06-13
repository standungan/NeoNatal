import 'package:flutter/material.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

class StatusBadge extends StatelessWidget {
  final String status;

  const StatusBadge(this.status, {super.key});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (status) {
      'terisi'        => ('Terisi',         AppColors.terisi),
      'kosong'        => ('Kosong',         AppColors.kosong),
      'warning'       => ('Warning',        AppColors.warning),
      'tidak_tersedia'=> ('Tidak Tersedia', AppColors.tidakTersedia),
      _               => (status,           Colors.grey),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(shape: BoxShape.circle, color: color),
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class VitalStatusDot extends StatelessWidget {
  final String status; // "normal" | "warning"
  const VitalStatusDot(this.status, {super.key});

  @override
  Widget build(BuildContext context) {
    final color = status == 'warning' ? AppColors.warning : AppColors.normal;
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(shape: BoxShape.circle, color: color),
    );
  }
}

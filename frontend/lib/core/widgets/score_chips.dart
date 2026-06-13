import 'package:flutter/material.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

class ScoreChips extends StatelessWidget {
  final int? value;
  final ValueChanged<int> onChanged;
  final bool enabled;

  const ScoreChips({
    super.key,
    required this.value,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: List.generate(5, (i) {
        final score = i + 1;
        final selected = value == score;
        return Padding(
          padding: const EdgeInsets.only(right: 8),
          child: GestureDetector(
            onTap: enabled ? () => onChanged(score) : null,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: selected ? AppColors.primary : const Color(0xFFF8FAFC),
                border: Border.all(
                  color: selected ? AppColors.primary : AppColors.border,
                  width: 1.5,
                ),
                boxShadow: selected
                    ? const [
                        BoxShadow(
                          color: Color(0x402563EB),
                          blurRadius: 10,
                          offset: Offset(0, 4),
                        ),
                      ]
                    : null,
              ),
              child: Center(
                child: Text(
                  '$score',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: selected ? Colors.white : AppColors.inkMuted,
                  ),
                ),
              ),
            ),
          ),
        );
      }),
    );
  }
}

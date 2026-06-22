import 'package:flutter/material.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

class ScoreChips extends StatelessWidget {
  final int? value;
  final ValueChanged<int> onChanged;
  final bool enabled;
  final int min;
  final int max;

  const ScoreChips({
    super.key,
    required this.value,
    required this.onChanged,
    this.enabled = true,
    this.min = 1,
    this.max = 5,
  });

  @override
  Widget build(BuildContext context) {
    final count = max - min + 1;
    final size = count > 6 ? 38.0 : 44.0;   // shrink chips for wider ranges
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: List.generate(count, (i) {
        final score = min + i;
        final selected = value == score;
        return GestureDetector(
            onTap: enabled ? () => onChanged(score) : null,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              width: size,
              height: size,
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
          );
      }),
    );
  }
}

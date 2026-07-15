import 'package:flutter/material.dart';
import '../models.dart';
import '../theme.dart';
import 'widgets.dart';

/// The honest step trace: deterministic vs LLM steps, clearly labelled.
class StepTrace extends StatelessWidget {
  final List<dynamic> steps;
  const StepTrace({super.key, required this.steps});

  @override
  Widget build(BuildContext context) {
    if (steps.isEmpty) return const SizedBox.shrink();
    return SectionCard(
      title: 'مسار المعالجة',
      child: Column(
        children: steps.map((raw) {
          final s = raw as Map<String, dynamic>;
          final isLlm = s['kind'] == 'llm';
          return Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surfaceAlt,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Pill(isLlm ? 'ذكاء اصطناعي' : 'حتمي',
                      color: isLlm ? AppColors.ai : AppColors.primary,
                      solid: true),
                  const Spacer(),
                  Text('${s['elapsed_ms']} م.ث',
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textMuted)),
                ]),
                const SizedBox(height: 8),
                Text(stepNamesAr[s['step']] ?? '${s['step']}',
                    style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text('${s['message_ar']}',
                    style: const TextStyle(
                        color: AppColors.textMuted, height: 1.6)),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

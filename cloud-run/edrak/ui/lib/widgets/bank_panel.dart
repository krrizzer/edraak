import 'package:flutter/material.dart';
import '../models.dart';
import '../theme.dart';
import 'widgets.dart';

/// "ما لا يراه بنكك" — detected obligations grouped by bank. The cross-bank money shot.
class BankPanel extends StatelessWidget {
  final Map<String, dynamic> byBank;
  const BankPanel({super.key, required this.byBank});

  @override
  Widget build(BuildContext context) {
    if (byBank.isEmpty) return const SizedBox.shrink();
    return SectionCard(
      title: 'ما لا يراه بنكك',
      accent: AppColors.warn,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'التزامات رصدها النظام من أوصاف المعاملات الخام عبر جميع بنوكك — ما لا يظهر في فحص بنك واحد.',
            style: TextStyle(color: AppColors.textMuted, height: 1.7),
          ),
          const SizedBox(height: 14),
          ...byBank.entries.map((e) =>
              _bankCard(e.key, (e.value as List).cast<Map<String, dynamic>>())),
        ],
      ),
    );
  }

  Widget _bankCard(String bankCode, List<Map<String, dynamic>> items) =>
      Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surfaceAlt,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              BankLogo(bankCode, size: 30),
              const SizedBox(width: 10),
              Text(bankNamesAr[bankCode] ?? bankCode,
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w800)),
            ]),
            const SizedBox(height: 10),
            ...items.map(_obligationRow),
          ],
        ),
      );

  Widget _obligationRow(Map<String, dynamic> item) {
    final remaining = item['remaining_months'];
    final confidence = ((item['confidence'] ?? 0) as num) * 100;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Pill(
                obligationBadges[item['obligation_type']] ??
                    '${item['obligation_type']}',
                color: _typeColor(item['obligation_type'] as String?),
                solid: true),
            const Spacer(),
            Text('${sar(item['monthly_amount'])} شهريًا',
                style: const TextStyle(
                    color: AppColors.primary, fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 4),
          Text('${item['label_ar'] ?? item['counterparty']}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          Text(
            'يوم ${item['day_of_month']}'
            '${remaining != null ? ' · متبقٍ $remaining شهر' : ' · مستمر'}'
            ' · ثقة ${confidence.round()}%',
            style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }

  Color _typeColor(String? type) {
    switch (type) {
      case 'bnpl_installment':
        return AppColors.warn;
      case 'jamiya':
        return AppColors.accent;
      case 'family_support':
        return const Color(0xFFE79AD0);
      case 'rent':
        return const Color(0xFFB9A8F5);
      default:
        return AppColors.primary;
    }
  }
}

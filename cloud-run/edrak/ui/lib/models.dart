import 'package:intl/intl.dart';

final _sar = NumberFormat('#,##0', 'en_US');

/// Format a number as Saudi riyals.
String sar(num? value) => value == null ? '-' : '${_sar.format(value.round())} ر.س';

/// The customer's host bank — Edraak runs inside this bank's world, so it is
/// always connected and never needs linking.
const hostBankCode = 'ALINMA';

/// The demo banks, host first, in the order the link screen shows them.
const bankNamesAr = {
  'ALINMA': 'مصرف الإنماء',
  'ALRAJHI': 'مصرف الراجحي',
  'SNB': 'البنك الأهلي السعودي',
  'RIYAD': 'بنك الرياض',
  'SAB': 'البنك السعودي الأول',
};

const obligationBadges = {
  'bnpl_installment': 'أقساط BNPL',
  'jamiya': 'جمعية',
  'family_support': 'حوالة عائلية',
  'rent': 'إيجار',
  'subscription': 'اشتراك',
  'loan_installment_other_bank': 'قرض بنك آخر',
};

const stepNamesAr = {
  'validator': 'التحقق من البيانات',
  'recurrence_detector': 'كشف الالتزامات المتكررة',
  'transaction_intelligence': 'تصنيف الالتزامات',
  'forecast_engine': 'محرك التوقعات',
  'risk_model': 'نموذج المخاطر',
  'verdict_rules': 'قواعد القرار',
  'decision_advisor': 'المستشار المالي',
  'radar_detector': 'كاشف الرادار',
  'intervention_agent': 'وكيل التدخل',
};

/// The logged-in customer.
class Customer {
  final String customerId;
  final String arName;
  Customer(this.customerId, this.arName);
  factory Customer.fromJson(Map<String, dynamic> j) =>
      Customer(j['customer_id'] as String, (j['ar_name'] ?? '') as String);
}

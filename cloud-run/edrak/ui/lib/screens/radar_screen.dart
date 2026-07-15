import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
// import '../widgets/step_trace.dart';  // مسار المعالجة — hidden for now
import '../widgets/widgets.dart';

const _steps = [
  'قراءة أرصدة وحركات الشهر الحالي',
  'مقارنة وتيرة الصرف بميزانيتك المعتادة',
  'إسقاط الرصيد يومًا بيوم حتى نهاية الشهر',
  'صياغة التنبيه والحل الأنسب',
];

class RadarScreen extends StatefulWidget {
  final Customer customer;
  const RadarScreen({super.key, required this.customer});
  @override
  State<RadarScreen> createState() => _RadarScreenState();
}

class _RadarScreenState extends State<RadarScreen> {
  bool _loading = false;
  Map<String, dynamic>? _result;
  List<dynamic> _alerts = [];

  @override
  void initState() {
    super.initState();
    _loadAlerts();
  }

  Future<void> _loadAlerts() async {
    try {
      final a = await Api.alerts(widget.customer.customerId);
      if (mounted) setState(() => _alerts = a);
    } catch (_) {}
  }

  Future<void> _trigger() async {
    setState(() {
      _loading = true;
      _result = null;
    });
    try {
      _result = await Api.radar(widget.customer.customerId);
      await _loadAlerts();
    } catch (e) {
      if (mounted) showError(context, e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الرادار المالي',
            style: TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: ListView(
        padding: EdgeInsets.fromLTRB(
            16, 16, 16, 24 + MediaQuery.viewPaddingOf(context).bottom),
        children: [
          SectionCard(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text(
                  'يراقب الرادار وتيرة صرفك الحالية مقابل ميزانيتك الشهرية، ويتوقع الفجوات قبل حدوثها.',
                  style: TextStyle(height: 1.8)),
              const SizedBox(height: 14),
              PrimaryButton('محاكاة فحص نهاية الشهر',
                  loading: _loading, onPressed: _trigger),
              const SizedBox(height: 10),
              const Text(
                'في الإنتاج يعمل هذا الفحص تلقائيًا عبر Cloud Scheduler — الزر يحاكي التشغيل المجدول.',
                style: TextStyle(
                    color: AppColors.textMuted, fontSize: 12, height: 1.7),
              ),
            ]),
          ),
          if (_loading)
            LoadingPanel(title: 'جاري فحص مسار الشهر الحالي', steps: _steps),
          if (!_loading && _result != null) _RadarResult(result: _result!),
          _PastAlerts(alerts: _alerts),
        ],
      ),
    );
  }
}

class _RadarResult extends StatelessWidget {
  final Map<String, dynamic> result;
  const _RadarResult({required this.result});

  Color get _color {
    switch (result['alert_type']) {
      case 'installment_gap':
        return AppColors.danger;
      case 'overspend':
        return AppColors.warn;
      default:
        return AppColors.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _color;
    final trajectory = result['trajectory'] as Map<String, dynamic>;
    final cause = result['cause_category'] as Map<String, dynamic>?;
    final cuts = ((trajectory['suggested_cuts'] ?? []) as List)
        .cast<Map<String, dynamic>>();
    final isAlert = result['alert_type'] != 'on_track';

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(20),
        decoration: heroDecoration(color),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(
                isAlert ? Icons.warning_amber_rounded : Icons.verified_outlined,
                color: color,
                size: 26),
            const SizedBox(width: 10),
            Expanded(
              child: Text(result['title_ar'] as String,
                  style: TextStyle(
                      fontSize: 18, fontWeight: FontWeight.w900, color: color)),
            ),
          ]),
          const SizedBox(height: 12),
          Text(result['message_ar'] as String,
              style: const TextStyle(fontSize: 15.5, height: 1.9)),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (isAlert) ...[
              Pill('النقص المتوقع: ${sar(result['gap_amount'])}', color: color),
              Pill('التاريخ: ${result['gap_date']}', color: color),
              if (cause != null)
                Pill(
                    'السبب: ${cause['label_ar']} (+${cause['deviation_pct']}%)',
                    color: color),
            ] else
              Pill(
                  'الرصيد المتوقع نهاية الشهر: ${sar(trajectory['projected_eom_balance'])}',
                  color: AppColors.primary),
          ]),
          if (cuts.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text('أسرع الحلول:',
                style: TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final c in cuts)
                Pill('خفّض ${c['label_ar']} → توفّر ${sar(c['recoverable'])}',
                    color: AppColors.primary),
            ]),
          ],
        ]),
      ),
      _BudgetCard(trajectory: trajectory),
      _Trajectory(trajectory: trajectory),
      // مسار المعالجة — kept in code, hidden for now; re-enable if wanted later:
      // StepTrace(steps: (result['step_trace'] as List)),
    ]);
  }
}

/// The month's budget picture: what's spendable, what's reserved, how much of the
/// flexible budget is already burned.
class _BudgetCard extends StatelessWidget {
  final Map<String, dynamic> trajectory;
  const _BudgetCard({required this.trajectory});

  @override
  Widget build(BuildContext context) {
    final used = (trajectory['flexible_used_mtd'] as num?) ?? 0;
    final budget = (trajectory['flexible_budget'] as num?) ?? 0;
    final pct = ((trajectory['budget_used_pct'] as num?) ?? 0).clamp(0, 200);
    final over = pct > 100;
    return SectionCard(
      title: 'ميزانية الشهر',
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
              child:
                  Metric('الرصيد المتاح الآن', sar(trajectory['balance_now']))),
          const SizedBox(width: 10),
          Expanded(
              child: Metric(
                  'احتياطي الادخار', sar(trajectory['savings_reserve']),
                  color: AppColors.accent)),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          Text('الصرف المرن: ${sar(used)} من ${sar(budget)}',
              style:
                  const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          const Spacer(),
          Text('$pct%',
              style: TextStyle(
                  fontWeight: FontWeight.w900,
                  color: over ? AppColors.danger : AppColors.primary)),
        ]),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(99),
          child: LinearProgressIndicator(
            value: (pct / 100).clamp(0.0, 1.0).toDouble(),
            minHeight: 9,
            backgroundColor: Colors.white.withValues(alpha: 0.06),
            color: over ? AppColors.danger : AppColors.primary,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
            'الميزانية محسوبة من متوسط إنفاقك والتزاماتك — المدخرات لا تُحتسب ضمن الصرف.',
            style: TextStyle(
                color: AppColors.textMuted, fontSize: 12, height: 1.6)),
      ]),
    );
  }
}

class _Trajectory extends StatelessWidget {
  final Map<String, dynamic> trajectory;
  const _Trajectory({required this.trajectory});

  @override
  Widget build(BuildContext context) {
    final categories =
        (trajectory['categories'] as List).cast<Map<String, dynamic>>();
    final payments =
        (trajectory['upcoming_payments'] as List).cast<Map<String, dynamic>>();
    final trough = trajectory['projected_trough'] as Map<String, dynamic>?;
    return SectionCard(
      title: 'الأرقام خلف النتيجة',
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('معادلة الرصيد المتوقع',
            style: TextStyle(fontWeight: FontWeight.w900)),
        const SizedBox(height: 8),
        _EquationRow(
            label: 'الرصيد المتاح الآن',
            value: trajectory['balance_now'],
            operator: ''),
        _EquationRow(
            label: 'راتب متوقع قبل نهاية الشهر',
            value: trajectory['pending_salary_amount'],
            operator: '+'),
        _EquationRow(
            label: 'صرف مرن متوقع للأيام المتبقية',
            value: trajectory['projected_flexible_remaining'],
            operator: '−'),
        _EquationRow(
            label: 'التزامات قادمة',
            value: trajectory['upcoming_commitments_total'],
            operator: '−'),
        const Divider(height: 18),
        _EquationRow(
            label: 'الرصيد المتوقع نهاية الشهر',
            value: trajectory['projected_eom_balance'],
            operator: '=',
            strong: true),
        const SizedBox(height: 14),
        Wrap(spacing: 8, runSpacing: 8, children: [
          Pill('الصرف اليومي: ${sar(trajectory['daily_flexible_pace'])}',
              color: AppColors.accent),
          if (trough != null && (trough['amount'] as num) < 0)
            Pill('أدنى نقطة: ${sar(trough['amount'])} في ${trough['date']}',
                color: AppColors.danger),
          if (trajectory['expected_salary_day'] != null)
            Pill('الراتب متوقع يوم ${trajectory['expected_salary_day']}',
                color: AppColors.accent),
        ]),
        const SizedBox(height: 16),
        const Text('تصنيف الإنفاق من وصف المعاملة',
            style: TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text(
            'أنظمة الذكاء الاصطناعي استنتجت الفئة من اسم التاجر والوصف وقناة الدفع؛ الحسابات أعلاه حتمية.',
            style: TextStyle(
                color: AppColors.textMuted, fontSize: 12, height: 1.6)),
        const SizedBox(height: 8),
        ...categories.take(6).map((c) {
          final dev = (c['deviation_pct'] as num).toInt();
          final devColor = dev > 20
              ? AppColors.danger
              : (dev < -20 ? AppColors.primary : AppColors.textMuted);
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Row(children: [
              Expanded(flex: 3, child: Text('${c['label_ar']}')),
              Expanded(
                  flex: 2,
                  child: Text(sar(c['mtd']),
                      style: const TextStyle(color: AppColors.textMuted))),
              Expanded(
                  flex: 2,
                  child: Text(sar(c['baseline_mtd']),
                      style: const TextStyle(color: AppColors.textMuted))),
              SizedBox(
                  width: 56,
                  child: Text('${dev > 0 ? '+' : ''}$dev%',
                      textAlign: TextAlign.end,
                      style: TextStyle(
                          color: devColor, fontWeight: FontWeight.w900))),
            ]),
          );
        }),
        if (payments.isNotEmpty) ...[
          const SizedBox(height: 14),
          const Text('الالتزامات القادمة هذا الشهر',
              style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          ...payments.map((p) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Text(
                    'يوم ${p['day']}: ${p['label']} — ${sar(p['amount'])}',
                    style: const TextStyle(color: AppColors.textMuted)),
              )),
        ],
      ]),
    );
  }
}

class _EquationRow extends StatelessWidget {
  final String label;
  final num? value;
  final String operator;
  final bool strong;
  const _EquationRow({
    required this.label,
    required this.value,
    required this.operator,
    this.strong = false,
  });

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
      fontWeight: strong ? FontWeight.w900 : FontWeight.w600,
      color: strong ? AppColors.primary : null,
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        SizedBox(
            width: 18,
            child: Text(operator, style: style, textAlign: TextAlign.center)),
        const SizedBox(width: 6),
        Expanded(child: Text(label, style: style)),
        Text(sar(value), style: style),
      ]),
    );
  }
}

class _PastAlerts extends StatelessWidget {
  final List<dynamic> alerts;
  const _PastAlerts({required this.alerts});
  @override
  Widget build(BuildContext context) {
    if (alerts.isEmpty) return const SizedBox.shrink();
    return SectionCard(
      title: 'تنبيهات سابقة',
      child: Column(
        children: alerts.map((raw) {
          final a = raw as Map<String, dynamic>;
          final isOverspend = a['alert_type'] == 'overspend';
          final color = isOverspend ? AppColors.warn : AppColors.danger;
          return Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.03),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.border),
            ),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text(sar(a['gap_amount']),
                    style:
                        TextStyle(color: color, fontWeight: FontWeight.w900)),
                const SizedBox(width: 8),
                Pill(isOverspend ? 'تجاوز ميزانية' : 'قسط في خطر',
                    color: color),
              ]),
              const SizedBox(height: 6),
              Text('${a['message_ar']}',
                  style:
                      const TextStyle(color: AppColors.textMuted, height: 1.6)),
            ]),
          );
        }).toList(),
      ),
    );
  }
}

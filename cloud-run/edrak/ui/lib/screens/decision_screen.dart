import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/bank_panel.dart';
import '../widgets/forecast_chart.dart';
// import '../widgets/step_trace.dart';  // مسار المعالجة — hidden for now
import '../widgets/widgets.dart';

const _goalTypes = {
  'car': 'تمويل سيارة',
  'home': 'التزام سكني',
  'wedding': 'مصاريف زواج',
  'travel': 'سفر',
  'debt': 'سداد دين',
  'emergency': 'تمويل طارئ',
};

const _steps = [
  'التحقق من اكتمال البيانات عبر البنوك',
  'كشف الالتزامات المتكررة وتصنيفها',
  'محاكاة التدفق النقدي 12 شهرًا',
  'تطبيق قواعد القرار وتقدير المخاطر',
  'كتابة التوصية والبدائل',
];

class DecisionScreen extends StatefulWidget {
  final Customer customer;
  const DecisionScreen({super.key, required this.customer});
  @override
  State<DecisionScreen> createState() => _DecisionScreenState();
}

class _DecisionScreenState extends State<DecisionScreen> {
  String _goalType = 'car';
  final _amount = TextEditingController(text: '120000');
  final _installment = TextEditingController(text: '2500');
  final _duration = TextEditingController(text: '48');
  final _downPayment = TextEditingController(text: '10000');
  bool _loading = false;
  Map<String, dynamic>? _result;

  Future<void> _submit() async {
    setState(() {
      _loading = true;
      _result = null;
    });
    try {
      // The smart validator (deterministic logic + the AI sufficiency judgment)
      // runs BEFORE the analysis: if it suspects activity at unlinked banks, the
      // user sees the findings and chooses whether to proceed.
      final coverage = await Api.coverageDeep(widget.customer.customerId);
      final findings = ((coverage['findings'] ?? []) as List).cast<Map<String, dynamic>>();
      if ((coverage['status'] != 'كافية' || findings.isNotEmpty) && mounted) {
        final proceed = await _confirmPartial(coverage, findings);
        if (!proceed) {
          setState(() => _loading = false);
          return;
        }
      }
      final result = await Api.analyze(widget.customer.customerId, {
        'goal_type': _goalType,
        'goal_amount': num.tryParse(_amount.text) ?? 0,
        'monthly_installment': num.tryParse(_installment.text) ?? 0,
        'duration_months': int.tryParse(_duration.text) ?? 12,
        'down_payment': num.tryParse(_downPayment.text) ?? 0,
      });
      setState(() => _result = result);
    } catch (e) {
      if (mounted) showError(context, e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// The dismissible notification block: what the validator noticed, and whether
  /// to continue anyway. AI findings carry the ذكاء اصطناعي badge.
  Future<bool> _confirmPartial(
      Map<String, dynamic> coverage, List<Map<String, dynamic>> findings) async {
    return await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            backgroundColor: AppColors.surface,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: Row(children: [
              const Icon(Icons.auto_awesome, color: AppColors.ai, size: 20),
              const SizedBox(width: 8),
              const Expanded(child: Text('لاحظنا شيئًا قبل التحليل')),
              IconButton(
                icon: const Icon(Icons.close, size: 20, color: AppColors.textMuted),
                onPressed: () => Navigator.pop(context, false),
              ),
            ]),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ...findings.map((f) {
                    final isAi = f['code'] == 'llm_sufficiency';
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Icon(isAi ? Icons.auto_awesome : Icons.info_outline,
                            size: 16, color: isAi ? AppColors.ai : AppColors.warn),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            if (isAi)
                              const Padding(
                                  padding: EdgeInsets.only(bottom: 4), child: AiBadge()),
                            Text(f['message_ar'] as String,
                                style: const TextStyle(
                                    color: AppColors.textMuted, height: 1.7, fontSize: 13.5)),
                          ]),
                        ),
                      ]),
                    );
                  }),
                  const SizedBox(height: 6),
                  const Text('هل تود المتابعة بالبيانات الحالية؟',
                      style: TextStyle(fontWeight: FontWeight.w800)),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('ربط الحسابات أولًا'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('متابعة', style: TextStyle(color: AppColors.warn)),
              ),
            ],
          ),
        ) ??
        false;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('حزام الأمان المالي', style: TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SectionCard(
            title: 'تفاصيل القرار',
            child: Column(children: [
              _dropdown(),
              _numField('مبلغ الهدف', _amount),
              _numField('القسط الشهري المتوقع', _installment),
              _numField('مدة الالتزام بالأشهر', _duration),
              _numField('الدفعة المقدمة', _downPayment),
              const SizedBox(height: 8),
              PrimaryButton('حلّل القرار', loading: _loading, onPressed: _submit),
            ]),
          ),
          if (_loading) LoadingPanel(title: 'جاري تحليل القرار عبر بنوكك', steps: _steps),
          if (!_loading && _result != null) _Results(result: _result!),
        ],
      ),
    );
  }

  Widget _dropdown() => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('نوع الهدف', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: AppColors.surfaceAlt,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _goalType,
                isExpanded: true,
                dropdownColor: AppColors.surfaceAlt,
                items: _goalTypes.entries
                    .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                    .toList(),
                onChanged: (v) => setState(() => _goalType = v!),
              ),
            ),
          ),
        ]),
      );

  Widget _numField(String label, TextEditingController controller) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          TextField(
            controller: controller,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              filled: true,
              fillColor: AppColors.surfaceAlt,
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: AppColors.border),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: AppColors.primary),
              ),
            ),
          ),
        ]),
      );
}

class _Results extends StatelessWidget {
  final Map<String, dynamic> result;
  const _Results({required this.result});

  @override
  Widget build(BuildContext context) {
    final forecast = result['forecast'] as Map<String, dynamic>;
    final verdict = result['recommendation'] as String;
    final color = verdictColor(verdict);
    final ready = result['ready_in_months'];
    final readiness = ready != null
        ? 'جاهز بعد $ready شهر'
        : (verdict == 'غير مناسب' ? 'غير قابل للتأجيل' : 'جاهز الآن');
    final profile = result['profile'] as Map<String, dynamic>;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Hero verdict card.
        Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 14),
          padding: const EdgeInsets.all(22),
          decoration: heroDecoration(color),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text(verdict,
                  style: TextStyle(
                      fontSize: 26, fontWeight: FontWeight.w900, color: color,
                      shadows: [Shadow(color: color.withOpacity(0.5), blurRadius: 18)])),
              const Spacer(),
              Pill(readiness, color: color, solid: true),
            ]),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: Metric('احتمالية التعثر',
                  '${((result['risk_probability'] as num) * 100).round()}%', color: color)),
              const SizedBox(width: 10),
              Expanded(child: Metric('أدنى فائض شهري', sar(forecast['min_buffer_value']),
                  color: (forecast['min_buffer_value'] as num) < 0 ? AppColors.danger : AppColors.primary)),
            ]),
            const SizedBox(height: 14),
            Text(result['explanation_ar'] as String, style: const TextStyle(height: 1.9, fontSize: 14.5)),
          ]),
        ),
        ForecastChart(forecast: forecast),
        BankPanel(byBank: (result['detected_obligations_by_bank'] as Map).cast<String, dynamic>()),
        SectionCard(
          title: 'ملفك المالي عبر البنوك',
          child: Wrap(spacing: 10, runSpacing: 10, children: [
            _profileMetric('الراتب', sar(profile['salary'])),
            _profileMetric('إجمالي الأرصدة', sar(profile['total_balance'])),
            _profileMetric('عدد البنوك', '${profile['banks_count']}'),
            _profileMetric('أقساط القروض', sar(profile['monthly_loan_installments'])),
            _profileMetric('متوسط الصرف', sar(profile['avg_monthly_spending'])),
            _profileMetric('الإنفاق المرن', sar(profile['avg_flexible_spending'])),
          ]),
        ),
        BulletList('عوامل المخاطر', _stringList(result['risk_factors_ar']), accent: AppColors.warn),
        BulletList('بدائل أكثر أمانًا', _stringList(result['safer_options_ar'])),
        BulletList('تنبيهات التحقق', _stringList(result['validation_warnings_ar']), accent: AppColors.warn),
        // مسار المعالجة — kept in code, hidden for now; re-enable if wanted later:
        // StepTrace(steps: (result['step_trace'] as List)),
      ],
    );
  }

  Widget _profileMetric(String label, String value) =>
      SizedBox(width: 150, child: Metric(label, value));

  List<String> _stringList(dynamic v) => (v as List? ?? []).map((e) => e.toString()).toList();
}

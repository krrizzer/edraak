-- BigQuery Standard SQL
-- Edraak synthetic sample data for prototype demos.

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change edraak_finance if you use a different dataset name.

INSERT INTO `YOUR_PROJECT_ID.edraak_finance.customer_profiles` (
  user_id,
  name_ar,
  customer_type,
  monthly_income,
  current_balance,
  savings,
  monthly_obligations,
  avg_flexible_spending,
  risk_preference_ar,
  behavior_summary_ar,
  created_at
)
VALUES
  (
    'stable',
    'سارة العميلة المستقرة',
    'stable_customer',
    18000,
    42000,
    65000,
    4200,
    3200,
    'حذرة ومتوازنة',
    'دخل ثابت، التزامات منخفضة، وادخار شهري منتظم.',
    CURRENT_TIMESTAMP()
  ),
  (
    'overcommitted',
    'خالد الملتزم بأقساط عالية',
    'overcommitted_customer',
    14500,
    8500,
    12000,
    8200,
    3000,
    'يميل لاتخاذ قرارات سريعة',
    'نسبة الالتزامات مرتفعة والمرونة الشهرية محدودة.',
    CURRENT_TIMESTAMP()
  ),
  (
    'high_spender',
    'نورة ذات الدخل العالي والإنفاق العالي',
    'high_income_high_spending',
    32000,
    26000,
    48000,
    9300,
    9700,
    'مرنة وتقبل المخاطرة المحسوبة',
    'دخل عال لكن الإنفاق المرن يستهلك جزءا كبيرا من الفائض.',
    CURRENT_TIMESTAMP()
  );

INSERT INTO `YOUR_PROJECT_ID.edraak_finance.transactions` (
  transaction_id,
  user_id,
  transaction_date,
  merchant,
  category,
  amount,
  transaction_type,
  is_recurring,
  created_at
)
VALUES
  ('txn_001', 'stable', DATE '2026-06-01', 'جهة العمل', 'salary', 18000, 'income', TRUE, CURRENT_TIMESTAMP()),
  ('txn_002', 'stable', DATE '2026-06-03', 'مالك العقار', 'rent', -4200, 'expense', TRUE, CURRENT_TIMESTAMP()),
  ('txn_003', 'stable', DATE '2026-06-07', 'سوبرماركت', 'groceries', -850, 'expense', FALSE, CURRENT_TIMESTAMP()),
  ('txn_004', 'stable', DATE '2026-06-12', 'حساب الادخار', 'transfer', -3500, 'transfer', TRUE, CURRENT_TIMESTAMP()),
  ('txn_005', 'overcommitted', DATE '2026-06-01', 'جهة العمل', 'salary', 14500, 'income', TRUE, CURRENT_TIMESTAMP()),
  ('txn_006', 'overcommitted', DATE '2026-06-02', 'مالك العقار', 'rent', -4800, 'expense', TRUE, CURRENT_TIMESTAMP()),
  ('txn_007', 'overcommitted', DATE '2026-06-05', 'مزود تمويل', 'BNPL payment', -1600, 'expense', TRUE, CURRENT_TIMESTAMP()),
  ('txn_008', 'overcommitted', DATE '2026-06-10', 'محطة وقود', 'transport/fuel', -650, 'expense', FALSE, CURRENT_TIMESTAMP()),
  ('txn_009', 'high_spender', DATE '2026-06-08', 'مطعم', 'restaurants', -1800, 'expense', FALSE, CURRENT_TIMESTAMP()),
  ('txn_010', 'high_spender', DATE '2026-06-14', 'متجر إلكتروني', 'shopping', -4200, 'expense', FALSE, CURRENT_TIMESTAMP()),
  ('txn_011', 'high_spender', DATE '2026-06-20', 'اشتراكات رقمية', 'subscriptions', -390, 'expense', TRUE, CURRENT_TIMESTAMP()),
  ('txn_012', 'overcommitted', DATE '2026-06-24', 'عيادة طبية', 'emergency expense', -2200, 'expense', FALSE, CURRENT_TIMESTAMP());

INSERT INTO `YOUR_PROJECT_ID.edraak_finance.decision_requests` (
  request_id,
  user_id,
  goal_type,
  goal_amount,
  monthly_installment,
  duration_months,
  down_payment,
  urgency,
  created_at
)
VALUES
  ('req_001', 'stable', 'car_financing', 120000, 2500, 48, 10000, 'medium', CURRENT_TIMESTAMP()),
  ('req_002', 'overcommitted', 'wedding_expense', 90000, 3500, 24, 5000, 'high', CURRENT_TIMESTAMP()),
  ('req_003', 'high_spender', 'travel', 35000, 2200, 12, 8000, 'low', CURRENT_TIMESTAMP()),
  ('req_004', 'overcommitted', 'emergency_financing', 25000, 1800, 18, 0, 'high', CURRENT_TIMESTAMP());

INSERT INTO `YOUR_PROJECT_ID.edraak_finance.recommendations` (
  recommendation_id,
  request_id,
  user_id,
  recommendation,
  risk_score,
  safety_score,
  obligation_ratio_before,
  obligation_ratio_after,
  monthly_buffer_after,
  financial_seatbelt_status,
  explanation_ar,
  risk_factors_json,
  safer_options_json,
  readiness_path_json,
  agent_trace_json,
  created_at
)
VALUES
  (
    'rec_001',
    'req_001',
    'stable',
    'Proceed',
    28,
    72,
    23,
    37,
    8100,
    'مفعل',
    'القرار يبدو قابلا للتنفيذ لأن الدخل مستقر والفائض الشهري يبقى مريحا بعد القسط.',
    '["نسبة الالتزامات ترتفع لكنها تبقى ضمن مستوى مقبول"]',
    '["الحفاظ على الدفعة المقدمة", "مراجعة عروض التمويل قبل التوقيع"]',
    '{"30_days":["مقارنة عروض التمويل"],"60_days":["تأكيد القسط النهائي"],"90_days":["إعادة فحص الفائض بعد أول شهر"]}',
    '[{"agent":"وكيل الملف المالي","status":"اكتمل"},{"agent":"وكيل التوصية","status":"اكتمل"}]',
    CURRENT_TIMESTAMP()
  ),
  (
    'rec_002',
    'req_003',
    'high_spender',
    'Caution',
    52,
    48,
    29,
    36,
    10800,
    'مفعل',
    'الدخل عال والفائض موجود، لكن الإنفاق المرن المرتفع يستدعي الحذر قبل إضافة التزام جديد.',
    '["الإنفاق المرن مرتفع", "الادخار لا ينمو بما يتناسب مع الدخل"]',
    '["خفض ميزانية السفر", "تجميد بعض الإنفاق الترفيهي لمدة شهرين"]',
    '{"30_days":["تحديد سقف إنفاق للسفر"],"60_days":["زيادة الادخار"],"90_days":["إعادة تشغيل التحليل"]}',
    '[{"agent":"وكيل المخاطر","status":"اكتمل"},{"agent":"وكيل البدائل","status":"اكتمل"}]',
    CURRENT_TIMESTAMP()
  ),
  (
    'rec_003',
    'req_002',
    'overcommitted',
    'Delay',
    73,
    27,
    57,
    81,
    -200,
    'مفعل',
    'يفضل تأجيل القرار لأن الالتزامات الحالية عالية والقسط المقترح سيضغط الفائض الشهري.',
    '["نسبة الالتزامات بعد القرار مرتفعة", "الفائض الشهري قريب من الصفر", "المدخرات محدودة"]',
    '["تقليل مبلغ الهدف", "زيادة الدفعة المقدمة", "تأجيل القرار 90 يوما"]',
    '{"30_days":["خفض المصروفات غير الضرورية"],"60_days":["سداد جزء من الالتزامات"],"90_days":["إعادة تقييم القرار"]}',
    '[{"agent":"وكيل الملف المالي","status":"اكتمل"},{"agent":"وكيل المخاطر","status":"اكتمل"},{"agent":"وكيل التوصية","status":"اكتمل"}]',
    CURRENT_TIMESTAMP()
  ),
  (
    'rec_004',
    'req_004',
    'overcommitted',
    'Avoid',
    88,
    12,
    57,
    69,
    -2500,
    'مفعل',
    'ينبغي تجنب التمويل الإضافي حاليا لأن الفائض الشهري يصبح سلبيا بعد الالتزام الجديد.',
    '["فائض شهري سلبي", "التزامات مرتفعة", "حاجة طارئة قد تتطلب حلا أقل تكلفة"]',
    '["البحث عن دعم بدون فوائد", "إعادة جدولة الالتزامات الحالية", "تقليل مبلغ التمويل"]',
    '{"30_days":["تحديد المصروفات الطارئة الأساسية"],"60_days":["التفاوض على الالتزامات القائمة"],"90_days":["بناء احتياطي طوارئ صغير"]}',
    '[{"agent":"وكيل المخاطر","status":"اكتمل"},{"agent":"وكيل البدائل","status":"اكتمل"},{"agent":"وكيل التوصية","status":"اكتمل"}]',
    CURRENT_TIMESTAMP()
  );

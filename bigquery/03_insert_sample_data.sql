-- BigQuery Standard SQL
-- Edraak realistic synthetic sample data for prototype demos.

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change edraak_finance if you use a different dataset name.

-- Source banking customers. All values are synthetic.
INSERT INTO `YOUR_PROJECT_ID.edraak_finance.customers` (
  customer_id,
  username_en,
  ar_name,
  en_name,
  national_id,
  birthday,
  salary,
  current_balance,
  city,
  employment_sector,
  employer_name,
  account_open_date,
  created_at
)
VALUES
  (
    'CUST001',
    'fahad',
    'فهد العتيبي',
    'Fahad Alotaibi',
    '1000000001',
    DATE '1990-04-12',
    16500,
    28500,
    'Riyadh',
    'Private',
    'Najd Logistics Co.',
    DATE '2018-09-16',
    TIMESTAMP '2026-07-01 09:00:00+03'
  ),
  (
    'CUST002',
    'sara',
    'سارة الحربي',
    'Sara Alharbi',
    '1000000002',
    DATE '1988-11-20',
    22000,
    76000,
    'Jeddah',
    'Government',
    'Ministry Entity',
    DATE '2016-03-03',
    TIMESTAMP '2026-07-01 09:00:00+03'
  ),
  (
    'CUST003',
    'khalid',
    'خالد الشهري',
    'Khalid Alshehri',
    '1000000003',
    DATE '1994-02-05',
    14500,
    9200,
    'Dammam',
    'Private',
    'Eastern Services Ltd.',
    DATE '2020-01-22',
    TIMESTAMP '2026-07-01 09:00:00+03'
  );

-- Transactions use positive amounts for income and negative amounts for money leaving the account.
INSERT INTO `YOUR_PROJECT_ID.edraak_finance.transactions` (
  transaction_id,
  customer_id,
  transaction_date,
  merchant,
  category,
  amount,
  transaction_type,
  is_recurring,
  channel,
  created_at
)
VALUES
  ('TXN001', 'CUST001', DATE '2026-06-27', 'Najd Logistics Co.', 'salary', 16500, 'income', TRUE, 'bank_transfer', TIMESTAMP '2026-06-27 08:30:00+03'),
  ('TXN002', 'CUST001', DATE '2026-06-28', 'Riyadh Apartment Rent', 'rent', -4200, 'expense', TRUE, 'standing_order', TIMESTAMP '2026-06-28 10:00:00+03'),
  ('TXN003', 'CUST001', DATE '2026-06-29', 'Danube', 'groceries', -780, 'expense', FALSE, 'pos', TIMESTAMP '2026-06-29 19:40:00+03'),
  ('TXN004', 'CUST001', DATE '2026-06-30', 'Fuel Station', 'transport', -510, 'expense', FALSE, 'pos', TIMESTAMP '2026-06-30 17:25:00+03'),
  ('TXN005', 'CUST001', DATE '2026-07-01', 'Restaurant', 'restaurants', -420, 'expense', FALSE, 'pos', TIMESTAMP '2026-07-01 21:10:00+03'),
  ('TXN006', 'CUST001', DATE '2026-07-02', 'STC Pay', 'transfer', -1000, 'transfer', FALSE, 'mobile', TIMESTAMP '2026-07-02 12:30:00+03'),

  ('TXN007', 'CUST002', DATE '2026-06-25', 'Government Payroll', 'salary', 22000, 'income', TRUE, 'bank_transfer', TIMESTAMP '2026-06-25 08:00:00+03'),
  ('TXN008', 'CUST002', DATE '2026-06-26', 'Utilities Provider', 'utilities', -700, 'expense', TRUE, 'sadad', TIMESTAMP '2026-06-26 09:20:00+03'),
  ('TXN009', 'CUST002', DATE '2026-06-27', 'Savings Account', 'transfer', -4500, 'transfer', TRUE, 'standing_order', TIMESTAMP '2026-06-27 09:05:00+03'),
  ('TXN010', 'CUST002', DATE '2026-06-28', 'Tamimi Markets', 'groceries', -1150, 'expense', FALSE, 'pos', TIMESTAMP '2026-06-28 18:40:00+03'),
  ('TXN011', 'CUST002', DATE '2026-06-29', 'Digital Subscriptions', 'subscriptions', -390, 'expense', TRUE, 'card', TIMESTAMP '2026-06-29 03:00:00+03'),
  ('TXN012', 'CUST002', DATE '2026-07-01', 'Mall Store', 'shopping', -1800, 'expense', FALSE, 'pos', TIMESTAMP '2026-07-01 20:15:00+03'),

  ('TXN013', 'CUST003', DATE '2026-06-25', 'Eastern Services Ltd.', 'salary', 14500, 'income', TRUE, 'bank_transfer', TIMESTAMP '2026-06-25 08:15:00+03'),
  ('TXN014', 'CUST003', DATE '2026-06-26', 'Dammam Apartment Rent', 'rent', -4800, 'expense', TRUE, 'standing_order', TIMESTAMP '2026-06-26 10:00:00+03'),
  ('TXN015', 'CUST003', DATE '2026-06-27', 'BNPL Provider', 'bnpl', -1400, 'expense', TRUE, 'card', TIMESTAMP '2026-06-27 12:00:00+03'),
  ('TXN016', 'CUST003', DATE '2026-06-28', 'Hypermarket', 'groceries', -1250, 'expense', FALSE, 'pos', TIMESTAMP '2026-06-28 19:00:00+03'),
  ('TXN017', 'CUST003', DATE '2026-06-30', 'Clinic', 'emergency', -2300, 'expense', FALSE, 'pos', TIMESTAMP '2026-06-30 16:20:00+03'),
  ('TXN018', 'CUST003', DATE '2026-07-01', 'Restaurant', 'restaurants', -680, 'expense', FALSE, 'pos', TIMESTAMP '2026-07-01 22:35:00+03');

-- Loan totals are explicit for readability: total_amount = loan_total_amount + total_profit_amount.
INSERT INTO `YOUR_PROJECT_ID.edraak_finance.loans` (
  loan_id,
  customer_id,
  loan_type,
  loan_total_amount,
  total_profit_amount,
  total_amount,
  remaining_amount,
  monthly_installment,
  start_date,
  end_date,
  status,
  created_at
)
VALUES
  ('LOAN001', 'CUST001', 'car', 90000, 18000, 108000, 65000, 2300, DATE '2024-01-01', DATE '2028-01-01', 'active', TIMESTAMP '2024-01-01 09:00:00+03'),
  ('LOAN002', 'CUST002', 'home', 450000, 135000, 585000, 390000, 5200, DATE '2022-05-01', DATE '2032-05-01', 'active', TIMESTAMP '2022-05-01 09:00:00+03'),
  ('LOAN003', 'CUST003', 'personal_finance', 70000, 14000, 84000, 58000, 3100, DATE '2025-03-01', DATE '2028-03-01', 'active', TIMESTAMP '2025-03-01 09:00:00+03'),
  ('LOAN004', 'CUST003', 'closed_car', 52000, 8000, 60000, 0, 0, DATE '2021-01-01', DATE '2024-01-01', 'closed', TIMESTAMP '2021-01-01 09:00:00+03');

-- Derived profiles. In the app, these are generated from customers + transactions + loans.
INSERT INTO `YOUR_PROJECT_ID.edraak_finance.user_profiles` (
  customer_id,
  ar_name,
  en_name,
  salary,
  current_balance,
  active_loans_count,
  total_remaining_loans,
  monthly_loan_installments,
  avg_monthly_spending,
  avg_flexible_spending,
  recurring_obligations,
  savings_estimate,
  obligation_ratio,
  spending_behavior_summary_ar,
  risk_preference_estimate_ar,
  profile_generated_at
)
VALUES
  ('CUST001', 'فهد العتيبي', 'Fahad Alotaibi', 16500, 28500, 1, 65000, 2300, 5910, 420, 6500, 22000, 39, 'التزامات فهد تحت السيطرة نسبيا، لكن قرض السيارة الحالي يحد من مرونة إضافة قسط جديد.', 'حذر ومتوازن', TIMESTAMP '2026-07-02 10:00:00+03'),
  ('CUST002', 'سارة الحربي', 'Sara Alharbi', 22000, 76000, 1, 390000, 5200, 8040, 2190, 6290, 69710, 29, 'سارة لديها دخل قوي وادخار جيد، مع التزام سكني طويل الأجل يجب أخذه في الحسبان.', 'حذرة ومنظمة', TIMESTAMP '2026-07-02 10:00:00+03'),
  ('CUST003', 'خالد الشهري', 'Khalid Alshehri', 14500, 9200, 1, 58000, 3100, 10430, 2080, 9300, 0, 64, 'خالد لديه ضغط التزامات مرتفع وفائض محدود، وأي قسط جديد قد يرفع المخاطر بسرعة.', 'حذر جدا', TIMESTAMP '2026-07-02 10:00:00+03');

INSERT INTO `YOUR_PROJECT_ID.edraak_finance.decision_requests` (
  request_id,
  customer_id,
  goal_type,
  goal_amount,
  monthly_installment,
  duration_months,
  down_payment,
  urgency,
  created_at
)
VALUES
  ('REQ001', 'CUST001', 'car', 120000, 2500, 48, 10000, 'medium', TIMESTAMP '2026-07-02 11:00:00+03'),
  ('REQ002', 'CUST002', 'travel', 35000, 1800, 12, 8000, 'low', TIMESTAMP '2026-07-02 11:05:00+03'),
  ('REQ003', 'CUST003', 'wedding', 90000, 3500, 24, 5000, 'high', TIMESTAMP '2026-07-02 11:10:00+03'),
  ('REQ004', 'CUST003', 'emergency', 25000, 1800, 18, 0, 'high', TIMESTAMP '2026-07-02 11:15:00+03');

INSERT INTO `YOUR_PROJECT_ID.edraak_finance.recommendations` (
  recommendation_id,
  request_id,
  customer_id,
  recommendation,
  risk_score,
  safety_score,
  obligation_ratio_before,
  obligation_ratio_after,
  monthly_buffer_after,
  financial_seatbelt_status,
  confidence,
  validation_warnings_json,
  explanation_ar,
  risk_factors_json,
  safer_options_json,
  readiness_path_json,
  agent_trace_json,
  created_at
)
VALUES
  (
    'REC001',
    'REQ002',
    'CUST002',
    'المضي قدمًا',
    32,
    68,
    29,
    37,
    7700,
    'مفعّل',
    'عالية',
    '[]',
    'التوصية هي المضي قدمًا. الراتب الشهري 22,000 ريال، ونسبة الالتزامات سترتفع من 29% إلى 37%، مع بقاء فائض شهري متوقع قدره 7,700 ريال.',
    '["الالتزام السكني طويل الأجل قائم لكنه مستقر", "الفائض الشهري بعد القرار يبقى مريحا"]',
    '["الحفاظ على الدفعة المقدمة", "تحديد سقف واضح لمصاريف السفر"]',
    '{"30_days":["تأكيد تكلفة السفر الفعلية"],"60_days":["مراجعة الفائض بعد الحجز"],"90_days":["تحديث الادخار بعد العودة"]}',
    '[{"agent":"وكيل التحقق من البيانات","status":"اكتمل"},{"agent":"وكيل التوصية","status":"اكتمل"}]',
    TIMESTAMP '2026-07-02 11:20:00+03'
  ),
  (
    'REC002',
    'REQ001',
    'CUST001',
    'الحذر',
    45,
    55,
    39,
    55,
    6780,
    'مفعّل',
    'عالية',
    '[]',
    'التوصية هي الحذر. الراتب الشهري 16,500 ريال، وبعد إضافة قسط 2,500 ريال سترتفع نسبة الالتزامات إلى 55%، مع فائض شهري متوقع قدره 6,780 ريال.',
    '["لدى العميل قرض سيارة قائم", "نسبة الالتزامات بعد القرار تصل إلى مستوى يحتاج متابعة"]',
    '["خفض مبلغ السيارة", "زيادة الدفعة المقدمة", "استهداف قسط أقل من 1,900 ريال"]',
    '{"30_days":["مقارنة عروض التمويل"],"60_days":["رفع الدفعة المقدمة"],"90_days":["إعادة التحليل بعد تقليل القسط"]}',
    '[{"agent":"وكيل التحقق من البيانات","status":"اكتمل"},{"agent":"وكيل مخاطر الالتزامات","status":"اكتمل"},{"agent":"وكيل التوصية","status":"اكتمل"}]',
    TIMESTAMP '2026-07-02 11:25:00+03'
  ),
  (
    'REC003',
    'REQ003',
    'CUST003',
    'التأجيل',
    78,
    22,
    64,
    88,
    -380,
    'مفعّل',
    'متوسطة',
    '["الفائض الشهري محدود", "الالتزامات الحالية مرتفعة"]',
    'التوصية هي التأجيل. الالتزامات الحالية تمثل 64% من الراتب، وبعد القسط الجديد سترتفع إلى 88% مع فائض شهري سلبي.',
    '["نسبة الالتزامات مرتفعة جدا", "المدخرات المقدرة ضعيفة", "درجة الاستعجال عالية"]',
    '["خفض مبلغ الهدف", "تأجيل القرار 90 يوما", "تقليل الإنفاق المرن", "إعادة هيكلة الالتزامات الحالية"]',
    '{"30_days":["خفض المصروفات غير الضرورية"],"60_days":["سداد جزء من الالتزامات"],"90_days":["إعادة تقييم القرار"]}',
    '[{"agent":"وكيل التحقق من البيانات","status":"اكتمل"},{"agent":"وكيل بناء الملف المالي","status":"اكتمل"},{"agent":"وكيل مخاطر الالتزامات","status":"اكتمل"},{"agent":"وكيل التوصية","status":"اكتمل"}]',
    TIMESTAMP '2026-07-02 11:30:00+03'
  ),
  (
    'REC004',
    'REQ004',
    'CUST003',
    'التجنّب',
    88,
    12,
    64,
    77,
    -2180,
    'مفعّل',
    'متوسطة',
    '["الحاجة طارئة لكن القدرة الشهرية ضعيفة"]',
    'التوصية هي التجنّب حاليا. إضافة قسط 1,800 ريال تجعل الفائض الشهري سالبا، والعميل لديه التزامات نشطة مرتفعة.',
    '["فائض شهري سلبي", "قرض شخصي نشط", "رصيد حالي منخفض مقارنة بالالتزامات"]',
    '["البحث عن دعم أقل تكلفة", "تقليل مبلغ التمويل", "إعادة جدولة القرض الشخصي", "بناء احتياطي طوارئ صغير أولا"]',
    '{"30_days":["تحديد المصروف الطارئ الأساسي فقط"],"60_days":["التفاوض على الالتزامات القائمة"],"90_days":["إعادة التحليل بعد تحسن الرصيد"]}',
    '[{"agent":"وكيل التحقق من البيانات","status":"اكتمل"},{"agent":"وكيل البدائل","status":"اكتمل"},{"agent":"وكيل التوصية","status":"اكتمل"}]',
    TIMESTAMP '2026-07-02 11:35:00+03'
  );

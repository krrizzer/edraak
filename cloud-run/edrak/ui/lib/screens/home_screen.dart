import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../navigation.dart';
import '../theme.dart';
import '../widgets/widgets.dart';
import 'decision_screen.dart';
import 'link_banks_screen.dart';
import 'login_screen.dart';
import 'radar_screen.dart';

class HomeScreen extends StatefulWidget {
  final Customer customer;
  const HomeScreen({super.key, required this.customer});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _connectedBanks = 1;
  bool _resettingDemo = false;
  bool _assetsPrecached = false;
  Map<String, dynamic>? _coverage;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_assetsPrecached) return;
    _assetsPrecached = true;
    for (final code in bankNamesAr.keys) {
      precacheImage(AssetImage('assets/icons/$code.png'), context);
    }
  }

  Future<void> _refresh() async {
    try {
      final c = await Api.coverage(widget.customer.customerId);
      if (mounted) {
        setState(() {
          _coverage = c;
          _connectedBanks = (c['connected_banks'] as List).length;
        });
      }
    } catch (_) {/* count is cosmetic on this screen */}
  }

  Future<void> _openLinkScreen() async {
    await Navigator.of(context).push(appRoute(
      builder: (_) => LinkBanksScreen(
        customer: widget.customer,
        initialCoverage: _coverage,
      ),
    ));
    _refresh();
  }

  void _logout() {
    Navigator.of(context)
        .pushReplacement(appRoute(builder: (_) => const LoginScreen()));
  }

  Future<void> _showDemoReset() async {
    if (_resettingDemo) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('إعادة ضبط العرض؟'),
        content: const Text(
          'سيتم فصل جميع البنوك الخارجية ومسح نتائج التحليل والتنبيهات لهذا المستخدم، ثم إعادة بيانات بنك الإنماء الأساسية.',
          style: TextStyle(height: 1.7),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('إلغاء')),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('إعادة الضبط'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _resettingDemo = true);
    try {
      await Api.demoReset(widget.customer.customerId);
      if (!mounted) return;
      setState(() => _connectedBanks = 1);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('تمت إعادة بيانات العرض وفصل البنوك الخارجية.'),
      ));
    } catch (e) {
      if (mounted) showError(context, e.toString());
    } finally {
      if (mounted) setState(() => _resettingDemo = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            Row(children: [
              GestureDetector(
                // Hidden demo control: long-press the logo, then confirm.
                onLongPress: _showDemoReset,
                child: Stack(alignment: Alignment.center, children: [
                  const AppLogo(size: 48),
                  if (_resettingDemo)
                    const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color: AppColors.onPrimary,
                      ),
                    ),
                ]),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('مرحبًا، ${widget.customer.arName}',
                          style: const TextStyle(
                              fontSize: 21, fontWeight: FontWeight.w900)),
                      const Text('مستشارك المالي عبر كل بنوكك',
                          style: TextStyle(
                              color: AppColors.textMuted, fontSize: 13)),
                    ]),
              ),
              IconButton(
                onPressed: _logout,
                icon: const Icon(Icons.logout, color: AppColors.textMuted),
                tooltip: 'تغيير المستخدم',
              ),
            ]),
            const SizedBox(height: 18),
            GestureDetector(
              onTap: _openLinkScreen,
              child: Container(
                margin: const EdgeInsets.only(bottom: 16),
                padding:
                    const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                decoration: cardDecoration(
                    borderColor: AppColors.primary.withValues(alpha: 0.35)),
                child: Row(children: [
                  const Icon(Icons.account_balance_wallet_outlined,
                      color: AppColors.primary),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('حساباتك البنكية',
                              style: TextStyle(fontWeight: FontWeight.w800)),
                          Text(
                              '$_connectedBanks من ${bankNamesAr.length} بنوك مرتبطة',
                              style: const TextStyle(
                                  color: AppColors.textMuted, fontSize: 12.5)),
                        ]),
                  ),
                  const Icon(Icons.chevron_left, color: AppColors.textMuted),
                ]),
              ),
            ),
            _ModeCard(
              icon: Icons.shield_outlined,
              color: AppColors.primary,
              title: 'حزام الأمان المالي',
              body:
                  'افحص قرارًا قبل اتخاذه: نحاكي أشهرك الاثني عشر القادمة عبر كل بنوكك ونخبرك متى وأين ستتعثر — ومتى تصبح جاهزًا.',
              cta: 'افحص قرارًا',
              onTap: () => Navigator.of(context).push(appRoute(
                builder: (_) => DecisionScreen(customer: widget.customer),
              )),
            ),
            _ModeCard(
              icon: Icons.radar,
              color: AppColors.accent,
              title: 'الرادار المالي',
              body:
                  'نراقب وتيرة صرفك هذا الشهر مقابل ميزانيتك، ونحذرك قبل أن ينقصك المبلغ — مع أفضل حل للفجوة.',
              cta: 'افتح الرادار',
              onTap: () => Navigator.of(context).push(appRoute(
                builder: (_) => RadarScreen(customer: widget.customer),
              )),
            ),
            const SizedBox(height: 4),
            const HackathonFooter(),
          ],
        ),
      ),
    );
  }
}

class _ModeCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title, body, cta;
  final VoidCallback onTap;
  const _ModeCard(
      {required this.icon,
      required this.color,
      required this.title,
      required this.body,
      required this.cta,
      required this.onTap});

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.only(bottom: 14),
          padding: const EdgeInsets.all(20),
          decoration: heroDecoration(color),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [
                  color.withValues(alpha: 0.3),
                  color.withValues(alpha: 0.08)
                ]),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: color.withValues(alpha: 0.5)),
              ),
              child: Icon(icon, color: color, size: 26),
            ),
            const SizedBox(height: 12),
            Text(title,
                style:
                    const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            Text(body,
                style:
                    const TextStyle(color: AppColors.textMuted, height: 1.8)),
            const SizedBox(height: 12),
            Row(children: [
              Text(cta,
                  style: TextStyle(color: color, fontWeight: FontWeight.w900)),
              const SizedBox(width: 6),
              Icon(Icons.arrow_back, color: color, size: 17),
            ]),
          ]),
        ),
      );
}

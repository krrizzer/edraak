import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/widgets.dart';
import 'consent_flow.dart';

/// The "اربط حساباتك" screen: shows every bank, the host bank as already
/// connected, external banks to link via the consent flow, and coverage findings.
class LinkBanksScreen extends StatefulWidget {
  final Customer customer;
  const LinkBanksScreen({super.key, required this.customer});
  @override
  State<LinkBanksScreen> createState() => _LinkBanksScreenState();
}

class _LinkBanksScreenState extends State<LinkBanksScreen> {
  Map<String, dynamic>? _coverage;
  bool _loading = true;
  String? _busyBank;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _coverage = await Api.coverage(widget.customer.customerId);
    } catch (e) {
      if (mounted) showError(context, e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _link(String bankCode) async {
    setState(() => _busyBank = bankCode);
    final ok = await linkBank(context, widget.customer, bankCode);
    if (mounted) setState(() => _busyBank = null);
    if (ok) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final connected = ((_coverage?['connected_banks'] ?? []) as List).cast<String>().toSet();
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.bg,
        title: const Text('اربط حساباتك', style: TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_coverage != null) CoverageCard(coverage: _coverage!),
                const SizedBox(height: 4),
                // The host bank first (always connected), then the linkable ones.
                _bankTile(hostBankCode, true, isHost: true),
                ...bankNamesAr.keys
                    .where((code) => code != hostBankCode)
                    .map((code) => _bankTile(code, connected.contains(code))),
                const SizedBox(height: 8),
                const Text(
                  'المصرفية المفتوحة تحت إشراف البنك المركزي السعودي — تشارك بياناتك بموافقتك فقط، ويمكنك الإلغاء في أي وقت.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12.5, height: 1.7),
                ),
              ],
            ),
    );
  }

  Widget _bankTile(String code, bool connected, {bool isHost = false}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: cardDecoration(
          borderColor: isHost ? AppColors.primary.withOpacity(0.45) : null),
      child: Row(children: [
        BankLogo(code),
        const SizedBox(width: 14),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(bankNamesAr[code]!, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 4),
            Text(isHost ? 'بنكك الحالي — متصل تلقائيًا' : (connected ? 'متصل عبر المصرفية المفتوحة' : 'غير مرتبط'),
                style: TextStyle(
                    color: connected ? AppColors.primary : AppColors.textMuted, fontSize: 13)),
          ]),
        ),
        if (connected)
          const Icon(Icons.check_circle, color: AppColors.primary)
        else if (_busyBank == code)
          const SizedBox(
              height: 22, width: 22,
              child: CircularProgressIndicator(strokeWidth: 2.5, color: AppColors.primary))
        else
          GhostButton('ربط', onPressed: () => _link(code)),
      ]),
    );
  }
}

/// The coverage card: status + connected banks + suggested banks + findings.
class CoverageCard extends StatelessWidget {
  final Map<String, dynamic> coverage;
  final void Function(String bankCode)? onLink;
  const CoverageCard({super.key, required this.coverage, this.onLink});

  @override
  Widget build(BuildContext context) {
    final status = coverage['status'] as String;
    final findings = (coverage['findings'] as List).cast<Map<String, dynamic>>();
    final color = status == 'كافية'
        ? AppColors.primary
        : status == 'غير كافية'
            ? AppColors.danger
            : AppColors.warn;
    return SectionCard(
      accent: color,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Text('اكتمال البيانات', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
            const Spacer(),
            Pill(status, color: color, solid: true),
          ]),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final b in (coverage['connected_banks_ar'] as List))
              Pill('$b ✓', color: AppColors.primary),
          ]),
          if (findings.isNotEmpty) const SizedBox(height: 12),
          ...findings.map((f) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Icon(Icons.info_outline, size: 18, color: color),
                  const SizedBox(width: 8),
                  Expanded(child: Text(f['message_ar'] as String,
                      style: const TextStyle(color: AppColors.textMuted, height: 1.6))),
                ]),
              )),
          if (onLink != null)
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final s in (coverage['suggested_banks'] as List))
                ActionChip(
                  backgroundColor: AppColors.surfaceAlt,
                  side: const BorderSide(color: AppColors.border),
                  label: Text('اربط ${s['bank_name_ar']} ←',
                      style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
                  onPressed: () => onLink!(s['bank_code'] as String),
                ),
            ]),
        ],
      ),
    );
  }
}

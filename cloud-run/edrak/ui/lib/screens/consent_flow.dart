import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/widgets.dart';

/// Runs the full open-banking consent dance for one bank and ingests on approval:
///   create consent -> open the BANK's approval page (its own domain) -> poll ->
///   pull the data into BigQuery. Returns true if data was ingested.
Future<bool> linkBank(BuildContext context, Customer customer, String bankCode) async {
  final bankName = bankNamesAr[bankCode] ?? bankCode;
  try {
    final consent = await Api.createConsent(bankCode, customer.customerId);
    final consentId = consent['ConsentId'] as String;

    // Open the bank's own approval screen in a new tab (real redirect theatre).
    await launchUrl(
      Uri.parse(Api.authorizeUrl(bankCode, consentId)),
      webOnlyWindowName: '_blank',
      mode: LaunchMode.externalApplication,
    );

    if (!context.mounted) return false;
    final approved = await _pollForApproval(context, bankCode, consentId, bankName);
    if (!approved || !context.mounted) return false;

    return await _ingest(context, customer, bankCode, consentId, bankName);
  } catch (e) {
    if (context.mounted) showError(context, e.toString());
    return false;
  }
}

/// Poll the gateway until the customer approves or rejects, behind a waiting dialog.
Future<bool> _pollForApproval(
    BuildContext context, String bankCode, String consentId, String bankName) async {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (_) => _WaitDialog(bankName: bankName),
  );
  try {
    for (var i = 0; i < 40; i++) {
      await Future.delayed(const Duration(milliseconds: 1500));
      final status = await Api.consentStatus(bankCode, consentId);
      if (status == 'Authorised') return true;
      if (status == 'Rejected') throw ApiException('تم رفض الموافقة في نافذة البنك.');
    }
    throw ApiException('انتهت مهلة انتظار الموافقة.');
  } finally {
    if (context.mounted) Navigator.of(context, rootNavigator: true).pop(); // close wait dialog
  }
}

/// Pull the consented bank's data into BigQuery, behind a blocking dialog.
Future<bool> _ingest(BuildContext context, Customer customer, String bankCode,
    String consentId, String bankName) async {
  _showBusy(context, 'جارٍ سحب بيانات $bankName عبر الواجهة البرمجية…');
  try {
    final result = await Api.ingest(customer.customerId, bankCode, consentId);
    if (context.mounted) {
      Navigator.of(context, rootNavigator: true).pop(); // close busy dialog
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('تم ربط $bankName — سُحبت ${result['transactions']} معاملة',
            textDirection: TextDirection.rtl),
        backgroundColor: AppColors.primary,
      ));
    }
    return true;
  } catch (e) {
    if (context.mounted) {
      Navigator.of(context, rootNavigator: true).pop(); // close busy dialog
      showError(context, e.toString());
    }
    return false;
  }
}

void _showBusy(BuildContext context, String message) {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (_) => Dialog(
      backgroundColor: AppColors.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const SizedBox(
              height: 22, width: 22,
              child: CircularProgressIndicator(strokeWidth: 2.5, color: AppColors.primary)),
          const SizedBox(width: 14),
          Flexible(child: Text(message)),
        ]),
      ),
    ),
  );
}

class _WaitDialog extends StatelessWidget {
  final String bankName;
  const _WaitDialog({required this.bankName});
  @override
  Widget build(BuildContext context) => Dialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const SizedBox(
                height: 36, width: 36,
                child: CircularProgressIndicator(strokeWidth: 3, color: AppColors.primary)),
            const SizedBox(height: 18),
            Text('بانتظار موافقتك في نافذة $bankName',
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(height: 8),
            const Text('أكمل الموافقة في نافذة البنك التي فُتحت، ثم عد إلى هنا.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textMuted, height: 1.6)),
          ]),
        ),
      );
}

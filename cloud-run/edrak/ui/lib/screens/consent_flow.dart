import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:web/web.dart' as web;
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/widgets.dart';

/// Runs the full open-banking consent dance for one bank and ingests on approval:
///   create consent -> open the BANK's approval page (its own domain) -> poll ->
///   pull the data into BigQuery. Returns true if data was ingested.
Future<bool> linkBank(
    BuildContext context, Customer customer, String bankCode) async {
  final bankName = bankNamesAr[bankCode] ?? bankCode;
  // Mobile Safari requires window.open() to run synchronously inside the tap
  // handler. Creating the consent first crosses an async boundary and causes
  // Safari to block the later approval tab. Reserve one named tab now, then
  // navigate that same tab as soon as the gateway returns the consent id.
  final approvalWindow = web.window.open('about:blank', 'edraak_bank_consent');
  try {
    final consent = await Api.createConsent(bankCode, customer.customerId);
    final consentId = consent['ConsentId'] as String;
    final approvalUri = Uri.parse(Api.authorizeUrl(bankCode, consentId));

    if (approvalWindow != null) {
      approvalWindow.location.href = approvalUri.toString();
    } else {
      // A strict popup setting can still reject even a user-initiated tab. Give
      // the customer a direct second-tap fallback instead of leaving the
      // consent silently stuck in AwaitingAuthorisation.
      if (!context.mounted ||
          !await _showApprovalFallback(context, approvalUri, bankName)) {
        return false;
      }
    }

    if (!context.mounted) return false;
    final approved =
        await _pollForApproval(context, bankCode, consentId, bankName);
    if (!approved || !context.mounted) return false;

    return await _ingest(context, customer, bankCode, consentId, bankName);
  } catch (e) {
    approvalWindow?.close();
    if (context.mounted) showError(context, e.toString());
    return false;
  }
}

Future<bool> _showApprovalFallback(
    BuildContext context, Uri approvalUri, String bankName) async {
  return await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => AlertDialog(
          backgroundColor: AppColors.surface,
          title: const Text('افتح صفحة الموافقة'),
          content: Text(
            'منع المتصفح فتح صفحة $bankName تلقائيًا. اضغط متابعة لفتحها بأمان.',
            textDirection: TextDirection.rtl,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('إلغاء'),
            ),
            FilledButton(
              onPressed: () async {
                // Invoke launchUrl before awaiting anything so this second tap
                // also retains Safari's transient user activation.
                final launch = launchUrl(
                  approvalUri,
                  webOnlyWindowName: '_blank',
                  mode: LaunchMode.externalApplication,
                );
                Navigator.of(dialogContext).pop(true);
                await launch;
              },
              child: const Text('متابعة'),
            ),
          ],
        ),
      ) ??
      false;
}

/// Poll the gateway until the customer approves or rejects, behind a waiting dialog.
Future<bool> _pollForApproval(BuildContext context, String bankCode,
    String consentId, String bankName) async {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (_) => _WaitDialog(bankName: bankName),
  );
  try {
    // Check immediately, then poll quickly. The old fixed 1.5-second wait made
    // an already-approved demo consent feel unnecessarily slow.
    for (var i = 0; i < 150; i++) {
      if (i > 0) await Future.delayed(const Duration(milliseconds: 400));
      final status = await Api.consentStatus(bankCode, consentId);
      if (status == 'Authorised') return true;
      if (status == 'Rejected') {
        throw ApiException('تم رفض الموافقة في نافذة البنك.');
      }
    }
    throw ApiException('انتهت مهلة انتظار الموافقة.');
  } finally {
    if (context.mounted) {
      Navigator.of(context, rootNavigator: true).pop(); // close wait dialog
    }
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
      final transactions = (result['transactions'] as num?)?.toInt() ?? 0;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(
            transactions == 0
                ? 'تم ربط $bankName بنجاح — لا توجد معاملات متاحة حاليًا'
                : 'تم ربط $bankName — سُحبت $transactions معاملة',
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
              height: 22,
              width: 22,
              child: CircularProgressIndicator(
                  strokeWidth: 2.5, color: AppColors.primary)),
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
                height: 36,
                width: 36,
                child: CircularProgressIndicator(
                    strokeWidth: 3, color: AppColors.primary)),
            const SizedBox(height: 18),
            Text('بانتظار موافقتك في نافذة $bankName',
                textAlign: TextAlign.center,
                style:
                    const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(height: 8),
            const Text(
                'أكمل الموافقة في نافذة البنك التي فُتحت، ثم عد إلى هنا.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textMuted, height: 1.6)),
          ]),
        ),
      );
}

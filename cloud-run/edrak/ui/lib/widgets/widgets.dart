import 'package:flutter/material.dart';
import '../theme.dart';

/// A gradient brand button with a soft glow.
class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final bool expand;
  const PrimaryButton(this.label, {super.key, this.onPressed, this.loading = false, this.expand = true});

  @override
  Widget build(BuildContext context) {
    final child = loading
        ? const SizedBox(
            height: 22, width: 22,
            child: CircularProgressIndicator(strokeWidth: 2.5, color: AppColors.onPrimary))
        : Text(label,
            style: const TextStyle(
                fontWeight: FontWeight.w900, fontSize: 16, color: AppColors.onPrimary));
    final button = DecoratedBox(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF2EE6A8), Color(0xFF25C9D4)],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(color: AppColors.primary.withOpacity(loading ? 0.10 : 0.30),
              blurRadius: 22, offset: const Offset(0, 8)),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: loading ? null : onPressed,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            height: 54,
            alignment: Alignment.center,
            padding: const EdgeInsets.symmetric(horizontal: 22),
            child: child,
          ),
        ),
      ),
    );
    return expand ? SizedBox(width: double.infinity, child: button) : button;
  }
}

/// A bordered outline button.
class GhostButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  const GhostButton(this.label, {super.key, this.onPressed});
  @override
  Widget build(BuildContext context) => OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          side: BorderSide(color: AppColors.primary.withOpacity(0.55)),
          minimumSize: const Size(0, 44),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800)),
      );
}

/// A titled glass card.
class SectionCard extends StatelessWidget {
  final String? title;
  final Widget child;
  final Color? accent;
  const SectionCard({super.key, this.title, required this.child, this.accent});
  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(18),
        decoration: cardDecoration(borderColor: accent?.withOpacity(0.5)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (title != null) ...[
              Text(title!, style: TextStyle(
                  fontSize: 17, fontWeight: FontWeight.w900,
                  color: accent ?? AppColors.textPrimary)),
              const SizedBox(height: 12),
            ],
            child,
          ],
        ),
      );
}

/// A small labelled metric tile with a glowing value.
class Metric extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;
  const Metric(this.label, this.value, {super.key, this.color});
  @override
  Widget build(BuildContext context) {
    final c = color ?? AppColors.primary;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.035),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(value, style: TextStyle(
              fontSize: 19, fontWeight: FontWeight.w900, color: c,
              shadows: [Shadow(color: c.withOpacity(0.5), blurRadius: 14)])),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

/// A pill chip.
class Pill extends StatelessWidget {
  final String text;
  final Color color;
  final bool solid;
  const Pill(this.text, {super.key, this.color = AppColors.primary, this.solid = false});
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
        decoration: BoxDecoration(
          color: solid ? color : color.withOpacity(0.13),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: color.withOpacity(solid ? 1 : 0.45)),
        ),
        child: Text(text, style: TextStyle(
            fontSize: 12.5, fontWeight: FontWeight.w800,
            color: solid ? const Color(0xFF06130D) : color)),
      );
}

/// The tiny "ذكاء اصطناعي" tag used wherever an LLM produced the content.
class AiBadge extends StatelessWidget {
  const AiBadge({super.key});
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 3, horizontal: 9),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [
            AppColors.ai.withOpacity(0.25), AppColors.accent.withOpacity(0.2),
          ]),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: AppColors.ai.withOpacity(0.6)),
        ),
        child: const Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.auto_awesome, size: 12, color: AppColors.ai),
          SizedBox(width: 4),
          Text('ذكاء اصطناعي',
              style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: AppColors.ai)),
        ]),
      );
}

/// A stepwise loading panel with a pulsing brand spinner.
class LoadingPanel extends StatelessWidget {
  final String title;
  final List<String> steps;
  const LoadingPanel({super.key, required this.title, required this.steps});
  @override
  Widget build(BuildContext context) => SectionCard(
        accent: AppColors.primary,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.primary.withOpacity(0.12),
                ),
                child: const SizedBox(
                    height: 22, width: 22,
                    child: CircularProgressIndicator(strokeWidth: 2.6, color: AppColors.primary)),
              ),
              const SizedBox(width: 12),
              Expanded(child: Text(title,
                  style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w900))),
            ]),
            const SizedBox(height: 14),
            ...steps.map((s) => Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: Row(children: [
                    Container(
                      height: 7, width: 7,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.primary,
                        boxShadow: [BoxShadow(color: AppColors.primary.withOpacity(0.6), blurRadius: 8)],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: Text(s, style: const TextStyle(color: AppColors.textMuted))),
                  ]),
                )),
          ],
        ),
      );
}

/// A simple bulleted list card.
class BulletList extends StatelessWidget {
  final String title;
  final List<String> items;
  final Color? accent;
  const BulletList(this.title, this.items, {super.key, this.accent});
  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return SectionCard(
      title: title,
      accent: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: items
            .map((it) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Padding(
                        padding: const EdgeInsets.only(top: 7),
                        child: Icon(Icons.circle, size: 6, color: accent ?? AppColors.primary)),
                    const SizedBox(width: 10),
                    Expanded(child: Text(it, style: const TextStyle(height: 1.7))),
                  ]),
                ))
            .toList(),
      ),
    );
  }
}

/// A bank's logo from assets/icons/{CODE}.png, falling back to a generic
/// bank icon until the PNG is added — so missing files never break the UI.
class BankLogo extends StatelessWidget {
  final String bankCode;
  final double size;
  const BankLogo(this.bankCode, {super.key, this.size = 44});
  @override
  Widget build(BuildContext context) => Container(
        height: size,
        width: size,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(size * 0.27),
          border: Border.all(color: AppColors.border),
        ),
        clipBehavior: Clip.antiAlias,
        child: Image.asset(
          'assets/icons/$bankCode.png',
          fit: BoxFit.contain,
          errorBuilder: (_, __, ___) =>
              Icon(Icons.account_balance, color: AppColors.primary, size: size * 0.5),
        ),
      );
}

void showError(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
    content: Text(message, textDirection: TextDirection.rtl),
    backgroundColor: AppColors.danger,
  ));
}

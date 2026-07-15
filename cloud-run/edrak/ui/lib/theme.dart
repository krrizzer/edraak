import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Edraak visual language: deep navy space, neon-mint intelligence, glass cards.
class AppColors {
  static const bg = Color(0xFF050D15);
  static const bgDeep = Color(0xFF02070D);
  static const surface = Color(0xFF0C1B27);
  static const surfaceAlt = Color(0xFF122736);
  static const primary = Color(0xFF2EE6A8);
  static const onPrimary = Color(0xFF03140D);
  static const accent = Color(0xFF4EA8FF);
  static const ai = Color(0xFF9D8CFF);
  static const textPrimary = Color(0xFFEDF6F4);
  static const textMuted = Color(0xFF93AEBC);
  static const danger = Color(0xFFFF6B62);
  static const warn = Color(0xFFFFC24D);
  static const border = Color(0x1FA8D8E8);

  // Verdict colours: safe green -> not-suitable red.
  static const verdictSafe = primary;
  static const verdictCaution = warn;
  static const verdictDelay = Color(0xFFFF9D5C);
  static const verdictAvoid = danger;
}

ThemeData buildTheme() {
  final base = ThemeData.dark(useMaterial3: true);
  return base.copyWith(
    // Transparent so the global gradient painted behind every route shows through.
    scaffoldBackgroundColor: Colors.transparent,
    colorScheme: base.colorScheme.copyWith(
      primary: AppColors.primary,
      secondary: AppColors.accent,
      surface: AppColors.surface,
      error: AppColors.danger,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      elevation: 0,
      centerTitle: false,
    ),
    textTheme: GoogleFonts.tajawalTextTheme(base.textTheme).apply(
      bodyColor: AppColors.textPrimary,
      displayColor: AppColors.textPrimary,
    ),
    cardColor: AppColors.surface,
    dialogTheme: const DialogThemeData(backgroundColor: AppColors.surface),
  );
}

/// The app-wide backdrop: a deep vertical fade with two soft neon glows.
class AppBackground extends StatelessWidget {
  final Widget child;
  const AppBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF08131E), Color(0xFF050D15), Color(0xFF03080E)],
        ),
      ),
      child: Stack(children: [
        Positioned(
          top: -140,
          right: -100,
          child: _glow(const Color(0x282EE6A8), 340),
        ),
        Positioned(
          bottom: -160,
          left: -120,
          child: _glow(const Color(0x1F4EA8FF), 380),
        ),
        child,
      ]),
    );
  }

  Widget _glow(Color color, double size) => IgnorePointer(
        child: Container(
          height: size,
          width: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient:
                RadialGradient(colors: [color, color.withValues(alpha: 0)]),
          ),
        ),
      );
}

/// Glass card: translucent fill + hairline border + deep shadow.
BoxDecoration cardDecoration({Color? color, Color? borderColor}) =>
    BoxDecoration(
      color: color ?? Colors.white.withValues(alpha: 0.045),
      borderRadius: BorderRadius.circular(22),
      border: Border.all(color: borderColor ?? AppColors.border),
      boxShadow: const [
        BoxShadow(
            color: Color(0x40000000), blurRadius: 28, offset: Offset(0, 14)),
      ],
    );

/// Hero card tinted and glowing in one colour (verdict/alert headers).
BoxDecoration heroDecoration(Color color) => BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topRight,
        end: Alignment.bottomLeft,
        colors: [
          color.withValues(alpha: 0.16),
          Colors.white.withValues(alpha: 0.03)
        ],
      ),
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: color.withValues(alpha: 0.55), width: 1.2),
      boxShadow: [
        BoxShadow(
            color: color.withValues(alpha: 0.18),
            blurRadius: 36,
            offset: const Offset(0, 10)),
      ],
    );

Color verdictColor(String verdict) {
  switch (verdict) {
    case 'قرار آمن':
      return AppColors.verdictSafe;
    case 'مقبول بحذر':
      return AppColors.verdictCaution;
    case 'الأفضل تأجيله':
      return AppColors.verdictDelay;
    case 'غير مناسب':
      return AppColors.verdictAvoid;
    default:
      return AppColors.verdictCaution;
  }
}

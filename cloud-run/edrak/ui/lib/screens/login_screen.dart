import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../navigation.dart';
import '../theme.dart';
import '../widgets/widgets.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _controller = TextEditingController();
  bool _loading = false;

  Future<void> _login() async {
    final username = _controller.text.trim();
    if (username.isEmpty) return;
    setState(() => _loading = true);
    try {
      final data = await Api.login(username);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(appRoute(
        builder: (_) => HomeScreen(customer: Customer.fromJson(data)),
      ));
    } catch (e) {
      if (mounted) showError(context, e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Container(
                padding: const EdgeInsets.all(28),
                decoration: cardDecoration(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const AppLogo(size: 84),
                    const SizedBox(height: 16),
                    const Text('إدراك',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            fontSize: 40,
                            fontWeight: FontWeight.w900,
                            height: 1.1)),
                    const SizedBox(height: 6),
                    const Text(
                        'حزام الأمان المالي — يرى كل بنوكك ويحسب أشهرك القادمة',
                        textAlign: TextAlign.center,
                        style:
                            TextStyle(color: AppColors.textMuted, height: 1.7)),
                    const SizedBox(height: 24),
                    const Text('اسم المستخدم بالإنجليزية',
                        style: TextStyle(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _controller,
                      textDirection: TextDirection.ltr,
                      textInputAction: TextInputAction.done,
                      autofillHints: const [AutofillHints.username],
                      autocorrect: false,
                      enableSuggestions: false,
                      onSubmitted: (_) => _login(),
                      decoration: InputDecoration(
                        hintText: 'fahad',
                        filled: true,
                        fillColor: AppColors.surfaceAlt,
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide: const BorderSide(color: AppColors.border),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide:
                              const BorderSide(color: AppColors.primary),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    PrimaryButton('دخول', loading: _loading, onPressed: _login),
                    const SizedBox(height: 12),
                    const Text(
                        'جرّب: fahad أو sara أو khalid أو noura أو abdullah',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            color: AppColors.textMuted, fontSize: 13)),
                    const SizedBox(height: 18),
                    const HackathonLogo(size: 104),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The EDRAAK.png app logo, with a fallback badge until the asset is added.
class AppLogo extends StatelessWidget {
  final double size;
  const AppLogo({super.key, this.size = 64});
  @override
  Widget build(BuildContext context) {
    return Center(
      child: ClipRRect(
        borderRadius: BorderRadius.circular(size * 0.28),
        child: Image.asset(
          'assets/icons/EDRAAK.png',
          height: size,
          width: size,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => Container(
            height: size,
            width: size,
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(size * 0.28),
            ),
            child: const Center(
              child: Text('إ',
                  style: TextStyle(
                      color: AppColors.onPrimary,
                      fontSize: 34,
                      fontWeight: FontWeight.w900)),
            ),
          ),
        ),
      ),
    );
  }
}

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
  static const _demoUsers = [
    'fahad',
    'sara',
    'khalid',
    'noura',
    'abdullah',
  ];

  final _controller = TextEditingController(text: 'fahad');
  bool _loading = false;
  String? _selectedDemo = 'fahad';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _selectDemoUser(String username) {
    _controller.text = username;
    _controller.selection = TextSelection.collapsed(offset: username.length);
    setState(() => _selectedDemo = username);
  }

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
      body: LayoutBuilder(
        builder: (context, constraints) {
          final heroHeight =
              (constraints.maxHeight * 0.39).clamp(285.0, 340.0).toDouble();
          return SingleChildScrollView(
            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight),
              child: IntrinsicHeight(
                child: Column(
                  children: [
                    _BrandHero(height: heroHeight),
                    Expanded(
                      child: Container(
                        width: double.infinity,
                        color: AppColors.lightSurface,
                        child: SafeArea(
                          top: false,
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(28, 34, 28, 18),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                const Text(
                                  'اسم المستخدم',
                                  style: TextStyle(
                                    color: AppColors.lightInk,
                                    fontSize: 16,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                const SizedBox(height: 9),
                                TextField(
                                  controller: _controller,
                                  textDirection: TextDirection.ltr,
                                  textInputAction: TextInputAction.done,
                                  autofillHints: const [AutofillHints.username],
                                  autocorrect: false,
                                  enableSuggestions: false,
                                  onChanged: (value) {
                                    final next = _demoUsers.contains(value.trim())
                                        ? value.trim()
                                        : null;
                                    if (next != _selectedDemo) {
                                      setState(() => _selectedDemo = next);
                                    }
                                  },
                                  onSubmitted: (_) => _login(),
                                  style: const TextStyle(
                                    color: AppColors.lightInk,
                                    fontSize: 18,
                                    fontWeight: FontWeight.w700,
                                  ),
                                  decoration: InputDecoration(
                                    prefixIcon: const Icon(
                                      Icons.person_outline_rounded,
                                      color: AppColors.lightMuted,
                                    ),
                                    filled: true,
                                    fillColor: Colors.white,
                                    contentPadding: const EdgeInsets.symmetric(
                                      horizontal: 18,
                                      vertical: 18,
                                    ),
                                    enabledBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(14),
                                      borderSide: const BorderSide(
                                        color: AppColors.lightBorder,
                                      ),
                                    ),
                                    focusedBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(14),
                                      borderSide: const BorderSide(
                                        color: AppColors.primary,
                                        width: 1.5,
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 18),
                                FilledButton(
                                  onPressed: _loading ? null : _login,
                                  style: FilledButton.styleFrom(
                                    backgroundColor: AppColors.primary,
                                    disabledBackgroundColor:
                                        AppColors.primary.withValues(alpha: 0.7),
                                    foregroundColor: AppColors.brandNavy,
                                    minimumSize: const Size.fromHeight(56),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                  ),
                                  child: _loading
                                      ? const SizedBox.square(
                                          dimension: 22,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2.5,
                                            color: AppColors.brandNavy,
                                          ),
                                        )
                                      : const Text(
                                          'دخول',
                                          style: TextStyle(
                                            fontSize: 17,
                                            fontWeight: FontWeight.w900,
                                          ),
                                        ),
                                ),
                                const SizedBox(height: 23),
                                const Text(
                                  'جرّب حساباً تجريبياً',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    color: AppColors.lightMuted,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                _DemoUserLinks(
                                  users: _demoUsers,
                                  selected: _selectedDemo,
                                  onSelected: _selectDemoUser,
                                ),
                                const Spacer(),
                                const SizedBox(height: 22),
                                const _SponsorLockup(),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _BrandHero extends StatelessWidget {
  final double height;
  const _BrandHero({required this.height});

  @override
  Widget build(BuildContext context) => ClipPath(
        clipper: const _HeroCurveClipper(),
        child: Container(
          height: height + 22,
          width: double.infinity,
          color: AppColors.brandNavy,
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 22, 24, 42),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  AppLogo(size: 98),
                  SizedBox(height: 8),
                  Text(
                    'إدراك',
                    style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 40,
                      height: 1,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  SizedBox(height: 11),
                  Text(
                    'حزام أمانك المالي',
                    style: TextStyle(
                      color: AppColors.primary,
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'يرى كل بنوكك، لتقرر بثقة.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 14.5,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class _HeroCurveClipper extends CustomClipper<Path> {
  const _HeroCurveClipper();

  @override
  Path getClip(Size size) => Path()
    ..lineTo(0, size.height - 42)
    ..quadraticBezierTo(
      size.width / 2,
      size.height + 16,
      size.width,
      size.height - 42,
    )
    ..lineTo(size.width, 0)
    ..close();

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}

class _DemoUserLinks extends StatelessWidget {
  final List<String> users;
  final String? selected;
  final ValueChanged<String> onSelected;

  const _DemoUserLinks({
    required this.users,
    required this.selected,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) => Wrap(
        alignment: WrapAlignment.center,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 2,
        runSpacing: 0,
        children: [
          for (var index = 0; index < users.length; index++) ...[
            TextButton(
              onPressed: () => onSelected(users[index]),
              style: TextButton.styleFrom(
                foregroundColor: selected == users[index]
                    ? AppColors.primary
                    : AppColors.lightInk,
                minimumSize: const Size(44, 48),
                padding: const EdgeInsets.symmetric(horizontal: 5),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                textStyle: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
              child: Text(users[index]),
            ),
            if (index < users.length - 1)
              const Text(
                '·',
                style: TextStyle(
                  color: AppColors.lightMuted,
                  fontWeight: FontWeight.w700,
                ),
              ),
          ],
        ],
      );
}

class _SponsorLockup extends StatelessWidget {
  const _SponsorLockup();

  @override
  Widget build(BuildContext context) => Column(
        children: [
          // const Text(
          //   'بالتعاون مع',
          //   style: TextStyle(
          //     color: AppColors.lightMuted,
          //     fontSize: 12.5,
          //     fontWeight: FontWeight.w600,
          //   ),
          // ),
          const SizedBox(height: 5),
          SizedBox(
            width: 174,
            height: 76,
            child: Image.asset(
              'assets/icons/AMAD.png',
              fit: BoxFit.contain,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),
        ],
      );
}

/// The EDRAAK.png app logo, with a fallback badge until the asset is added.
class AppLogo extends StatelessWidget {
  final double size;
  const AppLogo({super.key, this.size = 64});
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Image.asset(
        'assets/icons/EDRAAK.png',
        height: size,
        width: size,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) => Container(
          height: size,
          width: size,
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: BorderRadius.circular(size * 0.28),
          ),
          child: const Icon(
            Icons.shield_outlined,
            color: AppColors.onPrimary,
            size: 34,
          ),
        ),
      ),
    );
  }
}

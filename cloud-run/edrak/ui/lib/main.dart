import 'package:flutter/material.dart';
import 'api.dart';
import 'theme.dart';
import 'screens/login_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Api.loadRuntimeConfig();
  runApp(const EdraakApp());
}

class EdraakApp extends StatelessWidget {
  const EdraakApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'إدراك',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      // The whole app is Arabic / right-to-left, and on wide screens (the demo
      // runs in Chrome) it renders inside a phone-sized frame so it reads as a
      // mobile banking app, not a stretched website.
      builder: (context, child) => Directionality(
        textDirection: TextDirection.rtl,
        child: PhoneFrame(
          child: AppBackground(child: child ?? const SizedBox.shrink()),
        ),
      ),
      home: const LoginScreen(),
    );
  }
}

/// Constrains the app to a phone-sized, rounded frame on wide viewports.
/// On actual phones (narrow viewports) it is a no-op.
class PhoneFrame extends StatelessWidget {
  final Widget child;
  const PhoneFrame({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      if (constraints.maxWidth <= 540) return child;
      final height = (constraints.maxHeight - 40).clamp(560.0, 900.0);
      return ColoredBox(
        color: const Color(0xFF020A10),
        child: Center(
          child: Container(
            width: 414,
            height: height,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(38),
              border: Border.all(color: const Color(0xFF1E3A4C), width: 6),
              boxShadow: const [
                BoxShadow(color: Color(0x66000000), blurRadius: 60, offset: Offset(0, 24)),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(32),
              child: child,
            ),
          ),
        ),
      );
    });
  }
}

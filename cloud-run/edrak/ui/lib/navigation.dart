import 'package:flutter/material.dart';

/// A short, quiet transition that keeps the web app feeling native on phones.
Route<T> appRoute<T>({required WidgetBuilder builder}) => PageRouteBuilder<T>(
      pageBuilder: (context, animation, secondaryAnimation) => builder(context),
      transitionDuration: const Duration(milliseconds: 160),
      reverseTransitionDuration: const Duration(milliseconds: 130),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        final eased = CurvedAnimation(
          parent: animation,
          curve: Curves.easeOutCubic,
          reverseCurve: Curves.easeInCubic,
        );
        return FadeTransition(
          opacity: eased,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(-0.025, 0),
              end: Offset.zero,
            ).animate(eased),
            child: child,
          ),
        );
      },
    );

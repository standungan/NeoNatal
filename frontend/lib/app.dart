import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:neonatal_care/core/providers/auth_provider.dart';
import 'package:neonatal_care/core/router/app_router.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

class NeonatalApp extends ConsumerStatefulWidget {
  const NeonatalApp({super.key});

  @override
  ConsumerState<NeonatalApp> createState() => _NeonatalAppState();
}

class _NeonatalAppState extends ConsumerState<NeonatalApp> {
  @override
  void initState() {
    super.initState();
    // restore saved session on startup
    Future.microtask(() => ref.read(authProvider.notifier).init());
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Neonatal Care System',
      theme: AppTheme.light,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}

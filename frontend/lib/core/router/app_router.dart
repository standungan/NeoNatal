import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:neonatal_care/core/providers/auth_provider.dart';
import 'package:neonatal_care/features/admin/screens/audit_log_screen.dart';
import 'package:neonatal_care/features/admin/screens/user_management_screen.dart';
import 'package:neonatal_care/features/aksi/screens/aksi_screen.dart';
import 'package:neonatal_care/features/auth/screens/login_screen.dart';
import 'package:neonatal_care/features/baby/screens/register_baby_screen.dart';
import 'package:neonatal_care/features/dashboard/screens/dashboard_screen.dart';
import 'package:neonatal_care/features/incubator/screens/incubator_detail_screen.dart';
import 'package:neonatal_care/features/involvement/screens/involvement_screen.dart';
import 'package:neonatal_care/features/monitoring/screens/monitoring_screen.dart';
import 'package:neonatal_care/features/reports/screens/report_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/dashboard',
    redirect: (context, state) {
      final loggedIn = auth.isAuthenticated;
      final onLogin = state.matchedLocation == '/login';
      if (!loggedIn && !onLogin) return '/login';
      if (loggedIn && onLogin) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(path: '/login',     builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
      GoRoute(
        path: '/incubator/:id',
        builder: (_, state) =>
            IncubatorDetailScreen(incubatorId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/baby/register',
        builder: (_, __) => const RegisterBabyScreen(),
      ),
      GoRoute(
        path: '/baby/:id/monitoring',
        builder: (_, state) =>
            MonitoringScreen(babyId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/baby/:id/involvement',
        builder: (_, state) =>
            InvolvementScreen(babyId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/baby/:id/aksi',
        builder: (_, state) =>
            AksiScreen(babyId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/baby/:id/report',
        builder: (_, state) =>
            ReportScreen(babyId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/admin/users',
        builder: (_, __) => const UserManagementScreen(),
      ),
      GoRoute(
        path: '/admin/audit-logs',
        builder: (_, __) => const AuditLogScreen(),
      ),
    ],
  );
});

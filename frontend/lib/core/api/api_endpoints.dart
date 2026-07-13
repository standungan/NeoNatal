class ApiEndpoints {
  // Override at run/build time, e.g.:
  //   flutter run --dart-define=API_BASE=http://10.0.2.2:8000      (Android emulator)
  //   flutter run --dart-define=API_BASE=http://192.168.1.5:8000   (physical device on LAN)
  // Defaults to localhost for desktop/web runs.
  static const baseUrl = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'http://localhost:8000',
  );

  // auth
  static const login     = '/api/v1/auth/login';
  static const me        = '/api/v1/auth/me';

  // incubators
  static const incubators          = '/api/v1/incubators';
  static const incubatorsAvailable = '/api/v1/incubators/available';
  static String incubator(String id) => '/api/v1/incubators/$id';

  // babies
  static const babies = '/api/v1/babies';
  static String baby(String id)             => '/api/v1/babies/$id';
  static String discharge(String id)        => '/api/v1/babies/$id/discharge';

  // monitoring
  static String monitoring(String babyId)          => '/api/v1/babies/$babyId/monitoring';
  static String photoUpload(String monitoringId)   => '/api/v1/monitoring/$monitoringId/photo';

  // involvement
  static String involvement(String babyId)         => '/api/v1/babies/$babyId/involvement';
  static String involvementSummary(String babyId)  => '/api/v1/babies/$babyId/involvement/summary';

  // aksi (Kolaborasi Interprofesional)
  static String aksi(String babyId)                => '/api/v1/babies/$babyId/aksi';
  static String aksiSummary(String babyId)         => '/api/v1/babies/$babyId/aksi/summary';

  // dashboard
  static const dashboard = '/api/v1/dashboard';

  // reports
  static String report(String babyId)    => '/api/v1/babies/$babyId/report';
  static String reportPdf(String babyId) => '/api/v1/babies/$babyId/report/pdf';

  // users (admin)
  static const users = '/api/v1/users';
  static String user(String id)              => '/api/v1/users/$id';
  static String userResetPassword(String id) => '/api/v1/users/$id/reset-password';

  // audit log (admin)
  static const auditLogs = '/api/v1/audit-logs';
}

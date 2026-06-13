import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/models/auth_model.dart';

class AuthState {
  final TokenResponse? token;
  final bool isLoading;
  final String? error;

  const AuthState({this.token, this.isLoading = false, this.error});

  bool get isAuthenticated => token != null;
  String get role => token?.role ?? '';

  AuthState copyWith({TokenResponse? token, bool? isLoading, String? error}) =>
      AuthState(
        token: token ?? this.token,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState());

  final _api = ApiClient();
  final _storage = const FlutterSecureStorage();

  Future<void> init() async {
    final token = await _storage.read(key: 'access_token');
    final userId = await _storage.read(key: 'user_id');
    final fullName = await _storage.read(key: 'full_name');
    final role = await _storage.read(key: 'role');
    if (token != null && userId != null && fullName != null && role != null) {
      state = state.copyWith(
        token: TokenResponse(
          accessToken: token,
          userId: userId,
          fullName: fullName,
          role: role,
        ),
      );
    }
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final res = await _api.dio.post(
        ApiEndpoints.login,
        data: {'email': email, 'password': password},
      );
      final tokenResp = TokenResponse.fromJson(res.data);

      await _api.saveToken(tokenResp.accessToken);
      await _storage.write(key: 'user_id', value: tokenResp.userId);
      await _storage.write(key: 'full_name', value: tokenResp.fullName);
      await _storage.write(key: 'role', value: tokenResp.role);

      state = state.copyWith(token: tokenResp, isLoading: false);
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Login gagal';
      state = state.copyWith(isLoading: false, error: msg.toString());
    }
  }

  Future<void> logout() async {
    await _api.clearToken();
    await _storage.deleteAll();
    state = const AuthState();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (_) => AuthNotifier(),
);

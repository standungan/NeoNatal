class TokenResponse {
  final String accessToken;
  final String userId;
  final String fullName;
  final String role;

  const TokenResponse({
    required this.accessToken,
    required this.userId,
    required this.fullName,
    required this.role,
  });

  factory TokenResponse.fromJson(Map<String, dynamic> j) => TokenResponse(
        accessToken: j['access_token'],
        userId: j['user_id'],
        fullName: j['full_name'],
        role: j['role'],
      );
}

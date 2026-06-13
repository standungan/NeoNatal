import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:neonatal_care/core/api/api_client.dart';
import 'package:neonatal_care/core/api/api_endpoints.dart';
import 'package:neonatal_care/core/theme/app_theme.dart';

final _usersProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) async {
    final res = await ApiClient().dio.get(ApiEndpoints.users);
    return (res.data as List).cast<Map<String, dynamic>>();
  },
);

const _roleLabels = {
  'admin': 'Admin',
  'perawat': 'Perawat',
  'dokter': 'Dokter',
};

class UserManagementScreen extends ConsumerWidget {
  const UserManagementScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usersAsync = ref.watch(_usersProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Manajemen Pengguna')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => showDialog(
          context: context,
          builder: (_) => _UserFormDialog(
            onSuccess: () => ref.invalidate(_usersProvider),
          ),
        ),
        icon: const Icon(Icons.person_add),
        label: const Text('Tambah Pengguna'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      body: usersAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Gagal memuat: $e')),
        data: (users) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(_usersProvider),
          child: ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: users.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) => _UserCard(
              user: users[i],
              onChanged: () => ref.invalidate(_usersProvider),
            ),
          ),
        ),
      ),
    );
  }
}

class _UserCard extends ConsumerWidget {
  final Map<String, dynamic> user;
  final VoidCallback onChanged;
  const _UserCard({required this.user, required this.onChanged});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isActive = user['is_active'] == true;
    final role = user['role'] as String? ?? '';
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppColors.primary.withValues(alpha: 0.1),
          child: Text(
            (user['full_name'] as String? ?? '?')[0].toUpperCase(),
            style: const TextStyle(
                color: AppColors.primary, fontWeight: FontWeight.bold),
          ),
        ),
        title: Text(user['full_name'] ?? '-',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(user['email'] ?? '-',
                style: const TextStyle(fontSize: 12)),
            const SizedBox(height: 4),
            Row(
              children: [
                _Tag(_roleLabels[role] ?? role, AppColors.primary),
                const SizedBox(width: 6),
                _Tag(
                  isActive ? 'Aktif' : 'Nonaktif',
                  isActive ? AppColors.normal : AppColors.kosong,
                ),
              ],
            ),
          ],
        ),
        trailing: PopupMenuButton<String>(
          onSelected: (v) => _onAction(context, ref, v),
          itemBuilder: (_) => [
            const PopupMenuItem(value: 'edit', child: Text('Edit')),
            const PopupMenuItem(
                value: 'reset', child: Text('Reset Password')),
            PopupMenuItem(
              value: 'toggle',
              child: Text(isActive ? 'Nonaktifkan' : 'Aktifkan'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _onAction(
      BuildContext context, WidgetRef ref, String action) async {
    final id = user['id'] as String;
    switch (action) {
      case 'edit':
        await showDialog(
          context: context,
          builder: (_) => _UserFormDialog(existing: user, onSuccess: onChanged),
        );
        break;
      case 'reset':
        await showDialog(
          context: context,
          builder: (_) => _ResetPasswordDialog(userId: id),
        );
        break;
      case 'toggle':
        final isActive = user['is_active'] == true;
        try {
          if (isActive) {
            await ApiClient().dio.delete(ApiEndpoints.user(id));
          } else {
            await ApiClient()
                .dio
                .put(ApiEndpoints.user(id), data: {'is_active': true});
          }
          onChanged();
        } catch (e) {
          if (context.mounted) _snack(context, 'Gagal: $e', isError: true);
        }
        break;
    }
  }
}

class _Tag extends StatelessWidget {
  final String text;
  final Color color;
  const _Tag(this.text, this.color);

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(text,
            style: TextStyle(
                fontSize: 11, color: color, fontWeight: FontWeight.w600)),
      );
}

// ── Create / Edit dialog ─────────────────────────────────────────────────────

class _UserFormDialog extends StatefulWidget {
  final Map<String, dynamic>? existing;
  final VoidCallback onSuccess;
  const _UserFormDialog({this.existing, required this.onSuccess});

  @override
  State<_UserFormDialog> createState() => _UserFormDialogState();
}

class _UserFormDialogState extends State<_UserFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name;
  late final TextEditingController _email;
  final _password = TextEditingController();
  String _role = 'perawat';
  bool _saving = false;

  bool get _isEdit => widget.existing != null;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.existing?['full_name'] ?? '');
    _email = TextEditingController(text: widget.existing?['email'] ?? '');
    _role = widget.existing?['role'] ?? 'perawat';
  }

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      if (_isEdit) {
        await ApiClient().dio.put(
          ApiEndpoints.user(widget.existing!['id']),
          data: {'full_name': _name.text.trim()},
        );
      } else {
        await ApiClient().dio.post(ApiEndpoints.users, data: {
          'full_name': _name.text.trim(),
          'email': _email.text.trim(),
          'password': _password.text,
          'role': _role,
        });
      }
      if (mounted) Navigator.pop(context);
      widget.onSuccess();
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        _snack(context, 'Gagal menyimpan: $e', isError: true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEdit ? 'Edit Pengguna' : 'Tambah Pengguna'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _name,
                decoration: const InputDecoration(labelText: 'Nama Lengkap'),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Wajib diisi' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _email,
                enabled: !_isEdit,
                decoration: const InputDecoration(labelText: 'Email'),
                keyboardType: TextInputType.emailAddress,
                validator: (v) {
                  if (_isEdit) return null;
                  if (v == null || v.trim().isEmpty) return 'Wajib diisi';
                  if (!v.contains('@')) return 'Email tidak valid';
                  return null;
                },
              ),
              if (!_isEdit) ...[
                const SizedBox(height: 12),
                TextFormField(
                  controller: _password,
                  decoration: const InputDecoration(labelText: 'Password'),
                  obscureText: true,
                  validator: (v) => (v == null || v.length < 6)
                      ? 'Minimal 6 karakter'
                      : null,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: _role,
                  decoration: const InputDecoration(labelText: 'Role'),
                  items: _roleLabels.entries
                      .map((e) => DropdownMenuItem(
                          value: e.key, child: Text(e.value)))
                      .toList(),
                  onChanged: (v) => setState(() => _role = v ?? 'perawat'),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.pop(context),
          child: const Text('Batal'),
        ),
        ElevatedButton(
          onPressed: _saving ? null : _submit,
          child: _saving
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Simpan'),
        ),
      ],
    );
  }
}

// ── Reset password dialog ────────────────────────────────────────────────────

class _ResetPasswordDialog extends StatefulWidget {
  final String userId;
  const _ResetPasswordDialog({required this.userId});

  @override
  State<_ResetPasswordDialog> createState() => _ResetPasswordDialogState();
}

class _ResetPasswordDialogState extends State<_ResetPasswordDialog> {
  final _password = TextEditingController();
  bool _saving = false;

  @override
  void dispose() {
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_password.text.length < 6) {
      _snack(context, 'Password minimal 6 karakter', isError: true);
      return;
    }
    setState(() => _saving = true);
    try {
      await ApiClient().dio.post(
        ApiEndpoints.userResetPassword(widget.userId),
        data: {'new_password': _password.text},
      );
      if (mounted) {
        Navigator.pop(context);
        _snack(context, 'Password berhasil direset');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        _snack(context, 'Gagal: $e', isError: true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Reset Password'),
      content: TextField(
        controller: _password,
        decoration: const InputDecoration(labelText: 'Password Baru'),
        obscureText: true,
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.pop(context),
          child: const Text('Batal'),
        ),
        ElevatedButton(
          onPressed: _saving ? null : _submit,
          child: _saving
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Reset'),
        ),
      ],
    );
  }
}

void _snack(BuildContext context, String msg, {bool isError = false}) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
    content: Text(msg),
    backgroundColor: isError ? AppColors.abnormal : AppColors.normal,
  ));
}

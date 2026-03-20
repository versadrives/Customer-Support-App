import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../api/auth_store.dart';
import 'login_screen.dart';

class EngineerProfileScreen extends StatefulWidget {
  const EngineerProfileScreen({super.key, required this.engineerName});
  final String engineerName;

  @override
  State<EngineerProfileScreen> createState() => _EngineerProfileScreenState();
}

class _EngineerProfileScreenState extends State<EngineerProfileScreen> {
  final _oldPw = TextEditingController();
  final _newPw = TextEditingController();
  final _confirmPw = TextEditingController();
  bool _saving = false;

  @override
  void dispose() {
    _oldPw.dispose();
    _newPw.dispose();
    _confirmPw.dispose();
    super.dispose();
  }

  Future<void> _logout() async {
    AuthStore.clear();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const LoginScreen()), (r) => false);
  }

  Future<void> _changePassword() async {
    if (_oldPw.text.isEmpty || _newPw.text.isEmpty || _confirmPw.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Fill all password fields')));
      return;
    }
    if (_newPw.text != _confirmPw.text) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('New password does not match')));
      return;
    }
    setState(() => _saving = true);
    try {
      await ApiClient.changePassword(oldPassword: _oldPw.text, newPassword: _newPw.text);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Password changed. Please log in again.')));
      await _logout();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Change password failed. $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
      children: [
        const Text('Profile & Settings', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        const Text('Manage your account and security.', style: TextStyle(color: Color(0xFF6B7B8A))),
        const SizedBox(height: 10),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton.icon(onPressed: _logout, icon: const Icon(Icons.logout), label: const Text('Logout')),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFE2E8F0)),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 18, offset: const Offset(0, 10))],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Account', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              Row(
                children: [
                  CircleAvatar(
                    radius: 22,
                    backgroundColor: const Color(0xFFE6F4F1),
                    child: const Icon(Icons.person, color: Color(0xFF0F766E)),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(widget.engineerName, style: const TextStyle(fontWeight: FontWeight.w600)),
                      Text(AuthStore.username ?? '-', style: const TextStyle(color: Color(0xFF64748B))),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 4),
              const SizedBox(height: 6),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFE2E8F0)),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 18, offset: const Offset(0, 10))],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Change Password', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              TextField(
                controller: _oldPw,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Old password'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _newPw,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'New password'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _confirmPw,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Confirm new password'),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _saving ? null : _changePassword,
                  icon: const Icon(Icons.lock_reset),
                  label: Text(_saving ? 'Updating...' : 'Update Password'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

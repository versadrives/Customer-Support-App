import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/api_client.dart';
import '../api/auth_store.dart';
import '../models.dart';
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
  bool _checkingUpdate = true;
  bool _openingUpdate = false;
  String _appVersionLabel = '-';
  AppUpdateInfo? _updateInfo;

  @override
  void initState() {
    super.initState();
    _loadUpdateInfo();
  }

  @override
  void dispose() {
    _oldPw.dispose();
    _newPw.dispose();
    _confirmPw.dispose();
    super.dispose();
  }

  Future<void> _loadUpdateInfo() async {
    setState(() => _checkingUpdate = true);
    PackageInfo? packageInfo;
    try {
      packageInfo = await PackageInfo.fromPlatform();
      if (!mounted) return;
      setState(() {
        _appVersionLabel = '${packageInfo!.version}+${packageInfo.buildNumber}';
      });
    } catch (_) {}

    try {
      final updateInfo = await ApiClient.fetchAppUpdateInfo();
      if (!mounted) return;
      setState(() {
        _updateInfo = updateInfo;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _updateInfo = null;
      });
    } finally {
      if (mounted) setState(() => _checkingUpdate = false);
    }
  }

  Future<void> _downloadUpdate() async {
    final info = _updateInfo;
    if (info == null || info.apkUrl.isEmpty) return;
    setState(() => _openingUpdate = true);
    try {
      final uri = Uri.parse(info.apkUrl);
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not open download link.')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update download failed. $e')));
      }
    } finally {
      if (mounted) setState(() => _openingUpdate = false);
    }
  }

  bool get _hasUpdate {
    final info = _updateInfo;
    if (info == null) return false;
    final parts = _appVersionLabel.split('+');
    final currentBuild = parts.length > 1 ? int.tryParse(parts[1]) ?? 0 : 0;
    return info.buildNumber > currentBuild;
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
                    backgroundColor: const Color(0xFFE6EEF7),
                    child: const Icon(Icons.person, color: Color(0xFF0E61A5)),
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
              const Text('App Update', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              Text('Current Version: $_appVersionLabel', style: const TextStyle(color: Color(0xFF64748B))),
              const SizedBox(height: 8),
              if (_checkingUpdate)
                const Text('Checking for updates...', style: TextStyle(color: Color(0xFF64748B)))
              else if (_updateInfo == null)
                const Text('Unable to check updates right now.', style: TextStyle(color: Color(0xFF64748B)))
              else ...[
                Text(
                  _hasUpdate ? 'New version available: ${_updateInfo!.version}+${_updateInfo!.buildNumber}' : 'App is up to date.',
                  style: const TextStyle(color: Color(0xFF334155)),
                ),
                if (_updateInfo!.notes.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(_updateInfo!.notes, style: const TextStyle(color: Color(0xFF64748B))),
                ],
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: _hasUpdate && !_openingUpdate ? _downloadUpdate : null,
                        icon: const Icon(Icons.system_update_alt),
                        label: Text(_openingUpdate ? 'Opening...' : 'Download Update'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    IconButton(
                      tooltip: 'Refresh update check',
                      onPressed: _checkingUpdate ? null : _loadUpdateInfo,
                      icon: const Icon(Icons.refresh),
                    ),
                  ],
                ),
              ],
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


import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../api/auth_store.dart';
import 'engineer_home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _id = TextEditingController();
  final _pw = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _id.dispose();
    _pw.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);
    try {
      const role = AppRole.engineer;
      await ApiClient.login(username: _id.text.trim(), password: _pw.text, role: role);
      final me = await ApiClient.fetchMe();
      if (!mounted) return;
      if (role == AppRole.engineer && me['engineer_profile_id'] == null) {
        AuthStore.clear();
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('This user is not an engineer profile.')));
        return;
      }
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => EngineerHomeScreen(engineerName: _id.text.trim()),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Login failed. ${e.toString()}')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFFE6F7F4), Color(0xFFF2F7F9), Color(0xFFF8FAFF)]),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Stack(
            children: [
              Positioned(
                right: -60,
                top: -40,
                child: Container(
                  width: 220,
                  height: 220,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(colors: [Color(0xFF0EA5A4), Color(0xFF34D399)]),
                  ),
                ),
              ),
              Positioned(
                left: -40,
                bottom: -30,
                child: Container(
                  width: 180,
                  height: 180,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(colors: [Color(0xFF14B8A6), Color(0xFF38BDF8)]),
                  ),
                ),
              ),
              Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 460),
                    child: Column(
                      children: [
                        Container(
                          width: 86,
                          height: 86,
                          decoration: BoxDecoration(
                            color: const Color(0xFF0F766E),
                            borderRadius: BorderRadius.circular(28),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFF0F766E).withValues(alpha: 0.32),
                                blurRadius: 28,
                                offset: const Offset(0, 12),
                              )
                            ],
                          ),
                          child: const Icon(Icons.support_agent, color: Colors.white, size: 44),
                        ),
                        const SizedBox(height: 16),
                        const Text('Customer Support', style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 6),
                        const Text('Field service workflow for engineers', style: TextStyle(color: Color(0xFF5A7485))),
                        const SizedBox(height: 22),
                        Container(
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.92),
                            borderRadius: BorderRadius.circular(26),
                            border: Border.all(color: const Color(0xFFE2E8F0)),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.06),
                                blurRadius: 24,
                                offset: const Offset(0, 12),
                              )
                            ],
                          ),
                          padding: const EdgeInsets.all(20),
                          child: Form(
                            key: _formKey,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Sign in', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                                const SizedBox(height: 4),
                                const Text('Use your engineer account', style: TextStyle(color: Color(0xFF6B7B8A))),
                                const SizedBox(height: 14),
                                TextFormField(
                                  controller: _id,
                                  decoration: const InputDecoration(labelText: 'Engineer Username', prefixIcon: Icon(Icons.person_outline)),
                                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                                ),
                                const SizedBox(height: 10),
                                TextFormField(
                                  controller: _pw,
                                  obscureText: true,
                                  decoration: const InputDecoration(labelText: 'Password', prefixIcon: Icon(Icons.lock_outline)),
                                  validator: (v) => (v == null || v.length < 4) ? 'Minimum 4 characters' : null,
                                ),
                                const SizedBox(height: 16),
                                SizedBox(
                                  width: double.infinity,
                                  child: FilledButton.icon(
                                    onPressed: _isLoading ? null : _login,
                                    icon: const Icon(Icons.login),
                                    label: Padding(
                                      padding: const EdgeInsets.symmetric(vertical: 10),
                                      child: Text(_isLoading ? 'Signing in...' : 'Continue'),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        )
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

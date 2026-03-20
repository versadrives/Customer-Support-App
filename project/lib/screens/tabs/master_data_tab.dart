import 'package:flutter/material.dart';

import '../../api/api_client.dart';
import '../../models.dart';
import '../../widgets/panel.dart';

class MasterDataTab extends StatefulWidget {
  const MasterDataTab({super.key, required this.onRefresh});
  final VoidCallback onRefresh;
  @override
  State<MasterDataTab> createState() => _MasterDataTabState();
}

class _MasterDataTabState extends State<MasterDataTab> {
  final _engUsername = TextEditingController();
  final _engPassword = TextEditingController();
  final _engFirst = TextEditingController();
  final _engLast = TextEditingController();
  final _engPhone = TextEditingController();
  final _engSearch = TextEditingController();

  List<EngineerProfile> _engineers = [];
  bool _loading = true;
  bool _activeOnly = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _engineers = await ApiClient.fetchEngineers();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to load data. $e')));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addEngineer() async {
    if (_engUsername.text.trim().isEmpty || _engPassword.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Username and password required')));
      return;
    }
    try {
      await ApiClient.createEngineer(
        username: _engUsername.text.trim(),
        password: _engPassword.text.trim(),
        phone: _engPhone.text.trim(),
        firstName: _engFirst.text.trim(),
        lastName: _engLast.text.trim(),
      );
      _engUsername.clear();
      _engPassword.clear();
      _engFirst.clear();
      _engLast.clear();
      _engPhone.clear();
      await _load();
      if (!mounted) return;
      widget.onRefresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Create engineer failed. $e')));
    }
  }

  Future<void> _editEngineer(EngineerProfile engineer) async {
    final first = TextEditingController(text: engineer.firstName);
    final last = TextEditingController(text: engineer.lastName);
    final phone = TextEditingController(text: engineer.phone);
    final password = TextEditingController();
    bool active = engineer.active;

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Text('Edit ${engineer.displayName}'),
              content: SingleChildScrollView(
                child: Column(
                  children: [
                    TextField(controller: first, decoration: const InputDecoration(labelText: 'First name')),
                    const SizedBox(height: 8),
                    TextField(controller: last, decoration: const InputDecoration(labelText: 'Last name')),
                    const SizedBox(height: 8),
                    TextField(controller: phone, decoration: const InputDecoration(labelText: 'Phone')),
                    const SizedBox(height: 8),
                    TextField(controller: password, decoration: const InputDecoration(labelText: 'New password (optional)'), obscureText: true),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Text('Active'),
                        const Spacer(),
                        Switch(
                          value: active,
                          onChanged: (v) => setDialogState(() => active = v),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
                FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Save')),
              ],
            );
          },
        );
      },
    );

    if (saved != true) return;
    try {
      await ApiClient.updateEngineer(
        id: engineer.id,
        firstName: first.text.trim(),
        lastName: last.text.trim(),
        phone: phone.text.trim(),
        password: password.text.trim(),
        active: active,
      );
      await _load();
      if (!mounted) return;
      widget.onRefresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update failed. $e')));
    } finally {
      first.dispose();
      last.dispose();
      phone.dispose();
      password.dispose();
    }
  }

  Future<void> _toggleActive(EngineerProfile engineer) async {
    try {
      await ApiClient.updateEngineer(id: engineer.id, active: !engineer.active);
      await _load();
      if (!mounted) return;
      widget.onRefresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update failed. $e')));
    }
  }

  @override
  void dispose() {
    _engUsername.dispose();
    _engPassword.dispose();
    _engFirst.dispose();
    _engLast.dispose();
    _engPhone.dispose();
    _engSearch.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    final query = _engSearch.text.trim().toLowerCase();
    final filtered = _engineers.where((e) {
      final matchesQuery = query.isEmpty ||
          e.username.toLowerCase().contains(query) ||
          e.displayName.toLowerCase().contains(query) ||
          e.phone.toLowerCase().contains(query);
      final matchesActive = !_activeOnly || e.active;
      return matchesQuery && matchesActive;
    }).toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Manage engineers', style: TextStyle(color: Color(0xFF5A6E7A))),
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _engSearch,
                decoration: const InputDecoration(prefixIcon: Icon(Icons.search), labelText: 'Search engineers'),
                onChanged: (_) => setState(() {}),
              ),
            ),
            const SizedBox(width: 12),
            FilterChip(
              selected: _activeOnly,
              label: const Text('Active only'),
              onSelected: (v) => setState(() => _activeOnly = v),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Panel(
          title: 'Engineers',
          icon: Icons.engineering_outlined,
          child: Column(
            children: [
              TextField(controller: _engUsername, decoration: const InputDecoration(labelText: 'Username')),
              const SizedBox(height: 8),
              TextField(controller: _engPassword, decoration: const InputDecoration(labelText: 'Password'), obscureText: true),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(child: TextField(controller: _engFirst, decoration: const InputDecoration(labelText: 'First name'))),
                  const SizedBox(width: 8),
                  Expanded(child: TextField(controller: _engLast, decoration: const InputDecoration(labelText: 'Last name'))),
                ],
              ),
              const SizedBox(height: 8),
              TextField(controller: _engPhone, decoration: const InputDecoration(labelText: 'Phone')),
              const SizedBox(height: 10),
              SizedBox(width: double.infinity, child: FilledButton(onPressed: _addEngineer, child: const Text('Add Engineer'))),
              const SizedBox(height: 12),
              ...filtered.map(
                (e) => Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: Colors.white, border: Border.all(color: const Color(0xFFE3EAF0))),
                  child: ListTile(
                    leading: const CircleAvatar(child: Icon(Icons.person_outline)),
                    title: Text(e.displayName),
                    subtitle: Text(e.username),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(icon: const Icon(Icons.edit), tooltip: 'Edit', onPressed: () => _editEngineer(e)),
                        IconButton(
                          icon: Icon(e.active ? Icons.block : Icons.check_circle, color: e.active ? Colors.red : Colors.green),
                          tooltip: e.active ? 'Deactivate' : 'Activate',
                          onPressed: () => _toggleActive(e),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

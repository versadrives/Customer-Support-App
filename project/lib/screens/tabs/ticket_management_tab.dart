import 'package:flutter/material.dart';

import '../../api/api_client.dart';
import '../../models.dart';
import '../../utils/download_helper.dart';
import '../../widgets/panel.dart';
import '../../widgets/status_pill.dart';

class TicketManagementTab extends StatefulWidget {
  const TicketManagementTab({super.key, required this.onRefresh});
  final VoidCallback onRefresh;
  @override
  TicketManagementTabState createState() => TicketManagementTabState();
}

class TicketManagementTabState extends State<TicketManagementTab> {
  final _customerName = TextEditingController();
  final _customerPhone = TextEditingController();
  final _customerAddress = TextEditingController();
  final _location = TextEditingController();
  final _issue = TextEditingController();
  final _model = TextEditingController();
  final _serialNumber = TextEditingController();
  final _mfgDate = TextEditingController();
  final _search = TextEditingController();

  List<AppTicket> _tickets = [];
  List<EngineerProfile> _engineers = [];
  final Map<String, int> _reportByTicketId = {};
  bool _loading = true;
  TicketStatus? _statusFilter;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        ApiClient.fetchTickets(),
        ApiClient.fetchEngineers(),
        ApiClient.fetchReports(),
      ]);
      _tickets = results[0] as List<AppTicket>;
      _engineers = results[1] as List<EngineerProfile>;
      final reports = results[2] as List<ReportData>;
      _reportByTicketId
        ..clear()
        ..addEntries(reports.map((r) => MapEntry(r.ticketId, r.id)));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to load data. $e')));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _create() async {
    if (_customerName.text.trim().isEmpty ||
        _customerPhone.text.trim().isEmpty ||
        _customerAddress.text.trim().isEmpty ||
        _location.text.trim().isEmpty ||
        _issue.text.trim().isEmpty ||
        _model.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Fill all required ticket fields')));
      return;
    }
    try {
      await ApiClient.createTicket(
        customerName: _customerName.text.trim(),
        customerPhone: _customerPhone.text.trim(),
        customerAddress: _customerAddress.text.trim(),
        location: _location.text.trim(),
        issue: _issue.text.trim(),
        model: _model.text.trim(),
        serialNumber: _serialNumber.text.trim(),
        mfgDate: _mfgDate.text.trim(),
      );
      _customerName.clear();
      _customerPhone.clear();
      _customerAddress.clear();
      _location.clear();
      _issue.clear();
      _model.clear();
      _serialNumber.clear();
      _mfgDate.clear();
      await _load();
      if (!mounted) return;
      widget.onRefresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Create failed. $e')));
    }
  }

  Future<void> _pickMfgDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: now,
      firstDate: DateTime(1990),
      lastDate: now,
    );
    if (picked == null) return;
    final yyyy = picked.year.toString().padLeft(4, '0');
    final mm = picked.month.toString().padLeft(2, '0');
    final dd = picked.day.toString().padLeft(2, '0');
    setState(() => _mfgDate.text = '$yyyy-$mm-$dd');
  }

  Future<void> _assign(AppTicket t, EngineerProfile e) async {
    try {
      await ApiClient.assignTicket(ticketId: t.id, engineerId: e.id);
      await _load();
      if (!mounted) return;
      widget.onRefresh();
    } catch (err) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Assign failed. $err')));
    }
  }

  @override
  void dispose() {
    _customerName.dispose();
    _customerPhone.dispose();
    _customerAddress.dispose();
    _location.dispose();
    _issue.dispose();
    _model.dispose();
    _serialNumber.dispose();
    _mfgDate.dispose();
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    final query = _search.text.trim().toLowerCase();
    final filteredTickets = _tickets.where((t) {
      final matchesQuery = query.isEmpty ||
          t.ticketId.toLowerCase().contains(query) ||
          t.customerName.toLowerCase().contains(query) ||
          t.issue.toLowerCase().contains(query);
      final matchesStatus = _statusFilter == null || t.status == _statusFilter;
      return matchesQuery && matchesStatus;
    }).toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Create and assign tickets', style: TextStyle(color: Color(0xFF5A6E7A))),
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _search,
                decoration: const InputDecoration(prefixIcon: Icon(Icons.search), labelText: 'Search tickets'),
                onChanged: (_) => setState(() {}),
              ),
            ),
            const SizedBox(width: 12),
            DropdownButton<TicketStatus?>(
              value: _statusFilter,
              onChanged: (v) => setState(() => _statusFilter = v),
              items: const [
                DropdownMenuItem(value: null, child: Text('All')),
                DropdownMenuItem(value: TicketStatus.open, child: Text('Open')),
                DropdownMenuItem(value: TicketStatus.assigned, child: Text('Assigned')),
                DropdownMenuItem(value: TicketStatus.inProgress, child: Text('In Progress')),
                DropdownMenuItem(value: TicketStatus.completed, child: Text('Completed')),
              ],
            ),
          ],
        ),
        const SizedBox(height: 8),
        Panel(
          title: 'Create New Ticket',
          icon: Icons.note_add_outlined,
            child: Column(
              children: [
                TextField(controller: _customerName, decoration: const InputDecoration(labelText: 'Customer')),
                const SizedBox(height: 8),
                TextField(controller: _customerPhone, decoration: const InputDecoration(labelText: 'Phone number')),
                const SizedBox(height: 8),
                TextField(controller: _customerAddress, decoration: const InputDecoration(labelText: 'Address')),
                const SizedBox(height: 8),
                TextField(controller: _location, decoration: const InputDecoration(labelText: 'Location')),
                const SizedBox(height: 8),
                TextField(controller: _issue, maxLines: 2, decoration: const InputDecoration(labelText: 'Issue Description')),
                const SizedBox(height: 8),
                TextField(controller: _model, decoration: const InputDecoration(labelText: 'Model')),
                const SizedBox(height: 8),
                TextField(controller: _serialNumber, decoration: const InputDecoration(labelText: 'Serial Number (optional)')),
                const SizedBox(height: 8),
                TextField(
                  controller: _mfgDate,
                  readOnly: true,
                  decoration: InputDecoration(
                    labelText: 'MFG Date (optional)',
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.calendar_today),
                      onPressed: _pickMfgDate,
                    ),
                  ),
                  onTap: _pickMfgDate,
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(onPressed: _create, icon: const Icon(Icons.add_circle_outline), label: const Text('Create Ticket (OPEN)')),
                ),
              ],
            ),
          ),
        Panel(
          title: 'Assign Tickets',
          icon: Icons.assignment_ind_outlined,
          child: Column(
            children: filteredTickets.map((t) {
              return Container(
                margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE0E8EE))),
                child: ListTile(
                  title: Text('${t.ticketId}  ${t.customerName}'),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 4),
                      Text(t.issue),
                      const SizedBox(height: 4),
                      Text('Created by: ${t.createdByName ?? '-'}'),
                      const SizedBox(height: 2),
                      Text('Created at: ${t.createdAt.toLocal()}'),
                      const SizedBox(height: 2),
                      Text('Model: ${t.model.isEmpty ? '-' : t.model}'),
                      const SizedBox(height: 2),
                      Text('Serial: ${t.serialNumber ?? '-'}'),
                      const SizedBox(height: 2),
                      Text('MFG Date: ${t.mfgDate?.toLocal().toString() ?? '-'}'),
                      const SizedBox(height: 6),
                      StatusPill(status: t.status),
                    ],
                  ),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (t.status == TicketStatus.completed && _reportByTicketId.containsKey(t.ticketId))
                        IconButton(
                          tooltip: 'Download PDF',
                          icon: const Icon(Icons.download),
                          onPressed: () async {
                            final reportId = _reportByTicketId[t.ticketId]!;
                            if (!mounted) return;
                            try {
                              final bytes = await ApiClient.fetchReportPdf(reportId);
                              await downloadBytes(bytes, 'report_${t.ticketId}.pdf');
                            } catch (e) {
                              if (!mounted) return;
                              // ignore: use_build_context_synchronously
                              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Download failed. $e')));
                            }
                          },
                        ),
                      DropdownButton<int>(
                  borderRadius: BorderRadius.circular(12),
                  hint: const Text('Assign'),
                  value: t.engineerId,
                        items: _engineers.map((e) => DropdownMenuItem(value: e.id, child: Text(e.displayName))).toList(),
                        onChanged: (id) {
                          final eng = _engineers.where((e) => e.id == id).toList();
                          if (id == null || eng.isEmpty) return;
                          _assign(t, eng.first);
                        },
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}

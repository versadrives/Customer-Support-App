import 'package:flutter/material.dart';

import '../../api/api_client.dart';
import '../../models.dart';
import '../../widgets/status_pill.dart';
import '../task_detail_screen.dart';

class EngineerTasksTab extends StatefulWidget {
  const EngineerTasksTab({super.key, required this.engineerName, required this.onRefresh});
  final String engineerName;
  final VoidCallback onRefresh;

  @override
  State<EngineerTasksTab> createState() => _EngineerTasksTabState();
}

class _EngineerTasksTabState extends State<EngineerTasksTab> {
  List<AppTicket> _tickets = [];
  bool _loading = true;
  final _search = TextEditingController();
  TicketStatus? _statusFilter;
  bool _sortNewest = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _tickets = await ApiClient.fetchTickets();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _refresh() async {
    await _load();
    widget.onRefresh();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    final query = _search.text.trim().toLowerCase();
    const allowedEngineerStatuses = [TicketStatus.assigned, TicketStatus.inProgress, TicketStatus.completed];
    var visible = _tickets.where((t) {
      final matchesQuery = query.isEmpty ||
          t.ticketId.toLowerCase().contains(query) ||
          t.customerName.toLowerCase().contains(query) ||
          t.issue.toLowerCase().contains(query);
      final matchesStatus = allowedEngineerStatuses.contains(t.status) &&
          t.status != TicketStatus.open && // EXPLICIT: Exclude open tasks
          (_statusFilter == null || t.status == _statusFilter);
      return matchesQuery && matchesStatus;
    }).toList();

    visible.sort((a, b) => _sortNewest ? b.createdAt.compareTo(a.createdAt) : a.createdAt.compareTo(b.createdAt));

    if (visible.isEmpty) return const Center(child: Text('No assigned, in-progress, or completed tasks yet.'));

    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
        children: [
          const Text('My Tasks', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('', style: TextStyle(color: Color(0xFF6B7B8A))),
          const SizedBox(height: 12),
          TextField(
            controller: _search,
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), labelText: 'Search tickets, customers, issues'),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _StatusChip(
                label: 'All Tasks',
                selected: _statusFilter == null,
                onTap: () => setState(() => _statusFilter = null),
              ),
              _StatusChip(
                label: 'Assigned',
                selected: _statusFilter == TicketStatus.assigned,
                onTap: () => setState(() => _statusFilter = TicketStatus.assigned),
              ),
              _StatusChip(
                label: 'In Progress',
                selected: _statusFilter == TicketStatus.inProgress,
                onTap: () => setState(() => _statusFilter = TicketStatus.inProgress),
              ),
              _StatusChip(
                label: 'Completed',
                selected: _statusFilter == TicketStatus.completed,
                onTap: () => setState(() => _statusFilter = TicketStatus.completed),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              const Text('Sort by date', style: TextStyle(color: Color(0xFF5A6E7A))),
              TextButton.icon(
                onPressed: () => setState(() => _sortNewest = !_sortNewest),
                icon: Icon(_sortNewest ? Icons.south : Icons.north, size: 16),
                label: Text(_sortNewest ? 'Newest' : 'Oldest'),
              ),
              const Spacer(),
              IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
            ],
          ),
          const SizedBox(height: 6),
          ...visible.map((t) {
            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFE2E8F0)),
                boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 18, offset: const Offset(0, 10))],
              ),
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                title: Text('${t.ticketId}  ${t.customerName}', style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 6),
                    Text(t.issue),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        const Icon(Icons.call, size: 14, color: Color(0xFF64748B)),
                        const SizedBox(width: 4),
                        Text(t.customerPhone.isEmpty ? '-' : t.customerPhone),
                        const SizedBox(width: 12),
                        const Icon(Icons.location_on_outlined, size: 14, color: Color(0xFF64748B)),
                        const SizedBox(width: 4),
                        Expanded(child: Text(t.customerAddress.isEmpty ? '-' : t.customerAddress, overflow: TextOverflow.ellipsis)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    StatusPill(status: t.status),
                  ],
                ),
                trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                onTap: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => TaskDetailScreen(ticket: t, engineerName: widget.engineerName)));
                  _refresh();
                },
              ),
            );
          }),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF0F766E) : Colors.white,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: selected ? const Color(0xFF0F766E) : const Color(0xFFE2E8F0)),
          boxShadow: [
            if (selected)
              BoxShadow(
                color: const Color(0xFF0F766E).withValues(alpha: 0.18),
                blurRadius: 12,
                offset: const Offset(0, 6),
              )
          ],
        ),
        child: Text(
          label,
          style: TextStyle(color: selected ? Colors.white : const Color(0xFF334155), fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}

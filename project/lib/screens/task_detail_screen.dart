import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../api/auth_store.dart';
import '../models.dart';
import '../screens/qr_scan_screen.dart';
import '../widgets/panel.dart';
import '../widgets/status_pill.dart';

class TaskDetailScreen extends StatefulWidget {
  const TaskDetailScreen({super.key, required this.ticket, required this.engineerName});
  final AppTicket ticket;
  final String engineerName;

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  final _serviceProviderCode = TextEditingController();
  final _numberOfFans = TextEditingController();
  final _serialNumber = TextEditingController();
  final _problemIdentified = TextEditingController();
  final _action = TextEditingController();
  final _pcbBoardNumber = TextEditingController();
  final _comments = TextEditingController();
  final _chargesCollected = TextEditingController();
  final _kmsDriven = TextEditingController();
  bool _isCustomerPolite = true;
  bool _difficultToAttend = false;

  @override
  void dispose() {
    _serviceProviderCode.dispose();
    _numberOfFans.dispose();
    _serialNumber.dispose();
    _problemIdentified.dispose();
    _action.dispose();
    _pcbBoardNumber.dispose();
    _comments.dispose();
    _chargesCollected.dispose();
    _kmsDriven.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    try {
      await ApiClient.startTicket(ticketId: widget.ticket.id);
      setState(() {
        widget.ticket.status = TicketStatus.inProgress;
        widget.ticket.startedAt = DateTime.now();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to start job. $e')));
    }
  }

  Future<void> _complete() async {
    if (_serviceProviderCode.text.trim().isEmpty ||
        _numberOfFans.text.trim().isEmpty ||
        _serialNumber.text.trim().isEmpty ||
        _problemIdentified.text.trim().isEmpty ||
        _action.text.trim().isEmpty ||
        _comments.text.trim().isEmpty ||
        _chargesCollected.text.trim().isEmpty ||
        _kmsDriven.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Fill all report fields')));
      return;
    }
    final numberOfFans = int.tryParse(_numberOfFans.text.trim());
    final kmsDriven = int.tryParse(_kmsDriven.text.trim());
    if (numberOfFans == null || kmsDriven == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter valid numbers for fans and KM\'s driven')));
      return;
    }
    try {
      await ApiClient.completeTicket(
        ticketId: widget.ticket.id,
        serviceProviderCode: _serviceProviderCode.text.trim(),
        numberOfFans: numberOfFans,
        serialNumber: _serialNumber.text.trim(),
        problemIdentified: _problemIdentified.text.trim(),
        actionTaken: _action.text.trim(),
        pcbBoardNumber: _pcbBoardNumber.text.trim(),
        comments: _comments.text.trim(),
        chargesCollected: _chargesCollected.text.trim(),
        kmsDriven: kmsDriven.toString(),
        isCustomerPolite: _isCustomerPolite,
        difficultToAttend: _difficultToAttend,
      );
      widget.ticket.status = TicketStatus.completed;
      widget.ticket.completedAt = DateTime.now();
      if (!mounted) return;
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to submit report. $e')));
    }
  }

  Future<void> _scanInto(TextEditingController controller, {required String title}) async {
    final value = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => QrScanScreen(title: title)),
    );
    if (!mounted || value == null || value.trim().isEmpty) return;
    controller.text = value.trim();
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.ticket;
    final canStart = AuthStore.role == AppRole.engineer && t.status == TicketStatus.assigned;
    return Scaffold(
      appBar: AppBar(title: Text('Task ${t.ticketId}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Panel(
            title: 'Task Details',
            icon: Icons.info_outline,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Customer: ${t.customerName}', style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text('Phone: ${t.customerPhone.isEmpty ? '-' : t.customerPhone}'),
                const SizedBox(height: 4),
                Text('Address: ${t.customerAddress.isEmpty ? '-' : t.customerAddress}'),
                const SizedBox(height: 4),
                Text('Location: ${t.location}'),
                const SizedBox(height: 8),
                Text('Issue: ${t.issue}'),
                const SizedBox(height: 8),
                Text('Model: ${t.model.isEmpty ? '-' : t.model}'),
                const SizedBox(height: 4),
                Text('Serial: ${t.serialNumber ?? '-'}'),
                const SizedBox(height: 4),
                Text('MFG Date: ${t.mfgDate?.toLocal().toString() ?? '-'}'),
                const SizedBox(height: 8),
                StatusPill(status: t.status),
                if (canStart) ...[
                  const SizedBox(height: 12),
                  FilledButton.icon(onPressed: _start, icon: const Icon(Icons.play_arrow), label: const Text('Start Job')),
                ],
                if (!canStart && t.status == TicketStatus.assigned && AuthStore.role != AppRole.engineer) ...[
                  const SizedBox(height: 12),
                  const Text('Only the assigned engineer can start this job.', style: TextStyle(color: Color(0xFF5A6E7A))),
                ],
              ],
            ),
          ),
          Panel(
            title: 'Service Report',
            icon: Icons.description_outlined,
            child: Column(
              children: [
                TextField(controller: _serviceProviderCode, decoration: const InputDecoration(labelText: 'Service Provider Code')),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _numberOfFans,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Number of fans'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: _serialNumber,
                        readOnly: true,
                        decoration: InputDecoration(
                          labelText: 'Serial number',
                          helperText: 'Scan required',
                          suffixIcon: IconButton(
                            tooltip: 'Scan serial number',
                            icon: const Icon(Icons.qr_code_scanner),
                            onPressed: () => _scanInto(_serialNumber, title: 'Scan Serial Number'),
                          ),
                        ),
                        onTap: () => _scanInto(_serialNumber, title: 'Scan Serial Number'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                TextField(controller: _problemIdentified, decoration: const InputDecoration(labelText: 'Problem identified')),
                const SizedBox(height: 8),
                TextField(
                  controller: _action,
                  decoration: const InputDecoration(labelText: 'Action taken'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _pcbBoardNumber,
                  decoration: InputDecoration(
                    labelText: 'PCB board number',
                    helperText: 'Optional',
                    suffixIcon: IconButton(
                      tooltip: 'Scan PCB barcode',
                      icon: const Icon(Icons.qr_code_scanner),
                      onPressed: () => _scanInto(_pcbBoardNumber, title: 'Scan PCB Barcode (Optional)'),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                TextField(controller: _comments, decoration: const InputDecoration(labelText: 'Comments')),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _chargesCollected,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Charges collected'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: _kmsDriven,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'KM\'s driven'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Is customer polite?'),
                  value: _isCustomerPolite,
                  onChanged: (v) => setState(() => _isCustomerPolite = v),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Difficult to attend'),
                  value: _difficultToAttend,
                  onChanged: (v) => setState(() => _difficultToAttend = v),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: t.status == TicketStatus.completed ? null : _complete,
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Submit Report & Complete'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}


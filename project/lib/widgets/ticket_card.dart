import 'package:flutter/material.dart';

import '../models.dart';
import 'status_pill.dart';

class TicketCard extends StatelessWidget {
  const TicketCard({super.key, required this.ticket});

  final AppTicket ticket;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFE0E8EE))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [Expanded(child: Text('${ticket.ticketId}  ${ticket.customerName}', style: const TextStyle(fontWeight: FontWeight.w700))), StatusPill(status: ticket.status)],
          ),
          const SizedBox(height: 8),
          Text(ticket.issue),
          const SizedBox(height: 4),
          Text(ticket.location, style: const TextStyle(color: Color(0xFF5A6E7A))),
        ],
      ),
    );
  }
}


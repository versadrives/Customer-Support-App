import 'package:flutter/material.dart';

import '../models.dart';

Color statusColor(TicketStatus status) {
  switch (status) {
    case TicketStatus.open:
      return const Color(0xFFE67E22);
    case TicketStatus.assigned:
      return const Color(0xFF247BA0);
    case TicketStatus.inProgress:
      return const Color(0xFF118AB2);
    case TicketStatus.completed:
      return const Color(0xFF0E61A5);
    case TicketStatus.cancelled:
      return const Color(0xFFB42318);
    case TicketStatus.duplicate:
      return const Color(0xFF64748B);
    case TicketStatus.customerSolved:
      return const Color(0xFF2A9D8F);
  }
}

String statusLabel(TicketStatus status) {
  switch (status) {
    case TicketStatus.open:
      return 'OPEN';
    case TicketStatus.assigned:
      return 'ASSIGNED';
    case TicketStatus.inProgress:
      return 'IN PROGRESS';
    case TicketStatus.completed:
      return 'COMPLETED';
    case TicketStatus.cancelled:
      return 'CANCELLED';
    case TicketStatus.duplicate:
      return 'DUPLICATE';
    case TicketStatus.customerSolved:
      return 'PROBLEM SOLVED AT CUSTOMER END';
  }
}


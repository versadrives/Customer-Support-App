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
  }
}

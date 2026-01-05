import 'package:flutter/material.dart';
import '../../../core/models/procedure.dart';
import 'package:intl/intl.dart';

/// Procedure card widget
class ProcedureCard extends StatelessWidget {
  final Procedure procedure;
  final VoidCallback? onTap;

  const ProcedureCard({
    super.key,
    required this.procedure,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: _getOutcomeColor().withOpacity(0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Icon(
                            Icons.medical_services,
                            color: _getOutcomeColor(),
                            size: 24,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                procedure.category,
                                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: Colors.grey[600],
                                      fontWeight: FontWeight.w500,
                                    ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                procedure.procedureType,
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.bold,
                                    ),
                              ),
                              if (procedure.subType != null) ...[
                                const SizedBox(height: 2),
                                Text(
                                  procedure.subType!,
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (onTap != null)
                    Icon(
                      Icons.chevron_right,
                      color: Colors.grey[400],
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Date and outcome
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.calendar_today,
                        size: 14,
                        color: Colors.grey[600],
                      ),
                      const SizedBox(width: 4),
                      Text(
                        DateFormat('MMM dd, yyyy').format(procedure.procedureDate),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.grey[600],
                            ),
                      ),
                    ],
                  ),
                  _OutcomeBadge(outcome: procedure.outcome),
                ],
              ),

              // Doctor
              if (procedure.doctorName != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.person,
                      size: 14,
                      color: Colors.grey[600],
                    ),
                    const SizedBox(width: 4),
                    Text(
                      procedure.doctorName!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                          ),
                    ),
                  ],
                ),
              ],

              // Notes
              if (procedure.notes != null) ...[
                const SizedBox(height: 8),
                const Divider(height: 1),
                const SizedBox(height: 8),
                Text(
                  procedure.notes!,
                  style: Theme.of(context).textTheme.bodySmall,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],

              // Billing info
              if (procedure.billedAmount != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: Colors.orange.withOpacity(0.2),
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Billed Amount',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey[700],
                            ),
                      ),
                      Text(
                        '₹${procedure.billedAmount!.toStringAsFixed(2)}',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.orange[700],
                            ),
                      ),
                    ],
                  ),
                ),
              ],

              // ICD/CPT codes
              if (procedure.icdCode != null || procedure.cptCode != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    if (procedure.icdCode != null) ...[
                      _CodeBadge(label: 'ICD', code: procedure.icdCode!),
                      const SizedBox(width: 8),
                    ],
                    if (procedure.cptCode != null)
                      _CodeBadge(label: 'CPT', code: procedure.cptCode!),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Color _getOutcomeColor() {
    switch (procedure.outcome.toLowerCase()) {
      case 'successful':
        return Colors.green;
      case 'partial':
        return Colors.orange;
      case 'failed':
        return Colors.red;
      case 'referred':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }
}

class _OutcomeBadge extends StatelessWidget {
  final String outcome;

  const _OutcomeBadge({required this.outcome});

  @override
  Widget build(BuildContext context) {
    final color = _getColor();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        outcome.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Color _getColor() {
    switch (outcome.toLowerCase()) {
      case 'successful':
        return Colors.green;
      case 'partial':
        return Colors.orange;
      case 'failed':
        return Colors.red;
      case 'referred':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }
}

class _CodeBadge extends StatelessWidget {
  final String label;
  final String code;

  const _CodeBadge({
    required this.label,
    required this.code,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: Colors.grey[200],
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        '$label: $code',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
      ),
    );
  }
}

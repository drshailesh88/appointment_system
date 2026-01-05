import 'package:flutter/material.dart';

/// Insight Action Button Widget
///
/// Quick action button for insights.
class InsightActionButton extends StatefulWidget {
  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isPrimary;

  const InsightActionButton({
    Key? key,
    required this.label,
    this.onPressed,
    this.icon,
    this.isPrimary = false,
  }) : super(key: key);

  @override
  State<InsightActionButton> createState() => _InsightActionButtonState();
}

class _InsightActionButtonState extends State<InsightActionButton> {
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    if (widget.isPrimary) {
      return ElevatedButton.icon(
        onPressed: _isLoading ? null : _handlePressed,
        icon: _isLoading
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Icon(widget.icon ?? Icons.check, size: 16),
        label: Text(widget.label),
        style: ElevatedButton.styleFrom(
          visualDensity: VisualDensity.compact,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ),
      );
    }

    return OutlinedButton.icon(
      onPressed: _isLoading ? null : _handlePressed,
      icon: _isLoading
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(widget.icon ?? Icons.arrow_forward, size: 16),
      label: Text(widget.label),
      style: OutlinedButton.styleFrom(
        visualDensity: VisualDensity.compact,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
    );
  }

  Future<void> _handlePressed() async {
    if (widget.onPressed == null) return;

    setState(() {
      _isLoading = true;
    });

    try {
      widget.onPressed!();
      // Wait a bit for visual feedback
      await Future.delayed(const Duration(milliseconds: 300));
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
}

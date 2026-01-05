import 'package:flutter/material.dart';
import '../../../core/models/call_state.dart';

/// Connection quality indicator widget
class ConnectionQualityIndicator extends StatelessWidget {
  final ConnectionQuality quality;
  final bool showLabel;

  const ConnectionQualityIndicator({
    Key? key,
    required this.quality,
    this.showLabel = true,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: _getBackgroundColor(),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildSignalBars(),
          if (showLabel) ...[
            const SizedBox(width: 6),
            Text(
              _getQualityText(),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSignalBars() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: List.generate(4, (index) {
        final isActive = index < _getActiveBarCount();
        return Container(
          width: 3,
          height: 8.0 + (index * 3.0),
          margin: const EdgeInsets.only(right: 2),
          decoration: BoxDecoration(
            color: isActive ? Colors.white : Colors.white.withOpacity(0.3),
            borderRadius: BorderRadius.circular(1.5),
          ),
        );
      }),
    );
  }

  int _getActiveBarCount() {
    switch (quality) {
      case ConnectionQuality.excellent:
        return 4;
      case ConnectionQuality.good:
        return 3;
      case ConnectionQuality.fair:
        return 2;
      case ConnectionQuality.poor:
        return 1;
      case ConnectionQuality.disconnected:
        return 0;
    }
  }

  Color _getBackgroundColor() {
    switch (quality) {
      case ConnectionQuality.excellent:
        return Colors.green;
      case ConnectionQuality.good:
        return Colors.lightGreen;
      case ConnectionQuality.fair:
        return Colors.orange;
      case ConnectionQuality.poor:
        return Colors.red.shade700;
      case ConnectionQuality.disconnected:
        return Colors.grey;
    }
  }

  String _getQualityText() {
    switch (quality) {
      case ConnectionQuality.excellent:
        return 'Excellent';
      case ConnectionQuality.good:
        return 'Good';
      case ConnectionQuality.fair:
        return 'Fair';
      case ConnectionQuality.poor:
        return 'Poor';
      case ConnectionQuality.disconnected:
        return 'No Connection';
    }
  }
}

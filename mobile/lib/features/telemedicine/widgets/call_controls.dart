import 'package:flutter/material.dart';

/// Video call control buttons
class CallControls extends StatelessWidget {
  final bool isAudioMuted;
  final bool isVideoMuted;
  final bool isFrontCamera;
  final VoidCallback onToggleAudio;
  final VoidCallback onToggleVideo;
  final VoidCallback onSwitchCamera;
  final VoidCallback onEndCall;
  final VoidCallback? onToggleChat;
  final bool showChat;

  const CallControls({
    Key? key,
    required this.isAudioMuted,
    required this.isVideoMuted,
    required this.isFrontCamera,
    required this.onToggleAudio,
    required this.onToggleVideo,
    required this.onSwitchCamera,
    required this.onEndCall,
    this.onToggleChat,
    this.showChat = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            Colors.black.withOpacity(0.7),
          ],
        ),
      ),
      child: SafeArea(
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            // Audio toggle
            _ControlButton(
              icon: isAudioMuted ? Icons.mic_off : Icons.mic,
              label: isAudioMuted ? 'Unmute' : 'Mute',
              onPressed: onToggleAudio,
              isActive: !isAudioMuted,
            ),

            // Video toggle
            _ControlButton(
              icon: isVideoMuted ? Icons.videocam_off : Icons.videocam,
              label: isVideoMuted ? 'Video Off' : 'Video On',
              onPressed: onToggleVideo,
              isActive: !isVideoMuted,
            ),

            // Switch camera
            _ControlButton(
              icon: Icons.flip_camera_ios,
              label: 'Flip',
              onPressed: onSwitchCamera,
            ),

            // Chat (optional)
            if (onToggleChat != null)
              _ControlButton(
                icon: showChat ? Icons.chat : Icons.chat_bubble_outline,
                label: 'Chat',
                onPressed: onToggleChat!,
                isActive: showChat,
              ),

            // End call
            _ControlButton(
              icon: Icons.call_end,
              label: 'End',
              onPressed: onEndCall,
              backgroundColor: Colors.red,
              isDestructive: true,
            ),
          ],
        ),
      ),
    );
  }
}

class _ControlButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onPressed;
  final Color? backgroundColor;
  final bool isActive;
  final bool isDestructive;

  const _ControlButton({
    Key? key,
    required this.icon,
    required this.label,
    required this.onPressed,
    this.backgroundColor,
    this.isActive = true,
    this.isDestructive = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final bgColor = backgroundColor ??
        (isActive ? Colors.white.withOpacity(0.2) : Colors.red.withOpacity(0.8));

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Material(
          color: bgColor,
          shape: const CircleBorder(),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onPressed,
            child: Container(
              width: 56,
              height: 56,
              alignment: Alignment.center,
              child: Icon(
                icon,
                color: Colors.white,
                size: 28,
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}

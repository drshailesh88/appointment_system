import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';

/// Widget to display local video (self view)
class LocalVideoView extends StatelessWidget {
  final MediaStream? stream;
  final bool isMuted;
  final VoidCallback? onTap;

  const LocalVideoView({
    Key? key,
    required this.stream,
    this.isMuted = false,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: Colors.white.withOpacity(0.3),
            width: 2,
          ),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: stream != null
              ? Stack(
                  fit: StackFit.expand,
                  children: [
                    RTCVideoView(
                      stream.getVideoTracks().isNotEmpty
                          ? RTCVideoRenderer()
                        ..initialize().then((_) {
                            // Attach stream
                            _.srcObject = stream;
                          })
                          : RTCVideoRenderer(),
                      objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover,
                      mirror: true,
                    ),
                    if (isMuted)
                      Positioned(
                        bottom: 8,
                        left: 8,
                        child: Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: Colors.red,
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.videocam_off,
                            color: Colors.white,
                            size: 16,
                          ),
                        ),
                      ),
                  ],
                )
              : const Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.videocam_off,
                        color: Colors.white54,
                        size: 40,
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Camera Off',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
        ),
      ),
    );
  }
}

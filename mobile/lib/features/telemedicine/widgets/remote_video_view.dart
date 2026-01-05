import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';

/// Widget to display remote video (doctor/patient)
class RemoteVideoView extends StatefulWidget {
  final MediaStream? stream;
  final String? participantName;
  final bool isConnected;

  const RemoteVideoView({
    Key? key,
    required this.stream,
    this.participantName,
    this.isConnected = false,
  }) : super(key: key);

  @override
  State<RemoteVideoView> createState() => _RemoteVideoViewState();
}

class _RemoteVideoViewState extends State<RemoteVideoView> {
  RTCVideoRenderer? _renderer;

  @override
  void initState() {
    super.initState();
    _initializeRenderer();
  }

  Future<void> _initializeRenderer() async {
    if (widget.stream != null) {
      _renderer = RTCVideoRenderer();
      await _renderer!.initialize();
      _renderer!.srcObject = widget.stream;
      setState(() {});
    }
  }

  @override
  void didUpdateWidget(RemoteVideoView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.stream != widget.stream) {
      _initializeRenderer();
    }
  }

  @override
  void dispose() {
    _renderer?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.black,
      child: widget.stream != null && _renderer != null
          ? RTCVideoView(
              _renderer!,
              objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover,
              mirror: false,
            )
          : Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (!widget.isConnected) ...[
                    const CircularProgressIndicator(
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Connecting...',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 16,
                      ),
                    ),
                  ] else ...[
                    Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        color: Colors.blue,
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          widget.participantName?.substring(0, 1).toUpperCase() ?? 'U',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      widget.participantName ?? 'Participant',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Waiting for video...',
                      style: TextStyle(
                        color: Colors.white54,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ],
              ),
            ),
    );
  }
}

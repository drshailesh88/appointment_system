import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// import 'package:jitsi_meet_flutter_sdk/jitsi_meet_flutter_sdk.dart'; // Uncomment when Jitsi SDK is added
import '../../../core/providers/telemedicine_provider.dart';

/// Consultation screen with video call integration
class ConsultationScreen extends ConsumerStatefulWidget {
  final String consultationId;
  final String roomUrl;
  final String jwtToken;
  final String roomName;

  const ConsultationScreen({
    Key? key,
    required this.consultationId,
    required this.roomUrl,
    required this.jwtToken,
    required this.roomName,
  }) : super(key: key);

  @override
  ConsumerState<ConsultationScreen> createState() =>
      _ConsultationScreenState();
}

class _ConsultationScreenState extends ConsumerState<ConsultationScreen> {
  // final _jitsiMeet = JitsiMeet(); // Uncomment when Jitsi SDK is added
  bool _isCallActive = false;

  @override
  void initState() {
    super.initState();
    _joinMeeting();
  }

  Future<void> _joinMeeting() async {
    setState(() {
      _isCallActive = true;
    });

    // TODO: Integrate with Jitsi Meet Flutter SDK
    // Uncomment and configure when jitsi_meet_flutter_sdk package is added
    /*
    try {
      var options = JitsiMeetConferenceOptions(
        serverURL: widget.roomUrl.split('/').take(3).join('/'),
        room: widget.roomName,
        token: widget.jwtToken,
        configOverrides: {
          "startWithAudioMuted": false,
          "startWithVideoMuted": false,
          "subject": "DocAssist Consultation",
        },
        featureFlags: {
          "unsaferoomwarning.enabled": false,
          "recording.enabled": true,
          "live-streaming.enabled": false,
          "meeting-name.enabled": false,
          "invite.enabled": false,
          "chat.enabled": true,
          "raise-hand.enabled": true,
        },
        userInfo: JitsiMeetUserInfo(
          displayName: "Patient", // Get from user profile
          email: "patient@example.com",
        ),
      );

      await _jitsiMeet.join(options);
    } catch (e) {
      debugPrint('Error joining Jitsi meeting: $e');
      if (mounted) {
        _showError('Failed to join consultation');
      }
    }
    */

    // For now, show placeholder
    debugPrint('Joining consultation: ${widget.roomName}');
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: () async {
        return await _confirmEndCall();
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: Stack(
          children: [
            // Placeholder for Jitsi video call
            // When Jitsi SDK is integrated, this will be replaced with JitsiMeetConferencing widget
            _buildPlaceholderView(),

            // Call controls overlay
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: _buildControlsBar(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholderView() {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.video_call,
              size: 120,
              color: Colors.white.withOpacity(0.5),
            ),
            const SizedBox(height: 24),
            const Text(
              'Video Consultation',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Room: ${widget.roomName}',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.orange[900],
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text(
                'Jitsi Meet SDK Integration Required\n\n'
                'Add jitsi_meet_flutter_sdk package\n'
                'and uncomment integration code',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlsBar() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.bottomCenter,
          end: Alignment.topCenter,
          colors: [
            Colors.black.withOpacity(0.9),
            Colors.black.withOpacity(0.6),
            Colors.transparent,
          ],
        ),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _buildControlButton(
              icon: Icons.mic_off,
              label: 'Mute',
              onPressed: () {
                // TODO: Toggle microphone
              },
            ),
            _buildControlButton(
              icon: Icons.videocam_off,
              label: 'Camera',
              onPressed: () {
                // TODO: Toggle camera
              },
            ),
            _buildControlButton(
              icon: Icons.call_end,
              label: 'End',
              color: Colors.red,
              onPressed: _endCall,
            ),
            _buildControlButton(
              icon: Icons.chat,
              label: 'Chat',
              onPressed: () {
                // TODO: Open chat
              },
            ),
            _buildControlButton(
              icon: Icons.more_vert,
              label: 'More',
              onPressed: () {
                _showMoreOptions();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlButton({
    required IconData icon,
    required String label,
    required VoidCallback onPressed,
    Color? color,
  }) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Material(
          color: color ?? Colors.white.withOpacity(0.2),
          shape: const CircleBorder(),
          child: InkWell(
            onTap: onPressed,
            customBorder: const CircleBorder(),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Icon(
                icon,
                color: Colors.white,
                size: 28,
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
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

  void _showMoreOptions() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
        ),
        child: SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.videocam),
                title: const Text('Recording'),
                subtitle: const Text('Requires consent from both parties'),
                onTap: () {
                  Navigator.pop(context);
                  _requestRecording();
                },
              ),
              ListTile(
                leading: const Icon(Icons.switch_camera),
                title: const Text('Switch Camera'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Switch camera
                },
              ),
              ListTile(
                leading: const Icon(Icons.screen_share),
                title: const Text('Share Screen'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Share screen
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _requestRecording() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Request Recording'),
        content: const Text(
          'Recording this consultation requires consent from both doctor and patient. '
          'Do you consent to recording this consultation?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('No'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _submitRecordingConsent(true);
            },
            child: const Text('Yes, I Consent'),
          ),
        ],
      ),
    );
  }

  Future<void> _submitRecordingConsent(bool consent) async {
    // TODO: Call API to submit recording consent
    final notifier = ref.read(telemedicineProvider.notifier);
    // await notifier.submitRecordingConsent(widget.consultationId, consent);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
              'Recording consent submitted. Recording will start when both parties consent.'),
        ),
      );
    }
  }

  Future<bool> _confirmEndCall() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('End Consultation?'),
        content: const Text('Are you sure you want to end this consultation?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('End Call'),
          ),
        ],
      ),
    );

    return confirm ?? false;
  }

  Future<void> _endCall() async {
    final confirm = await _confirmEndCall();
    if (!confirm || !mounted) return;

    // End consultation via API
    final notifier = ref.read(telemedicineProvider.notifier);
    await notifier.endConsultation(
      widget.consultationId,
      connectionQuality: 'good', // Could track actual quality
    );

    if (mounted) {
      // Show rating dialog
      _showRatingDialog();
    }
  }

  void _showRatingDialog() {
    int rating = 5;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Rate Consultation'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('How was your consultation experience?'),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  return IconButton(
                    icon: Icon(
                      index < rating ? Icons.star : Icons.star_border,
                      color: Colors.amber,
                      size: 32,
                    ),
                    onPressed: () {
                      setState(() {
                        rating = index + 1;
                      });
                    },
                  );
                }),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                Navigator.pop(context); // Return to previous screen
              },
              child: const Text('Skip'),
            ),
            ElevatedButton(
              onPressed: () async {
                final notifier = ref.read(telemedicineProvider.notifier);
                await notifier.submitRating(widget.consultationId, rating);
                if (mounted) {
                  Navigator.pop(context);
                  Navigator.pop(context);
                }
              },
              child: const Text('Submit'),
            ),
          ],
        ),
      ),
    );
  }

  void _showError(String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Error'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              Navigator.pop(context);
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}

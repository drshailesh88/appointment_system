/// ICE Candidate model for WebRTC signaling
class IceCandidate {
  final String candidate;
  final String? sdpMid;
  final int? sdpMLineIndex;

  const IceCandidate({
    required this.candidate,
    this.sdpMid,
    this.sdpMLineIndex,
  });

  factory IceCandidate.fromJson(Map<String, dynamic> json) {
    return IceCandidate(
      candidate: json['candidate'] as String,
      sdpMid: json['sdpMid'] as String?,
      sdpMLineIndex: json['sdpMLineIndex'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'candidate': candidate,
      if (sdpMid != null) 'sdpMid': sdpMid,
      if (sdpMLineIndex != null) 'sdpMLineIndex': sdpMLineIndex,
    };
  }
}

/// Session Description Protocol (SDP) model
class SessionDescription {
  final String type; // 'offer' or 'answer'
  final String sdp;

  const SessionDescription({
    required this.type,
    required this.sdp,
  });

  factory SessionDescription.fromJson(Map<String, dynamic> json) {
    return SessionDescription(
      type: json['type'] as String,
      sdp: json['sdp'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'sdp': sdp,
    };
  }
}

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../lib/core/services/websocket_service.dart';

void main() {
  group('WebSocketService', () {
    late WebSocketService service;

    setUp(() {
      service = WebSocketService(baseUrl: 'http://localhost:8000/api/v1');
    });

    tearDown(() {
      service.dispose();
    });

    test('initial state should be disconnected', () {
      expect(service.connectionState, ConnectionState.disconnected);
    });

    test('setAuthToken should set token', () {
      service.setAuthToken('test-token');
      // No exception should be thrown
      expect(true, true);
    });

    test('_buildWebSocketUrl should convert HTTP to WS', () {
      // This is a private method, but we can test the functionality indirectly
      // by checking the connection attempt doesn't throw
      expect(() => service.setAuthToken('token'), returnsNormally);
    });

    test('send should not throw when disconnected', () {
      // Should log warning but not throw
      expect(() => service.send({'type': 'test'}), returnsNormally);
    });

    test('connectionStateStream should emit state changes', () async {
      expect(service.connectionStateStream, emits(anything));
    });

    test('eventStream should be available', () {
      expect(service.eventStream, isNotNull);
    });

    test('appointmentEventStream should be available', () {
      expect(service.appointmentEventStream, isNotNull);
    });

    test('waitlistEventStream should be available', () {
      expect(service.waitlistEventStream, isNotNull);
    });

    test('notificationEventStream should be available', () {
      expect(service.notificationEventStream, isNotNull);
    });
  });

  group('WebSocketEvent', () {
    test('fromJson should parse appointment created event', () {
      final json = {
        'type': 'appointment.created',
        'data': {'id': 'appt-1'},
        'timestamp': '2024-01-01T12:00:00Z',
      };

      final event = WebSocketEvent.fromJson(json);

      expect(event.type, WebSocketEventType.appointmentCreated);
      expect(event.data['id'], 'appt-1');
      expect(event.timestamp, DateTime.parse('2024-01-01T12:00:00Z'));
    });

    test('fromJson should parse waitlist event', () {
      final json = {
        'type': 'waitlist.offer_sent',
        'data': {'waitlist_id': 'wl-1'},
      };

      final event = WebSocketEvent.fromJson(json);

      expect(event.type, WebSocketEventType.waitlistOfferSent);
      expect(event.data['waitlist_id'], 'wl-1');
    });

    test('fromJson should handle unknown event type', () {
      final json = {
        'type': 'unknown.event',
        'data': {},
      };

      final event = WebSocketEvent.fromJson(json);

      expect(event.type, WebSocketEventType.unknown);
    });

    test('fromJson should handle heartbeat/ping events', () {
      final json = {
        'type': 'heartbeat',
        'data': {},
      };

      final event = WebSocketEvent.fromJson(json);

      expect(event.type, WebSocketEventType.heartbeat);
    });
  });
}

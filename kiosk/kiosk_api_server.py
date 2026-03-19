#!/usr/bin/env python3
"""
Flask API Server for NYU Study Room Kiosk
Provides room status endpoint for ESP32 LCD smart updates
Works with ReservationManager that returns Reservation objects
"""

from flask import Flask, jsonify
from flask_cors import CORS
from reservation_manager_calendar import ReservationManager
from config import CALENDAR_CONFIG
from datetime import datetime
import threading

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from ESP32

# Initialize ReservationManager
print("Initializing Reservation Manager...")
reservation_manager = ReservationManager(
    room_name=CALENDAR_CONFIG['room_name'],
    credentials_file=CALENDAR_CONFIG['credentials_file'],
    calendar_id=CALENDAR_CONFIG['calendar_id']
)
print(f"✓ Reservation Manager ready for {CALENDAR_CONFIG['room_name']}")


@app.route('/api/room_status', methods=['GET'])
def get_room_status():
    """
    Get current room status for LCD display
    
    Returns JSON:
    {
        'state': 'available' | 'check_in_ready' | 'occupied',
        'current_reservation': {
            'end_time': '2024-11-19T15:30:00',
            'user_name': 'N12345678',
            'start_time': '2024-11-19T14:00:00'
        } or None,
        'timestamp': '2024-11-19T14:25:00'
    }
    """
    try:
        # Get status from ReservationManager
        status = reservation_manager.get_current_status()
        
        print(f"[DEBUG] Status type: {type(status)}")
        print(f"[DEBUG] Status: {status}")
        
        # Handle if status itself is an object
        if hasattr(status, '__dict__'):
            # Convert object to dict
            status_dict = status.__dict__ if hasattr(status, '__dict__') else {}
            state = getattr(status, 'state', 'available')
            current_booking = getattr(status, 'current_booking', None)
        elif isinstance(status, dict):
            status_dict = status
            state = status.get('state', 'available')
            current_booking = status.get('current_booking')
        else:
            # Fallback
            return jsonify({
                'state': 'available',
                'current_reservation': None,
                'timestamp': datetime.now().isoformat(),
                'error': f'Unexpected status type: {type(status)}'
            })
        
        # Format response for LCD
        current_reservation = None
        if current_booking:
            print(f"[DEBUG] Booking type: {type(current_booking)}")
            print(f"[DEBUG] Booking: {current_booking}")
            print(f"[DEBUG] Booking dir: {dir(current_booking)}")
            
            try:
                # Try object attribute access (most likely for your GUI)
                if hasattr(current_booking, 'end_time'):
                    start_time = None
                    end_time = None
                    user_name = 'Reserved'
                    
                    # Get end_time
                    if hasattr(current_booking, 'end_time'):
                        end_attr = getattr(current_booking, 'end_time')
                        if hasattr(end_attr, 'isoformat'):
                            end_time = end_attr.isoformat()
                        else:
                            end_time = str(end_attr)
                    
                    # Get start_time
                    if hasattr(current_booking, 'start_time'):
                        start_attr = getattr(current_booking, 'start_time')
                        if hasattr(start_attr, 'isoformat'):
                            start_time = start_attr.isoformat()
                        else:
                            start_time = str(start_attr)
                    
                    # Get user name
                    if hasattr(current_booking, 'user_name'):
                        user_name = getattr(current_booking, 'user_name')
                    elif hasattr(current_booking, 'n_number'):
                        user_name = getattr(current_booking, 'n_number')
                    elif hasattr(current_booking, 'booked_by'):
                        user_name = getattr(current_booking, 'booked_by')
                    
                    current_reservation = {
                        'start_time': start_time,
                        'end_time': end_time,
                        'user_name': user_name
                    }
                    print(f"[DEBUG] Created reservation from object: {current_reservation}")
                
                # Try dictionary access (Google Calendar format)
                elif isinstance(current_booking, dict):
                    start_time = current_booking.get('start', {}).get('dateTime')
                    end_time = current_booking.get('end', {}).get('dateTime')
                    n_number = current_booking.get('extendedProperties', {}).get('private', {}).get('bookedBy', 'Reserved')
                    
                    current_reservation = {
                        'start_time': start_time,
                        'end_time': end_time,
                        'user_name': n_number
                    }
                    print(f"[DEBUG] Created reservation from dict: {current_reservation}")
                
            except Exception as booking_error:
                print(f"[ERROR] Error parsing booking: {booking_error}")
                import traceback
                traceback.print_exc()
                # Still mark as occupied but without details
                current_reservation = {
                    'start_time': None,
                    'end_time': None,
                    'user_name': 'Reserved'
                }
        
        response = {
            'state': state,
            'current_reservation': current_reservation,
            'timestamp': datetime.now().isoformat(),
            'room_name': CALENDAR_CONFIG['room_name']
        }
        
        print(f"[DEBUG] Final response: {response}")
        return jsonify(response)
    
    except Exception as e:
        print(f"[ERROR] Error getting room status: {e}")
        import traceback
        traceback.print_exc()
        # Return safe fallback
        return jsonify({
            'state': 'available',
            'current_reservation': None,
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 200  # Return 200 even on error so LCD doesn't crash


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'room': CALENDAR_CONFIG['room_name'],
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    """Get today's schedule (bonus endpoint for debugging)"""
    try:
        schedule = reservation_manager.get_schedule_for_display()
        return jsonify({
            'schedule': schedule,
            'count': len(schedule),
            'room': CALENDAR_CONFIG['room_name']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/force_refresh', methods=['POST'])
def force_refresh():
    """Force refresh bookings (useful for debugging)"""
    try:
        reservation_manager.force_refresh()
        return jsonify({
            'status': 'refreshed',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def start_flask_in_thread():
    """Start Flask in a background thread (for running alongside Kivy)"""
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✓ Flask API server started in background thread")
    return flask_thread


if __name__ == '__main__':
    # Standalone mode - run Flask directly
    print("\n" + "=" * 60)
    print("NYU Study Room Kiosk - API Server (Object-Safe Version)")
    print("=" * 60)
    print(f"Room: {CALENDAR_CONFIG['room_name']}")
    print(f"Endpoints:")
    print(f"  - http://0.0.0.0:5000/api/room_status")
    print(f"  - http://0.0.0.0:5000/api/health")
    print(f"  - http://0.0.0.0:5000/api/schedule")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\nShutting down...")

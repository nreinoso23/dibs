#!/usr/bin/env python3
"""
Integration Test Suite for NYU Study Room Kiosk
Run this BEFORE integrating with your Kivy app to verify everything works
"""

from google_calendar_client import CalendarClient
from reservation_manager_calendar import ReservationManager
from datetime import datetime, timedelta
import sys
import time

# Import configuration
try:
    from config import CALENDAR_CONFIG
except ImportError:
    print("❌ ERROR: config.py not found!")
    print("   Make sure config.py is in the same directory")
    sys.exit(1)


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def test_1_configuration():
    """Test 1: Verify configuration is set up"""
    print_header("TEST 1: Checking Configuration")
    
    errors = []
    
    # Check credentials file path
    cred_file = CALENDAR_CONFIG['credentials_file']
    print(f"📁 Credentials file: {cred_file}")
    
    import os
    if not os.path.exists(cred_file):
        errors.append(f"Credentials file not found: {cred_file}")
    else:
        print("   ✅ Credentials file exists")
    
    # Check calendar ID
    calendar_id = CALENDAR_CONFIG['calendar_id']
    print(f"📅 Calendar ID: {calendar_id}")
    
    if 'YOUR_CALENDAR_ID' in calendar_id:
        errors.append("Calendar ID not updated in config.py")
    else:
        print("   ✅ Calendar ID is configured")
    
    # Check room name
    room_name = CALENDAR_CONFIG['room_name']
    print(f"🚪 Room name: {room_name}")
    print("   ✅ Room name is set")
    
    if errors:
        print("\n❌ Configuration errors found:")
        for error in errors:
            print(f"   - {error}")
        print("\n📝 Fix these in config.py before continuing")
        return False
    
    print("\n✅ Configuration looks good!")
    return True


def test_2_connection():
    """Test 2: Test connection to Google Calendar"""
    print_header("TEST 2: Testing Google Calendar Connection")
    
    try:
        client = CalendarClient(
            CALENDAR_CONFIG['credentials_file'],
            CALENDAR_CONFIG['calendar_id']
        )
        print("✅ Successfully connected to Google Calendar API")
        return client
    except FileNotFoundError as e:
        print(f"❌ Credentials file not found: {e}")
        print("\n📝 Troubleshooting:")
        print("   1. Copy key.json to the path specified in config.py")
        print("   2. Check file permissions: chmod 600 key.json")
        return None
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("\n📝 Troubleshooting:")
        print("   1. Verify calendar ID in config.py")
        print("   2. Check service account has calendar access")
        print("   3. Ensure internet connection is working")
        return None


def test_3_read_bookings(client):
    """Test 3: Read existing bookings"""
    print_header("TEST 3: Reading Today's Bookings")
    
    if not client:
        print("⏭️  Skipped (no connection)")
        return False
    
    try:
        bookings = client.get_todays_bookings(CALENDAR_CONFIG['room_name'])
        print(f"✅ Found {len(bookings)} booking(s) for {CALENDAR_CONFIG['room_name']}")
        
        if bookings:
            print("\n📅 Today's bookings:")
            for i, booking in enumerate(bookings, 1):
                start = booking['start']['dateTime']
                booked_by = booking.get('extendedProperties', {}).get('private', {}).get('bookedBy', 'Unknown')
                print(f"   {i}. {booking['summary']}")
                print(f"      Start: {start}")
                print(f"      Booked by: {booked_by}")
        else:
            print("   ℹ️  No bookings found (this is fine for testing)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to read bookings: {e}")
        return False


def test_4_check_availability(client):
    """Test 4: Check room availability"""
    print_header("TEST 4: Checking Room Availability")
    
    if not client:
        print("⏭️  Skipped (no connection)")
        return False
    
    try:
        now = datetime.now()
        is_available = client.is_room_available(
            CALENDAR_CONFIG['room_name'],
            now,
            60
        )
        
        if is_available:
            print(f"✅ Room is AVAILABLE right now for 60 minutes")
        else:
            print(f"⚠️  Room is OCCUPIED right now")
            
            # Find next available slot
            next_slot = client.get_next_available_slot(
                CALENDAR_CONFIG['room_name'],
                now,
                60
            )
            if next_slot:
                print(f"   Next available: {next_slot.strftime('%I:%M %p')}")
            else:
                print("   No availability found today")
        
        return True
    except Exception as e:
        print(f"❌ Failed to check availability: {e}")
        return False


def test_5_create_booking(client):
    """Test 5: Create and delete a test booking"""
    print_header("TEST 5: Creating Test Booking")
    
    if not client:
        print("⏭️  Skipped (no connection)")
        return False
    
    # Create booking 2 hours from now
    start_time = datetime.now() + timedelta(hours=2)
    
    print(f"\nTest booking details:")
    print(f"   Room: {CALENDAR_CONFIG['room_name']}")
    print(f"   Time: {start_time.strftime('%I:%M %p')}")
    print(f"   Duration: 30 minutes")
    print(f"   N-number: N99999999 (test)")
    
    response = input("\n❓ Create this test booking? (y/n): ")
    if response.lower() != 'y':
        print("⏭️  Skipping booking creation")
        return True
    
    try:
        booking = client.create_booking(
            room_name=CALENDAR_CONFIG['room_name'],
            start_time=start_time,
            duration_minutes=30,
            n_number="N99999999",
            name="Test User"
        )
        
        print(f"\n✅ Test booking created successfully!")
        print(f"   Event ID: {booking['id']}")
        print(f"   Time: {booking['start']['dateTime']}")
        
        # Ask to delete
        response = input("\n❓ Delete this test booking now? (y/n): ")
        if response.lower() == 'y':
            client.delete_booking(booking['id'])
            print("✅ Test booking deleted")
        else:
            print("⚠️  Test booking left in calendar")
            print(f"   Delete it manually if needed: Event ID {booking['id']}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create booking: {e}")
        return False


def test_6_reservation_manager():
    """Test 6: Test ReservationManager class"""
    print_header("TEST 6: Testing ReservationManager")
    
    try:
        manager = ReservationManager(
            CALENDAR_CONFIG['room_name'],
            CALENDAR_CONFIG['credentials_file'],
            CALENDAR_CONFIG['calendar_id']
        )
        print("✅ ReservationManager initialized")
        
        # Wait for initial refresh
        print("\n⏳ Waiting for initial booking refresh...", end='', flush=True)
        time.sleep(3)
        print(" Done")
        
        status = manager.get_current_status()
        print(f"\n📊 Current room status:")
        print(f"   State: {status['state'].upper()}")
        
        if status['current_booking']:
            booking = status['current_booking']
            booked_by = booking.get('extendedProperties', {}).get('private', {}).get('bookedBy', 'Unknown')
            print(f"   Current booking: {booking['summary']}")
            print(f"   Booked by: {booked_by}")
        else:
            print(f"   Current booking: None")
        
        if status['next_booking']:
            print(f"   Next booking: in {status['time_until_next']} minutes")
        else:
            print(f"   Next booking: None today")
        
        schedule = manager.get_schedule_for_display()
        print(f"\n📅 Today's schedule: {len(schedule)} booking(s)")
        for item in schedule:
            status_icon = "✅" if item['checked_in'] else "⏳"
            print(f"   {status_icon} {item['start_time']} - {item['end_time']} ({item['booked_by']})")
        
        return True
    except Exception as e:
        print(f"❌ ReservationManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_walk_in_booking():
    """Test 7: Test walk-in booking creation"""
    print_header("TEST 7: Testing Walk-in Booking")
    
    response = input("\n❓ Test walk-in booking creation? (y/n): ")
    if response.lower() != 'y':
        print("⏭️  Skipping walk-in booking test")
        return True
    
    try:
        manager = ReservationManager(
            CALENDAR_CONFIG['room_name'],
            CALENDAR_CONFIG['credentials_file'],
            CALENDAR_CONFIG['calendar_id']
        )
        
        # Try to create a walk-in booking 5 minutes from now
        print("\n📝 Creating 30-minute walk-in booking...")
        print("   N-number: N88888888 (test)")
        
        booking = manager.create_walk_in_booking(
            duration_minutes=30,
            n_number="N88888888",
            name="Walk-in Test"
        )
        
        if booking:
            print("✅ Walk-in booking created successfully!")
            print(f"   Event ID: {booking['id']}")
            
            # Clean up
            response = input("\n❓ Delete this test booking? (y/n): ")
            if response.lower() == 'y':
                manager.calendar.delete_booking(booking['id'])
                print("✅ Test booking deleted")
        else:
            print("⚠️  Could not create walk-in booking (room may be occupied)")
        
        return True
    except Exception as e:
        print(f"❌ Walk-in booking test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🔧" * 35)
    print("NYU STUDY ROOM KIOSK - Integration Test Suite")
    print("🔧" * 35)
    
    print(f"\n📋 Testing configuration:")
    print(f"   Room: {CALENDAR_CONFIG.get('room_name', 'Not set')}")
    print(f"   Calendar: {CALENDAR_CONFIG.get('calendar_id', 'Not set')}")
    
    # Run tests in order
    tests = [
        ("Configuration", test_1_configuration),
        ("Google Calendar Connection", lambda: test_2_connection()),
    ]
    
    results = []
    client = None
    
    # Test 1: Configuration
    if not test_1_configuration():
        print("\n❌ Configuration test failed. Fix config.py and try again.")
        return
    results.append(True)
    
    # Test 2: Connection
    client = test_2_connection()
    results.append(client is not None)
    
    if client:
        # Run remaining tests
        remaining_tests = [
            ("Read Bookings", lambda: test_3_read_bookings(client)),
            ("Check Availability", lambda: test_4_check_availability(client)),
            ("Create/Delete Booking", lambda: test_5_create_booking(client)),
            ("ReservationManager", test_6_reservation_manager),
            ("Walk-in Booking", test_7_walk_in_booking),
        ]
        
        for name, test_func in remaining_tests:
            result = test_func()
            results.append(result)
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"\n📊 Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("   Your calendar integration is working correctly.")
        print("   You're ready to integrate with your Kivy app.")
        print("\n📝 Next steps:")
        print("   1. Update your main Kivy app with new ReservationManager")
        print("   2. Replace demo logic with calendar-backed methods")
        print("   3. Test on your Raspberry Pi with touchscreen")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("   Review the errors above and fix them before continuing.")
        print("\n📝 Common issues:")
        print("   - Wrong calendar ID in config.py")
        print("   - Credentials file not found")
        print("   - Service account doesn't have calendar access")
        print("   - Internet connection issues")
    
    print("\n" + "🔧" * 35 + "\n")


if __name__ == "__main__":
    main()

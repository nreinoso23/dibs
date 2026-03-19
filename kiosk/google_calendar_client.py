"""
Google Calendar API Client for NYU Study Room Kiosk
Handles all calendar operations: bookings, availability, check-ins
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

class CalendarClient:
    def __init__(self, credentials_file, calendar_id):
        """
        Initialize Google Calendar client
        
        Args:
            credentials_file: Path to service account JSON file
            calendar_id: Google Calendar ID
        """
        self.calendar_id = calendar_id
        self.timezone = pytz.timezone('America/New_York')
        
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        # Build calendar service
        self.service = build('calendar', 'v3', credentials=credentials)
        print(f"✅ Calendar client initialized for {calendar_id}")
    
    def create_booking(self, room_name, start_time, duration_minutes, n_number, name=None, is_walk_in=False):
        """
        Create a new booking
        
        Args:
            room_name: Name of study room (e.g., "Study Room LC416")
            start_time: datetime object for booking start
            duration_minutes: Duration in minutes
            n_number: Student N-number (e.g., "N12345678")
            name: Optional student name
            is_walk_in: If True, marks as walk-in and auto-checks-in (immune to no-show cancellation)
            
        Returns:
            Event object from Google Calendar API
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Create description
        description = f"Booked by: {n_number}"
        if name:
            description += f" ({name})"
        
        # Ensure times are timezone-aware
        if start_time.tzinfo is None:
            start_time = self.timezone.localize(start_time)
        if end_time.tzinfo is None:
            end_time = self.timezone.localize(end_time)
        
        # Walk-ins are ALWAYS checked in at creation - they are immune to no-show cancellation
        if is_walk_in:
            checked_in = 'true'
            is_walk_in_flag = 'true'
            check_in_time = datetime.now().isoformat()
        else:
            checked_in = 'false'
            is_walk_in_flag = 'false'
            check_in_time = ''
        
        event = {
            'summary': f'{room_name} - Reserved',
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/New_York',
            },
            'extendedProperties': {
                'private': {
                    'bookedBy': n_number,
                    'roomName': room_name,
                    'kioskBooking': 'true',
                    'checkedIn': checked_in,
                    'isWalkIn': is_walk_in_flag,
                    'checkInTime': check_in_time
                }
            }
        }
        
        try:
            event_result = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            if is_walk_in:
                print(f"✅ Walk-in booking created (auto-checked-in): {event_result['id']}")
            else:
                print(f"✅ Booking created: {event_result['id']}")
            return event_result
            
        except Exception as e:
            print(f"❌ Error creating booking: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_bookings(self, start_date=None, end_date=None):
        """
        Get all bookings for a date range
        
        Args:
            start_date: datetime object (defaults to today at midnight)
            end_date: datetime object (defaults to 7 days from start)
            
        Returns:
            List of event objects
        """
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        # Make timezone-aware
        if start_date.tzinfo is None:
            start_date = self.timezone.localize(start_date)
        if end_date.tzinfo is None:
            end_date = self.timezone.localize(end_date)
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat(),
                timeMax=end_date.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            print(f"📅 Retrieved {len(events)} events from calendar")
            return events
            
        except Exception as e:
            print(f"❌ Error getting bookings: {e}")
            raise
    
    def get_todays_bookings(self, room_name=None):
        """
        Get all bookings for today, optionally filtered by room
        
        Args:
            room_name: Optional room name to filter by
            
        Returns:
            List of event objects
        """
        # Get today in local timezone
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        print(f"🔍 Querying bookings from {today_start} to {today_end}")
        all_bookings = self.get_bookings(today_start, today_end)
        print(f"📋 Found {len(all_bookings)} total bookings today")
        
        if room_name:
            # Extract room number for flexible matching
            # "Study Room LC416" or "LC 416" → extract "416"
            room_number = room_name.replace('Study Room', '').replace('LC', '').replace(' ', '').strip()
            
            # Filter by room name in summary or extended properties
            filtered = []
            for event in all_bookings:
                event_room = event.get('extendedProperties', {}).get('private', {}).get('roomName', '')
                summary_room = event.get('summary', '')
                
                # Check if room number appears in event (flexible matching)
                if (room_number in event_room.replace(' ', '') or 
                    room_number in summary_room.replace(' ', '')):
                    filtered.append(event)
                    print(f"  ✓ Event: {event.get('summary', 'No title')} - Matches room {room_name}")
                else:
                    print(f"  ✗ Event: {event.get('summary', 'No title')} - Doesn't match")
            
            print(f"✅ Filtered to {len(filtered)} bookings for {room_name}")
            return filtered
        
        return all_bookings
    
    def check_in_booking(self, event_id):
        """
        Mark a booking as checked in
        CRITICAL: This must save to Google Calendar or the no-show policy will cancel!
        
        Args:
            event_id: Google Calendar event ID
            
        Returns:
            Updated event object
        """
        try:
            print(f"[CHECK-IN] Starting check-in for event: {event_id}")
            
            # Get the event first
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            print(f"[CHECK-IN] Retrieved event: {event.get('summary', 'No title')}")
            
            # Initialize extended properties if needed
            if 'extendedProperties' not in event:
                event['extendedProperties'] = {'private': {}}
                print("[CHECK-IN] Created extendedProperties structure")
            if 'private' not in event['extendedProperties']:
                event['extendedProperties']['private'] = {}
                print("[CHECK-IN] Created private properties structure")
            
            # Set check-in flags
            event['extendedProperties']['private']['checkedIn'] = 'true'
            event['extendedProperties']['private']['checkInTime'] = datetime.now().isoformat()
            
            print(f"[CHECK-IN] Setting checkedIn='true' for event {event_id}")
            
            # Update the event on Google Calendar
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            # VERIFY the update actually happened
            verify_event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            checked_in_status = verify_event.get('extendedProperties', {}).get('private', {}).get('checkedIn', 'NOT SET')
            
            if checked_in_status == 'true':
                print(f"✅ CHECK-IN VERIFIED: Event {event_id} is marked as checked in")
                print(f"   Check-in time: {verify_event.get('extendedProperties', {}).get('private', {}).get('checkInTime')}")
            else:
                print(f"⚠️ CHECK-IN FAILED TO VERIFY: checkedIn status = '{checked_in_status}'")
                raise Exception(f"Check-in verification failed - status is '{checked_in_status}'")
            
            return updated_event
            
        except Exception as e:
            print(f"❌ ERROR in check_in_booking: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def is_walk_in(self, event_id):
        """
        Check if an event is a walk-in booking
        
        Args:
            event_id: Google Calendar event ID
            
        Returns:
            True if walk-in, False otherwise
        """
        try:
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            return event.get('extendedProperties', {}).get('private', {}).get('isWalkIn') == 'true'
        except Exception as e:
            print(f"❌ Error checking walk-in status: {e}")
            return False
    
    def delete_booking(self, event_id, n_number=None):
        """
        Delete a booking
        
        Args:
            event_id: Google Calendar event ID
            n_number: Optional N-number for ownership verification
            
        Returns:
            True if successful
        """
        try:
            if n_number:
                # Verify ownership
                event = self.service.events().get(
                    calendarId=self.calendar_id,
                    eventId=event_id
                ).execute()
                
                booked_by = event.get('extendedProperties', {}).get('private', {}).get('bookedBy', '')
                
                if booked_by != n_number:
                    raise ValueError("You can only delete your own bookings")
            
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            print(f"✅ Booking deleted: {event_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting booking: {e}")
            raise
    
    def is_room_available(self, room_name, start_time, duration_minutes):
        """
        Check if a room is available for a given time slot
        
        Args:
            room_name: Name of the study room
            start_time: datetime object
            duration_minutes: Duration in minutes
            
        Returns:
            True if available, False if occupied
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Get bookings that might overlap
        bookings = self.get_bookings(
            start_time - timedelta(hours=1),
            end_time + timedelta(hours=1)
        )
        
        # Extract room number for flexible matching
        room_number = room_name.replace('Study Room', '').replace('LC', '').replace(' ', '').strip()
        
        # Check for overlaps
        for event in bookings:
            event_room = event.get('extendedProperties', {}).get('private', {}).get('roomName', '')
            summary_room = event.get('summary', '')
            
            # Check if this event is for the same room (flexible matching)
            if not (room_number in event_room.replace(' ', '') or 
                    room_number in summary_room.replace(' ', '')):
                continue  # Different room
            
            event_start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
            
            # Remove timezone info for comparison
            event_start = event_start.replace(tzinfo=None)
            event_end = event_end.replace(tzinfo=None)
            
            # Check for overlap
            if start_time < event_end and end_time > event_start:
                print(f"⚠️ Conflict found with event: {event.get('summary', 'No title')}")
                return False  # Conflict found
        
        return True
    
    def get_next_available_slot(self, room_name, start_time, duration_minutes):
        """
        Find the next available time slot for a room
        
        Args:
            room_name: Name of the study room
            start_time: datetime to start searching from
            duration_minutes: Desired duration
            
        Returns:
            datetime object of next available slot, or None if not found today
        """
        current_time = start_time
        end_of_day = start_time.replace(hour=22, minute=0, second=0, microsecond=0)  # 10 PM
        
        while current_time < end_of_day:
            if self.is_room_available(room_name, current_time, duration_minutes):
                return current_time
            
            # Try next 15-minute slot
            current_time += timedelta(minutes=15)
        
        return None

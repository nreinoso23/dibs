"""
Reservation Manager with Google Calendar Integration - FIXED CHECK-IN VERSION
"""

from datetime import datetime, timedelta, time
from typing import List, Tuple, Optional
from google_calendar_client import CalendarClient
import threading
import platform


class Reservation:
    """Represents a single reservation (wraps Google Calendar event)"""
    
    def __init__(self, booking_data: dict):
        """Initialize from Google Calendar booking data"""
        self._booking = booking_data
        
        # Parse times
        start = datetime.fromisoformat(booking_data['start']['dateTime'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(booking_data['end']['dateTime'].replace('Z', '+00:00'))
        
        self.start_time = start.replace(tzinfo=None)
        self.end_time = end.replace(tzinfo=None)
        self.duration_minutes = int((self.end_time - self.start_time).total_seconds() / 60)
        
        # Get name - prefer actual name from description, fall back to N-number
        n_number = booking_data.get('extendedProperties', {}).get('private', {}).get('bookedBy', 'Unknown')
        description = booking_data.get('description', '')
        
        # Try to extract name from description
        if '(' in description and ')' in description:
            start_idx = description.find('(')
            end_idx = description.find(')')
            self.name = description[start_idx+1:end_idx]
        else:
            self.name = n_number
        
        self.checked_in = booking_data.get('extendedProperties', {}).get('private', {}).get('checkedIn') == 'true'
        self.is_walk_in = booking_data.get('extendedProperties', {}).get('private', {}).get('isWalkIn') == 'true'
        self.event_id = booking_data['id']
    
    def is_active(self, current_time: datetime) -> bool:
        """Check if reservation is currently active"""
        return self.checked_in and self.start_time <= current_time <= self.end_time
    
    def can_check_in(self, current_time: datetime) -> bool:
        """Check if user can check in (15 min before to 15 min after start)"""
        grace_start = self.start_time - timedelta(minutes=15)
        grace_end = self.start_time + timedelta(minutes=15)
        return not self.checked_in and grace_start <= current_time <= grace_end
    
    def is_future(self, current_time: datetime) -> bool:
        """Check if reservation hasn't started yet"""
        return current_time < self.start_time


class ReservationManager:
    """Manages room reservations using Google Calendar backend"""
    
    LIBRARY_OPEN_HOUR = 7    # 7am
    LIBRARY_CLOSE_HOUR = 1   # 1am next day
    CHECK_IN_GRACE_MINUTES = 15

    def __init__(self, room_name, credentials_file, calendar_id):
        self.room_name = room_name
        self.calendar = CalendarClient(credentials_file, calendar_id)
        self.bookings_cache = []
        self.reservations: List[Reservation] = []
        self.last_refresh = None
        
        self.start_background_refresh()
        self.refresh_bookings()
    
    def refresh_bookings(self):
        """Refresh bookings from Google Calendar"""
        try:
            self.bookings_cache = self.calendar.get_todays_bookings(self.room_name)
            self.reservations = [Reservation(booking) for booking in self.bookings_cache]
            self.last_refresh = datetime.now()
            print(f"🔄 Refreshed bookings: {len(self.reservations)} found for {self.room_name}")
        except Exception as e:
            print(f"❌ Error refreshing bookings: {e}")
    
    def start_background_refresh(self):
        """Start background thread to refresh bookings every 30 seconds"""
        def refresh_loop():
            import time as time_module
            while True:
                time_module.sleep(30)
                self.refresh_bookings()
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
        print("🔄 Background refresh thread started")
    
    def get_current_reservation(self, current_time: datetime = None) -> Optional[Reservation]:
        """Get the currently active (checked-in) reservation"""
        if current_time is None:
            current_time = datetime.now()
        
        for res in self.reservations:
            if res.is_active(current_time):
                return res
        
        return None
    
    def get_next_reservation(self, current_time: datetime = None) -> Optional[Reservation]:
        """Get the next upcoming reservation"""
        if current_time is None:
            current_time = datetime.now()
        
        future_reservations = [
            r for r in self.reservations 
            if r.is_future(current_time) or r.can_check_in(current_time)
        ]
        
        if future_reservations:
            return min(future_reservations, key=lambda r: r.start_time)
        
        return None
    
    def get_check_in_reservation(self, current_time: datetime = None) -> Optional[Reservation]:
        """Get reservation that can be checked in right now"""
        if current_time is None:
            current_time = datetime.now()
        
        for res in self.reservations:
            if res.can_check_in(current_time):
                return res
        
        return None
    
    def is_room_occupied(self, current_time: datetime = None) -> bool:
        """Check if room is currently occupied"""
        return self.get_current_reservation(current_time) is not None
    
    def check_in_reservation(self, name: str, current_time: datetime = None) -> bool:
        """
        Check in a reservation by name or N-number
        CRITICAL: Must save to Google Calendar!
        """
        if current_time is None:
            current_time = datetime.now()
        
        print(f"[CHECK-IN] Attempting to check in: {name}")
        
        for res in self.reservations:
            if res.can_check_in(current_time) and res.name == name:
                try:
                    print(f"[CHECK-IN] Found matching reservation for {name}, event ID: {res.event_id}")
                    
                    # CRITICAL: This MUST update Google Calendar
                    self.calendar.check_in_booking(res.event_id)
                    
                    print(f"[CHECK-IN] Successfully checked in to Google Calendar")
                    
                    # Force immediate refresh to verify
                    self.refresh_bookings()
                    
                    # Verify the check-in persisted
                    for updated_res in self.reservations:
                        if updated_res.event_id == res.event_id:
                            if updated_res.checked_in:
                                print(f"✅ CHECK-IN VERIFIED: {name} is checked in")
                                return True
                            else:
                                print(f"⚠️ CHECK-IN VERIFICATION FAILED: Status not updated")
                                return False
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ Error checking in: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
        
        print(f"❌ No matching reservation found for {name}")
        return False
    
    def get_max_walk_in_minutes(self, current_time: datetime = None) -> int:
        """Calculate maximum walk-in duration"""
        if current_time is None:
            current_time = datetime.now()
        
        if self.is_room_occupied(current_time):
            return 0
        
        close_time = datetime.combine(current_time.date(), time(hour=self.LIBRARY_CLOSE_HOUR))
        if current_time.time() >= time(hour=self.LIBRARY_CLOSE_HOUR):
            close_time += timedelta(days=1)
        mins_to_close = int((close_time - current_time).total_seconds() / 60)
        
        next_res = self.get_next_reservation(current_time)
        if next_res:
            mins_to_next = int((next_res.start_time - current_time).total_seconds() / 60)
            max_mins = min(mins_to_close, mins_to_next)
        else:
            max_mins = mins_to_close
        
        return max(15, max_mins)
    
    def can_walk_in(self, current_time: datetime = None) -> bool:
        """Check if walk-in is allowed right now"""
        if current_time is None:
            current_time = datetime.now()
        
        return not self.is_room_occupied(current_time) and not self.get_check_in_reservation(current_time)
    
    def get_room_state(self, current_time: datetime = None) -> Tuple[str, str, bool, bool]:
        """Get current room state"""
        if current_time is None:
            current_time = datetime.now()
        
        current_res = self.get_current_reservation(current_time)
        if current_res:
            return ('occupied', f"Room occupied by {current_res.name}", False, False)
        
        check_in_res = self.get_check_in_reservation(current_time)
        if check_in_res:
            return ('check_in_available', f"{check_in_res.name} can check in now", False, True)
        
        next_res = self.get_next_reservation(current_time)
        if next_res:
            mins_until = int((next_res.start_time - current_time).total_seconds() / 60)
            message = f"Next booking in {mins_until} min"
        else:
            message = "Available"
        
        return ('available', message, True, False)
    
    def add_walk_in(self, duration_minutes: int, name: str = "Walk-in User", current_time: datetime = None) -> bool:
        """
        Add a walk-in reservation (ALWAYS auto-checked-in at creation)
        Walk-ins are immune to no-show cancellation because they are marked as walk-ins
        and checked in at the moment of creation.
        """
        if current_time is None:
            current_time = datetime.now()
        
        max_duration = self.get_max_walk_in_minutes(current_time)
        if duration_minutes > max_duration:
            print(f"❌ Duration {duration_minutes} exceeds max {max_duration}")
            return False
        
        if not self.can_walk_in(current_time):
            print("❌ Room not available for walk-in")
            return False
        
        # Round to nearest 5 minutes
        current_time = current_time.replace(second=0, microsecond=0)
        minute = (current_time.minute // 5) * 5
        current_time = current_time.replace(minute=minute)
        
        try:
            print(f"📝 Creating walk-in for {name}, {duration_minutes} minutes")
            
            # CRITICAL: Use is_walk_in=True to auto-check-in at creation
            # This makes walk-ins immune to no-show cancellation
            booking = self.calendar.create_booking(
                room_name=self.room_name,
                start_time=current_time,
                duration_minutes=duration_minutes,
                n_number="WALKIN",
                name=name,
                is_walk_in=True  # AUTO-CHECKS-IN AND MARKS AS WALK-IN
            )
            
            if not booking:
                print("❌ Booking creation returned None")
                return False
            
            event_id = booking['id']
            print(f"✅ Walk-in booking created and auto-checked-in: {event_id}")
            
            # Force immediate refresh
            print("[WALK-IN] Refreshing to verify...")
            self.refresh_bookings()
            
            # Verify the walk-in appears and is checked in
            for res in self.reservations:
                if res.event_id == event_id:
                    if res.checked_in and res.is_walk_in:
                        print(f"✅ WALK-IN VERIFIED: {name} is checked in and marked as walk-in (immune to no-show cancellation)")
                    elif res.checked_in:
                        print(f"✅ WALK-IN VERIFIED: {name} is checked in")
                    else:
                        print(f"⚠️ WALK-IN WARNING: Created but status unclear")
                    break
            
            return True
                
        except Exception as e:
            print(f"❌ Error creating walk-in: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_upcoming_reservations(self, limit: int = 3, current_time: datetime = None) -> List[Reservation]:
        """Get list of upcoming reservations"""
        if current_time is None:
            current_time = datetime.now()
        
        future = [
            r for r in self.reservations 
            if r.start_time >= current_time or r.can_check_in(current_time)
        ]
        future.sort(key=lambda r: r.start_time)
        
        return future[:limit]
    
    def get_all_today_reservations(self, current_time: datetime = None) -> List[Reservation]:
        """Get all reservations for today (midnight to midnight)"""
        if current_time is None:
            current_time = datetime.now()
        
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        today_reservations = [
            r for r in self.reservations 
            if today_start <= r.start_time < today_end
        ]
        today_reservations.sort(key=lambda r: r.start_time)
        
        return today_reservations
    
    def get_library_day_reservations(self, current_time: datetime = None) -> List[Reservation]:
        """
        Get all reservations for the current library operating day.
        Library hours: 7am to 1am next day
        
        If current time is between 12am-1am, we're still in "yesterday's" library day.
        """
        if current_time is None:
            current_time = datetime.now()
        
        current_hour = current_time.hour
        
        if current_hour < self.LIBRARY_CLOSE_HOUR:
            # Between midnight and 1am - still "yesterday's" library day
            day_start = (current_time - timedelta(days=1)).replace(
                hour=self.LIBRARY_OPEN_HOUR, minute=0, second=0, microsecond=0
            )
            day_end = current_time.replace(
                hour=self.LIBRARY_CLOSE_HOUR, minute=0, second=0, microsecond=0
            )
        else:
            # Normal hours (1am onwards) - today's library day
            day_start = current_time.replace(
                hour=self.LIBRARY_OPEN_HOUR, minute=0, second=0, microsecond=0
            )
            day_end = (current_time + timedelta(days=1)).replace(
                hour=self.LIBRARY_CLOSE_HOUR, minute=0, second=0, microsecond=0
            )
        
        # Query calendar directly for the expanded range to include late night reservations
        try:
            bookings = self.calendar.get_bookings(day_start, day_end)
            
            # Filter by room
            room_number = self.room_name.replace('Study Room', '').replace('LC', '').replace(' ', '').strip()
            
            library_day_reservations = []
            for booking in bookings:
                event_room = booking.get('extendedProperties', {}).get('private', {}).get('roomName', '')
                summary_room = booking.get('summary', '')
                
                if (room_number in event_room.replace(' ', '') or 
                    room_number in summary_room.replace(' ', '')):
                    library_day_reservations.append(Reservation(booking))
            
            library_day_reservations.sort(key=lambda r: r.start_time)
            return library_day_reservations
            
        except Exception as e:
            print(f"❌ Error getting library day reservations: {e}")
            # Fall back to cached reservations filtered by time
            return [
                r for r in self.reservations 
                if day_start <= r.start_time < day_end
            ]
    
    @staticmethod
    def format_time(dt: datetime) -> str:
        """Format time in 12-hour format"""
        if platform.system() == "Windows":
            return dt.strftime('%#I:%M %p')
        else:
            return dt.strftime('%-I:%M %p')
    
    def calculate_walk_in_end_time(self, hours: int, minutes: int, current_time: datetime = None) -> datetime:
        """Calculate when walk-in would end"""
        if current_time is None:
            current_time = datetime.now()
        return current_time + timedelta(hours=hours, minutes=minutes)
    
    def get_schedule_for_display(self):
        """Get formatted schedule for LCD display"""
        schedule = []
        for res in self.reservations:
            schedule.append({
                'start_time': self.format_time(res.start_time),
                'end_time': self.format_time(res.end_time),
                'booked_by': res.name,
                'checked_in': res.checked_in,
                'is_walk_in': res.is_walk_in,
                'event_id': res.event_id
            })
        return schedule
    
    def create_walk_in_booking(self, duration_minutes, n_number, name=None):
        """Create walk-in booking (ALWAYS auto-checked-in)"""
        display_name = name if name else n_number
        success = self.add_walk_in(duration_minutes, display_name)
        
        if success:
            self.refresh_bookings()
            if self.reservations:
                return {'success': True}
        
        return None
    
    def check_in_current_booking(self, n_number):
        """Check in using N-number"""
        return self.check_in_reservation(n_number)
    
    def force_refresh(self):
        """Force an immediate refresh of bookings"""
        self.refresh_bookings()
    
    def get_current_status(self):
        """Get current room status (for compatibility)"""
        now = datetime.now()
        state, message, walk_in_enabled, check_in_enabled = self.get_room_state(now)
        
        current_booking = self.get_current_reservation(now)
        next_booking = self.get_next_reservation(now)
        
        time_until_next = None
        if next_booking:
            time_until_next = int((next_booking.start_time - now).total_seconds() / 60)
        
        state_map = {
            'occupied': 'occupied',
            'check_in_available': 'check_in_ready',
            'available': 'available'
        }
        
        return {
            'state': state_map.get(state, 'available'),
            'current_booking': current_booking,
            'next_booking': next_booking,
            'time_until_next': time_until_next
        }

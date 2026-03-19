"""
Reservation Manager - INSTANT REFRESH VERSION
- Faster refresh when reservations are imminent
- Guaranteed mutual exclusivity of check-in and walk-in
- Walk-ins are auto-checked-in and immune to no-show cancellation
"""

from datetime import datetime, timedelta, time
from typing import List, Tuple, Optional
from google_calendar_client import CalendarClient
import threading
import platform


class Reservation:
    """Represents a single reservation"""
    
    def __init__(self, booking_data: dict):
        self._booking = booking_data
        
        start = datetime.fromisoformat(booking_data['start']['dateTime'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(booking_data['end']['dateTime'].replace('Z', '+00:00'))
        
        self.start_time = start.replace(tzinfo=None)
        self.end_time = end.replace(tzinfo=None)
        self.duration_minutes = int((self.end_time - self.start_time).total_seconds() / 60)
        
        n_number = booking_data.get('extendedProperties', {}).get('private', {}).get('bookedBy', 'Unknown')
        description = booking_data.get('description', '')
        
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
        """Check if user can check in (10 min BEFORE start only)"""
        grace_start = self.start_time - timedelta(minutes=10)
        return not self.checked_in and grace_start <= current_time < self.start_time
    
    def is_future(self, current_time: datetime) -> bool:
        """Check if reservation hasn't started yet"""
        return current_time < self.start_time


class ReservationManager:
    """Manages room reservations with intelligent refresh rates"""
    
    LIBRARY_OPEN_HOUR = 7    # 7am
    LIBRARY_CLOSE_HOUR = 1   # 1am next day
    CHECK_IN_GRACE_MINUTES = 10

    def __init__(self, room_name, credentials_file, calendar_id):
        self.room_name = room_name
        self.calendar = CalendarClient(credentials_file, calendar_id)
        self.bookings_cache = []
        self.reservations: List[Reservation] = []
        self.last_refresh = None
        
        # Dynamic refresh rate
        self.current_refresh_interval = 30  # Start with 30 seconds
        
        self.start_background_refresh()
        self.refresh_bookings()
    
    def refresh_bookings(self):
        """Refresh bookings from Google Calendar"""
        try:
            self.bookings_cache = self.calendar.get_todays_bookings(self.room_name)
            self.reservations = [Reservation(booking) for booking in self.bookings_cache]
            self.last_refresh = datetime.now()
            print(f"🔄 Refreshed bookings: {len(self.reservations)} found for {self.room_name}")
            
            # Adjust refresh rate based on proximity to next event
            self._adjust_refresh_rate()
            
        except Exception as e:
            print(f"❌ Error refreshing bookings: {e}")
    
    def _adjust_refresh_rate(self):
        """Adjust refresh rate based on proximity to next reservation"""
        now = datetime.now()
        next_res = self.get_next_reservation()
        
        if next_res:
            # Time until check-in opens (10 min before start)
            check_in_opens = next_res.start_time - timedelta(minutes=10)
            mins_until = int((check_in_opens - now).total_seconds() / 60)
            
            if mins_until <= 2:
                # Critical: 2 min or less until check-in - refresh every 5 seconds
                self.current_refresh_interval = 5
                print("[REFRESH] CRITICAL PERIOD - Refreshing every 5 seconds")
            elif mins_until <= 5:
                # Warning: 5 min or less - refresh every 10 seconds
                self.current_refresh_interval = 10
                print("[REFRESH] WARNING PERIOD - Refreshing every 10 seconds")
            elif mins_until <= 15:
                # Caution: 15 min or less - refresh every 15 seconds
                self.current_refresh_interval = 15
                print("[REFRESH] CAUTION PERIOD - Refreshing every 15 seconds")
            else:
                # Normal: refresh every 30 seconds
                self.current_refresh_interval = 30
        else:
            # No upcoming reservations - normal refresh
            self.current_refresh_interval = 30
    
    def start_background_refresh(self):
        """Start background thread with dynamic refresh rate"""
        def refresh_loop():
            import time as time_module
            while True:
                time_module.sleep(self.current_refresh_interval)
                self.refresh_bookings()
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
        print("🔄 Background refresh thread started with dynamic intervals")
    
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
        """Check in a reservation"""
        if current_time is None:
            current_time = datetime.now()
        
        print(f"[CHECK-IN] Attempting to check in: {name}")
        
        for res in self.reservations:
            if res.can_check_in(current_time) and res.name == name:
                try:
                    print(f"[CHECK-IN] Found matching reservation, event ID: {res.event_id}")
                    self.calendar.check_in_booking(res.event_id)
                    print(f"[CHECK-IN] Successfully checked in to Google Calendar")
                    
                    # Force immediate refresh
                    self.refresh_bookings()
                    
                    # Verify
                    for updated_res in self.reservations:
                        if updated_res.event_id == res.event_id:
                            if updated_res.checked_in:
                                print(f"✅ CHECK-IN VERIFIED: {name}")
                                return True
                            else:
                                print(f"⚠️ CHECK-IN VERIFICATION FAILED")
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
        """
        Calculate maximum walk-in duration
        Returns 0 if walk-in not allowed
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Rule 1: NEVER allow walk-in if room is occupied
        if self.is_room_occupied(current_time):
            print("[WALK-IN] ❌ Room is occupied - walk-in disabled")
            return 0
        
        # Rule 2: NEVER allow walk-in if check-in is available
        if self.get_check_in_reservation(current_time):
            print("[WALK-IN] ❌ Check-in available - walk-in disabled")
            return 0
        
        # Calculate time until library closes
        close_time = datetime.combine(current_time.date(), time(hour=self.LIBRARY_CLOSE_HOUR))
        if current_time.time() >= time(hour=self.LIBRARY_CLOSE_HOUR):
            close_time += timedelta(days=1)
        mins_to_close = int((close_time - current_time).total_seconds() / 60)
        
        # Calculate time until next check-in window opens
        next_res = self.get_next_reservation(current_time)
        if next_res:
            check_in_opens = next_res.start_time - timedelta(minutes=10)
            mins_to_checkin = int((check_in_opens - current_time).total_seconds() / 60)
            
            if mins_to_checkin <= 0:
                print("[WALK-IN] ❌ Check-in window has opened - walk-in disabled")
                return 0
            
            max_mins = min(mins_to_close, mins_to_checkin)
        else:
            max_mins = mins_to_close
        
        return max(15, max_mins)
    
    def can_walk_in(self, current_time: datetime = None) -> bool:
        """
        Check if walk-in is allowed
        CRITICAL: Returns False if check-in is available OR room is occupied
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Absolute rule: No walk-in if room occupied
        if self.is_room_occupied(current_time):
            return False
        
        # Absolute rule: No walk-in if check-in available
        if self.get_check_in_reservation(current_time):
            return False
        
        # Check if there's time available
        return self.get_max_walk_in_minutes(current_time) > 0
    
    def get_room_state(self, current_time: datetime = None) -> Tuple[str, str, bool, bool]:
        """
        Get current room state with GUARANTEED mutual exclusivity
        Returns: (state, message, walk_in_enabled, check_in_enabled)
        
        CRITICAL: walk_in_enabled and check_in_enabled can NEVER both be True
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Priority 1: Room occupied
        current_res = self.get_current_reservation(current_time)
        if current_res:
            print(f"[STATE] Room occupied by {current_res.name}")
            return ('occupied', f"Room occupied by {current_res.name}", False, False)
        
        # Priority 2: Check-in available (DISABLES walk-in)
        check_in_res = self.get_check_in_reservation(current_time)
        if check_in_res:
            print(f"[STATE] Check-in available - walk-in DISABLED")
            return ('check_in_available', f"{check_in_res.name} can check in now", False, True)
        
        # Priority 3: Available for walk-in (check-in is NOT available)
        if self.can_walk_in(current_time):
            next_res = self.get_next_reservation(current_time)
            if next_res:
                check_in_opens = next_res.start_time - timedelta(minutes=10)
                mins_until_checkin = int((check_in_opens - current_time).total_seconds() / 60)
                
                if mins_until_checkin > 0:
                    message = f"Available (check-in in {mins_until_checkin} min)"
                else:
                    message = "Available"
            else:
                message = "Available"
            
            print(f"[STATE] Available for walk-in")
            return ('available', message, True, False)
        
        # Priority 4: Not available for anything
        print(f"[STATE] Not available")
        return ('unavailable', "Not available", False, False)
    
    def add_walk_in(self, duration_minutes: int, name: str = "Walk-in User", current_time: datetime = None) -> bool:
        """
        Add walk-in reservation (ALWAYS auto-checked-in at creation)
        Walk-ins are immune to no-show cancellation because they are marked as walk-ins
        and checked in at the moment of creation.
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Double-check walk-in is allowed
        if not self.can_walk_in(current_time):
            print("❌ Walk-in not allowed - check-in may be available or room occupied")
            return False
        
        max_duration = self.get_max_walk_in_minutes(current_time)
        if max_duration == 0:
            print(f"❌ No walk-in time available")
            return False
        
        if duration_minutes > max_duration:
            print(f"❌ Duration {duration_minutes} exceeds max {max_duration}")
            return False
        
        # Round time
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
                print("❌ Booking creation failed")
                return False
            
            event_id = booking['id']
            print(f"✅ Walk-in booking created and auto-checked-in: {event_id}")
            
            # Force immediate refresh
            self.refresh_bookings()
            
            # Verify
            for res in self.reservations:
                if res.event_id == event_id:
                    if res.checked_in and res.is_walk_in:
                        print(f"✅ WALK-IN VERIFIED: {name} is checked in and marked as walk-in (immune to no-show cancellation)")
                    elif res.checked_in:
                        print(f"✅ WALK-IN VERIFIED: {name} is checked in")
                    else:
                        print(f"⚠️ WARNING: Walk-in created but status unclear")
                    break
            
            return True
                
        except Exception as e:
            print(f"❌ Error creating walk-in: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_upcoming_reservations(self, limit: int = 3, current_time: datetime = None) -> List[Reservation]:
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
        if platform.system() == "Windows":
            return dt.strftime('%#I:%M %p')
        else:
            return dt.strftime('%-I:%M %p')
    
    def calculate_walk_in_end_time(self, hours: int, minutes: int, current_time: datetime = None) -> datetime:
        if current_time is None:
            current_time = datetime.now()
        return current_time + timedelta(hours=hours, minutes=minutes)
    
    def get_schedule_for_display(self):
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
        display_name = name if name else n_number
        success = self.add_walk_in(duration_minutes, display_name)
        
        if success:
            self.refresh_bookings()
            if self.reservations:
                return {'success': True}
        
        return None
    
    def check_in_current_booking(self, n_number):
        return self.check_in_reservation(n_number)
    
    def force_refresh(self):
        self.refresh_bookings()
    
    def get_current_status(self):
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

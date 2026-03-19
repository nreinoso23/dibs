from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.logger import Logger
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock
import logging
from kivy.uix.widget import Widget
from kivy.graphics import RoundedRectangle, Color
from rounded import RoundedRectangleContainer
from weather import WeatherWidget
from reservation_manager_calendar import ReservationManager
from config import CALENDAR_CONFIG
import platform
from datetime import datetime, timedelta

# Import GPIO handler only on Raspberry Pi
try:
    from gpio_handler import GPIOHandler
    from focus_manager import FocusManager
    from pir_handler import PIRHandler
    from led_status_handler import LEDStatusHandler
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    Logger.warning("TestApp: GPIO not available - running without physical buttons")

Logger.setLevel(level='INFO')
logging.basicConfig(level=logging.WARNING)

import kivy

kivy.config.Config.set('kivy', 'log_level', 'warning')
kivy.config.Config.write()
kivy.config.Config.set('graphics', 'borderless', '1')
kivy.config.Config.set('graphics', 'fullscreen', '0')
kivy.config.Config.write()


# Declare screens
class MenuScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass

class NewsScreen(Screen):
    pass

class WeatherScreen(Screen):
    pass

class SmartHomeScreen(Screen):
    pass

class ScheduleScreen(Screen):
    pass

class CheckInScreen(Screen):
    pass

class WalkInScreen(Screen):
    pass

class WalkInDetailedScreen(Screen):
    pass

class PasswordQuitScreen(Screen):
    pass

class ConfirmQuitScreen(Screen):
    pass

class PasswordSettingsScreen(Screen):
    pass

class RoundedButton(Widget):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.size_hint = (1, 1)
        with self.canvas.before:
            Color(0.1, 0.5, 0.8, 1)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[20])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class TestApp(App):
    # Properties for clock and weather display
    current_time = StringProperty("")
    current_date = StringProperty("")
    temperature_text = StringProperty("--°F")
    weather_icon_source = StringProperty("")
    
    # NetID input tracking (old, kept for compatibility)
    netid_input = StringProperty("")
    
    # N number input for check-in
    n_number_input = StringProperty("N")
    
    # Password inputs
    quit_password_input = StringProperty("")
    settings_password_input = StringProperty("")
    
    # Check-in status message
    checkin_status_text = StringProperty("No appointment now")
    
    # Walk-in status message
    walk_in_status_text = StringProperty("Next booking in 45 min")
    
    # Walk-in duration controls
    max_walk_in_duration = NumericProperty(120)
    walk_in_limit_reason = StringProperty("Limited by next reservation")
    walk_in_end_time = StringProperty("")
    
    # Detailed walk-in controls (hours/minutes)
    walk_in_hours = NumericProperty(0)
    walk_in_minutes = NumericProperty(30)
    walk_in_end_time_detailed = StringProperty("")
    
    # Button states
    walk_in_enabled = BooleanProperty(True)
    check_in_enabled = BooleanProperty(False)
    
    # Password (in production, hash this and store securely!)
    admin_password = os.environ.get("KIOSK_ADMIN_PW", "changeme")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize reservation manager
        self.reservation_manager = ReservationManager(
            room_name=CALENDAR_CONFIG['room_name'],
            credentials_file=CALENDAR_CONFIG['credentials_file'],
            calendar_id=CALENDAR_CONFIG['calendar_id']
        )
        # Initialize GPIO handler (will be None if not on Pi)
        self.gpio_handler = None
        self.focus_manager = None
        self.pir_handler = None
        self.led_handler = None
    
    def build(self):
        Builder.load_file('app.kv')

        sm = ScreenManager()
        sm.transition.direction = 'left'  # Default transition direction
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.add_widget(NewsScreen(name='news'))
        sm.add_widget(WeatherScreen(name='weather'))
        sm.add_widget(SmartHomeScreen(name='smarthome'))
        sm.add_widget(ScheduleScreen(name='schedule'))
        sm.add_widget(CheckInScreen(name='checkin'))
        sm.add_widget(WalkInScreen(name='walkin'))
        sm.add_widget(WalkInDetailedScreen(name='walkin_detailed'))
        sm.add_widget(PasswordQuitScreen(name='password_quit'))
        sm.add_widget(ConfirmQuitScreen(name='confirm_quit'))
        sm.add_widget(PasswordSettingsScreen(name='password_settings'))
        
        # Initialize clock and weather
        self.update_time_date()
        Clock.schedule_interval(lambda dt: self.update_time_date(), 1)
        
        # Update room status
        self.update_room_status()
        Clock.schedule_interval(lambda dt: self.update_room_status(), 30)  # Every 30 seconds
        
        # Initialize weather widget to get data
        self.weather_widget = WeatherWidget()
        self.weather_widget.bind(temperature=self.on_weather_update)
        self.weather_widget.bind(icon_url=self.on_weather_icon_update)
        Clock.schedule_interval(lambda dt: self.update_weather_display(), 10)
        
        # Initialize GPIO buttons and PIR sensor if available
        if GPIO_AVAILABLE:
            try:
                self.focus_manager = FocusManager(self)
                self.gpio_handler = GPIOHandler(self)
                self.gpio_handler.focus_manager = self.focus_manager
                self.pir_handler = PIRHandler(self)
                self.led_handler = LEDStatusHandler(self)
                Logger.info("TestApp: GPIO handler, focus manager, PIR sensor, and LED handler initialized")
            except Exception as e:
                Logger.error(f"TestApp: Failed to initialize GPIO/PIR/LED: {e}")
        
        # Schedule canvas refresh to fix black box rendering issue on startup
        # This forces a redraw after all widgets are initialized
        Clock.schedule_once(lambda dt: self.force_canvas_refresh(), 1.5)
        Clock.schedule_once(lambda dt: self.force_canvas_refresh(), 3.0)
        
        return sm
    
    def force_canvas_refresh(self):
        """Force a canvas refresh to fix rendering artifacts on startup"""
        try:
            if self.root:
                # Get the current screen
                current_screen = self.root.current_screen
                if current_screen:
                    # Force canvas to redraw by triggering a property change
                    current_screen.canvas.ask_update()
                    
                    # Also refresh all children
                    for child in current_screen.walk():
                        if hasattr(child, 'canvas'):
                            child.canvas.ask_update()
                
                # Force the root to redraw
                self.root.canvas.ask_update()
                
                Logger.info("TestApp: Canvas refresh completed")
        except Exception as e:
            Logger.warning(f"TestApp: Canvas refresh error (non-critical): {e}")
    
    def update_time_date(self):
        """Update time and date display"""
        now = datetime.now()
        if platform.system() == "Windows":
            time_fmt = "%#I:%M %p"
            date_fmt = "%A, %B %#d, %Y"
        else:
            time_fmt = "%-I:%M %p"
            date_fmt = "%A, %B %-d, %Y"
        
        self.current_time = now.strftime(time_fmt)
        self.current_date = now.strftime(date_fmt)
    
    def on_weather_update(self, instance, value):
        """Update temperature display when weather widget updates"""
        self.temperature_text = f"{value}°F"
    
    def on_weather_icon_update(self, instance, value):
        """Update weather icon when available"""
        if value:
            self.weather_icon_source = "weather_icon.png"
    
    def update_weather_display(self):
        """Periodically refresh weather display"""
        if hasattr(self.weather_widget, 'temperature'):
            self.temperature_text = f"{self.weather_widget.temperature}°F"
        if hasattr(self.weather_widget, 'icon') and self.weather_widget.icon.source:
            self.weather_icon_source = self.weather_widget.icon.source
    
    def update_room_status(self):
        """Update all room status based on reservation manager"""
        state, message, walk_in_enabled, check_in_enabled = self.reservation_manager.get_room_state()
        
        # Update button states
        self.walk_in_enabled = walk_in_enabled
        self.check_in_enabled = check_in_enabled
        
        # Update status messages
        if state == 'occupied':
            self.walk_in_status_text = message
            self.checkin_status_text = "Room is occupied"
        elif state == 'check_in_available':
            self.checkin_status_text = message
            # Still show next reservation info for walk-in
            next_res = self.reservation_manager.get_next_reservation()
            if next_res:
                mins_until = int((next_res.start_time - datetime.now()).total_seconds() / 60)
                self.walk_in_status_text = f"Next booking in {mins_until} min"
            else:
                self.walk_in_status_text = "Available"
        else:  # available
            self.walk_in_status_text = message
            self.checkin_status_text = "No appointment now"
        
        # Update walk-in maximum duration and limit reason
        self.max_walk_in_duration = self.reservation_manager.get_max_walk_in_minutes()
        
        # Determine limit reason
        now = datetime.now()
        close_time = datetime.combine(now.date(), datetime.min.time().replace(hour=1))
        if now.time() >= datetime.min.time().replace(hour=1):
            close_time += timedelta(days=1)
        mins_to_close = int((close_time - now).total_seconds() / 60)
        
        next_res = self.reservation_manager.get_next_reservation()
        if next_res:
            mins_to_next = int((next_res.start_time - now).total_seconds() / 60)
            if mins_to_close < mins_to_next:
                self.walk_in_limit_reason = "Limited by library closing at 1:00 AM"
            else:
                self.walk_in_limit_reason = "Limited by next reservation"
        else:
            self.walk_in_limit_reason = "Limited by library closing at 1:00 AM"
        
        # Update end times
        self.update_walk_in_end_times()
        
        # Update LED status
        if self.led_handler:
            self.led_handler.update_led_status()
    
    def update_walk_in_end_times(self):
        """Calculate and update walk-in end times"""
        # For slider screen (assumes 60 min default)
        end_time = datetime.now() + timedelta(minutes=60)
        self.walk_in_end_time = self.reservation_manager.format_time(end_time)
        
        # For detailed screen
        total_minutes = self.walk_in_hours * 60 + self.walk_in_minutes
        end_time_detailed = datetime.now() + timedelta(minutes=total_minutes)
        self.walk_in_end_time_detailed = self.reservation_manager.format_time(end_time_detailed)
    
    # Password verification methods
    def verify_quit_password(self, password):
        """Verify password before showing quit confirmation"""
        if password == self.admin_password:
            self.root.transition.direction = 'left'
            self.root.current = 'confirm_quit'
            self.quit_password_input = ""  # Clear after success
        else:
            Logger.warning("TestApp: Incorrect quit password")
    
    def verify_settings_password(self, password):
        """Verify password before entering settings"""
        if password == self.admin_password:
            self.root.transition.direction = 'left'
            self.root.current = 'settings'
            self.settings_password_input = ""  # Clear after success
        else:
            Logger.warning("TestApp: Incorrect settings password")
    
    def quit_app(self):
        """Quit the application"""
        Logger.info("TestApp: Application closing")
        App.get_running_app().stop()
    
    def goto_menu(self):
        """Go back to menu with right transition"""
        Logger.info("TestApp: Navigating to menu")
        self.root.transition.direction = 'right'
        self.root.current = 'menu'
        # Clear all password inputs when returning to menu
        self.quit_password_input = ""
        self.settings_password_input = ""
        self.netid_input = ""
        self.n_number_input = "N"  # Reset N number
    
    def goto_walkin_screen(self):
        """Route to appropriate walk-in screen based on max duration"""
        self.root.transition.direction = 'left'
        
        # Always use slider for 2 hours or less
        # Only use detailed selector when there's MORE than 2 hours available
        if self.max_walk_in_duration <= 120:  # 2 hours or less
            Logger.info(f"TestApp: Using slider (max {self.max_walk_in_duration} min)")
            self.root.current = 'walkin'
        else:
            Logger.info(f"TestApp: Using detailed selector (max {self.max_walk_in_duration} min)")
            # Set default values for detailed screen
            self.walk_in_hours = 2
            self.walk_in_minutes = 0
            self.update_walk_in_end_times()
            self.root.current = 'walkin_detailed'
    
    # NetID keyboard methods (kept for compatibility if needed elsewhere)
    def add_to_netid(self, char):
        """Add character to NetID input"""
        self.netid_input += char
    
    def backspace_netid(self):
        """Remove last character from NetID input"""
        self.netid_input = self.netid_input[:-1]
    
    def clear_netid(self):
        """Clear entire NetID input"""
        self.netid_input = ""
    
    # N Number keyboard methods for check-in
    def add_to_n_number(self, digit):
        """Add digit to N number input (max 8 digits after N)"""
        # N number is "N" + 8 digits = 9 characters total
        if len(self.n_number_input) < 9:
            self.n_number_input += digit
    
    def backspace_n_number(self):
        """Remove last digit from N number (but keep the N)"""
        if len(self.n_number_input) > 1:  # Keep the "N"
            self.n_number_input = self.n_number_input[:-1]
    
    def clear_n_number(self):
        """Clear N number back to just 'N'"""
        self.n_number_input = "N"
    
    def submit_n_number(self):
        """Submit N number for check-in"""
        if len(self.n_number_input) == 9:  # N + 8 digits
            print(f"[CHECK-IN] Attempting check-in with N number: {self.n_number_input}")
            
            # Get the current check-in reservation
            check_in_res = self.reservation_manager.get_check_in_reservation()
            
            if check_in_res:
                # TODO: Here you would verify the N number matches the reservation
                # For now, just check in the reservation
                success = self.reservation_manager.check_in_reservation(check_in_res.name)
                
                if success:
                    print(f"[CHECK-IN] Successfully checked in {check_in_res.name}")
                    self.checkin_status_text = f"✓ Checked in: {check_in_res.name}"
                    self.update_room_status()  # Update LED and room state
                else:
                    print(f"[CHECK-IN] Failed to check in")
                    self.checkin_status_text = "Check-in failed"
            else:
                print(f"[CHECK-IN] No reservation available for check-in")
                self.checkin_status_text = "No appointment found"
            
            # Go back to menu after showing message briefly
            Clock.schedule_once(lambda dt: self.goto_menu(), 2.0)
        else:
            print(f"[CHECK-IN] Invalid N number length: {len(self.n_number_input)} (expected 9)")
            self.checkin_status_text = "Must enter 8 digits"
    
    # Quit password keyboard methods
    def add_to_quit_password(self, char):
        """Add character to quit password input"""
        self.quit_password_input += char
    
    def backspace_quit_password(self):
        """Remove last character from quit password input"""
        self.quit_password_input = self.quit_password_input[:-1]
    
    def clear_quit_password(self):
        """Clear entire quit password input"""
        self.quit_password_input = ""
    
    # Settings password keyboard methods
    def add_to_settings_password(self, char):
        """Add character to settings password input"""
        self.settings_password_input += char
    
    def backspace_settings_password(self):
        """Remove last character from settings password input"""
        self.settings_password_input = self.settings_password_input[:-1]
    
    def clear_settings_password(self):
        """Clear entire settings password input"""
        self.settings_password_input = ""
    
    def start_scan(self):
        """Start barcode scanner for NYU ID"""
        print("TODO: Start barcode scanner")
        Logger.info("TestApp: Barcode scanner activated")
    
    def submit_checkin(self, netid):
        """Submit check-in with NetID (old method, kept for compatibility)"""
        print(f"Check-in attempt for NetID: {netid}")
        Logger.info(f"TestApp: Check-in for {netid}")
        
        # Get the reservation that can be checked in
        check_in_res = self.reservation_manager.get_check_in_reservation()
        if check_in_res:
            success = self.reservation_manager.check_in_reservation(check_in_res.name)
            if success:
                Logger.info(f"TestApp: Successfully checked in {check_in_res.name}")
                self.update_room_status()
            else:
                Logger.warning(f"TestApp: Failed to check in")
        
        self.netid_input = ""  # Clear input
        self.root.transition.direction = 'right'
        self.root.current = 'menu'
    
    def confirm_walkin(self, minutes):
        """Confirm walk-in booking from slider screen"""
        # TODO: Get user's name - for now use a default
        user_name = "Walk-in User"  # Replace this with actual name input
        
        print(f"Walk-in confirmed for {minutes} minutes by {user_name}")
        Logger.info(f"TestApp: Walk-in booking for {minutes} min by {user_name}")
        
        success = self.reservation_manager.add_walk_in(minutes, user_name)
        if success:
            Logger.info(f"TestApp: Walk-in reservation created and checked-in successfully")
            self.update_room_status()
        else:
            Logger.warning(f"TestApp: Failed to create walk-in reservation")
        
        self.root.transition.direction = 'right'
        self.root.current = 'menu'
    
    def confirm_walkin_detailed(self):
        """Confirm walk-in booking from detailed hour/minute screen"""
        # TODO: Get user's name - for now use a default
        user_name = "Walk-in User"  # Replace this with actual name input
        
        total_minutes = self.walk_in_hours * 60 + self.walk_in_minutes
        print(f"Walk-in confirmed for {total_minutes} minutes by {user_name}")
        Logger.info(f"TestApp: Walk-in booking for {total_minutes} min by {user_name}")
        
        success = self.reservation_manager.add_walk_in(total_minutes, user_name)
        if success:
            Logger.info(f"TestApp: Walk-in reservation created and checked-in successfully")
            self.update_room_status()
        else:
            Logger.warning(f"TestApp: Failed to create walk-in reservation")
        
        self.root.transition.direction = 'right'
        self.root.current = 'menu'
    
    # Walk-in hour/minute controls
    def increase_walk_in_hours(self):
        """Increase walk-in hours"""
        max_total_minutes = self.max_walk_in_duration
        current_total = self.walk_in_hours * 60 + self.walk_in_minutes
        if current_total + 60 <= max_total_minutes:
            self.walk_in_hours += 1
            self.update_walk_in_end_times()
    
    def decrease_walk_in_hours(self):
        """Decrease walk-in hours"""
        if self.walk_in_hours > 0:
            self.walk_in_hours -= 1
            self.update_walk_in_end_times()
    
    def increase_walk_in_minutes(self):
        """Increase walk-in minutes by 15"""
        max_total_minutes = self.max_walk_in_duration
        current_total = self.walk_in_hours * 60 + self.walk_in_minutes
        
        if self.walk_in_minutes == 45:
            # Roll over to next hour if possible
            if current_total + 15 <= max_total_minutes:
                self.walk_in_minutes = 0
                self.walk_in_hours += 1
        else:
            if current_total + 15 <= max_total_minutes:
                self.walk_in_minutes += 15
        
        self.update_walk_in_end_times()
    
    def decrease_walk_in_minutes(self):
        """Decrease walk-in minutes by 15"""
        if self.walk_in_minutes == 0:
            # Borrow from hours if available
            if self.walk_in_hours > 0:
                self.walk_in_minutes = 45
                self.walk_in_hours -= 1
        else:
            self.walk_in_minutes -= 15
        
        # Ensure minimum of 15 minutes total
        total = self.walk_in_hours * 60 + self.walk_in_minutes
        if total < 15:
            self.walk_in_hours = 0
            self.walk_in_minutes = 15
        
        self.update_walk_in_end_times()

if __name__ == '__main__':
    app = TestApp()
    try:
        app.run()
    finally:
        # Clean up GPIO, PIR, and LED on exit
        if hasattr(app, 'gpio_handler') and app.gpio_handler:
            app.gpio_handler.cleanup()
        if hasattr(app, 'led_handler') and app.led_handler:
            app.led_handler.cleanup()
        if hasattr(app, 'pir_handler') and app.pir_handler:
            app.pir_handler.cleanup()

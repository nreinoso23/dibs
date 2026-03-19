"""
GPIO Button Handler for Raspberry Pi Kiosk
Maps physical buttons to GUI navigation
"""
from gpiozero import Button
from kivy.clock import Clock
from kivy.logger import Logger
import time


class GPIOHandler:
    """Handle GPIO button inputs for kiosk navigation"""
    
    # GPIO Pin assignments
    PIN_DOWN = 5
    PIN_LEFT = 6
    PIN_RIGHT = 13
    PIN_SELECT = 19
    PIN_UP = 26
    
    def __init__(self, app):
        """Initialize GPIO buttons
        
        Args:
            app: Reference to the Kivy app instance
        """
        self.app = app
        self.buttons = {}
        self.focus_manager = None  # Will be set by app
        
        # Track last button press time for additional software debouncing
        self.last_button_time = {}
        self.debounce_delay = 0.15  # 150ms minimum between button presses
        
        try:
            # Initialize buttons with pull-up resistors and increased bounce time
            self.buttons['down'] = Button(self.PIN_DOWN, pull_up=True, bounce_time=0.15)
            self.buttons['left'] = Button(self.PIN_LEFT, pull_up=True, bounce_time=0.15)
            self.buttons['right'] = Button(self.PIN_RIGHT, pull_up=True, bounce_time=0.15)
            self.buttons['select'] = Button(self.PIN_SELECT, pull_up=True, bounce_time=0.15)
            self.buttons['up'] = Button(self.PIN_UP, pull_up=True, bounce_time=0.15)
            
            # Bind button press events
            self.buttons['down'].when_pressed = self.on_down
            self.buttons['left'].when_pressed = self.on_left
            self.buttons['right'].when_pressed = self.on_right
            self.buttons['select'].when_pressed = self.on_select
            self.buttons['up'].when_pressed = self.on_up
            
            Logger.info("GPIOHandler: Buttons initialized successfully")
            
        except Exception as e:
            Logger.error(f"GPIOHandler: Failed to initialize buttons: {e}")
    
    def is_debounced(self, button_name):
        """Check if enough time has passed since last button press"""
        current_time = time.time()
        if button_name in self.last_button_time:
            time_since_last = current_time - self.last_button_time[button_name]
            if time_since_last < self.debounce_delay:
                Logger.info(f"GPIOHandler: {button_name} debounced (only {time_since_last*1000:.1f}ms since last press)")
                return False
        self.last_button_time[button_name] = current_time
        return True
    
    def schedule_on_main_thread(self, callback):
        """Schedule callback to run on Kivy's main thread"""
        Clock.schedule_once(lambda dt: callback(), 0)
    
    def on_down(self):
        """Handle DOWN button press"""
        if not self.is_debounced('down'):
            return
        Logger.info("GPIOHandler: DOWN pressed")
        self.schedule_on_main_thread(self.handle_down)
    
    def on_up(self):
        """Handle UP button press"""
        if not self.is_debounced('up'):
            return
        Logger.info("GPIOHandler: UP pressed")
        self.schedule_on_main_thread(self.handle_up)
    
    def on_left(self):
        """Handle LEFT button press"""
        if not self.is_debounced('left'):
            return
        Logger.info("GPIOHandler: LEFT pressed")
        self.schedule_on_main_thread(self.handle_left)
    
    def on_right(self):
        """Handle RIGHT button press"""
        if not self.is_debounced('right'):
            return
        Logger.info("GPIOHandler: RIGHT pressed")
        self.schedule_on_main_thread(self.handle_right)
    
    def on_select(self):
        """Handle SELECT button press"""
        if not self.is_debounced('select'):
            return
        Logger.info("GPIOHandler: SELECT pressed")
        self.schedule_on_main_thread(self.handle_select)
    
    # Navigation handlers
    def handle_down(self):
        """DOWN button - move focus down"""
        if self.focus_manager:
            self.focus_manager.move_focus_down()
    
    def handle_up(self):
        """UP button - move focus up"""
        if self.focus_manager:
            self.focus_manager.move_focus_up()
    
    def handle_left(self):
        """LEFT button - move focus left or go back"""
        if self.focus_manager:
            self.focus_manager.move_focus_left()
    
    def handle_right(self):
        """RIGHT button - move focus right"""
        if self.focus_manager:
            self.focus_manager.move_focus_right()
    
    def handle_select(self):
        """SELECT button - activate focused widget"""
        if self.focus_manager:
            self.focus_manager.activate_focused()
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            for button in self.buttons.values():
                button.close()
            Logger.info("GPIOHandler: Cleaned up GPIO resources")
        except Exception as e:
            Logger.error(f"GPIOHandler: Error cleaning up: {e}")

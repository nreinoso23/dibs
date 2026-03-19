"""
PIR Motion Sensor Handler for Screen Power Management
Detects motion and controls screen display
"""
import RPi.GPIO as GPIO
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.graphics import Color, Rectangle
import time


class PIRHandler:
    """Handle PIR motion sensor for screen blanking"""
    
    PIN_PIR = 14
    TIMEOUT_SECONDS = 30  # Turn off screen after 30 seconds of no motion
    
    def __init__(self, app):
        """Initialize PIR sensor
        
        Args:
            app: Reference to the Kivy app instance
        """
        self.app = app
        self.motion_timeout_event = None
        self.screen_is_on = True
        self.last_motion_state = 0
        self.black_overlay = None
        
        try:
            # Initialize PIR sensor using RPi.GPIO (like your working code)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.PIN_PIR, GPIO.IN)
            
            print("\n" + "="*60)
            print("PIR MOTION SENSOR INITIALIZED")
            print(f"GPIO Pin: {self.PIN_PIR}")
            print(f"Timeout: {self.TIMEOUT_SECONDS} seconds")
            print("="*60 + "\n")
            
            # Read initial state
            initial_state = GPIO.input(self.PIN_PIR)
            self.last_motion_state = initial_state
            print(f"[PIR] Initial sensor state: {initial_state} ({'MOTION' if initial_state == 1 else 'NO MOTION'})")
            
            # Start with screen OFF (black overlay)
            print("[PIR] Starting with screen OFF (black)...")
            #Clock.schedule_once(lambda dt: self.turn_screen_off(), 0.5)  # DISABLED
            
            # Schedule PIR checking every 0.1 seconds (like your working code)
            Clock.schedule_interval(self.check_pir_sensor, 0.1)
            
            print("[PIR] Sensor monitoring started. Checking every 0.1 seconds.\n")
            Logger.info("PIRHandler: Motion sensor initialized successfully, screen starting OFF")
            
        except Exception as e:
            print(f"[PIR ERROR] Failed to initialize: {e}")
            Logger.error(f"PIRHandler: Failed to initialize PIR sensor: {e}")
    
    def check_pir_sensor(self, dt):
        """Check PIR sensor state (called every 0.1 seconds)"""
        try:
            current_state = GPIO.input(self.PIN_PIR)
            
            # State changed from no motion to motion
            if current_state == 1 and self.last_motion_state == 0:
                print(f"\n[PIR] >>> MOTION DETECTED at {time.strftime('%H:%M:%S')} <<<")
                self.on_motion_detected()
            # State changed from motion to no motion
            elif current_state == 0 and self.last_motion_state == 1:
                print(f"\n[PIR] >>> NO MOTION at {time.strftime('%H:%M:%S')} <<<")
                self.on_no_motion()
            
            self.last_motion_state = current_state
            
        except Exception as e:
            print(f"[PIR ERROR] Error reading sensor: {e}")
            Logger.error(f"PIRHandler: Error reading PIR sensor: {e}")
    
    def on_motion_detected(self):
        """Handle motion detection"""
        print(f"[PIR] Processing motion event...")
        Logger.info("PIRHandler: Motion detected")
        self.handle_motion()
    
    def on_no_motion(self):
        """Handle when motion stops"""
        print(f"[PIR] Processing no-motion event...")
        Logger.info("PIRHandler: No motion")
        self.handle_no_motion()
    
    def handle_motion(self):
        """Turn screen on when motion detected"""
        # Cancel any pending screen-off event
        if self.motion_timeout_event:
            print(f"[PIR] Cancelling scheduled screen turn-off")
            self.motion_timeout_event.cancel()
            self.motion_timeout_event = None
        
        # Turn screen on if it's off
        if not self.screen_is_on:
            print(f"[PIR] Screen is currently OFF, turning it ON...")
            self.turn_screen_on()
        else:
            print(f"[PIR] Screen already ON, keeping it on")
    
    def handle_no_motion(self):
        """Schedule screen turn-off after timeout"""
        # Cancel any existing timeout
        if self.motion_timeout_event:
            self.motion_timeout_event.cancel()
        
        # Schedule screen turn-off
        print(f"[PIR] Scheduling screen turn-off in {self.TIMEOUT_SECONDS} seconds...")
        Logger.info(f"PIRHandler: Scheduling screen turn-off in {self.TIMEOUT_SECONDS} seconds")
        self.motion_timeout_event = Clock.schedule_once(
            lambda dt: self.turn_screen_off(), 
            self.TIMEOUT_SECONDS
        )
    
    def turn_screen_on(self):
        """Turn the screen on by removing black overlay"""
        try:
            print(f"[PIR] Removing black overlay from window...")
            
            # Remove the black overlay
            if self.black_overlay:
                self.app.root.canvas.after.remove(self.black_overlay)
                self.black_overlay = None
            
            self.screen_is_on = True
            print(f"[PIR] ✓ Screen turned ON")
            
            # Reset focus to check-in button when screen turns on
            if hasattr(self.app, 'focus_manager') and self.app.focus_manager:
                print(f"[PIR] Resetting focus to check-in button...")
                Clock.schedule_once(lambda dt: self.app.focus_manager.set_focus('checkin'), 0.1)
            
            print()
            Logger.info("PIRHandler: Screen turned ON")
        except Exception as e:
            print(f"[PIR ERROR] Failed to turn screen on: {e}\n")
            Logger.error(f"PIRHandler: Failed to turn screen on: {e}")
    
    def turn_screen_off(self):
        """Turn the screen off by adding black overlay"""
        try:
            print(f"[PIR] Adding black overlay to window...")
            
            # Create a black rectangle that covers the entire window
            if not self.black_overlay:
                from kivy.graphics import Color, Rectangle, InstructionGroup
                
                self.black_overlay = InstructionGroup()
                self.black_overlay.add(Color(0, 0, 0, 1))  # Black color
                
                # Get window size
                window = self.app.root.get_parent_window()
                if window:
                    width = window.width
                    height = window.height
                else:
                    width = 800
                    height = 600
                
                self.black_overlay.add(Rectangle(pos=(0, 0), size=(width, height)))
                
                # Add to canvas (on top of everything)
                self.app.root.canvas.after.add(self.black_overlay)
                
                print(f"[PIR] Black overlay added (size: {width}x{height})")
            
            self.screen_is_on = False
            print(f"[PIR] ✓ Screen turned OFF (black overlay active)\n")
            Logger.info("PIRHandler: Screen turned OFF")
        except Exception as e:
            print(f"[PIR ERROR] Failed to turn screen off: {e}\n")
            Logger.error(f"PIRHandler: Failed to turn screen off: {e}")
    
    def cleanup(self):
        """Clean up PIR sensor resources"""
        try:
            print("\n[PIR] Cleaning up...")
            
            # Cancel any pending timeout
            if self.motion_timeout_event:
                self.motion_timeout_event.cancel()
            
            # Turn screen back on (remove overlay)
            if not self.screen_is_on:
                print("[PIR] Turning screen back on before exit...")
                self.turn_screen_on()
            
            # Clean up GPIO
            GPIO.cleanup()
            
            print("[PIR] Cleanup complete\n")
            Logger.info("PIRHandler: Cleaned up PIR sensor resources")
        except Exception as e:
            print(f"[PIR ERROR] Error cleaning up: {e}")
            Logger.error(f"PIRHandler: Error cleaning up: {e}")

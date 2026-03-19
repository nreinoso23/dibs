"""
LED Status Handler for Room Occupancy Indication
Controls red and green LEDs based on room status
"""
import RPi.GPIO as GPIO
from kivy.logger import Logger


class LEDStatusHandler:
    """Handle LED status indicators for room occupancy"""
    
    PIN_RED_LED = 11   # Red LED - Room OCCUPIED/NOT AVAILABLE
    PIN_GREEN_LED = 9   # Green LED - Room AVAILABLE
    
    def __init__(self, app):
        """Initialize LED status handler
        
        Args:
            app: Reference to the Kivy app instance
        """
        self.app = app
        self.current_status = None
        
        try:
            # Initialize GPIO pins for LEDs
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.PIN_RED_LED, GPIO.OUT)
            GPIO.setup(self.PIN_GREEN_LED, GPIO.OUT)
            
            # Start with both LEDs off
            GPIO.output(self.PIN_RED_LED, GPIO.LOW)
            GPIO.output(self.PIN_GREEN_LED, GPIO.LOW)
            
            print("\n" + "="*60)
            print("LED STATUS HANDLER INITIALIZED")
            print(f"Green LED (Available): GPIO {self.PIN_GREEN_LED}")
            print(f"Red LED (Occupied/Not Available): GPIO {self.PIN_RED_LED}")
            print("="*60)
            print("[LED] Both LEDs set to OFF initially")
            print("="*60 + "\n")
            
            # Set initial LED status based on room state
            self.update_led_status()
            
            Logger.info("LEDStatusHandler: LED status handler initialized successfully")
            
        except Exception as e:
            print(f"[LED ERROR] Failed to initialize: {e}")
            Logger.error(f"LEDStatusHandler: Failed to initialize LED handler: {e}")
    
    def update_led_status(self):
        """Update LED status based on current room state"""
        try:
            # Get current room state from reservation manager
            if hasattr(self.app, 'reservation_manager'):
                is_occupied = self.app.reservation_manager.is_room_occupied()
                
                print(f"[LED DEBUG] Checking room status...")
                print(f"[LED DEBUG] is_room_occupied() returned: {is_occupied}")
                
                if is_occupied:
                    # Room is OCCUPIED - RED LED on, GREEN LED off
                    if self.current_status != 'occupied':
                        print(f"\n[LED] >>> STATUS CHANGE: Room is now OCCUPIED <<<")
                        print(f"[LED] Setting RED LED (GPIO {self.PIN_RED_LED}) to HIGH")
                        GPIO.output(self.PIN_RED_LED, GPIO.HIGH)
                        
                        print(f"[LED] Setting GREEN LED (GPIO {self.PIN_GREEN_LED}) to LOW")
                        GPIO.output(self.PIN_GREEN_LED, GPIO.LOW)
                        
                        # Read back the GPIO states to verify
                        red_state = GPIO.input(self.PIN_RED_LED)
                        green_state = GPIO.input(self.PIN_GREEN_LED)
                        print(f"[LED] Verification - RED LED state: {red_state} (1=ON, 0=OFF)")
                        print(f"[LED] Verification - GREEN LED state: {green_state} (1=ON, 0=OFF)")
                        
                        self.current_status = 'occupied'
                        print(f"[LED] Current status set to: {self.current_status}\n")
                        Logger.info("LEDStatusHandler: Room occupied - red LED on")
                    else:
                        print(f"[LED] Status unchanged - still occupied (RED LED already on)")
                else:
                    # Room is AVAILABLE - GREEN LED on, RED LED off
                    if self.current_status != 'available':
                        print(f"\n[LED] >>> STATUS CHANGE: Room is now AVAILABLE <<<")
                        print(f"[LED] Setting RED LED (GPIO {self.PIN_RED_LED}) to LOW")
                        GPIO.output(self.PIN_RED_LED, GPIO.LOW)
                        
                        print(f"[LED] Setting GREEN LED (GPIO {self.PIN_GREEN_LED}) to HIGH")
                        GPIO.output(self.PIN_GREEN_LED, GPIO.HIGH)
                        
                        # Read back the GPIO states to verify
                        red_state = GPIO.input(self.PIN_RED_LED)
                        green_state = GPIO.input(self.PIN_GREEN_LED)
                        print(f"[LED] Verification - RED LED state: {red_state} (1=ON, 0=OFF)")
                        print(f"[LED] Verification - GREEN LED state: {green_state} (1=ON, 0=OFF)")
                        
                        self.current_status = 'available'
                        print(f"[LED] Current status set to: {self.current_status}\n")
                        Logger.info("LEDStatusHandler: Room available - green LED on")
                    else:
                        print(f"[LED] Status unchanged - still available (GREEN LED already on)")
            else:
                print("[LED ERROR] Reservation manager not found!")
            
        except Exception as e:
            print(f"[LED ERROR] Failed to update LED status: {e}")
            import traceback
            traceback.print_exc()
            Logger.error(f"LEDStatusHandler: Failed to update LED status: {e}")
    
    def turn_red_on(self):
        """Turn red LED on (occupied/not available)"""
        try:
            print("[LED MANUAL] Manually turning RED LED ON (occupied)")
            GPIO.output(self.PIN_RED_LED, GPIO.HIGH)
            GPIO.output(self.PIN_GREEN_LED, GPIO.LOW)
            
            # Verify
            red_state = GPIO.input(self.PIN_RED_LED)
            green_state = GPIO.input(self.PIN_GREEN_LED)
            print(f"[LED MANUAL] RED: {red_state}, GREEN: {green_state}")
            
            self.current_status = 'occupied'
        except Exception as e:
            print(f"[LED ERROR] Failed to turn red LED on: {e}")
    
    def turn_green_on(self):
        """Turn green LED on (available)"""
        try:
            print("[LED MANUAL] Manually turning GREEN LED ON (available)")
            GPIO.output(self.PIN_RED_LED, GPIO.LOW)
            GPIO.output(self.PIN_GREEN_LED, GPIO.HIGH)
            
            # Verify
            red_state = GPIO.input(self.PIN_RED_LED)
            green_state = GPIO.input(self.PIN_GREEN_LED)
            print(f"[LED MANUAL] RED: {red_state}, GREEN: {green_state}")
            
            self.current_status = 'available'
        except Exception as e:
            print(f"[LED ERROR] Failed to turn green LED on: {e}")
    
    def turn_all_off(self):
        """Turn all LEDs off"""
        try:
            print("[LED] Turning ALL LEDs OFF")
            GPIO.output(self.PIN_RED_LED, GPIO.LOW)
            GPIO.output(self.PIN_GREEN_LED, GPIO.LOW)
            self.current_status = None
        except Exception as e:
            print(f"[LED ERROR] Failed to turn LEDs off: {e}")
    
    def cleanup(self):
        """Clean up LED resources"""
        try:
            print("\n[LED] Cleaning up LEDs...")
            
            # Turn off all LEDs
            GPIO.output(self.PIN_RED_LED, GPIO.LOW)
            GPIO.output(self.PIN_GREEN_LED, GPIO.LOW)
            
            # Note: We don't call GPIO.cleanup() here because PIR handler will do it
            # Multiple GPIO.cleanup() calls will cause errors
            
            print("[LED] LED cleanup complete\n")
            Logger.info("LEDStatusHandler: Cleaned up LED resources")
        except Exception as e:
            print(f"[LED ERROR] Error cleaning up: {e}")
            Logger.error(f"LEDStatusHandler: Error cleaning up: {e}")

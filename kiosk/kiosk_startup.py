#!/usr/bin/env python3
"""
NYU Study Room Kiosk - Startup GUI (Kivy-based)
Matches the style of the main check-in screen
UPDATED VERSION - Correct paths and venv support
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.config import Config
import subprocess
import os
import time
import sys

# Configure fullscreen before window creation
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'borderless', '1')

# Set window size to match your main GUI
Window.size = (800, 600)

class IPKeyboard(GridLayout):
    """Custom keyboard for IP address input with . button"""
    def __init__(self, on_key_press=None, **kwargs):
        super().__init__(**kwargs)
        self.cols = 10
        self.spacing = 5
        self.padding = 10
        self.on_key_press = on_key_press
        
        # Numbers row
        numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
        for num in numbers:
            btn = Button(
                text=num,
                font_size='24sp',
                background_color=(0.3, 0.5, 0.7, 1),
                background_normal=''
            )
            btn.bind(on_press=lambda x, key=num: self.key_pressed(key))
            self.add_widget(btn)
        
        # Dot button (larger, spans multiple columns)
        dot_btn = Button(
            text='.',
            font_size='32sp',
            background_color=(0.2, 0.6, 0.4, 1),
            background_normal='',
            size_hint_x=3
        )
        dot_btn.bind(on_press=lambda x: self.key_pressed('.'))
        self.add_widget(dot_btn)
        
        # Clear button
        clear_btn = Button(
            text='Clear',
            font_size='20sp',
            background_color=(0.8, 0.4, 0.2, 1),
            background_normal='',
            size_hint_x=3
        )
        clear_btn.bind(on_press=lambda x: self.key_pressed('Clear'))
        self.add_widget(clear_btn)
        
        # Backspace button
        back_btn = Button(
            text='⌫',
            font_size='28sp',
            background_color=(0.7, 0.3, 0.3, 1),
            background_normal='',
            size_hint_x=4
        )
        back_btn.bind(on_press=lambda x: self.key_pressed('Backspace'))
        self.add_widget(back_btn)
    
    def key_pressed(self, key):
        """Handle key press"""
        if self.on_key_press:
            self.on_key_press(key)


class StartupScreen(BoxLayout):
    """Main startup screen"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 20
        
        # Load saved IP or use default
        self.ip_text = self.load_saved_ip()
        
        self.build_ui()
    
    def load_saved_ip(self):
        """Load saved IP from config file"""
        config_path = os.path.expanduser("~/esp32_cam/esp32_ip.txt")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    saved_ip = f.read().strip()
                    if saved_ip:
                        return saved_ip
        except:
            pass
        return "10.253.58.22"  # Default IP
    
    def save_ip(self, ip):
        """Save IP to config file"""
        config_path = os.path.expanduser("~/esp32_cam/esp32_ip.txt")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                f.write(ip)
        except Exception as e:
            print(f"Warning: Could not save IP: {e}")
    
    def build_ui(self):
        """Build the UI matching check-in screen style"""
        # Title
        title = Label(
            text='NYU Study Room Kiosk',
            font_size='36sp',
            size_hint_y=0.15,
            bold=True,
            color=(0.2, 0.4, 0.8, 1)
        )
        self.add_widget(title)
        
        # Subtitle
        subtitle = Label(
            text='System Startup Configuration',
            font_size='24sp',
            size_hint_y=0.1,
            color=(0.3, 0.3, 0.3, 1)
        )
        self.add_widget(subtitle)
        
        # Instruction
        instruction = Label(
            text='Enter ESP32-CAM IP Address:',
            font_size='20sp',
            size_hint_y=0.08,
            color=(0.2, 0.2, 0.2, 1)
        )
        self.add_widget(instruction)
        
        # IP Display (like N-number display in check-in)
        self.ip_display = Label(
            text=self.ip_text,
            font_size='48sp',
            size_hint_y=0.15,
            bold=True,
            color=(0.1, 0.1, 0.1, 1)
        )
        self.add_widget(self.ip_display)
        
        # Keyboard
        keyboard = IPKeyboard(
            on_key_press=self.handle_key,
            size_hint_y=0.25
        )
        self.add_widget(keyboard)
        
        # Status label
        self.status_label = Label(
            text='Ready to start',
            font_size='18sp',
            size_hint_y=0.08,
            color=(0.2, 0.5, 0.8, 1)
        )
        self.add_widget(self.status_label)
        
        # Buttons container
        button_box = BoxLayout(
            orientation='horizontal',
            size_hint_y=0.15,
            spacing=10
        )
        
        # Start button
        start_btn = Button(
            text='Start System',
            font_size='24sp',
            background_color=(0.2, 0.7, 0.3, 1),
            background_normal='',
            bold=True
        )
        start_btn.bind(on_press=self.start_system)
        button_box.add_widget(start_btn)
        
        # Cancel button
        cancel_btn = Button(
            text='Cancel',
            font_size='24sp',
            background_color=(0.7, 0.3, 0.3, 1),
            background_normal='',
            bold=True
        )
        cancel_btn.bind(on_press=self.cancel)
        button_box.add_widget(cancel_btn)
        
        self.add_widget(button_box)
    
    def handle_key(self, key):
        """Handle keyboard input"""
        if key == 'Clear':
            self.ip_text = ""
        elif key == 'Backspace':
            self.ip_text = self.ip_text[:-1]
        else:
            # Limit length to reasonable IP (15 chars max: xxx.xxx.xxx.xxx)
            if len(self.ip_text) < 15:
                self.ip_text += key
        
        self.ip_display.text = self.ip_text if self.ip_text else "___.___.___.___"
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.text = message
    
    def start_system(self, instance):
        """Start all system components"""
        esp32_ip = self.ip_text.strip()
        
        # Validate IP
        if not esp32_ip or esp32_ip.count('.') != 3:
            self.update_status("✗ Invalid IP address format")
            return
        
        parts = esp32_ip.split('.')
        try:
            if not all(0 <= int(part) <= 255 for part in parts):
                self.update_status("✗ Invalid IP address")
                return
        except ValueError:
            self.update_status("✗ Invalid IP address")
            return
        
        # Save IP for next time
        self.save_ip(esp32_ip)
        
        # Disable buttons
        instance.disabled = True
        
        try:
            # Paths - using correct structure
            sldp_dir = os.path.expanduser("~/projects/SLDP")
            esp32_cam_dir = os.path.expanduser("~/esp32_cam")
            
            # Check if directories exist
            if not os.path.exists(sldp_dir):
                self.update_status(f"✗ Error: {sldp_dir} not found")
                instance.disabled = False
                return
            
            if not os.path.exists(esp32_cam_dir):
                self.update_status(f"✗ Error: {esp32_cam_dir} not found")
                instance.disabled = False
                return
            
            # 1. Start API Server
            self.update_status("Starting API server...")
            api_log_path = os.path.join(sldp_dir, "api_server.log")
            api_log = open(api_log_path, 'w')
            api_script = os.path.join(sldp_dir, "kiosk_api_server.py")
            
            api_process = subprocess.Popen(
                [sys.executable, api_script],
                cwd=sldp_dir,
                stdout=api_log,
                stderr=subprocess.STDOUT
            )
            time.sleep(3)  # Wait for API to start
            
            # 2. Start Smart LCD with ESP32 IP (using VENV)
            self.update_status("Starting face detection & LCD...")
            
            # Check for venv
            venv_python = os.path.join(esp32_cam_dir, "venv", "bin", "python3")
            if os.path.exists(venv_python):
                python_cmd = venv_python
                self.update_status("Using venv for ESP32 controller...")
            else:
                python_cmd = sys.executable
                self.update_status("No venv found, using system Python...")
            
            # Use the HEADLESS version
            lcd_script = os.path.join(esp32_cam_dir, "pi_cam_smart_lcd_headless.py")
            
            # Check if headless version exists, otherwise use regular version
            if not os.path.exists(lcd_script):
                lcd_script = os.path.join(esp32_cam_dir, "pi_cam_smart_lcd.py")
                self.update_status("Warning: Using windowed version (headless not found)")
            
            lcd_log_path = os.path.join(esp32_cam_dir, "lcd_controller.log")
            lcd_log = open(lcd_log_path, 'w')
            
            # Start LCD controller with IP piped in
            lcd_process = subprocess.Popen(
                [python_cmd, lcd_script],
                cwd=esp32_cam_dir,
                stdin=subprocess.PIPE,
                stdout=lcd_log,
                stderr=subprocess.STDOUT
            )
            
            # Send IP address via stdin
            lcd_process.stdin.write(f"{esp32_ip}\n".encode())
            lcd_process.stdin.flush()
            lcd_process.stdin.close()
            
            time.sleep(2)
            
            # 3. Start Main GUI (fullscreen)
            self.update_status("Starting main kiosk interface...")
            
            # Use fullscreen wrapper if it exists
            fullscreen_script = os.path.join(sldp_dir, "run_gui_fullscreen.sh")
            app_script = os.path.join(sldp_dir, "app.py")
            
            if os.path.exists(fullscreen_script):
                gui_process = subprocess.Popen(
                    ['bash', fullscreen_script],
                    cwd=sldp_dir
                )
            else:
                # Start directly if no wrapper
                gui_process = subprocess.Popen(
                    [sys.executable, app_script],
                    cwd=sldp_dir
                )
            
            # Success!
            self.update_status("✓ All systems started!")
            
            # Log the PIDs for reference
            log_info = f"""
System Started Successfully!
API Server PID: {api_process.pid}
LCD Controller PID: {lcd_process.pid}
Main GUI PID: {gui_process.pid}
ESP32 IP: {esp32_ip}

Logs:
- API: {api_log_path}
- LCD: {lcd_log_path}
"""
            startup_log = os.path.join(sldp_dir, "startup.log")
            with open(startup_log, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Startup at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(log_info)
            
            print(log_info)
            
            # Close this window after 2 seconds
            Clock.schedule_once(lambda dt: App.get_running_app().stop(), 2)
            
        except Exception as e:
            self.update_status(f"✗ Error: {str(e)}")
            print(f"Startup error: {e}")
            import traceback
            traceback.print_exc()
            instance.disabled = False
    
    def cancel(self, instance):
        """Cancel and exit"""
        App.get_running_app().stop()


class KioskStartupApp(App):
    def build(self):
        self.title = 'Study Room Kiosk - Startup'
        return StartupScreen()


if __name__ == '__main__':
    print("=" * 60)
    print("NYU Study Room Kiosk - Startup Launcher")
    print("=" * 60)
    print(f"Python: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 60)
    KioskStartupApp().run()

#!/usr/bin/env python3
"""
ESP32-CAM Smart LCD Controller - HEADLESS VERSION
NO GUI WINDOW - Runs completely in background
Auto-turns off LCD backlight when no faces detected for a period
"""

import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # Prevent any GUI windows

import cv2
import requests
import time
import sys
import logging
from datetime import datetime
from cvzone import FaceDetectionModule

# Setup logging
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'lcd_controller.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

class ESP32CamSmartController:
    def __init__(self, esp32_ip='10.253.71.82', api_base_url='http://localhost:5000'):
        self.esp32_ip = esp32_ip
        self.stream_url = f'http://{esp32_ip}:81/stream'
        self.lcd_url = f'http://{esp32_ip}/lcd'
        self.lcd_backlight_url = f'http://{esp32_ip}/lcd/backlight'
        self.api_base_url = api_base_url
        self.face_detector = FaceDetectionModule.FaceDetector(minDetectionCon=0.45)
        self.cap = None
        
        # State tracking
        self.last_face_count = 0
        self.last_lcd_update = 0
        self.lcd_update_interval = 10  # Only check every 10 seconds
        self.lcd_retry_count = 0
        self.max_lcd_retries = 5
        self.lcd_working = False
        self.last_lcd_line1 = ""
        self.last_lcd_line2 = ""
        
        # Backlight control
        self.backlight_on = True
        self.last_face_seen_time = time.time()
        self.backlight_timeout = 30  # Turn off backlight after 30 seconds with no faces
        
    def connect_stream(self):
        """Connect to the video stream"""
        logging.info(f"Connecting to video stream at {self.stream_url}...")
        self.cap = cv2.VideoCapture(self.stream_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            raise ConnectionError(f"Failed to connect to stream at {self.stream_url}")
        
        logging.info("Stream connected successfully!")
        return True
    
    def set_lcd_backlight(self, on):
        """Control LCD backlight on/off"""
        # Only send if state is changing
        if on == self.backlight_on:
            return True
        
        state = 'on' if on else 'off'
        
        try:
            response = requests.post(
                self.lcd_backlight_url, 
                data={'state': state}, 
                timeout=5
            )
            
            if response.status_code == 200:
                self.backlight_on = on
                logging.info(f"LCD backlight turned {state.upper()}")
                return True
            else:
                logging.warning(f"Failed to set backlight: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logging.warning("Backlight request timeout")
            return False
        except Exception as e:
            logging.error(f"Backlight error: {e}")
            return False
    
    def send_lcd_text(self, line1="", line2=""):
        """Send text to ESP32 LCD display - only if text changed"""
        line1 = str(line1)[:16]
        line2 = str(line2)[:16]
        
        # Only send if text has changed
        if line1 == self.last_lcd_line1 and line2 == self.last_lcd_line2:
            return True  # No update needed
        
        for attempt in range(self.max_lcd_retries):
            try:
                data = {'line1': line1, 'line2': line2}
                response = requests.post(self.lcd_url, data=data, timeout=5)
                
                if response.status_code == 200:
                    self.lcd_retry_count = 0
                    self.lcd_working = True
                    # Remember what we sent
                    self.last_lcd_line1 = line1
                    self.last_lcd_line2 = line2
                    logging.info(f"LCD: '{line1}' / '{line2}'")
                    return True
                    
            except requests.exceptions.Timeout:
                logging.warning(f"LCD timeout (attempt {attempt+1}/{self.max_lcd_retries})")
                time.sleep(1)
            except Exception as e:
                logging.error(f"LCD error: {e}")
                time.sleep(1)
        
        self.lcd_retry_count += 1
        return False
    
    def get_room_status(self):
        """Get current room status from kiosk API"""
        try:
            response = requests.get(f'{self.api_base_url}/api/room_status', timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.debug(f"API error (using fallback): {e}")
        
        return {'state': 'available', 'current_reservation': None}
    
    def format_time_short(self, time_str):
        """Convert time string to format like '10:00 PM' or '9:15 AM'"""
        try:
            # Parse the datetime string
            if 'Z' in time_str:
                time_str = time_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(time_str)
            
            hour = dt.hour
            minute = dt.minute
            
            # Convert to 12-hour format
            if hour == 0:
                h = 12
                ap = "AM"
            elif hour < 12:
                h = hour
                ap = "AM"
            elif hour == 12:
                h = 12
                ap = "PM"
            else:
                h = hour - 12
                ap = "PM"
            
            # Build string manually
            result = str(h) + ":" + str(minute).zfill(2) + " " + ap
            return result
        except Exception as e:
            logging.error(f"Time format error: {e}")
            return "--:-- --"
    
    def format_time_brief(self, time_str):
        """Convert time string to brief format like '9:30a' for tight spaces"""
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            hour = dt.hour
            minute = dt.minute
            
            # Convert to 12-hour format
            if hour == 0:
                hour_12 = 12
                ampm = 'a'
            elif hour < 12:
                hour_12 = hour
                ampm = 'a'
            elif hour == 12:
                hour_12 = 12
                ampm = 'p'
            else:
                hour_12 = hour - 12
                ampm = 'p'
            
            return f"{hour_12}:{minute:02d}{ampm}"
        except:
            return "--:--"
    
    def format_time_remaining(self, end_time_str):
        """Convert end time for LCD - returns exactly 16 chars"""
        time_part = self.format_time_short(end_time_str)
        result = "Ends " + time_part
        # Pad to exactly 16 chars with spaces
        while len(result) < 16:
            result = result + " "
        return result
    
    def update_smart_lcd(self, face_count, room_status):
        """Update LCD based on face detection + room status"""
        state = room_status.get('state', 'available')
        current_res = room_status.get('current_reservation')
        
        if face_count == 0:
            if state == 'available':
                self.send_lcd_text("Room Available", "Ready to book")
            elif state == 'check_in_ready':
                # Show appointment time and direct to outer kiosk
                if current_res and 'start_time' in current_res:
                    time_str = self.format_time_brief(current_res['start_time'])
                    self.send_lcd_text(f"Appt at {time_str}", "Use outer kiosk")
                else:
                    self.send_lcd_text("Appt scheduled", "Use outer kiosk")
            elif state == 'occupied':
                if current_res and 'end_time' in current_res:
                    end_str = self.format_time_remaining(current_res['end_time'])
                    self.send_lcd_text("Occupied", end_str)
                else:
                    self.send_lcd_text("Occupied", "In use")
        else:
            if state == 'available':
                self.send_lcd_text("Please check in", "on the device")
            elif state == 'check_in_ready':
                # Show appointment time and direct to outer kiosk
                if current_res and 'start_time' in current_res:
                    time_str = self.format_time_brief(current_res['start_time'])
                    self.send_lcd_text(f"Appt at {time_str}", "Use outer kiosk")
                else:
                    self.send_lcd_text("Appt scheduled", "Use outer kiosk")
            elif state == 'occupied':
                if current_res and 'end_time' in current_res:
                    end_str = self.format_time_remaining(current_res['end_time'])
                    if face_count == 1:
                        self.send_lcd_text("Active Booking", end_str)
                    else:
                        self.send_lcd_text(f"{face_count} people", end_str)
                else:
                    self.send_lcd_text("Session active", "In use")
    
    def update_backlight_state(self, face_count):
        """Update backlight based on face detection"""
        current_time = time.time()
        
        if face_count > 0:
            # Face detected - update last seen time and turn on backlight
            self.last_face_seen_time = current_time
            if not self.backlight_on:
                logging.info("Face detected - turning backlight ON")
                self.set_lcd_backlight(True)
        else:
            # No faces - check if timeout reached
            time_since_face = current_time - self.last_face_seen_time
            if self.backlight_on and time_since_face >= self.backlight_timeout:
                logging.info(f"No faces for {self.backlight_timeout}s - turning backlight OFF")
                self.set_lcd_backlight(False)
    
    def run_smart_face_detection_headless(self):
        """HEADLESS face detection - NO GUI WINDOW"""
        if not self.cap:
            self.connect_stream()
        
        skip_frames = 12
        process_width = 180
        
        face_count = 0
        frame_count = 0
        detection_count = 0
        start_time = time.time()
        
        room_status_check_timer = time.time()
        status_report_timer = time.time()
        backlight_check_timer = time.time()
        
        logging.info("=" * 60)
        logging.info("SMART LCD Face Detection Running (HEADLESS)")
        logging.info(f"Backlight timeout: {self.backlight_timeout} seconds")
        logging.info("=" * 60)
        
        room_status = self.get_room_status()
        time.sleep(2)
        self.update_smart_lcd(0, room_status)
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    logging.warning("Can't receive frame. Reconnecting...")
                    self.cap.release()
                    time.sleep(2)
                    self.cap = cv2.VideoCapture(self.stream_url)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    continue
                
                frame_count += 1
                
                if frame_count % skip_frames == 0:
                    height, width = frame.shape[:2]
                    scale = process_width / width
                    small_frame = cv2.resize(frame, (process_width, int(height * scale)))
                    
                    small_frame_detected, list_faces = self.face_detector.findFaces(small_frame, draw=False)
                    face_count = len(list_faces) if list_faces else 0
                    detection_count += 1
                    logging.debug(f"Detected {face_count} faces")
                
                # Check room status every 5 seconds
                if time.time() - room_status_check_timer > 5.0:
                    room_status = self.get_room_status()
                    room_status_check_timer = time.time()
                
                # Update LCD text when face count changes or periodically
                current_time = time.time()
                if (face_count != self.last_face_count or 
                    current_time - self.last_lcd_update > self.lcd_update_interval):
                    self.update_smart_lcd(face_count, room_status)
                    self.last_face_count = face_count
                    self.last_lcd_update = current_time
                
                # Check backlight state every second
                if time.time() - backlight_check_timer > 1.0:
                    self.update_backlight_state(face_count)
                    backlight_check_timer = time.time()
                
                # Log status every 30 seconds
                if time.time() - status_report_timer > 30.0:
                    elapsed = time.time() - start_time
                    avg_detection_rate = detection_count / elapsed
                    state_text = room_status.get('state', 'unknown')
                    backlight_status = "ON" if self.backlight_on else "OFF"
                    time_since_face = int(time.time() - self.last_face_seen_time)
                    logging.info(f"Status: {face_count} faces | Room: {state_text} | Backlight: {backlight_status} | Last face: {time_since_face}s ago | Rate: {avg_detection_rate:.2f}/s")
                    status_report_timer = time.time()
        
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Release resources"""
        logging.info("Cleaning up...")
        # Turn backlight back on when exiting
        self.set_lcd_backlight(True)
        if self.cap:
            self.cap.release()


def main():
    logging.info("=" * 60)
    logging.info("ESP32-CAM Smart LCD Controller - HEADLESS")
    logging.info("With auto-backlight control")
    logging.info("=" * 60)
    
    esp32_ip = '10.253.71.82'
    if not sys.stdin.isatty():
        try:
            piped_ip = sys.stdin.readline().strip()
            import re
            ip_match = re.match(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', piped_ip)
            if ip_match:
                esp32_ip = ip_match.group(1)
                logging.info(f"Read IP from stdin: {piped_ip} -> cleaned to: {esp32_ip}")
        except Exception as e:
            logging.warning(f"Error reading stdin: {e}")
    
    api_base_url = 'http://localhost:5000'
    logging.info(f"ESP32 IP: {esp32_ip}")
    logging.info(f"Kiosk API: {api_base_url}")
    
    controller = ESP32CamSmartController(esp32_ip, api_base_url)
    controller.run_smart_face_detection_headless()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
ESP32-CAM Smart LCD Controller - IMPROVED VERSION
Enhanced LCD communication with extensive debugging

Improvements:
- Test LCD connection on startup
- Longer delays between updates
- Detailed response logging
- Connection verification
- Better error messages
"""

import cv2
import requests
import time
import sys
import os
import logging
from datetime import datetime, timedelta
from cvzone import FaceDetectionModule

# Setup logging
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'lcd_controller.log')

logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more details
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
        self.web_url = f'http://{esp32_ip}'
        self.api_base_url = api_base_url
        self.face_detector = FaceDetectionModule.FaceDetector(minDetectionCon=0.45)
        self.cap = None
        
        # State tracking
        self.last_face_count = 0
        self.last_lcd_update = 0
        self.lcd_update_interval = 3  # Increased to 3 seconds
        self.lcd_retry_count = 0
        self.max_lcd_retries = 5  # Increased retries
        self.lcd_working = False  # Track if LCD ever worked
        
    def test_esp32_connection(self):
        """Test all ESP32 endpoints before starting"""
        logging.info("=" * 60)
        logging.info("Testing ESP32 Connection...")
        logging.info("=" * 60)
        
        # Test 1: Web interface
        logging.info(f"Test 1: Web interface at {self.web_url}")
        try:
            response = requests.get(self.web_url, timeout=5)
            if response.status_code == 200:
                logging.info("✓ Web interface OK")
            else:
                logging.warning(f"⚠ Web interface returned {response.status_code}")
        except Exception as e:
            logging.error(f"✗ Web interface failed: {e}")
            return False
        
        # Test 2: Video stream
        logging.info(f"Test 2: Video stream at {self.stream_url}")
        try:
            response = requests.get(self.stream_url, timeout=5, stream=True)
            if response.status_code == 200:
                logging.info("✓ Video stream OK")
            else:
                logging.warning(f"⚠ Video stream returned {response.status_code}")
        except Exception as e:
            logging.error(f"✗ Video stream failed: {e}")
        
        # Test 3: LCD endpoint (CRITICAL)
        logging.info(f"Test 3: LCD endpoint at {self.lcd_url}")
        test_successful = False
        for attempt in range(3):
            try:
                logging.info(f"  Attempt {attempt + 1}/3...")
                data = {'line1': 'Test Connection', 'line2': f'Attempt {attempt + 1}'}
                response = requests.post(self.lcd_url, data=data, timeout=5)
                
                logging.info(f"  Status Code: {response.status_code}")
                logging.info(f"  Response Headers: {dict(response.headers)}")
                logging.info(f"  Response Body: {response.text[:200]}")
                
                if response.status_code == 200:
                    logging.info("✓ LCD endpoint OK")
                    self.lcd_working = True
                    test_successful = True
                    break
                else:
                    logging.warning(f"⚠ LCD endpoint returned {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logging.error(f"✗ LCD timeout on attempt {attempt + 1}")
            except Exception as e:
                logging.error(f"✗ LCD error on attempt {attempt + 1}: {e}")
            
            if attempt < 2:
                time.sleep(2)  # Wait before retry
        
        if not test_successful:
            logging.error("✗ LCD endpoint failed all tests!")
            logging.error("  Check ESP32 Serial Monitor for errors")
            logging.error("  Verify I2C LCD is connected properly")
            return False
        
        logging.info("=" * 60)
        logging.info("All tests passed! Starting main loop...")
        logging.info("=" * 60)
        return True
    
    def connect_stream(self):
        """Connect to the video stream"""
        logging.info(f"Connecting to video stream at {self.stream_url}...")
        self.cap = cv2.VideoCapture(self.stream_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            raise ConnectionError(f"Failed to connect to stream at {self.stream_url}")
        
        logging.info("Stream connected successfully!")
        return True
    
    def send_lcd_text(self, line1="", line2=""):
        """Send text to ESP32 LCD display with enhanced retry logic"""
        # Truncate to 16 characters
        line1 = line1[:16]
        line2 = line2[:16]
        
        for attempt in range(self.max_lcd_retries):
            try:
                data = {'line1': line1, 'line2': line2}
                
                # Log the attempt
                if attempt > 0:
                    logging.warning(f"LCD retry {attempt}/{self.max_lcd_retries}")
                
                response = requests.post(self.lcd_url, data=data, timeout=5)
                
                # Log detailed response
                logging.debug(f"LCD Request: {data}")
                logging.debug(f"LCD Response Status: {response.status_code}")
                logging.debug(f"LCD Response Body: {response.text[:100]}")
                
                if response.status_code == 200:
                    logging.info(f"LCD: '{line1}' / '{line2}'")
                    self.lcd_retry_count = 0
                    self.lcd_working = True
                    return True
                else:
                    logging.warning(f"LCD returned status {response.status_code}: {response.text[:50]}")
                    
            except requests.exceptions.Timeout:
                logging.warning(f"LCD timeout (attempt {attempt+1}/{self.max_lcd_retries})")
                time.sleep(1)  # Wait before retry
            except requests.exceptions.ConnectionError as e:
                logging.error(f"LCD connection error: {e}")
                time.sleep(1)
            except Exception as e:
                logging.error(f"LCD unexpected error: {e}")
                time.sleep(1)
        
        self.lcd_retry_count += 1
        if self.lcd_retry_count > 5:
            logging.error("=" * 60)
            logging.error("LCD COMMUNICATION FAILING REPEATEDLY!")
            logging.error("Possible causes:")
            logging.error("  1. ESP32 crashed - check serial monitor")
            logging.error("  2. I2C LCD disconnected")
            logging.error("  3. Network issues")
            logging.error("  4. ESP32 /lcd endpoint not responding")
            logging.error("=" * 60)
        return False
    
    def get_room_status(self):
        """Get current room status from your kiosk API"""
        try:
            response = requests.get(f'{self.api_base_url}/api/room_status', timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.debug(f"API error (using fallback): {e}")
        
        # Fallback - return available state
        return {'state': 'available', 'current_reservation': None}
    
    def format_time_remaining(self, end_time_str):
        """Convert end time string to readable format"""
        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            return end_time.strftime("Ends: %I:%M %p")
        except:
            return "Ends: Unknown"
    
    def update_smart_lcd(self, face_count, room_status):
        """Update LCD based on face detection + room status"""
        state = room_status.get('state', 'available')
        current_res = room_status.get('current_reservation')
        
        # No faces detected
        if face_count == 0:
            if state == 'available':
                self.send_lcd_text("Room Available", "Ready to book")
            elif state == 'check_in_ready':
                self.send_lcd_text("Check-in Ready", "Waiting for you")
            elif state == 'occupied':
                if current_res and 'end_time' in current_res:
                    end_str = self.format_time_remaining(current_res['end_time'])
                    self.send_lcd_text("Occupied", end_str)
                else:
                    self.send_lcd_text("Occupied", "In use")
        
        # Faces detected!
        else:
            if state == 'available':
                self.send_lcd_text("Please check in", "on the device")
            elif state == 'check_in_ready':
                self.send_lcd_text("Check-in open!", "Scan your ID")
            elif state == 'occupied':
                if current_res and 'end_time' in current_res:
                    end_str = self.format_time_remaining(current_res['end_time'])
                    if face_count == 1:
                        self.send_lcd_text("Active booking", end_str)
                    else:
                        self.send_lcd_text(f"{face_count} people here", end_str)
                else:
                    self.send_lcd_text("Session active", "In use")
    
    def run_smart_face_detection_headless(self):
        """HEADLESS face detection - NO GUI WINDOW"""
        
        # Test connection first
        if not self.test_esp32_connection():
            logging.error("=" * 60)
            logging.error("CONNECTION TEST FAILED!")
            logging.error("Please check:")
            logging.error(f"  1. ESP32 IP is correct: {self.esp32_ip}")
            logging.error("  2. Raspberry Pi is connected to ESP32 WiFi")
            logging.error("  3. ESP32 is powered on and running")
            logging.error("  4. Check ESP32 Serial Monitor for errors")
            logging.error("=" * 60)
            return
        
        if not self.cap:
            self.connect_stream()
        
        # Adaptive parameters
        skip_frames = 12
        process_width = 180
        
        # State variables
        face_count = 0
        frame_count = 0
        detection_count = 0
        start_time = time.time()
        
        # Timers
        adjustment_timer = time.time()
        room_status_check_timer = time.time()
        status_report_timer = time.time()
        
        logging.info("=" * 60)
        logging.info("SMART LCD Face Detection Running (HEADLESS)")
        logging.info("=" * 60)
        logging.info(f"ESP32 IP: {self.esp32_ip}")
        logging.info(f"LCD URL: {self.lcd_url}")
        logging.info(f"Stream URL: {self.stream_url}")
        logging.info(f"Skip frames: {skip_frames}")
        logging.info(f"LCD update interval: {self.lcd_update_interval}s")
        logging.info("=" * 60)
        
        # Initial status check and LCD update
        room_status = self.get_room_status()
        time.sleep(2)  # Give ESP32 time to be ready
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
                
                # Process face detection every Nth frame
                if frame_count % skip_frames == 0:
                    # Resize for faster processing
                    height, width = frame.shape[:2]
                    scale = process_width / width
                    small_frame = cv2.resize(frame, (process_width, int(height * scale)))
                    
                    # Detect faces
                    small_frame_detected, list_faces = self.face_detector.findFaces(small_frame, draw=False)
                    
                    # Update face count
                    face_count = len(list_faces) if list_faces else 0
                    detection_count += 1
                    
                    logging.debug(f"Detected {face_count} faces")
                
                # Check room status every 5 seconds
                if time.time() - room_status_check_timer > 5.0:
                    room_status = self.get_room_status()
                    room_status_check_timer = time.time()
                    logging.debug(f"Room status: {room_status.get('state')}")
                
                # Update LCD if face count changed or interval passed
                current_time = time.time()
                if (face_count != self.last_face_count or 
                    current_time - self.last_lcd_update > self.lcd_update_interval):
                    
                    logging.info(f"Updating LCD (face_count={face_count}, last={self.last_face_count})")
                    self.update_smart_lcd(face_count, room_status)
                    self.last_face_count = face_count
                    self.last_lcd_update = current_time
                
                # Status report every 30 seconds
                if time.time() - status_report_timer > 30.0:
                    elapsed = time.time() - start_time
                    avg_detection_rate = detection_count / elapsed
                    state_text = room_status.get('state', 'unknown')
                    
                    logging.info("=" * 60)
                    logging.info(f"STATUS REPORT")
                    logging.info(f"  Faces: {face_count}")
                    logging.info(f"  Room state: {state_text}")
                    logging.info(f"  Detection rate: {avg_detection_rate:.2f}/s")
                    logging.info(f"  LCD working: {self.lcd_working}")
                    logging.info(f"  LCD failures: {self.lcd_retry_count}")
                    logging.info("=" * 60)
                    
                    status_report_timer = time.time()
        
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Release resources"""
        logging.info("Cleaning up...")
        if self.cap:
            self.cap.release()


def main():
    logging.info("=" * 60)
    logging.info("ESP32-CAM Smart LCD Controller - IMPROVED")
    logging.info("Enhanced debugging and reliability")
    logging.info("=" * 60)
    
    # Read IP from stdin (for shell script) or use default
    esp32_ip = '10.253.71.82'
    if not sys.stdin.isatty():  # Being piped
        try:
            piped_ip = sys.stdin.readline().strip()
            
            # Clean up the IP - sometimes extra characters get added
            # Only keep valid IP format: xxx.xxx.xxx.xxx
            import re
            ip_match = re.match(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', piped_ip)
            if ip_match:
                esp32_ip = ip_match.group(1)
                logging.info(f"Read IP from stdin: {piped_ip} -> cleaned to: {esp32_ip}")
            elif piped_ip:
                logging.warning(f"Invalid IP from stdin: {piped_ip}, using default")
        except Exception as e:
            logging.warning(f"Error reading stdin: {e}")
    
    # API URL always uses localhost
    api_base_url = 'http://localhost:5000'
    
    logging.info(f"ESP32 IP: {esp32_ip}")
    logging.info(f"Kiosk API: {api_base_url}")
    logging.info(f"Log file: {os.path.join(os.path.dirname(__file__), 'lcd_controller.log')}")
    
    controller = ESP32CamSmartController(esp32_ip, api_base_url)
    controller.run_smart_face_detection_headless()


if __name__ == "__main__":
    main()

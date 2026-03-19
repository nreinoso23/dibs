"""
Configuration file for NYU Study Room Kiosk
All settings for your kiosk system
"""

# ============================================
# GOOGLE CALENDAR SETTINGS
# ============================================
CALENDAR_CONFIG = {
    # Path to your service account key file
    'credentials_file': '/home/eg1004/nyu_kiosk/key.json',
    
    # Your Google Calendar ID
    'calendar_id': 'c_de32bb151f040557c0aa0f4c04cd10b101fef9b10ce82366b2e248dbc0a81bea@group.calendar.google.com',
    
    # Room name for THIS kiosk
    # Change this for each room: LC416, LC417, LC418, LC419, LC420
    'room_name': 'Study Room LC416',
}

# ============================================
# KIOSK BEHAVIOR SETTINGS
# ============================================
KIOSK_CONFIG = {
    # Check-in grace period (minutes after booking start time)
    'checkin_grace_period': 15,
    
    # Auto-refresh interval for bookings (seconds)
    'refresh_interval': 30,
    
    # Available booking durations for walk-ins (minutes)
    'available_durations': [30, 60, 90, 120],
    
    # Operating hours (24-hour format)
    'open_time': 8,   # 8 AM
    'close_time': 22, # 10 PM
    
    # Screen timeout for PIR sensor (seconds)
    'screen_timeout': 300,  # 5 minutes
}

# ============================================
# GPIO PIN CONFIGURATION
# ============================================
GPIO_CONFIG = {
    # Sensors
    'pir_sensor': 14,  # Motion sensor input
    
    # Status LEDs
    'led_red': 17,     # Red LED (occupied/check-in)
    'led_green': 27,   # Green LED (available)
    
    # Navigation buttons
    'btn_up': 5,       # Up button
    'btn_down': 6,     # Down button
    'btn_select': 13,  # Select/Enter button
    'btn_back': 19,    # Back button
}

# ============================================
# DISPLAY SETTINGS
# ============================================
DISPLAY_CONFIG = {
    'width': 800,
    'height': 480,
    'fullscreen': True,
    'show_cursor': False,
    
    # Font sizes
    'font_size_large': 48,
    'font_size_medium': 32,
    'font_size_small': 24,
    
    # Colors (RGB)
    'color_available': (0.2, 0.8, 0.2, 1),  # Green
    'color_occupied': (0.8, 0.2, 0.2, 1),   # Red
    'color_warning': (0.9, 0.6, 0.1, 1),    # Orange
}

# ============================================
# VALIDATION RULES
# ============================================
VALIDATION = {
    # N-number format
    'n_number_length': 9,
    'n_number_prefix': 'N',
    
    # Email validation (for web bookings only)
    'require_nyu_email': True,
    'email_domain': '@nyu.edu',
}

# ============================================
# ADMIN PASSWORD
# ============================================
# Password for admin functions (force occupy, view all bookings, etc.)
# Change this to something secure!
ADMIN_PASSWORD = "1234"

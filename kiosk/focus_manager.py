"""
Focus Manager for GPIO Button Navigation
Displays white border around currently focused widget
"""
from kivy.graphics import Line, Color, InstructionGroup
from kivy.clock import Clock
from kivy.logger import Logger


class FocusManager:
    """Manages focus highlighting for GPIO navigation"""
    
    # Define menu navigation grid
    MENU_GRID = {
        'quit': {'down': 'schedule', 'right': 'settings', 'up': None, 'left': None},
        'settings': {'down': 'walkin', 'left': 'quit', 'up': None, 'right': None},
        'schedule': {'up': 'quit', 'right': 'walkin', 'down': 'clock', 'left': None},
        'walkin': {'up': 'settings', 'down': 'checkin', 'left': 'schedule', 'right': None},
        'checkin': {'up': 'walkin', 'left': 'clock', 'down': None, 'right': None},
        'clock': {'up': 'schedule', 'right': 'checkin', 'down': None, 'left': None},
    }
    
    # Walk-in slider screen navigation
    WALKIN_GRID = {
        'slider': {'down': 'need_more_time', 'left': None, 'right': None, 'up': None},
        'need_more_time': {'up': 'slider', 'right': 'confirm', 'down': 'back', 'left': None},
        'confirm': {'up': 'slider', 'left': 'need_more_time', 'down': 'back', 'right': None},
        'back': {'up': 'need_more_time', 'left': None, 'right': None, 'down': None},
    }
    
    # Walk-in detailed screen navigation
    WALKIN_DETAILED_GRID = {
        'hour_minus': {'right': 'hour_plus', 'down': 'minute_minus', 'up': None, 'left': None},
        'hour_plus': {'left': 'hour_minus', 'down': 'minute_plus', 'up': None, 'right': None},
        'minute_minus': {'up': 'hour_minus', 'right': 'minute_plus', 'down': 'use_slider', 'left': None},
        'minute_plus': {'up': 'hour_plus', 'left': 'minute_minus', 'down': 'confirm_walkin', 'right': None},
        'use_slider': {'up': 'minute_minus', 'right': 'confirm_walkin', 'down': 'back', 'left': None},
        'confirm_walkin': {'up': 'minute_plus', 'left': 'use_slider', 'down': 'back', 'right': None},
        'back': {'up': 'use_slider', 'left': None, 'right': None, 'down': None},
    }
    
    # Schedule screen navigation
    SCHEDULE_GRID = {
        'back': {'up': None, 'down': None, 'left': None, 'right': None},
    }
    
    # Settings screen navigation
    SETTINGS_GRID = {
        'back': {'up': None, 'down': None, 'left': None, 'right': None},
    }
    
    # Confirm quit screen navigation
    CONFIRM_QUIT_GRID = {
        'yes': {'up': None, 'down': 'no', 'left': None, 'right': None},
        'no': {'up': 'yes', 'down': None, 'left': None, 'right': None},
    }
    
    def __init__(self, app):
        """Initialize focus manager
        
        Args:
            app: Reference to the Kivy app instance
        """
        self.app = app
        self.current_focus = 'checkin'  # Start on check-in button
        self.focus_widgets = {}
        self.focus_instruction = None
        
        # Schedule focus update to run after UI is built
        Clock.schedule_once(lambda dt: self.initialize_focus(), 1.0)
        
        # Bind to screen manager to automatically detect screen changes
        Clock.schedule_once(lambda dt: self.bind_to_screen_manager(), 1.1)
    
    def initialize_focus(self):
        """Initialize focus on the check-in button"""
        print("[FOCUS] Initializing focus system...")
        self.clear_focus()
        self.update_focus_list()
        print(f"[FOCUS] Setting initial focus to 'checkin' button")
        self.set_focus('checkin')  # Start on check-in
        print(f"[FOCUS] Focus initialization complete\n")
    
    def bind_to_screen_manager(self):
        """Bind to ScreenManager to automatically detect screen changes"""
        if hasattr(self.app, 'root') and hasattr(self.app.root, 'bind'):
            self.app.root.bind(current=self._on_screen_manager_change)
            print("[FOCUS] Bound to ScreenManager for automatic screen change detection")
    
    def _on_screen_manager_change(self, instance, value):
        """Called automatically when ScreenManager changes screens"""
        print(f"[FOCUS] Screen changed to: {value}")
        self.on_screen_change()
    
    def on_screen_change(self):
        """Called when screen changes - update focus"""
        Logger.info("FocusManager: Screen changed, updating focus")
        self.clear_focus()
        # Clear keyboard navigation state
        if hasattr(self, 'keyboard_buttons'):
            delattr(self, 'keyboard_buttons')
        if hasattr(self, 'current_focus_index'):
            delattr(self, 'current_focus_index')
        Clock.schedule_once(lambda dt: self.update_focus_list(), 0.2)
    
    def update_focus_list(self):
        """Update dictionary of focusable widgets based on current screen"""
        self.focus_widgets = {}
        current_screen_name = self.app.root.current
        
        try:
            current_screen = self.app.root.get_screen(current_screen_name)
        except:
            Logger.warning(f"FocusManager: Could not get screen {current_screen_name}")
            return
        
        if current_screen_name == 'menu':
            # Find actual widgets by walking the widget tree
            # First pass - log all widgets to understand structure
            def log_all_widgets(widget, depth=0):
                if depth > 15:
                    return
                widget_class = type(widget).__name__
                indent = "  " * depth
                text_info = ""
                if hasattr(widget, 'text'):
                    text_info = f" - text: {str(widget.text)[:30]}"
                Logger.info(f"{indent}{widget_class} at {widget.pos}{text_info}")
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        log_all_widgets(child, depth + 1)
            
            Logger.info("=== Widget Tree ===")
            log_all_widgets(current_screen)
            Logger.info("=== End Widget Tree ===")
            
            def find_menu_widgets(widget, depth=0):
                if depth > 15:
                    return
                
                widget_class = type(widget).__name__
                
                # Look for specific button classes directly
                if widget_class == 'CheckInButton' and 'checkin' not in self.focus_widgets:
                    self.focus_widgets['checkin'] = widget
                    Logger.info(f"FocusManager: Found CheckInButton at {widget.pos}")
                
                elif widget_class == 'WalkInButton' and 'walkin' not in self.focus_widgets:
                    self.focus_widgets['walkin'] = widget
                    Logger.info(f"FocusManager: Found WalkInButton at {widget.pos}")
                
                # BigButtonTile detection - need to distinguish quit, settings, and schedule
                elif widget_class == 'BigButtonTile':
                    # Check text content to identify which button this is
                    # Need to search deeper for complex widgets like SchedulerWidget
                    all_text = []
                    
                    def collect_text(w, max_depth=5, current_depth=0):
                        """Recursively collect text from widget and its children"""
                        if current_depth > max_depth:
                            return
                        if hasattr(w, 'text'):
                            all_text.append(str(w.text))
                        if hasattr(w, 'children'):
                            for child in w.children:
                                collect_text(child, max_depth, current_depth + 1)
                    
                    collect_text(widget)
                    combined = ' '.join(all_text)
                    
                    # Only match if we haven't found this widget yet
                    if 'Quit' in combined and 'quit' not in self.focus_widgets:
                        self.focus_widgets['quit'] = widget
                        Logger.info(f"FocusManager: Found quit BigButtonTile at {widget.pos}")
                    elif 'Settings' in combined and 'settings' not in self.focus_widgets:
                        self.focus_widgets['settings'] = widget
                        Logger.info(f"FocusManager: Found settings BigButtonTile at {widget.pos}")
                    elif 'Study Pod' in combined and 'schedule' not in self.focus_widgets:
                        self.focus_widgets['schedule'] = widget
                        Logger.info(f"FocusManager: Found schedule BigButtonTile at {widget.pos}")
                    elif 'Next Reservations' in combined and 'schedule' not in self.focus_widgets:
                        # Alternative detection for SchedulerWidget
                        self.focus_widgets['schedule'] = widget
                        Logger.info(f"FocusManager: Found schedule BigButtonTile (via 'Next Reservations') at {widget.pos}")
                
                # BigTile detection for clock (non-clickable)
                elif widget_class == 'BigTile':
                    if hasattr(widget, 'children'):
                        all_text = []
                        for child in widget.children:
                            if hasattr(child, 'text'):
                                all_text.append(str(child.text))
                            if hasattr(child, 'children'):
                                for grandchild in child.children:
                                    if hasattr(grandchild, 'text'):
                                        all_text.append(str(grandchild.text))
                        
                        combined = ' '.join(all_text)
                        if any(day in combined for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']) and 'clock' not in self.focus_widgets:
                            self.focus_widgets['clock'] = widget
                            Logger.info(f"FocusManager: Found clock BigTile at {widget.pos}")
                
                # Recurse to find all buttons
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        find_menu_widgets(child, depth + 1)
            
            find_menu_widgets(current_screen)
            Logger.info(f"FocusManager: Menu widgets found: {list(self.focus_widgets.keys())}")
            
            # Set initial focus on menu
            if not self.current_focus or self.current_focus not in self.focus_widgets:
                self.current_focus = 'checkin' if 'checkin' in self.focus_widgets else 'walkin'
            
            if self.current_focus and self.current_focus in self.focus_widgets:
                self.set_focus(self.current_focus)
            else:
                Logger.warning(f"FocusManager: Cannot set focus to {self.current_focus}")
        
        elif current_screen_name == 'walkin':
            # Walk-in slider screen - navigate between buttons
            print("[FOCUS] Setting up walk-in slider screen navigation")
            
            def find_walkin_buttons(widget, depth=0):
                if depth > 15:
                    return
                
                widget_class = type(widget).__name__
                
                # Find slider
                if widget_class == 'Slider' and 'slider' not in self.focus_widgets:
                    self.focus_widgets['slider'] = widget
                    print(f"[FOCUS] Found 'Slider' widget")
                
                # Find buttons by their text
                elif widget_class == 'Button':
                    if hasattr(widget, 'text'):
                        text = str(widget.text)
                        if 'Need More Time' in text and 'need_more_time' not in self.focus_widgets:
                            self.focus_widgets['need_more_time'] = widget
                            print(f"[FOCUS] Found 'Need More Time' button")
                        elif text == 'Confirm' and 'confirm' not in self.focus_widgets:
                            self.focus_widgets['confirm'] = widget
                            print(f"[FOCUS] Found 'Confirm' button")
                        elif 'Back' in text and 'back' not in self.focus_widgets:
                            self.focus_widgets['back'] = widget
                            print(f"[FOCUS] Found 'Back' button")
                
                # Recurse
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        find_walkin_buttons(child, depth + 1)
            
            find_walkin_buttons(current_screen)
            print(f"[FOCUS] Walk-in buttons found: {list(self.focus_widgets.keys())}")
            
            # Set initial focus to slider
            self.current_focus = 'slider'
            if self.current_focus in self.focus_widgets:
                self.set_focus(self.current_focus)
        
        elif current_screen_name == 'walkin_detailed':
            # Walk-in detailed screen - navigate between hour/minute controls
            print("[FOCUS] Setting up walk-in detailed screen navigation")
            
            # Track how many +/- buttons we've found
            minus_buttons = []
            plus_buttons = []
            
            def find_detailed_buttons(widget, depth=0):
                if depth > 15:
                    return
                
                widget_class = type(widget).__name__
                
                # Find buttons by their text
                if widget_class == 'Button':
                    if hasattr(widget, 'text'):
                        text = str(widget.text)
                        
                        # Collect all minus and plus buttons
                        if text == '−':
                            minus_buttons.append(widget)
                        elif text == '+':
                            plus_buttons.append(widget)
                        elif 'Use Slider' in text and 'use_slider' not in self.focus_widgets:
                            self.focus_widgets['use_slider'] = widget
                            print(f"[FOCUS] Found 'Use Slider' button at {widget.pos}")
                        elif 'Confirm Walk-In' in text and 'confirm_walkin' not in self.focus_widgets:
                            self.focus_widgets['confirm_walkin'] = widget
                            print(f"[FOCUS] Found 'Confirm Walk-In' button at {widget.pos}")
                        elif 'Back' in text and 'back' not in self.focus_widgets:
                            self.focus_widgets['back'] = widget
                            print(f"[FOCUS] Found 'Back' button at {widget.pos}")
                
                # Recurse
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        find_detailed_buttons(child, depth + 1)
            
            find_detailed_buttons(current_screen)
            
            # Sort buttons by Y position (top to bottom)
            # Higher Y = higher on screen in Kivy
            minus_buttons.sort(key=lambda w: w.y, reverse=True)
            plus_buttons.sort(key=lambda w: w.y, reverse=True)
            
            # Assign hour buttons (top pair)
            if len(minus_buttons) >= 2:
                self.focus_widgets['hour_minus'] = minus_buttons[0]
                self.focus_widgets['minute_minus'] = minus_buttons[1]
                print(f"[FOCUS] Found 'Hour Minus' button at {minus_buttons[0].pos}")
                print(f"[FOCUS] Found 'Minute Minus' button at {minus_buttons[1].pos}")
            
            if len(plus_buttons) >= 2:
                self.focus_widgets['hour_plus'] = plus_buttons[0]
                self.focus_widgets['minute_plus'] = plus_buttons[1]
                print(f"[FOCUS] Found 'Hour Plus' button at {plus_buttons[0].pos}")
                print(f"[FOCUS] Found 'Minute Plus' button at {plus_buttons[1].pos}")
            
            print(f"[FOCUS] Walk-in detailed buttons found: {list(self.focus_widgets.keys())}")
            
            # Set initial focus to confirm button
            self.current_focus = 'confirm_walkin'
            if self.current_focus in self.focus_widgets:
                self.set_focus(self.current_focus)
        
        elif current_screen_name == 'schedule':
            # Schedule screen - just back button
            print("[FOCUS] Setting up schedule screen navigation")
            
            def find_schedule_buttons(widget, depth=0):
                if depth > 15:
                    return
                
                widget_class = type(widget).__name__
                
                # Find back button
                if widget_class == 'Button':
                    if hasattr(widget, 'text'):
                        text = str(widget.text)
                        if 'Back' in text and 'back' not in self.focus_widgets:
                            self.focus_widgets['back'] = widget
                            print(f"[FOCUS] Found 'Back' button at {widget.pos}")
                
                # Recurse
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        find_schedule_buttons(child, depth + 1)
            
            find_schedule_buttons(current_screen)
            print(f"[FOCUS] Schedule screen buttons found: {list(self.focus_widgets.keys())}")
            
            # Set initial focus to back button
            self.current_focus = 'back'
            if self.current_focus in self.focus_widgets:
                self.set_focus(self.current_focus)
        
        elif current_screen_name == 'settings':
            # Settings screen - just back button
            print("[FOCUS] Setting up settings screen navigation")
            
            def find_settings_buttons(widget, depth=0):
                if depth > 15:
                    return
                
                widget_class = type(widget).__name__
                
                # Find back button
                if widget_class == 'Button':
                    if hasattr(widget, 'text'):
                        text = str(widget.text)
                        if ('Back' in text or 'Menu' in text) and 'back' not in self.focus_widgets:
                            self.focus_widgets['back'] = widget
                            print(f"[FOCUS] Found 'Back to Menu' button at {widget.pos}")
                
                # Recurse
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        find_settings_buttons(child, depth + 1)
            
            find_settings_buttons(current_screen)
            print(f"[FOCUS] Settings screen buttons found: {list(self.focus_widgets.keys())}")
            
            # Set initial focus to back button
            self.current_focus = 'back'
            if self.current_focus in self.focus_widgets:
                self.set_focus(self.current_focus)
        
        elif current_screen_name == 'confirm_quit':
            # Confirm quit screen - Yes and No buttons
            print("[FOCUS] Setting up confirm quit screen navigation")
            
            def find_confirm_buttons(widget, depth=0):
                if depth > 15:
                    return
                
                widget_class = type(widget).__name__
                
                # Find Yes and No buttons
                if widget_class == 'Button':
                    if hasattr(widget, 'text'):
                        text = str(widget.text)
                        if 'Yes' in text and 'yes' not in self.focus_widgets:
                            self.focus_widgets['yes'] = widget
                            print(f"[FOCUS] Found 'Yes' button at {widget.pos}")
                        elif 'No' in text and 'no' not in self.focus_widgets:
                            self.focus_widgets['no'] = widget
                            print(f"[FOCUS] Found 'No' button at {widget.pos}")
                
                # Recurse
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        find_confirm_buttons(child, depth + 1)
            
            find_confirm_buttons(current_screen)
            print(f"[FOCUS] Confirm quit screen buttons found: {list(self.focus_widgets.keys())}")
            
            # Set initial focus to No button (safer default)
            self.current_focus = 'no' if 'no' in self.focus_widgets else 'yes'
            if self.current_focus in self.focus_widgets:
                self.set_focus(self.current_focus)
        
        elif current_screen_name in ['checkin', 'password_quit', 'password_settings']:
            # Keyboard screens - set up grid navigation
            if current_screen_name == 'password_settings':
                print("[FOCUS] Setting up password settings keyboard navigation")
                self.setup_keyboard_navigation(current_screen, 'settings')
            elif current_screen_name == 'password_quit':
                print("[FOCUS] Setting up password quit keyboard navigation")
                self.setup_keyboard_navigation(current_screen, 'quit')
            elif current_screen_name == 'checkin':
                print("[FOCUS] Setting up check-in numeric keypad navigation")
                self.setup_keyboard_navigation(current_screen, 'checkin')
            else:
                self.current_focus = None
                self.clear_focus()
    
    def setup_keyboard_navigation(self, screen, keyboard_type):
        """Setup keyboard navigation for password/input screens
        
        Args:
            screen: The screen widget
            keyboard_type: 'settings', 'quit', or 'checkin'
        """
        print(f"[FOCUS] Setting up {keyboard_type} keyboard")
        
        # Collect all buttons in order
        all_buttons = []
        
        def collect_buttons(widget, depth=0):
            if depth > 15:
                return
            
            widget_class = type(widget).__name__
            
            if widget_class == 'Button':
                all_buttons.append(widget)
            
            # Recurse
            if hasattr(widget, 'children'):
                for child in widget.children:
                    collect_buttons(child, depth + 1)
        
        collect_buttons(screen)
        
        # Sort buttons by position (top-left to bottom-right, row by row)
        # Kivy Y coordinates: higher Y = higher on screen
        # Sort by Y (descending) first, then by X (ascending)
        all_buttons.sort(key=lambda b: (-b.y, b.x))
        
        print(f"[FOCUS] Found {len(all_buttons)} keyboard buttons")
        
        # Detect actual rows based on Y positions
        # Group buttons that have similar Y coordinates (within 5 pixels)
        self.keyboard_buttons = all_buttons
        self.keyboard_rows = []
        
        if all_buttons:
            current_row = [all_buttons[0]]
            current_y = all_buttons[0].y
            
            for button in all_buttons[1:]:
                # If Y position is close to current row (within 50 pixels), add to current row
                # Increased from 5 to 50 to handle buttons in separate containers
                if abs(button.y - current_y) < 50:
                    current_row.append(button)
                else:
                    # Start a new row
                    self.keyboard_rows.append(current_row)
                    current_row = [button]
                    current_y = button.y
            
            # Add the last row
            self.keyboard_rows.append(current_row)
            
            # Sort each row by X position (left to right)
            for row in self.keyboard_rows:
                row.sort(key=lambda b: b.x)
            
            print(f"[FOCUS] Detected {len(self.keyboard_rows)} keyboard rows:")
            for i, row in enumerate(self.keyboard_rows):
                row_texts = [b.text if hasattr(b, 'text') else '?' for b in row]
                print(f"[FOCUS]   Row {i}: {len(row)} buttons - {' '.join(row_texts[:5])}{'...' if len(row) > 5 else ''}")
        
        # Find special buttons (Submit, Back, Clear) by their text
        for i, button in enumerate(all_buttons):
            if hasattr(button, 'text'):
                text = str(button.text)
                if 'Submit' in text:
                    self.focus_widgets['submit'] = button
                    self.keyboard_submit_index = i
                    print(f"[FOCUS] Found 'Submit' button at index {i}")
                elif 'Back' in text and 'back' not in self.focus_widgets:
                    self.focus_widgets['back'] = button
                    self.keyboard_back_index = i
                    print(f"[FOCUS] Found 'Back' button at index {i}")
                elif 'Clear' in text:
                    self.focus_widgets['clear'] = button
                    self.keyboard_clear_index = i
                    print(f"[FOCUS] Found 'Clear' button at index {i}")
        
        # Start focus on first key (top-left)
        if all_buttons:
            self.current_focus_index = 0
            self.draw_focus_rectangle(all_buttons[0])
            print(f"[FOCUS] Starting focus on first key: {all_buttons[0].text if hasattr(all_buttons[0], 'text') else '?'}")
    
    def clear_focus(self):
        """Remove focus rectangle"""
        if self.focus_instruction:
            try:
                self.app.root.canvas.after.remove(self.focus_instruction)
            except:
                pass
            self.focus_instruction = None
    
    def draw_focus_rectangle(self, widget):
        """Draw white border around focused widget"""
        if widget is None:
            Logger.warning("FocusManager: Cannot draw - widget is None")
            return
        
        # Clear old focus first
        self.clear_focus()
        
        # Get widget position and size
        x = widget.x
        y = widget.y
        width = widget.width
        height = widget.height
        
        Logger.info(f"FocusManager: Drawing at ({x}, {y}, {width}, {height})")
        
        # Create instruction group for focus
        self.focus_instruction = InstructionGroup()
        self.focus_instruction.add(Color(1, 1, 1, 1))  # White
        self.focus_instruction.add(Line(rectangle=(x, y, width, height), width=6))
        
        # Add to canvas
        self.app.root.canvas.after.add(self.focus_instruction)
    
    def set_focus(self, widget_id):
        """Set focus to specific widget"""
        if widget_id not in self.focus_widgets:
            print(f"[FOCUS WARNING] Widget '{widget_id}' not found in focus_widgets")
            print(f"[FOCUS] Available widgets: {list(self.focus_widgets.keys())}")
            Logger.warning(f"FocusManager: Widget '{widget_id}' not found in focus_widgets")
            return
        
        self.current_focus = widget_id
        widget_ref = self.focus_widgets[widget_id]
        
        print(f"[FOCUS] Setting focus to: {widget_id}")
        Logger.info(f"FocusManager: Focus on {widget_id}")
        
        # Draw rectangle around widget
        if widget_ref:
            self.draw_focus_rectangle(widget_ref)
            print(f"[FOCUS] White border drawn around {widget_id}")
        else:
            print(f"[FOCUS WARNING] No widget reference for {widget_id}")
            Logger.warning(f"FocusManager: No widget reference for {widget_id}")
    
    def get_current_grid(self):
        """Get the navigation grid for the current screen"""
        current_screen = self.app.root.current
        if current_screen == 'menu':
            return self.MENU_GRID
        elif current_screen == 'walkin':
            return self.WALKIN_GRID
        elif current_screen == 'walkin_detailed':
            return self.WALKIN_DETAILED_GRID
        elif current_screen == 'schedule':
            return self.SCHEDULE_GRID
        elif current_screen == 'settings':
            return self.SETTINGS_GRID
        elif current_screen == 'confirm_quit':
            return self.CONFIRM_QUIT_GRID
        else:
            return None
    
    def move_focus_up(self):
        """Move focus up"""
        # Special case: keyboard navigation
        if hasattr(self, 'keyboard_buttons') and self.keyboard_buttons and hasattr(self, 'current_focus_index'):
            if not hasattr(self, 'keyboard_rows') or not self.keyboard_rows:
                print("[FOCUS] No keyboard rows detected")
                return
            
            current_idx = self.current_focus_index
            current_button = self.keyboard_buttons[current_idx]
            
            # Find which row the current button is in
            current_row_idx = None
            current_pos_in_row = None
            for row_idx, row in enumerate(self.keyboard_rows):
                if current_button in row:
                    current_row_idx = row_idx
                    current_pos_in_row = row.index(current_button)
                    break
            
            if current_row_idx is None:
                print("[FOCUS] Could not find current button in rows")
                return
            
            # Check if there's a row above
            if current_row_idx > 0:
                prev_row = self.keyboard_rows[current_row_idx - 1]
                
                # Special case: If moving from Submit/Back row up to Z,X,C,V,B,N,M,Clear row
                # Route Submit (left) to left-center and Back (right) to right-center
                current_row = self.keyboard_rows[current_row_idx]
                if len(current_row) == 2 and len(prev_row) >= 5:
                    # Check if current buttons are Submit and Back
                    button_texts = [b.text if hasattr(b, 'text') else '' for b in current_row]
                    if 'Submit' in button_texts or 'Back' in button_texts:
                        # Submit (position 0) goes to left-center (position 2 - C)
                        # Back (position 1) goes to right-center (position 6 - M)
                        if current_pos_in_row == 0:
                            target_pos = 2  # C
                            print(f"[FOCUS] Submit routing to left-center")
                        else:
                            target_pos = min(6, len(prev_row) - 1)  # M or last button
                            print(f"[FOCUS] Back routing to right-center")
                        
                        if target_pos < len(prev_row):
                            prev_button = prev_row[target_pos]
                        else:
                            prev_button = prev_row[-1]
                    else:
                        # Normal routing
                        if current_pos_in_row < len(prev_row):
                            prev_button = prev_row[current_pos_in_row]
                        else:
                            prev_button = prev_row[-1]
                else:
                    # Normal routing: Try to maintain horizontal position
                    if current_pos_in_row < len(prev_row):
                        # Same position exists in previous row
                        prev_button = prev_row[current_pos_in_row]
                    else:
                        # Go to last button in previous row
                        prev_button = prev_row[-1]
                
                # Find index of previous button
                prev_idx = self.keyboard_buttons.index(prev_button)
                self.current_focus_index = prev_idx
                self.draw_focus_rectangle(prev_button)
                print(f"[FOCUS] Moved up to: {prev_button.text if hasattr(prev_button, 'text') else '?'}")
            else:
                print(f"[FOCUS] Already at top row")
            return
        
        grid = self.get_current_grid()
        if not grid:
            return
        
        if self.current_focus and self.current_focus in grid:
            next_focus = grid[self.current_focus]['up']
            if next_focus:
                self.set_focus(next_focus)
            else:
                print(f"[FOCUS] Cannot move up from {self.current_focus}")
                Logger.info(f"FocusManager: Cannot move up from {self.current_focus}")
    
    def move_focus_down(self):
        """Move focus down"""
        # Special case: keyboard navigation
        if hasattr(self, 'keyboard_buttons') and self.keyboard_buttons and hasattr(self, 'current_focus_index'):
            if not hasattr(self, 'keyboard_rows') or not self.keyboard_rows:
                print("[FOCUS] No keyboard rows detected")
                return
            
            current_idx = self.current_focus_index
            current_button = self.keyboard_buttons[current_idx]
            
            # Find which row the current button is in
            current_row_idx = None
            current_pos_in_row = None
            for row_idx, row in enumerate(self.keyboard_rows):
                if current_button in row:
                    current_row_idx = row_idx
                    current_pos_in_row = row.index(current_button)
                    break
            
            if current_row_idx is None:
                print("[FOCUS] Could not find current button in rows")
                return
            
            print(f"[FOCUS DEBUG] Current button: {current_button.text if hasattr(current_button, 'text') else '?'}, row: {current_row_idx}, position in row: {current_pos_in_row}")
            
            # Check if there's a row below
            if current_row_idx + 1 < len(self.keyboard_rows):
                next_row = self.keyboard_rows[current_row_idx + 1]
                
                # Special case: If moving from row with Z,X,C,V,B,N,M,Clear to Submit/Back row
                # Route left side (Z,X,C,V,B) to Submit and right side (N,M,Clear) to Back
                current_row = self.keyboard_rows[current_row_idx]
                if len(next_row) == 2 and len(current_row) >= 5:
                    # This is likely the Submit/Back row
                    # Check if buttons are Submit and Back
                    button_texts = [b.text if hasattr(b, 'text') else '' for b in next_row]
                    if 'Submit' in button_texts or 'Back' in button_texts:
                        # Left side of keyboard (positions 0-4) goes to first button (Submit)
                        # Right side (positions 5+) goes to second button (Back)
                        if current_pos_in_row < 5:
                            next_button = next_row[0]  # Submit
                            print(f"[FOCUS] Left side routing to: {next_button.text if hasattr(next_button, 'text') else '?'}")
                        else:
                            next_button = next_row[1]  # Back
                            print(f"[FOCUS] Right side routing to: {next_button.text if hasattr(next_button, 'text') else '?'}")
                    else:
                        # Normal routing
                        if current_pos_in_row < len(next_row):
                            next_button = next_row[current_pos_in_row]
                        else:
                            next_button = next_row[-1]
                else:
                    # Normal routing: Try to maintain horizontal position
                    if current_pos_in_row < len(next_row):
                        # Same position exists in next row
                        next_button = next_row[current_pos_in_row]
                    else:
                        # Go to last button in next row
                        next_button = next_row[-1]
                
                # Find index of next button
                next_idx = self.keyboard_buttons.index(next_button)
                self.current_focus_index = next_idx
                self.draw_focus_rectangle(next_button)
                print(f"[FOCUS] Moved down to: {next_button.text if hasattr(next_button, 'text') else '?'}")
            else:
                print(f"[FOCUS] Already at bottom row, staying on current button")
            return
        
        grid = self.get_current_grid()
        if not grid:
            return
        
        if self.current_focus and self.current_focus in grid:
            next_focus = grid[self.current_focus]['down']
            if next_focus:
                self.set_focus(next_focus)
            else:
                print(f"[FOCUS] Cannot move down from {self.current_focus}")
                Logger.info(f"FocusManager: Cannot move down from {self.current_focus}")
    
    def move_focus_left(self):
        """Move focus left"""
        # Special case: keyboard navigation
        if hasattr(self, 'keyboard_buttons') and self.keyboard_buttons and hasattr(self, 'current_focus_index'):
            if not hasattr(self, 'keyboard_rows') or not self.keyboard_rows:
                print("[FOCUS] No keyboard rows detected")
                return
            
            current_idx = self.current_focus_index
            current_button = self.keyboard_buttons[current_idx]
            
            # Find which row the current button is in
            current_row_idx = None
            current_pos_in_row = None
            for row_idx, row in enumerate(self.keyboard_rows):
                if current_button in row:
                    current_row_idx = row_idx
                    current_pos_in_row = row.index(current_button)
                    break
            
            if current_row_idx is None:
                print("[FOCUS] Could not find current button in rows")
                return
            
            # Check if we can move left in current row
            if current_pos_in_row > 0:
                current_row = self.keyboard_rows[current_row_idx]
                prev_button = current_row[current_pos_in_row - 1]
                prev_idx = self.keyboard_buttons.index(prev_button)
                self.current_focus_index = prev_idx
                self.draw_focus_rectangle(prev_button)
                print(f"[FOCUS] Moved left to: {prev_button.text if hasattr(prev_button, 'text') else '?'}")
            else:
                # At leftmost position - look for buttons to the left at similar Y level
                print(f"[FOCUS] At leftmost position, looking for buttons to the left...")
                
                current_x = current_button.x
                current_y = current_button.y
                current_text = current_button.text if hasattr(current_button, 'text') else ''
                
                # Find all buttons to the left of current button
                buttons_to_left = [b for b in self.keyboard_buttons if b.x < current_x - 10]
                
                if buttons_to_left:
                    # Filter to buttons within generous Y tolerance (250px)
                    y_similar = [b for b in buttons_to_left if abs(b.y - current_y) < 250]
                    
                    if y_similar:
                        # Special logic for check-in screen buttons
                        # If navigating from Submit, prefer button 9 (lower Y in number grid)
                        # If navigating from Back, prefer button 3 (higher Y in number grid)
                        
                        if current_text == 'Submit':
                            # From Submit, prefer the button with LOWER Y (like button 9)
                            closest_button = min(y_similar, key=lambda b: b.y)
                            print(f"[FOCUS] From 'Submit', preferring lower button")
                        elif current_text == 'Back':
                            # From Back, prefer the button with HIGHER Y (like button 3)
                            closest_button = max(y_similar, key=lambda b: b.y)
                            print(f"[FOCUS] From 'Back', preferring upper button")
                        else:
                            # For other buttons, pick the rightmost (closest to us)
                            closest_button = max(y_similar, key=lambda b: b.x)
                        
                        next_idx = self.keyboard_buttons.index(closest_button)
                        self.current_focus_index = next_idx
                        self.draw_focus_rectangle(closest_button)
                        y_diff = abs(closest_button.y - current_y)
                        button_text = closest_button.text if hasattr(closest_button, 'text') else '?'
                        print(f"[FOCUS] Jumped to adjacent section: {button_text} (Y diff: {y_diff:.1f}px)")
                    else:
                        print(f"[FOCUS] No buttons within Y tolerance to the left")
                else:
                    print(f"[FOCUS] No buttons to the left")
            return
        
        grid = self.get_current_grid()
        if not grid:
            return
        
        # Special case: if we're on the slider, adjust its value
        if self.current_focus == 'slider' and self.app.root.current == 'walkin':
            screen = self.app.root.get_screen('walkin')
            slider = screen.ids.duration_slider
            new_value = max(slider.min, slider.value - slider.step)
            slider.value = new_value
            print(f"[FOCUS] Slider decreased to {int(new_value)} minutes")
            return
        
        if self.current_focus and self.current_focus in grid:
            next_focus = grid[self.current_focus]['left']
            if next_focus:
                self.set_focus(next_focus)
            else:
                print(f"[FOCUS] Cannot move left from {self.current_focus}")
                Logger.info(f"FocusManager: Cannot move left from {self.current_focus}")
    
    def move_focus_right(self):
        """Move focus right"""
        # Special case: keyboard navigation
        if hasattr(self, 'keyboard_buttons') and self.keyboard_buttons and hasattr(self, 'current_focus_index'):
            if not hasattr(self, 'keyboard_rows') or not self.keyboard_rows:
                print("[FOCUS] No keyboard rows detected")
                return
            
            current_idx = self.current_focus_index
            current_button = self.keyboard_buttons[current_idx]
            
            # Find which row the current button is in
            current_row_idx = None
            current_pos_in_row = None
            for row_idx, row in enumerate(self.keyboard_rows):
                if current_button in row:
                    current_row_idx = row_idx
                    current_pos_in_row = row.index(current_button)
                    break
            
            if current_row_idx is None:
                print("[FOCUS] Could not find current button in rows")
                return
            
            current_row = self.keyboard_rows[current_row_idx]
            
            # Check if we can move right in current row
            if current_pos_in_row < len(current_row) - 1:
                next_button = current_row[current_pos_in_row + 1]
                next_idx = self.keyboard_buttons.index(next_button)
                self.current_focus_index = next_idx
                self.draw_focus_rectangle(next_button)
                print(f"[FOCUS] Moved right to: {next_button.text if hasattr(next_button, 'text') else '?'}")
            else:
                # At rightmost position - look for buttons to the right at similar Y level
                print(f"[FOCUS] At rightmost position, looking for buttons to the right...")
                
                current_x = current_button.x
                current_y = current_button.y
                current_text = current_button.text if hasattr(current_button, 'text') else ''
                
                # Find all buttons to the right of current button
                buttons_to_right = [b for b in self.keyboard_buttons if b.x > current_x + 10]
                
                if buttons_to_right:
                    # Filter to buttons within generous Y tolerance (250px to catch both Back and Submit)
                    y_similar = [b for b in buttons_to_right if abs(b.y - current_y) < 250]
                    
                    if y_similar:
                        # Special logic for check-in screen buttons
                        # If navigating from button 9 or backspace, prefer Submit (lower Y)
                        # If navigating from button 3, prefer Back (higher Y)
                        
                        if current_text in ['9', '⌫']:
                            # From button 9 or backspace, prefer the button with LOWER Y (Submit, at bottom)
                            closest_button = min(y_similar, key=lambda b: b.y)
                            print(f"[FOCUS] From '{current_text}', preferring lower button")
                        elif current_text == '3':
                            # From button 3, prefer the button with HIGHER Y (Back, at top)
                            closest_button = max(y_similar, key=lambda b: b.y)
                            print(f"[FOCUS] From '3', preferring upper button")
                        else:
                            # For other buttons, pick the one with closest Y coordinate
                            closest_button = min(y_similar, key=lambda b: abs(b.y - current_y))
                        
                        next_idx = self.keyboard_buttons.index(closest_button)
                        self.current_focus_index = next_idx
                        self.draw_focus_rectangle(closest_button)
                        y_diff = abs(closest_button.y - current_y)
                        button_text = closest_button.text if hasattr(closest_button, 'text') else '?'
                        print(f"[FOCUS] Jumped to adjacent section: {button_text} (Y diff: {y_diff:.1f}px)")
                    else:
                        print(f"[FOCUS] No buttons within Y tolerance to the right")
                else:
                    print(f"[FOCUS] No buttons to the right")
            return
        
        grid = self.get_current_grid()
        if not grid:
            return
        
        # Special case: if we're on the slider, adjust its value
        if self.current_focus == 'slider' and self.app.root.current == 'walkin':
            screen = self.app.root.get_screen('walkin')
            slider = screen.ids.duration_slider
            new_value = min(slider.max, slider.value + slider.step)
            slider.value = new_value
            print(f"[FOCUS] Slider increased to {int(new_value)} minutes")
            return
        
        if self.current_focus and self.current_focus in grid:
            next_focus = grid[self.current_focus]['right']
            if next_focus:
                self.set_focus(next_focus)
            else:
                print(f"[FOCUS] Cannot move right from {self.current_focus}")
                Logger.info(f"FocusManager: Cannot move right from {self.current_focus}")
    
    def activate_focused(self):
        """Activate/click the currently focused widget"""
        if not self.current_focus:
            print("[FOCUS] No current focus to activate")
            Logger.info("FocusManager: No current focus to activate")
            return
        
        current_screen = self.app.root.current
        
        print(f"[FOCUS] Activating '{self.current_focus}' on screen '{current_screen}'")
        Logger.info(f"FocusManager: Activating {self.current_focus}")
        
        # MENU SCREEN
        if current_screen == 'menu':
            # Clock widget does nothing
            if self.current_focus == 'clock':
                print("[FOCUS] Clock widget - SELECT does nothing")
                Logger.info("FocusManager: Clock widget - SELECT does nothing")
                return
            
            # Map focus IDs to actions
            if self.current_focus == 'quit':
                self.clear_focus()
                self.app.root.transition.direction = 'left'
                self.app.clear_quit_password()
                self.app.root.current = 'password_quit'
                self.on_screen_change()
            
            elif self.current_focus == 'settings':
                self.clear_focus()
                self.app.root.transition.direction = 'left'
                self.app.clear_settings_password()
                self.app.root.current = 'password_settings'
                self.on_screen_change()
            
            elif self.current_focus == 'schedule':
                self.clear_focus()
                self.app.root.transition.direction = 'left'
                self.app.root.current = 'schedule'
                self.on_screen_change()
            
            elif self.current_focus == 'walkin':
                if self.app.walk_in_enabled:
                    self.clear_focus()
                    self.app.goto_walkin_screen()
                    self.on_screen_change()
                else:
                    print("[FOCUS] Walk-in not enabled")
                    Logger.info("FocusManager: Walk-in not enabled")
            
            elif self.current_focus == 'checkin':
                if self.app.check_in_enabled:
                    self.clear_focus()
                    self.app.root.transition.direction = 'left'
                    self.app.root.current = 'checkin'
                    self.on_screen_change()
                else:
                    print("[FOCUS] Check-in not enabled")
                    Logger.info("FocusManager: Check-in not enabled")
        
        # WALK-IN SLIDER SCREEN
        elif current_screen == 'walkin':
            if self.current_focus == 'slider':
                print("[FOCUS] Slider is focused - use LEFT/RIGHT to adjust")
                # Slider adjustment happens in move_focus_left/right when on slider
            
            elif self.current_focus == 'need_more_time':
                print("[FOCUS] Activating 'Need More Time' button")
                self.clear_focus()
                self.app.root.transition.direction = 'left'
                self.app.root.current = 'walkin_detailed'
                self.on_screen_change()
            
            elif self.current_focus == 'confirm':
                print("[FOCUS] Activating 'Confirm' button")
                self.clear_focus()
                # Get slider value from the screen
                screen = self.app.root.get_screen('walkin')
                slider = screen.ids.duration_slider
                duration = int(slider.value)
                self.app.confirm_walkin(duration)
                # confirm_walkin goes back to menu, so update focus
                self.on_screen_change()
            
            elif self.current_focus == 'back':
                print("[FOCUS] Activating 'Back' button")
                self.clear_focus()
                self.app.goto_menu()
                self.on_screen_change()
        
        # WALK-IN DETAILED SCREEN
        elif current_screen == 'walkin_detailed':
            if self.current_focus == 'hour_minus':
                print("[FOCUS] Decreasing hours")
                self.app.decrease_walk_in_hours()
            
            elif self.current_focus == 'hour_plus':
                print("[FOCUS] Increasing hours")
                self.app.increase_walk_in_hours()
            
            elif self.current_focus == 'minute_minus':
                print("[FOCUS] Decreasing minutes")
                self.app.decrease_walk_in_minutes()
            
            elif self.current_focus == 'minute_plus':
                print("[FOCUS] Increasing minutes")
                self.app.increase_walk_in_minutes()
            
            elif self.current_focus == 'use_slider':
                print("[FOCUS] Switching to slider view")
                self.clear_focus()
                self.app.root.transition.direction = 'right'
                self.app.root.current = 'walkin'
                self.on_screen_change()
            
            elif self.current_focus == 'confirm_walkin':
                print("[FOCUS] Confirming walk-in")
                self.clear_focus()
                self.app.confirm_walkin_detailed()
                # confirm_walkin_detailed goes back to menu, so update focus
                self.on_screen_change()
            
            elif self.current_focus == 'back':
                print("[FOCUS] Going back to menu")
                self.clear_focus()
                self.app.goto_menu()
                self.on_screen_change()
        
        # SCHEDULE SCREEN
        elif current_screen == 'schedule':
            if self.current_focus == 'back':
                print("[FOCUS] Going back to menu from schedule")
                self.clear_focus()
                self.app.goto_menu()
                self.on_screen_change()
        
        # SETTINGS SCREEN
        elif current_screen == 'settings':
            if self.current_focus == 'back':
                print("[FOCUS] Going back to menu from settings")
                self.clear_focus()
                self.app.goto_menu()
                self.on_screen_change()
        
        # CONFIRM QUIT SCREEN
        elif current_screen == 'confirm_quit':
            if self.current_focus == 'yes':
                print("[FOCUS] Activating 'Yes' - Quitting application")
                self.clear_focus()
                self.app.stop()
            elif self.current_focus == 'no':
                print("[FOCUS] Activating 'No' - Going back to menu")
                self.clear_focus()
                self.app.goto_menu()
                self.on_screen_change()
        
        # PASSWORD/KEYBOARD SCREENS
        elif current_screen == 'password_settings' and hasattr(self, 'keyboard_buttons'):
            # Activate the currently focused keyboard button
            if hasattr(self, 'current_focus_index') and self.current_focus_index < len(self.keyboard_buttons):
                button = self.keyboard_buttons[self.current_focus_index]
                print(f"[FOCUS] Activating keyboard button: {button.text if hasattr(button, 'text') else '?'}")
                # Trigger the button's on_release event
                button.dispatch('on_release')
        
        elif current_screen == 'password_quit' and hasattr(self, 'keyboard_buttons'):
            # Activate the currently focused keyboard button
            if hasattr(self, 'current_focus_index') and self.current_focus_index < len(self.keyboard_buttons):
                button = self.keyboard_buttons[self.current_focus_index]
                print(f"[FOCUS] Activating keyboard button: {button.text if hasattr(button, 'text') else '?'}")
                # Trigger the button's on_release event
                button.dispatch('on_release')
        
        elif current_screen == 'checkin' and hasattr(self, 'keyboard_buttons'):
            # Activate the currently focused numeric keypad button
            if hasattr(self, 'current_focus_index') and self.current_focus_index < len(self.keyboard_buttons):
                button = self.keyboard_buttons[self.current_focus_index]
                print(f"[FOCUS] Activating keypad button: {button.text if hasattr(button, 'text') else '?'}")
                # Trigger the button's on_release event
                button.dispatch('on_release')

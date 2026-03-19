import platform
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.properties import NumericProperty, ObjectProperty
from datetime import datetime
from kivy.graphics import RoundedRectangle, Color

class ClockWidget(BoxLayout):

    time_font_size = NumericProperty(120)  # Default font size for time
    date_font_size = NumericProperty(80)  # Default font size for date
    time_label = ObjectProperty(None)     # Reference to the time label
    date_label = ObjectProperty(None)     # Reference to the date label

    def __init__(self, **kwargs):
        super(ClockWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'  # Arrange the clock vertically
        self.padding = 20
        self.spacing = 10

        # Add a label to display the date
        self.date_label = Label(font_size=self.date_font_size, halign="left", valign="bottom")
        self.date_label.bind(size=self.date_label.setter('text_size'))  # Ensure proper alignment
        self.add_widget(self.date_label)

        # Add a label to display the time
        self.time_label = Label(font_size=self.time_font_size, halign="left", valign="top")
        self.time_label.bind(size=self.time_label.setter('text_size'))  # Ensure proper alignment
        self.add_widget(self.time_label)

        # Schedule the time update to happen every second
        Clock.schedule_interval(self.update_time, 1)  # Update every second
        self.update_time()  # Initial update

        # Bind the font size update to the size of the widget
        self.bind(size=self.update_font_size)

    def _update_rect(self, *args):
        """Update the size and position of the rounded rectangle."""
        self.rect.size = self.size
        self.rect.pos = self.pos

    def update_time(self, *args):
        now = datetime.now()

        # Windows uses %#d / %#I, Unix/mac use %-d / %-I for no-leading-zero
        if platform.system() == "Windows":
            time_fmt = "%#I:%M %p"  # e.g., 1:15 PM
            date_fmt = "%A, %B %#d, %Y"  # e.g., Monday, October 15, 2025
        else:
            time_fmt = "%-I:%M %p"
            date_fmt = "%A, %B %-d, %Y"

        self.time_label.text = now.strftime(time_fmt)
        self.date_label.text = now.strftime(date_fmt)

    def update_font_size(self, *args):
        """Update the font sizes for the time and date labels."""
        self.time_label.font_size = self.width * 0.2
        self.date_label.font_size = self.width * 0.1
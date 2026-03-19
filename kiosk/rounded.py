from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import RoundedRectangle, Color
from kivy.properties import ListProperty, NumericProperty


class RoundedRectangleContainer(BoxLayout):
    background_color = ListProperty([0.1, 0.5, 0.8, 1])  # Default background color (blue)
    corner_radius = NumericProperty(20)  # Default corner radius

    def __init__(self, **kwargs):
        super(RoundedRectangleContainer, self).__init__(**kwargs)
        self.padding = 10  # Internal padding
        self.spacing = 10  # Internal spacing between child widgets

        # Add a rounded rectangle background
        with self.canvas.before:
            self.color = Color(*self.background_color)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[self.corner_radius])

        # Bind updates to size, position, and background color
        self.bind(size=self._update_rect, pos=self._update_rect, background_color=self._update_color)

    def _update_rect(self, *args):
        """Update the size and position of the rounded rectangle."""
        self.rect.size = self.size
        self.rect.pos = self.pos
        self.rect.radius = [self.corner_radius]

    def _update_color(self, *args):
        """Update the color of the rounded rectangle."""
        self.color.rgba = self.background_color
from datetime import datetime, timedelta, time
import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.graphics import RoundedRectangle, Color
from kivy.app import App


class SchedulerWidget(BoxLayout):
    """Widget showing room name and next few reservations"""
    room_name = StringProperty("Study Pod A-103")
    next_reservations_text = StringProperty("")

    def __init__(self, **kwargs):
        super(SchedulerWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 12

        self.room_label = Label(
            text=self.room_name,
            font_size='36sp',
            bold=True,
            size_hint_y=None,
            height=50,
            halign='left',
            valign='middle'
        )
        self.room_label.bind(size=self.room_label.setter('text_size'))
        self.add_widget(self.room_label)

        header = Label(
            text="Next Reservations:",
            font_size='24sp',
            bold=True,
            size_hint_y=None,
            height=40,
            halign='left',
            valign='middle',
            color=(0.9, 0.9, 0.9, 1)
        )
        header.bind(size=header.setter('text_size'))
        self.add_widget(header)

        scroll = ScrollView(bar_width=8)
        self.reservations_label = Label(
            text=self.next_reservations_text,
            font_size='22sp',
            size_hint_y=None,
            halign='left',
            valign='top',
            markup=True
        )
        self.reservations_label.bind(
            texture_size=self.reservations_label.setter('size'),
            size=self.reservations_label.setter('text_size')
        )
        scroll.add_widget(self.reservations_label)
        self.add_widget(scroll)

        self.refresh_schedule()
        Clock.schedule_interval(lambda dt: self.refresh_schedule(), 10)
        self.bind(room_name=self.on_room_name)

    def on_room_name(self, instance, value):
        self.room_label.text = value

    def refresh_schedule(self):
        """Get reservations from reservation manager"""
        app = App.get_running_app()
        if hasattr(app, 'reservation_manager'):
            now = datetime.now()
            
            current = app.reservation_manager.get_current_reservation()
            upcoming = app.reservation_manager.get_upcoming_reservations(limit=3)

            lines = []
            
            if current:
                time_str = app.reservation_manager.format_time(current.start_time)
                end_str = app.reservation_manager.format_time(current.end_time)
                mins_left = int((current.end_time - now).total_seconds() / 60)
                lines.append(f"[color=00ff00][b]ACTIVE NOW[/b][/color]")
                lines.append(f"[b]{time_str} - {end_str}[/b]")
                lines.append(f"{current.name} • {mins_left} min left")
                lines.append("")
            
            for res in upcoming:
                time_str = app.reservation_manager.format_time(res.start_time)
                end_str = app.reservation_manager.format_time(res.end_time)
                
                mins_until = int((res.start_time - now).total_seconds() / 60)
                
                if res.checked_in:
                    status = " (Checked in)"
                elif res.can_check_in(now):
                    status = " [color=00ff00](Can check in)[/color]"
                else:
                    # Show when check-in opens (10 min before)
                    check_in_opens = res.start_time - timedelta(minutes=10)
                    mins_to_checkin = int((check_in_opens - now).total_seconds() / 60)
                    if mins_to_checkin > 0:
                        status = f" (Check-in in {mins_to_checkin} min)"
                    else:
                        status = f" (In {mins_until} min)" if mins_until > 0 else ""
                
                lines.append(f"[b]{time_str} - {end_str}[/b]")
                lines.append(f"{res.name}{status}")
                lines.append("")

            self.next_reservations_text = "\n".join(lines) if lines else "No upcoming reservations"
            self.reservations_label.text = self.next_reservations_text


class CheckInButton(ButtonBehavior, BoxLayout):
    """Check-in button that changes color based on eligibility"""
    eligible = BooleanProperty(False)
    status_text = StringProperty("No appointment now")

    def __init__(self, **kwargs):
        super(CheckInButton, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 5

        self.main_label = Label(
            text="Check In",
            font_size='36sp',
            bold=True,
            halign='center',
            valign='bottom',
            size_hint_y=0.6
        )
        self.main_label.bind(size=self.main_label.setter('text_size'))

        self.status_label = Label(
            text=self.status_text,
            font_size='18sp',
            color=(0.7, 0.7, 0.7, 1),
            halign='center',
            valign='top',
            size_hint_y=0.4
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))

        self.add_widget(self.main_label)
        self.add_widget(self.status_label)

        self.update_eligibility()
        Clock.schedule_interval(lambda dt: self.update_eligibility(), 10)

        self.bind(eligible=self.on_eligible_change)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.on_eligible_change(None, self.eligible)

    def update_eligibility(self):
        """Check if within 10-min window before reservation"""
        app = App.get_running_app()
        if not hasattr(app, 'reservation_manager'):
            self.eligible = False
            self.status_text = "No appointment now"
            self.status_label.text = self.status_text
            self.main_label.text = "Unavailable"
            return
        
        now = datetime.now()
        check_in_res = app.reservation_manager.get_check_in_reservation()
        
        if check_in_res:
            self.eligible = True
            # Show check-in window (10 min before start)
            start_str = app.reservation_manager.format_time(check_in_res.start_time)
            
            self.status_text = f"{check_in_res.name}\nBooked: {start_str}\nCheck-in now open!"
            self.main_label.text = "Check In"
        else:
            next_res = app.reservation_manager.get_next_reservation()
            
            if next_res:
                self.eligible = False
                # Show when check-in opens (10 min before)
                check_in_opens = next_res.start_time - timedelta(minutes=10)
                mins_until_checkin = int((check_in_opens - now).total_seconds() / 60)
                start_str = app.reservation_manager.format_time(next_res.start_time)
                
                if mins_until_checkin > 0:
                    self.status_text = f"Next: {next_res.name}\nBooked: {start_str}\nCheck-in in {mins_until_checkin} min"
                else:
                    self.status_text = f"Next: {next_res.name}\nBooked: {start_str}"
                
                self.main_label.text = "Unavailable"
            else:
                self.eligible = False
                self.status_text = "No appointment now"
                self.main_label.text = "Unavailable"
        
        self.status_label.text = self.status_text

    def on_eligible_change(self, instance, value):
        """Update button appearance"""
        self.canvas.before.clear()
        with self.canvas.before:
            if value:
                Color(0, 0.6, 0, 1)  # Green
            else:
                Color(0.4, 0.4, 0.4, 1)  # Grey
            self.bg_rect = RoundedRectangle(
                size=self.size,
                pos=self.pos,
                radius=[16]
            )

    def update_bg(self, *args):
        """Update background rectangle"""
        if hasattr(self, 'bg_rect'):
            self.bg_rect.size = self.size
            self.bg_rect.pos = self.pos

    def on_release(self):
        """Handle button click"""
        if self.eligible:
            from kivy.app import App
            App.get_running_app().root.current = 'checkin'


class WalkInWidget(BoxLayout):
    """Walk-in booking widget"""
    walkin_max_minutes = NumericProperty(120)
    walkin_limit_reason = StringProperty("Limited by next reservation")

    def __init__(self, **kwargs):
        super(WalkInWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 16
        self.spacing = 10

        title = Label(
            text="Walk-In Booking",
            font_size='32sp',
            bold=True,
            size_hint_y=None,
            height=60
        )
        self.add_widget(title)

        instructions = Label(
            text="Select Duration",
            font_size='24sp',
            size_hint_y=None,
            height=40
        )
        self.add_widget(instructions)

        self.duration_label = Label(
            text=f"60 minutes (max {int(self.walkin_max_minutes)} min)",
            font_size='28sp',
            bold=True,
            size_hint_y=None,
            height=50
        )
        self.add_widget(self.duration_label)

        self.reason_label = Label(
            text=self.walkin_limit_reason,
            font_size='18sp',
            size_hint_y=None,
            height=40,
            color=(0.7, 0.7, 0.7, 1)
        )
        self.add_widget(self.reason_label)

        self.update_walkin_cap()
        Clock.schedule_interval(lambda dt: self.update_walkin_cap(), 10)

    def update_walkin_cap(self):
        """Calculate max walk-in time"""
        app = App.get_running_app()
        if not hasattr(app, 'reservation_manager'):
            self.walkin_max_minutes = 120
            self.walkin_limit_reason = "Limited by next reservation"
            self.reason_label.text = self.walkin_limit_reason
            return
        
        self.walkin_max_minutes = app.reservation_manager.get_max_walk_in_minutes()
        
        now = datetime.now()
        close_dt = datetime.combine(now.date(), time(hour=1))
        if now.time() >= time(hour=1):
            close_dt += timedelta(days=1)
        mins_to_close = max(0, int((close_dt - now).total_seconds() // 60))
        
        next_res = app.reservation_manager.get_next_reservation()
        if next_res:
            # Check-in opens 10 minutes before
            check_in_opens = next_res.start_time - timedelta(minutes=10)
            mins_to_checkin = max(0, int((check_in_opens - now).total_seconds() // 60))
            
            if mins_to_close < mins_to_checkin:
                self.walkin_limit_reason = "Limited by library closing at 1:00 AM"
            else:
                self.walkin_limit_reason = "Limited by next check-in window"
        else:
            self.walkin_limit_reason = "Until library closing"
        
        self.reason_label.text = self.walkin_limit_reason

    def update_duration_display(self, value):
        """Update the duration label"""
        self.duration_label.text = f"{int(value)} minutes (max {int(self.walkin_max_minutes)} min)"


class FullDayScheduleWidget(BoxLayout):
    """Widget showing all bookings for the day - current and future"""
    room_name = StringProperty("NYU Dibner Study Pod LC 416")
    day_reservations_text = StringProperty("")

    def __init__(self, **kwargs):
        super(FullDayScheduleWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 12

        self.title_label = Label(
            text=f"{self.room_name}",
            font_size='28sp',
            bold=True,
            size_hint_y=None,
            height=50,
            halign='center',
            valign='middle'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        self.add_widget(self.title_label)

        self.subtitle_label = Label(
            text="Today's Schedule (7am - 1am)",
            font_size='22sp',
            size_hint_y=None,
            height=35,
            halign='center',
            valign='middle',
            color=(0.7, 0.7, 0.7, 1)
        )
        self.subtitle_label.bind(size=self.subtitle_label.setter('text_size'))
        self.add_widget(self.subtitle_label)

        scroll = ScrollView(bar_width=8)
        self.schedule_label = Label(
            text=self.day_reservations_text,
            font_size='22sp',
            size_hint_y=None,
            halign='left',
            valign='top',
            markup=True
        )
        self.schedule_label.bind(
            texture_size=self.schedule_label.setter('size'),
            size=self.schedule_label.setter('text_size')
        )
        scroll.add_widget(self.schedule_label)
        self.add_widget(scroll)

        self.refresh_schedule()
        Clock.schedule_interval(lambda dt: self.refresh_schedule(), 10)
        self.bind(room_name=self.on_room_name)

    def on_room_name(self, instance, value):
        self.title_label.text = f"{value}"

    def refresh_schedule(self):
        """Get all reservations for library day (7am - 1am)"""
        app = App.get_running_app()
        if hasattr(app, 'reservation_manager'):
            now = datetime.now()
            all_reservations = app.reservation_manager.get_library_day_reservations()
            current_res = app.reservation_manager.get_current_reservation()

            lines = []
            
            # Show current active reservation first
            if current_res:
                time_str = app.reservation_manager.format_time(current_res.start_time)
                end_str = app.reservation_manager.format_time(current_res.end_time)
                mins_left = int((current_res.end_time - now).total_seconds() / 60)
                
                lines.append("[color=00ff00]━━━━━ ACTIVE NOW ━━━━━[/color]")
                lines.append(f"[b]{time_str} - {end_str}[/b]")
                lines.append(f"  {current_res.name}")
                lines.append(f"  [color=00ff00]{mins_left} minutes remaining[/color]")
                lines.append("")
            
            # Separate future reservations
            future_reservations = []
            past_reservations = []
            
            for res in all_reservations:
                # Skip the current active reservation (already shown above)
                if current_res and res.event_id == current_res.event_id:
                    continue
                
                if res.end_time < now:
                    past_reservations.append(res)
                elif res.start_time > now:
                    future_reservations.append(res)
                elif not res.checked_in:
                    # Started but not checked in (might be no-show)
                    future_reservations.append(res)
            
            # Show future reservations
            if future_reservations:
                lines.append("[color=ffff00]━━━━━ UPCOMING ━━━━━[/color]")
                lines.append("")
                
                for res in future_reservations:
                    time_str = app.reservation_manager.format_time(res.start_time)
                    end_str = app.reservation_manager.format_time(res.end_time)
                    mins_until = int((res.start_time - now).total_seconds() / 60)
                    
                    # Determine status
                    if res.can_check_in(now):
                        status = "[color=00ff00](Check-in open)[/color]"
                    elif mins_until > 0:
                        if mins_until < 60:
                            status = f"[color=aaaaaa](in {mins_until} min)[/color]"
                        else:
                            hours = mins_until // 60
                            mins = mins_until % 60
                            if mins > 0:
                                status = f"[color=aaaaaa](in {hours}h {mins}m)[/color]"
                            else:
                                status = f"[color=aaaaaa](in {hours}h)[/color]"
                    else:
                        status = "[color=ff6666](Awaiting check-in)[/color]"
                    
                    lines.append(f"[b]{time_str} - {end_str}[/b] {status}")
                    lines.append(f"  {res.name} • {res.duration_minutes} min")
                    lines.append("")
            
            # Show past reservations (completed)
            if past_reservations:
                lines.append("[color=666666]━━━━━ COMPLETED ━━━━━[/color]")
                lines.append("")
                
                for res in past_reservations:
                    time_str = app.reservation_manager.format_time(res.start_time)
                    end_str = app.reservation_manager.format_time(res.end_time)
                    
                    if res.checked_in:
                        status = "[color=666666](Completed)[/color]"
                    else:
                        status = "[color=664444](No-show)[/color]"
                    
                    lines.append(f"[color=888888]{time_str} - {end_str}[/color] {status}")
                    lines.append(f"  [color=888888]{res.name}[/color]")
                    lines.append("")

            if not lines:
                lines.append("")
                lines.append("[color=aaaaaa]No reservations scheduled for today[/color]")
                lines.append("")
                lines.append("The room is available for walk-in bookings.")
            
            self.day_reservations_text = "\n".join(lines)
            self.schedule_label.text = self.day_reservations_text

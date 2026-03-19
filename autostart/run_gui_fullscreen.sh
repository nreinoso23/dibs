#!/bin/bash
# Wrapper script to launch the main Kivy GUI in fullscreen mode

# Set Kivy environment variables for fullscreen
export KIVY_WINDOW=sdl2
export KIVY_GL_BACKEND=gl

# Set window to fullscreen
export SDL_VIDEO_WINDOW_POS="0,0"

# Disable mouse cursor (optional - uncomment if needed)
# export KIVY_NO_CURSOR=1

cd ~/projects/SLDP

# Launch with fullscreen config via environment
python3 -c "
from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'window_state', 'maximized')
Config.write()
" 2>/dev/null

# Run the app
python3 app.py

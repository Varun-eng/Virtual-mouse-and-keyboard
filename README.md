# Virtual-mouse-and-keyboard
This code implements a Virtual Mouse and Floating Keyboard System using hand gesture recognition through a webcam. It uses computer vision and hand tracking to control mouse movements and keyboard inputs without physical devices.
Main Features:
Hand Tracking: Uses MediaPipe to detect and track hand landmarks in real time.
Virtual Mouse Mode:
Move cursor using index finger movement
Left click using thumb + index finger pinch
Right click using thumb + middle finger pinch
Virtual Keyboard Mode:
Move keyboard using pinch gesture
Highlight keys using index finger
Type characters using a two-finger gesture
Mode Switching:
Open palm (4+ fingers) → Mouse mode
Closed fist (0 fingers) → Keyboard mode
Smooth Operation: Uses gesture cooldowns and smoothing techniques for stable control.

This system provides a touchless human-computer interaction method, useful for accessibility, smart interfaces, and gesture-based control applications.

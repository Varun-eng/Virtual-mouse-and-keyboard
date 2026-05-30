# -*- coding: utf-8 -*-
import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time
import sys

# Force UTF-8 output on Windows so emoji in print() don't crash
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Suppress MediaPipe warnings
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("🎮 VIRTUAL MOUSE - PINCH GESTURES + SCROLL (FIXED)")
print("=" * 60)

# Initialize MediaPipe
try:
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    mp_draw = mp.solutions.drawing_utils
    print("✅ MediaPipe initialized")
except Exception as e:
    print(f"❌ MediaPipe error: {e}")
    sys.exit(1)

# Get screen size
try:
    screen_w, screen_h = pyautogui.size()
    print(f"✅ Screen: {screen_w} x {screen_h}")
except Exception as e:
    print(f"❌ Screen detection error: {e}")
    screen_w, screen_h = 1920, 1080

# Get current cursor position (FIX: Start from current position)
current_mouse_x, current_mouse_y = pyautogui.position()
print(f"✅ Current cursor position: ({current_mouse_x}, {current_mouse_y})")

# Camera setup
print("\n🔍 Looking for camera...")
cap = None
camera_index = -1

for i in range(3):
    print(f"  Trying camera {i}...")
    test_cap = cv2.VideoCapture(i)
    if test_cap.isOpened():
        ret, test_frame = test_cap.read()
        if ret and test_frame is not None:
            camera_index = i
            cap = test_cap
            print(f"  ✅ Camera {i} working!")
            break
    test_cap.release()

if cap is None:
    print("\n❌ No camera found!")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Variables - FIX: Initialize with current cursor position
prev_x, prev_y = current_mouse_x, current_mouse_y  # Start from current position
smoothing = 2
click_cooldown = 10
scroll_mode = False
last_scroll_y = 0
scroll_sensitivity = 50
last_pinch_time = 0
pinch_active = False
pinch_start_time = 0
pinch_progress = 0
first_hand_detected = False  # Track if hand has been detected

# Colors (BGR)
COLORS = {
    'WHITE': (255, 255, 255),
    'GREEN': (0, 255, 0),
    'RED': (0, 0, 255),
    'BLUE': (255, 0, 0),
    'CYAN': (255, 255, 0),
    'YELLOW': (0, 255, 255),
    'ORANGE': (0, 165, 255),
    'PURPLE': (128, 0, 128),
    'PINK': (255, 105, 180)
}

def calculate_distance(p1, p2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def count_extended_fingers(hand_landmarks):
    """Count extended fingers (excluding thumb)"""
    fingers = 0
    
    # Index, Middle, Ring, Pinky
    if hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y:
        fingers += 1
    if hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y:
        fingers += 1
    if hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y:
        fingers += 1
    if hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y:
        fingers += 1
    
    return fingers

def draw_pinch_indicator(frame, center, radius, color, progress):
    """Draw animated pinch indicator"""
    if center[0] < 0 or center[1] < 0:
        return
    
    # Outer ring
    for i in range(3):
        alpha = max(0.1, 1 - (i * 0.3))
        ring_color = tuple(int(c * alpha) for c in color)
        cv2.circle(frame, center, radius + i*3, ring_color, 2)
    
    # Progress circle
    if progress > 0:
        end_angle = int(360 * min(1.0, progress))
        cv2.ellipse(frame, center, (radius, radius), 0, 0, end_angle, color, 3)
    
    # Center dot
    cv2.circle(frame, center, 5, COLORS['WHITE'], -1)

def draw_hand(frame, hand_landmarks, is_pinching=False, pinch_type=None):
    """Draw beautiful hand landmarks with pinch effect"""
    h, w = frame.shape[:2]
    
    # Draw connections
    for connection in mp_hands.HAND_CONNECTIONS:
        start = hand_landmarks.landmark[connection[0]]
        end = hand_landmarks.landmark[connection[1]]
        start_point = (int(start.x * w), int(start.y * h))
        end_point = (int(end.x * w), int(end.y * h))
        
        # Highlight pinch connection
        if is_pinching and pinch_type:
            if (pinch_type == "left" and ((connection[0] == 4 and connection[1] == 8) or 
               (connection[0] == 8 and connection[1] == 4))):
                cv2.line(frame, start_point, end_point, COLORS['GREEN'], 4)
            elif (pinch_type == "right" and ((connection[0] == 4 and connection[1] == 12) or 
                 (connection[0] == 12 and connection[1] == 4))):
                cv2.line(frame, start_point, end_point, COLORS['RED'], 4)
            else:
                cv2.line(frame, start_point, end_point, COLORS['CYAN'], 2)
        else:
            cv2.line(frame, start_point, end_point, COLORS['CYAN'], 2)
    
    # Draw landmarks
    for id, lm in enumerate(hand_landmarks.landmark):
        cx, cy = int(lm.x * w), int(lm.y * h)
        
        # Highlight pinched fingertips
        if is_pinching and pinch_type == "left" and id == 8:
            cv2.circle(frame, (cx, cy), 12, COLORS['GREEN'], -1)
            cv2.circle(frame, (cx, cy), 8, COLORS['WHITE'], -1)
        elif is_pinching and pinch_type == "right" and id == 12:
            cv2.circle(frame, (cx, cy), 12, COLORS['RED'], -1)
            cv2.circle(frame, (cx, cy), 8, COLORS['WHITE'], -1)
        elif id in [4, 8, 12, 16, 20]:
            cv2.circle(frame, (cx, cy), 8, COLORS['WHITE'], -1)
            cv2.circle(frame, (cx, cy), 5, COLORS['YELLOW'], -1)
        else:
            cv2.circle(frame, (cx, cy), 4, COLORS['WHITE'], -1)
            cv2.circle(frame, (cx, cy), 2, COLORS['BLUE'], -1)

def draw_instructions(frame, scroll_mode_active, fps):
    h, w = frame.shape[:2]
    
    # Semi-transparent dark panel (left side)
    panel_w, panel_h = 210, 150
    overlay = frame.copy()
    cv2.rectangle(overlay, (8, 8), (8 + panel_w, 8 + panel_h), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)
    
    # FPS  (top-left of panel)
    fps_color = COLORS['GREEN'] if fps >= 20 else COLORS['YELLOW'] if fps >= 10 else COLORS['RED']
    cv2.putText(frame, f"FPS: {fps}", (16, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.55, fps_color, 1)
    
    # Mode badge
    if scroll_mode_active:
        mode_text, mode_color = "SCROLL MODE", COLORS['ORANGE']
    else:
        mode_text, mode_color = "MOUSE MODE", COLORS['GREEN']
    cv2.putText(frame, mode_text, (16, 55),
               cv2.FONT_HERSHEY_SIMPLEX, 0.55, mode_color, 2)
    
    # Divider
    cv2.line(frame, (16, 63), (8 + panel_w - 8, 63), (80, 80, 80), 1)
    
    # Controls (compact)
    controls = [
        ("Pinch Idx", "Left click"),
        ("Pinch Mid", "Right click"),
        ("4 fingers", "Scroll mode"),
        ("Q / ESC",   "Quit"),
    ]
    for i, (key, val) in enumerate(controls):
        y = 82 + i * 18
        cv2.putText(frame, f"{key}:", (16, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.36, COLORS['CYAN'], 1)
        cv2.putText(frame, val, (100, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.36, COLORS['WHITE'], 1)
    
    return frame

print("\n" + "=" * 60)
print("🎮 CONTROLS:")
print("  PINCH GESTURES (Mouse Mode):")
print("  • Thumb + Index finger pinch → LEFT CLICK")
print("  • Thumb + Middle finger pinch → RIGHT CLICK")
print("  • Quick double pinch (within 0.3s) → DOUBLE CLICK")
print("\n  SCROLL MODE:")
print("  • 4 fingers extended → Enter scroll mode")
print("  • Move hand UP/DOWN → Scroll")
print("  • Lower to 3 fingers → Exit scroll mode")
print("\n  GENERAL:")
print("  • Index finger → Move cursor")
print("  • Cursor starts from current position (no jumping)")
print("  • Press 'q' or ESC → Quit")
print("=" * 60 + "\n")

# Main loop
fps_counter = 0
fps_time = time.time()
fps = 0
action_display = ""
action_timer = 0

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        time.sleep(0.01)
        continue
    
    frame = cv2.flip(frame, 1)
    h, w = frame.shape[:2]
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)
    
    fingers = 0
    pinch_type = None
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            
            # Get landmarks
            index_tip = hand_landmarks.landmark[8]
            thumb_tip = hand_landmarks.landmark[4]
            middle_tip = hand_landmarks.landmark[12]
            
            # Count fingers
            fingers = count_extended_fingers(hand_landmarks)
            
            # Calculate pinch distances
            left_pinch_dist = calculate_distance(thumb_tip, index_tip)
            right_pinch_dist = calculate_distance(thumb_tip, middle_tip)
            
            # SCROLL MODE (4+ fingers)
            if fingers >= 4:
                if not scroll_mode:
                    scroll_mode = True
                    action_display = "SCROLL MODE"
                    action_timer = 30
                
                # Scroll logic
                current_y = index_tip.y
                if last_scroll_y != 0:
                    delta_y = current_y - last_scroll_y
                    if abs(delta_y) > 0.01:
                        scroll_amount = int(delta_y * scroll_sensitivity)
                        if scroll_amount != 0:
                            pyautogui.scroll(scroll_amount)
                            action_display = f"SCROLL: {scroll_amount:+d}"
                            action_timer = 15
                
                last_scroll_y = current_y
                
                # Scroll indicator
                cv2.circle(frame, (w-50, h//2), 40, COLORS['ORANGE'], 3)
                cv2.circle(frame, (w-50, h//2), 30, COLORS['ORANGE'], 2)
                cv2.putText(frame, "SCROLL", (w-95, h//2-25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['ORANGE'], 2)
                cv2.putText(frame, "MODE", (w-90, h//2+30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['ORANGE'], 1)
                
                # Draw hand without pinch effects
                draw_hand(frame, hand_landmarks, False, None)
                
            else:
                # MOUSE MODE
                if scroll_mode:
                    scroll_mode = False
                    last_scroll_y = 0
                    action_display = "MOUSE MODE"
                    action_timer = 30
                
                # Only move cursor if hand is detected (FIX: No jumping)
                if fingers >= 1:  # At least index finger detected
                    cursor_x = int(index_tip.x * screen_w)
                    cursor_y = int(index_tip.y * screen_h)
                    
                    # Boundary checking
                    cursor_x = max(0, min(screen_w, cursor_x))
                    cursor_y = max(0, min(screen_h, cursor_y))
                    
                    # Apply smoothing only after first detection
                    if not first_hand_detected:
                        # First detection - set position directly (no smoothing jump)
                        curr_x, curr_y = cursor_x, cursor_y
                        prev_x, prev_y = cursor_x, cursor_y
                        first_hand_detected = True
                    else:
                        # Normal smoothing
                        curr_x = prev_x + (cursor_x - prev_x) / smoothing
                        curr_y = prev_y + (cursor_y - prev_y) / smoothing
                    
                    # Move cursor
                    try:
                        pyautogui.moveTo(curr_x, curr_y)
                    except:
                        pass
                    
                    prev_x, prev_y = curr_x, curr_y
                else:
                    # No fingers detected - don't move cursor, but keep tracking ready
                    pass
                
                # Draw cursor
                cx, cy = int(index_tip.x * w), int(index_tip.y * h)
                cx = max(0, min(w, cx))
                cy = max(0, min(h, cy))
                
                # PINCH DETECTION
                if click_cooldown == 0:
                    # LEFT CLICK (Thumb + Index pinch)
                    if left_pinch_dist < 0.045:
                        if not pinch_active:
                            pinch_active = True
                            pinch_type = "left"
                            pinch_start_time = time.time()
                            pinch_progress = 0
                        
                        # Animate pinch
                        pinch_progress = min(1.0, (time.time() - pinch_start_time) * 15)
                        draw_pinch_indicator(frame, (cx, cy), 20, COLORS['GREEN'], pinch_progress)
                        
                        # Check for double click
                        current_time = time.time()
                        if last_pinch_time > 0 and (current_time - last_pinch_time) < 0.35:
                            pyautogui.doubleClick()
                            action_display = "DOUBLE CLICK!"
                            action_timer = 25
                            cv2.putText(frame, "DOUBLE CLICK!", (w//2-100, h//2), 
                                       cv2.FONT_HERSHEY_DUPLEX, 1, COLORS['PURPLE'], 3)
                            last_pinch_time = 0
                            pinch_active = False
                        else:
                            pyautogui.click()
                            action_display = "LEFT CLICK"
                            action_timer = 20
                            cv2.putText(frame, "LEFT CLICK!", (w//2-80, h//2), 
                                       cv2.FONT_HERSHEY_DUPLEX, 1, COLORS['GREEN'], 3)
                            last_pinch_time = current_time
                        
                        click_cooldown = 15
                        cv2.circle(frame, (cx, cy), 35, COLORS['GREEN'], 3)
                    
                    # RIGHT CLICK (Thumb + Middle pinch)
                    elif right_pinch_dist < 0.045:
                        if not pinch_active:
                            pinch_active = True
                            pinch_type = "right"
                            pinch_start_time = time.time()
                            pinch_progress = 0
                        
                        # Animate pinch
                        pinch_progress = min(1.0, (time.time() - pinch_start_time) * 15)
                        draw_pinch_indicator(frame, (cx, cy), 20, COLORS['RED'], pinch_progress)
                        
                        pyautogui.rightClick()
                        action_display = "RIGHT CLICK"
                        action_timer = 20
                        cv2.putText(frame, "RIGHT CLICK!", (w//2-80, h//2), 
                                   cv2.FONT_HERSHEY_DUPLEX, 1, COLORS['RED'], 3)
                        click_cooldown = 15
                        cv2.circle(frame, (cx, cy), 35, COLORS['RED'], 3)
                    
                    else:
                        if pinch_active:
                            pinch_active = False
                            pinch_type = None
                            pinch_progress = 0
                
                # Draw hand with or without pinch effect
                draw_hand(frame, hand_landmarks, pinch_active, pinch_type)
                
                # Draw cursor circle
                cv2.circle(frame, (cx, cy), 15, COLORS['CYAN'], 2)
                cv2.circle(frame, (cx, cy), 8, COLORS['WHITE'], -1)
                
                # Show pinch guide (when close but not pinching)
                if not pinch_active and (left_pinch_dist < 0.08 or right_pinch_dist < 0.08):
                    thumb_pos = (int(thumb_tip.x * w), int(thumb_tip.y * h))
                    if left_pinch_dist < 0.08:
                        finger_pos = (int(index_tip.x * w), int(index_tip.y * h))
                        cv2.line(frame, thumb_pos, finger_pos, COLORS['YELLOW'], 2)
                    if right_pinch_dist < 0.08:
                        finger_pos = (int(middle_tip.x * w), int(middle_tip.y * h))
                        cv2.line(frame, thumb_pos, finger_pos, COLORS['YELLOW'], 2)
    
    # Update cooldown
    if click_cooldown > 0:
        click_cooldown -= 1
    
    # Show action on screen
    if action_timer > 0:
        text_size = cv2.getTextSize(action_display, cv2.FONT_HERSHEY_DUPLEX, 0.8, 2)[0]
        bg_x1 = w//2 - text_size[0]//2 - 15
        bg_x2 = w//2 + text_size[0]//2 + 15
        cv2.rectangle(frame, (bg_x1, 65), (bg_x2, 110), (0, 0, 0), -1)
        cv2.rectangle(frame, (bg_x1, 65), (bg_x2, 110), COLORS['YELLOW'], 2)
        cv2.putText(frame, action_display, (w//2 - text_size[0]//2, 100), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.8, COLORS['YELLOW'], 2)
        action_timer -= 1
    
    # FPS calculation (updated every second)
    fps_counter += 1
    if time.time() - fps_time > 1:
        fps = fps_counter
        fps_counter = 0
        fps_time = time.time()
    
    # Draw HUD overlay (FPS + mode + controls)
    frame = draw_instructions(frame, scroll_mode, fps)

    # Show frame
    cv2.imshow("Virtual Mouse - Pinch Gestures", frame)
    
    # Quit
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == ord('Q') or key == 27:
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("✅ Virtual Mouse stopped successfully!")
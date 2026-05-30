# -*- coding: utf-8 -*-
import cv2
import mediapipe as mp
import pyautogui
from pynput.keyboard import Controller
import numpy as np
import threading
import time
import math
import sys
import os

# Suppress MediaPipe warnings
import warnings
warnings.filterwarnings('ignore')
os.environ['GLOG_minloglevel'] = '3'

# Force UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from virtual_keyboard import FloatingKeyboard, special_widths, keys

print("=" * 60)
print("🦾 COMBINED VIRTUAL DEVICE (MOUSE + FLOATING KEYBOARD)")
print("=" * 60)

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

try:
    screen_w, screen_h = pyautogui.size()
except:
    screen_w, screen_h = 1920, 1080

def calculate_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def count_fingers(hand_landmarks):
    fingers = 0
    if hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y: fingers += 1
    if hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y: fingers += 1
    if hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y: fingers += 1
    if hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y: fingers += 1
    return fingers

def run_camera(keyboard):
    print("\n🔍 Looking for camera...")
    cap = None
    for i in range(3):
        test_cap = cv2.VideoCapture(i)
        if test_cap.isOpened():
            ret, test_frame = test_cap.read()
            if ret and test_frame is not None:
                cap = test_cap
                print(f"  ✅ Camera {i} working!")
                break
            test_cap.release()

    if cap is None:
        print("\n❌ No camera found!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

    # Variables
    mode = "KEYBOARD"  # Start in KEYBOARD mode
    mode_switch_cooldown = 0
    
    # Mouse variables
    current_mouse_x, current_mouse_y = pyautogui.position()
    prev_x, prev_y = current_mouse_x, current_mouse_y
    smoothing = 2
    click_cooldown = 0
    first_hand_detected = False
    
    # Keyboard dragging variables
    is_pinching_kb = False
    pinch_start_x, pinch_start_y = 0, 0
    keyboard_start_x, keyboard_start_y = 0, 0

    print("\n✅ Camera ready! Unified tracking active")
    print("\n🔄 MODE SWITCHING:")
    print("  • 🖐️ Show 4+ fingers (open palm) -> switch to MOUSE mode")
    print("  • ✊ Make a fist (0 fingers) -> switch to KEYBOARD mode")
    print("\nMouse: Index point to move, Thumb+Index to Left Click, Thumb+Middle to Right Click")
    print("Keyboard: Pinch to move UI, Index to highlight, Peace sign to type")
    print("=" * 60 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        
        # Display current mode tracking
        mode_color = (0, 165, 255) if mode == "MOUSE" else (255, 0, 255)
        cv2.rectangle(frame, (0, 0), (320, 80), (0, 0, 0), -1)
        cv2.putText(frame, f"MODE: {mode}", (10, 30), cv2.FONT_HERSHEY_DUPLEX, 0.8, mode_color, 2)
        
        fingers = 0
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                index_tip = hand_landmarks.landmark[8]
                thumb_tip = hand_landmarks.landmark[4]
                middle_tip = hand_landmarks.landmark[12]
                
                screen_x = int(index_tip.x * screen_w)
                screen_y = int(index_tip.y * screen_h)
                
                fingers = count_fingers(hand_landmarks)
                cv2.putText(frame, f"Fingers: {fingers}", (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                
                # --- MODE SWITCHING ---
                if mode_switch_cooldown == 0:
                    if fingers >= 4 and mode != "MOUSE":
                        mode = "MOUSE"
                        mode_switch_cooldown = 40
                        cv2.putText(frame, "SWITCHED TO MOUSE", (w//2-150, h//2), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                    elif fingers == 0 and mode != "KEYBOARD":
                        mode = "KEYBOARD"
                        pyautogui.mouseUp() # Ensure no stuck dragging
                        mode_switch_cooldown = 40
                        cv2.putText(frame, "SWITCHED TO KEYBOARD", (w//2-180, h//2), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 0, 255), 2)

                # --- MOUSE MODE ---
                if mode == "MOUSE":
                    # Display Mouse Help
                    cv2.putText(frame, "Move: Index  |  L-Click: Thumb+Index  |  R-Click: Thumb+Middle", 
                               (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    if fingers >= 1:
                        if not first_hand_detected:
                            curr_x, curr_y = screen_x, screen_y
                            prev_x, prev_y = screen_x, screen_y
                            first_hand_detected = True
                        else:
                            curr_x = prev_x + (screen_x - prev_x) / smoothing
                            curr_y = prev_y + (screen_y - prev_y) / smoothing
                        
                        curr_x, curr_y = max(0, min(screen_w, curr_x)), max(0, min(screen_h, curr_y))
                        
                        try:
                            pyautogui.moveTo(curr_x, curr_y)
                        except:
                            pass
                        prev_x, prev_y = curr_x, curr_y
                    
                    # Pointer dot
                    cx, cy = int(index_tip.x * w), int(index_tip.y * h)
                    cv2.circle(frame, (cx, cy), 8, (0, 255, 0), cv2.FILLED)
                    
                    # Clicks
                    dist_l = calculate_distance(thumb_tip, index_tip)
                    dist_r = calculate_distance(thumb_tip, middle_tip)
                    
                    if click_cooldown == 0:
                        if dist_l < 0.045:
                            pyautogui.click()
                            cv2.circle(frame, (cx, cy), 15, (0, 255, 0), cv2.FILLED)
                            cv2.putText(frame, "LEFT CLICK", (cx+20, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            click_cooldown = 15
                        elif dist_r < 0.045:
                            pyautogui.rightClick()
                            cv2.circle(frame, (cx, cy), 15, (0, 0, 255), cv2.FILLED)
                            cv2.putText(frame, "RIGHT CLICK", (cx+20, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            click_cooldown = 15
                            
                # --- KEYBOARD MODE ---
                elif mode == "KEYBOARD":
                    cv2.putText(frame, "Move KB: Pinch  |  Highlight: Index  |  Type: Peace Sign", 
                               (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                               
                    dist_pinch = calculate_distance(thumb_tip, index_tip)
                    is_pinching_now = dist_pinch < 0.045
                    
                    fx, fy = int(index_tip.x * w), int(index_tip.y * h)
                    
                    # Drag Keyboard
                    if is_pinching_now:
                        cv2.circle(frame, (fx, fy), 15, (0, 0, 255), 3)
                        cv2.circle(frame, (fx, fy), 8, (0, 0, 255), -1)
                        if not is_pinching_kb:
                            is_pinching_kb = True
                            pinch_start_x, pinch_start_y = screen_x, screen_y
                            keyboard_start_x, keyboard_start_y = keyboard.kb_x, keyboard.kb_y
                        else:
                            keyboard.move_keyboard(screen_x - pinch_start_x, screen_y - pinch_start_y)
                            cv2.putText(frame, "DRAGGING KEYBOARD", (w//2-100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    else:
                        is_pinching_kb = False
                        cv2.circle(frame, (fx, fy), 10, (0, 255, 255), 2)
                        cv2.circle(frame, (fx, fy), 5, (0, 255, 255), -1)
                        
                        # Get focused key
                        key_pos = None
                        try:
                            if (keyboard.kb_x <= screen_x <= keyboard.kb_x + keyboard.kb_width and 
                                keyboard.kb_y + 35 <= screen_y <= keyboard.kb_y + keyboard.kb_height):
                                
                                key_area_y = keyboard.kb_y + 35 + 8
                                key_area_h = keyboard.kb_height - 35 - 16
                                rows = len(keys)
                                row_h = key_area_h // rows
                                
                                for row_idx, row in enumerate(keys):
                                    row_y = key_area_y + row_idx * row_h
                                    if row_y <= screen_y <= row_y + row_h:
                                        curr_x = keyboard.kb_x + 5
                                        for col_idx, key in enumerate(row):
                                            key_w = special_widths.get(key, 1) * (keyboard.kb_width - 10) // sum(special_widths.get(k, 1) for k in row)
                                            if curr_x <= screen_x <= curr_x + key_w:
                                                key_pos = (row_idx, col_idx)
                                                break
                                            curr_x += key_w + 2
                                        break
                        except:
                            pass
                            
                        if key_pos:
                            keyboard.highlight_key_external(key_pos)
                        
                        # Type
                        if fingers == 2 and click_cooldown == 0:
                            if key_pos:
                                keyboard.type_from_external(key_pos)
                                click_cooldown = 20
                                cv2.putText(frame, "TYPED", (fx-30, fy-20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        else:
            first_hand_detected = False

        if click_cooldown > 0: click_cooldown -= 1
        if mode_switch_cooldown > 0: mode_switch_cooldown -= 1
        
        cv2.imshow("Combined Virtual Device", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Camera tracking stopped")
    # Stop keyboard when camera closes
    keyboard.root.quit()

if __name__ == "__main__":
    keyboard_app = FloatingKeyboard()
    camera_thread = threading.Thread(target=run_camera, args=(keyboard_app,), daemon=True)
    camera_thread.start()
    keyboard_app.run()
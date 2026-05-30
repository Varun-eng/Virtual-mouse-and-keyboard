import tkinter as tk
from tkinter import ttk
import threading
import cv2
import mediapipe as mp
from pynput.keyboard import Controller, Key
import math
import time
import sys
import os

# Suppress MediaPipe warnings
os.environ['GLOG_minloglevel'] = '3'

print("=" * 60)
print("🎹 FLOATING TRANSPARENT KEYBOARD - PINCH TO MOVE")
print("=" * 60)

# Initialize MediaPipe for hand tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils
keyboard_controller = Controller()

# Keyboard layout
keys = [
    ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'BACKSPACE'],
    ['TAB', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\'],
    ['CAPS', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'", 'ENTER'],
    ['SHIFT', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'SHIFT'],
    ['CTRL', 'WIN', 'ALT', 'SPACE', 'ALT', 'WIN', 'CTRL']
]

# Key sizes
special_widths = {
    'BACKSPACE': 1.5, 'TAB': 1.2, 'CAPS': 1.2, 'ENTER': 1.2,
    'SHIFT': 1.5, 'SPACE': 4, 'CTRL': 1.2, 'WIN': 1.2, 'ALT': 1.2
}

# Colors
COLORS = {
    'KEY_NORMAL': '#2a2a3a',
    'KEY_HOVER': '#5a5a8a',
    'KEY_PRESS': '#00cc00',
    'KEY_SPECIAL': '#3a3a4a',
    'TEXT': '#ffffff',
    'TEXT_HOVER': '#ffff00',
    'BORDER': '#6a6a8a',
    'GLOW': '#00ccff',
    'DRAG_BAR': '#4a4a6a'
}

class FloatingKeyboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Floating Keyboard")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.85)
        self.root.overrideredirect(True)
        
        # Get screen size
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Keyboard size
        self.kb_width = 1100
        self.kb_height = 320
        
        # Initial position (bottom center)
        self.kb_x = (self.screen_width - self.kb_width) // 2
        self.kb_y = self.screen_height - self.kb_height - 50
        
        self.root.geometry(f"{self.kb_width}x{self.kb_height}+{self.kb_x}+{self.kb_y}")
        self.root.attributes('-transparentcolor', '#000001')
        
        # Create main frame
        self.main_frame = tk.Frame(self.root, bg='#000001')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize variables
        self.hover_key = None
        self.pressed_key = None
        self.last_typed = ""
        self.press_timer = 0
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.key_buttons = {}
        
        # Create UI
        self.create_drag_bar()
        self.create_keyboard()
        
        # Bind drag events
        self.drag_bar.bind('<Button-1>', self.start_drag)
        self.drag_bar.bind('<B1-Motion>', self.on_drag)
        self.drag_bar.bind('<ButtonRelease-1>', self.stop_drag)
        
        # Start animation
        self.update_animation()
        
    def create_drag_bar(self):
        """Create draggable top bar"""
        self.drag_bar = tk.Frame(self.main_frame, bg=COLORS['DRAG_BAR'], height=35)
        self.drag_bar.pack(fill=tk.X, pady=(0, 5))
        self.drag_bar.pack_propagate(False)
        
        drag_label = tk.Label(self.drag_bar, text="⋮⋮⋮  DRAG OR PINCH TO MOVE KEYBOARD  ⋮⋮⋮", 
                              fg=COLORS['GLOW'], bg=COLORS['DRAG_BAR'],
                              font=('Arial', 10, 'bold'))
        drag_label.pack(side=tk.LEFT, padx=10, pady=8)
        
        close_btn = tk.Label(self.drag_bar, text="✕", fg='#ff5555', 
                            bg=COLORS['DRAG_BAR'], font=('Arial', 12, 'bold'),
                            cursor='hand2')
        close_btn.pack(side=tk.RIGHT, padx=10, pady=8)
        close_btn.bind('<Button-1>', lambda e: self.quit())
        
        min_btn = tk.Label(self.drag_bar, text="−", fg='#ffff55', 
                          bg=COLORS['DRAG_BAR'], font=('Arial', 14, 'bold'),
                          cursor='hand2')
        min_btn.pack(side=tk.RIGHT, padx=5, pady=8)
        min_btn.bind('<Button-1>', lambda e: self.minimize())
        
    def create_keyboard(self):
        """Create keyboard buttons"""
        canvas = tk.Canvas(self.main_frame, bg='#000001', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        self.keyboard_frame = tk.Frame(canvas, bg='#000001')
        self.keyboard_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.keyboard_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        rows = len(keys)
        available_height = self.kb_height - 45
        row_height = available_height // rows
        
        for row_idx, row in enumerate(keys):
            row_frame = tk.Frame(self.keyboard_frame, bg='#000001')
            row_frame.pack(fill=tk.X, pady=1)
            
            for col_idx, key in enumerate(row):
                key_width = special_widths.get(key, 1) * (self.kb_width - 20) // sum(special_widths.get(k, 1) for k in row)
                key_width = max(40, key_width - 2)
                
                btn_frame = tk.Frame(row_frame, bg=COLORS['KEY_NORMAL'], 
                                    width=key_width, height=row_height-2,
                                    relief='flat', bd=1)
                btn_frame.pack(side=tk.LEFT, padx=1, pady=1)
                btn_frame.pack_propagate(False)
                
                font_size = 9 if len(key) > 3 else 11
                label = tk.Label(btn_frame, text=key, fg=COLORS['TEXT'], 
                                bg=COLORS['KEY_NORMAL'], font=('Arial', font_size, 'bold'))
                label.pack(expand=True, fill=tk.BOTH)
                
                self.key_buttons[(row_idx, col_idx)] = {
                    'frame': btn_frame,
                    'label': label,
                    'key': key,
                    'row': row_idx,
                    'col': col_idx
                }
                
                btn_frame.bind('<Enter>', lambda e, r=row_idx, c=col_idx: self.on_hover(r, c))
                btn_frame.bind('<Leave>', lambda e: self.on_leave())
                btn_frame.bind('<Button-1>', lambda e, r=row_idx, c=col_idx: self.on_click(r, c))
    
    def start_drag(self, event):
        self.is_dragging = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        
    def on_drag(self, event):
        if self.is_dragging:
            delta_x = event.x_root - self.drag_start_x
            delta_y = event.y_root - self.drag_start_y
            
            new_x = self.kb_x + delta_x
            new_y = self.kb_y + delta_y
            
            new_x = max(0, min(new_x, self.screen_width - self.kb_width))
            new_y = max(0, min(new_y, self.screen_height - self.kb_height))
            
            self.kb_x = new_x
            self.kb_y = new_y
            self.root.geometry(f"{self.kb_width}x{self.kb_height}+{self.kb_x}+{self.kb_y}")
            
    def stop_drag(self, event):
        self.is_dragging = False
        
    def move_keyboard(self, delta_x, delta_y):
        """Move keyboard by delta amount"""
        new_x = self.kb_x + delta_x
        new_y = self.kb_y + delta_y
        
        new_x = max(0, min(new_x, self.screen_width - self.kb_width))
        new_y = max(0, min(new_y, self.screen_height - self.kb_height))
        
        self.kb_x = new_x
        self.kb_y = new_y
        self.root.geometry(f"{self.kb_width}x{self.kb_height}+{self.kb_x}+{self.kb_y}")
        
    def minimize(self):
        self.root.iconify()
        
    def on_hover(self, row, col):
        if self.pressed_key:
            return
        
        self.hover_key = (row, col)
        btn_info = self.key_buttons.get((row, col))
        if btn_info:
            btn_info['frame'].config(bg=COLORS['KEY_HOVER'])
            btn_info['label'].config(bg=COLORS['KEY_HOVER'], fg=COLORS['TEXT_HOVER'])
    
    def on_leave(self):
        if self.hover_key and not self.pressed_key:
            btn_info = self.key_buttons.get(self.hover_key)
            if btn_info:
                btn_info['frame'].config(bg=COLORS['KEY_NORMAL'])
                btn_info['label'].config(bg=COLORS['KEY_NORMAL'], fg=COLORS['TEXT'])
            self.hover_key = None
    
    def on_click(self, row, col):
        btn_info = self.key_buttons.get((row, col))
        if btn_info:
            key = btn_info['key']
            self.type_key(key)
            self.pressed_key = (row, col)
            self.press_timer = 15
            btn_info['frame'].config(bg=COLORS['KEY_PRESS'])
            btn_info['label'].config(bg=COLORS['KEY_PRESS'], fg='#000000')
            self.root.after(300, lambda: self.reset_key(row, col))
    
    def reset_key(self, row, col):
        if self.pressed_key == (row, col):
            self.pressed_key = None
            btn_info = self.key_buttons.get((row, col))
            if btn_info and self.hover_key != (row, col):
                btn_info['frame'].config(bg=COLORS['KEY_NORMAL'])
                btn_info['label'].config(bg=COLORS['KEY_NORMAL'], fg=COLORS['TEXT'])
    
    def type_key(self, key):
        special_keys = {
            'SPACE': Key.space, 'ENTER': Key.enter, 'BACKSPACE': Key.backspace,
            'TAB': Key.tab, 'CAPS': Key.caps_lock, 'SHIFT': Key.shift,
            'CTRL': Key.ctrl, 'WIN': Key.cmd, 'ALT': Key.alt
        }
        
        if key in special_keys:
            keyboard_controller.press(special_keys[key])
            keyboard_controller.release(special_keys[key])
        else:
            keyboard_controller.press(key.lower())
            keyboard_controller.release(key.lower())
        
        self.last_typed = key
        self.show_popup(f"▶ {key} ◀")
        print(f"⌨️ Typed: {key}")
    
    def show_popup(self, text):
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes('-topmost', True)
        popup.attributes('-alpha', 0.9)
        
        x = self.screen_width // 2 - 60
        y = 100
        popup.geometry(f"120x40+{x}+{y}")
        
        label = tk.Label(popup, text=text, fg=COLORS['GLOW'], 
                        bg='#000000', font=('Arial', 12, 'bold'))
        label.pack(expand=True, fill=tk.BOTH)
        self.root.after(1000, popup.destroy)
    
    def update_animation(self):
        if self.press_timer > 0:
            self.press_timer -= 1
        elif self.pressed_key:
            self.reset_key(self.pressed_key[0], self.pressed_key[1])
        self.root.after(50, self.update_animation)
    
    def highlight_key_external(self, key_pos):
        if key_pos and key_pos != self.hover_key and not self.pressed_key:
            if self.hover_key:
                old_btn = self.key_buttons.get(self.hover_key)
                if old_btn:
                    old_btn['frame'].config(bg=COLORS['KEY_NORMAL'])
                    old_btn['label'].config(bg=COLORS['KEY_NORMAL'], fg=COLORS['TEXT'])
            
            self.hover_key = key_pos
            btn_info = self.key_buttons.get(key_pos)
            if btn_info:
                btn_info['frame'].config(bg=COLORS['KEY_HOVER'])
                btn_info['label'].config(bg=COLORS['KEY_HOVER'], fg=COLORS['TEXT_HOVER'])
    
    def type_from_external(self, key_pos):
        if key_pos and not self.pressed_key:
            btn_info = self.key_buttons.get(key_pos)
            if btn_info:
                self.root.after(0, lambda: self.on_click(key_pos[0], key_pos[1]))
    
    def run(self):
        self.root.mainloop()
    
    def quit(self):
        self.root.quit()

# Run camera with pinch to move functionality (NO CONSOLE SPAM)
def run_camera():
    """Run camera tracking with pinch to move keyboard"""
    print("\n📷 Opening camera window...")
    
    # Try multiple camera indices
    cap = None
    for i in range(3):
        test_cap = cv2.VideoCapture(i)
        if test_cap.isOpened():
            ret, test_frame = test_cap.read()
            if ret and test_frame is not None:
                cap = test_cap
                print(f"  ✅ Camera {i} found and working!")
                break
        test_cap.release()
    
    if cap is None:
        print("\n❌ No camera found!")
        print("💡 Keyboard will still work with mouse clicks!")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n✅ Camera ready! Hand tracking active")
    print("\n🎮 HOW TO USE:")
    print("  • 🤏 PINCH (thumb + index) anywhere → Move keyboard")
    print("  • 👆 Point index finger at keys → Highlight")
    print("  • ✌️ Peace sign (2 fingers) → TYPE")
    print("  • Press 'q' to stop camera")
    print("\n" + "=" * 60 + "\n")
    
    def calculate_distance(p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    
    def count_fingers(hand):
        fingers = 0
        if hand.landmark[8].y < hand.landmark[6].y:
            fingers += 1
        if hand.landmark[12].y < hand.landmark[10].y:
            fingers += 1
        if hand.landmark[16].y < hand.landmark[14].y:
            fingers += 1
        if hand.landmark[20].y < hand.landmark[18].y:
            fingers += 1
        return fingers
    
    # Get keyboard instance from global
    global keyboard_instance
    keyboard = keyboard_instance
    
    cooldown = 0
    screen_width = keyboard.screen_width
    screen_height = keyboard.screen_height
    hand_detected = False
    
    # Pinch to move variables
    is_pinching = False
    pinch_start_x = 0
    pinch_start_y = 0
    keyboard_start_x = 0
    keyboard_start_y = 0
    pinch_message_shown = False  # To show message only once
    
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        
        # Draw instructions on camera feed
        h, w = frame.shape[:2]
        cv2.putText(frame, "Virtual Keyboard - PINCH TO MOVE", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, "🤏 Pinch anywhere = Move | ✌️ Peace sign = Type", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(frame, "Press 'q' to stop camera", (10, h - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        if results.multi_hand_landmarks:
            hand_detected = True
            for hand in results.multi_hand_landmarks:
                # Draw hand landmarks
                mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                
                # Get finger positions
                index_tip = hand.landmark[8]
                thumb_tip = hand.landmark[4]
                middle_tip = hand.landmark[12]
                
                # Calculate pinch distance
                pinch_dist = calculate_distance(thumb_tip, index_tip)
                is_pinching_now = pinch_dist < 0.030
                
                # Convert to screen coordinates
                screen_x = int(index_tip.x * screen_width)
                screen_y = int(index_tip.y * screen_height)
                
                # Handle pinch to move keyboard (NO CONSOLE OUTPUT)
                if is_pinching_now:
                    if not is_pinching:
                        # Start pinching - NO PRINT
                        is_pinching = True
                        pinch_start_x = screen_x
                        pinch_start_y = screen_y
                        keyboard_start_x = keyboard.kb_x
                        keyboard_start_y = keyboard.kb_y
                        pinch_message_shown = True
                        cv2.putText(frame, "MOVING KEYBOARD!", (w//2-100, h//2), 
                                   cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 255), 2)
                    else:
                        # Move keyboard - NO PRINT
                        delta_x = screen_x - pinch_start_x
                        delta_y = screen_y - pinch_start_y
                        keyboard.move_keyboard(delta_x, delta_y)
                        cv2.putText(frame, "🔽 DRAGGING KEYBOARD 🔽", (w//2-120, 100), 
                                   cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 255), 2)
                else:
                    if is_pinching:
                        is_pinching = False
                        pinch_message_shown = False
                
                # Get key at position (only if not pinching)
                key_pos = None
                if not is_pinching:
                    try:
                        kb_x = keyboard.kb_x
                        kb_y = keyboard.kb_y
                        kb_width = keyboard.kb_width
                        kb_height = keyboard.kb_height
                        
                        if (kb_x <= screen_x <= kb_x + kb_width and 
                            kb_y + 35 <= screen_y <= kb_y + kb_height):
                            
                            key_area_y = kb_y + 35 + 8
                            key_area_h = kb_height - 35 - 16
                            rows = len(keys)
                            row_h = key_area_h // rows
                            
                            for row_idx, row in enumerate(keys):
                                row_y = key_area_y + row_idx * row_h
                                if row_y <= screen_y <= row_y + row_h:
                                    current_x = kb_x + 5
                                    for col_idx, key in enumerate(row):
                                        key_w = special_widths.get(key, 1) * (kb_width - 10) // sum(special_widths.get(k, 1) for k in row)
                                        if current_x <= screen_x <= current_x + key_w:
                                            key_pos = (row_idx, col_idx)
                                            break
                                        current_x += key_w + 2
                                    break
                    except:
                        pass
                
                # Highlight key
                if key_pos:
                    keyboard.highlight_key_external(key_pos)
                    cv2.putText(frame, f"Pointing at: {keys[key_pos[0]][key_pos[1]]}", 
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Count fingers (for typing)
                fingers = count_fingers(hand)
                
                # Draw finger count
                cv2.putText(frame, f"Fingers: {fingers}", (10, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Draw circle at finger tip
                fx, fy = int(index_tip.x * w), int(index_tip.y * h)
                
                # Different color for pinch vs pointing
                if is_pinching_now:
                    cv2.circle(frame, (fx, fy), 15, (0, 0, 255), 3)
                    cv2.circle(frame, (fx, fy), 8, (0, 0, 255), -1)
                else:
                    cv2.circle(frame, (fx, fy), 10, (0, 255, 255), 2)
                    cv2.circle(frame, (fx, fy), 5, (0, 255, 255), -1)
                
                # Type with peace sign (2 fingers) - only if not pinching
                if not is_pinching and fingers == 2 and cooldown == 0:
                    if key_pos:
                        keyboard.type_from_external(key_pos)
                        cooldown = 30
                        cv2.putText(frame, "TYPING!", (fx - 30, fy - 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            if hand_detected:
                hand_detected = False
            cv2.putText(frame, "No hand detected - Please show your hand", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            is_pinching = False
        
        cv2.imshow("Hand Tracking - Pinch to Move Keyboard", frame)
        
        if cooldown > 0:
            cooldown -= 0.5
        
        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n📹 Camera tracking stopped (keyboard still works with mouse)")

# Main execution
if __name__ == "__main__":
    print("\n🔥 Starting Floating Transparent Keyboard...\n")
    print("=" * 60)
    print("✨ FEATURES:")
    print("  • Transparent keyboard on your screen")
    print("  • Always on top of all applications")
    print("  • 🤏 PINCH ANYWHERE to move keyboard")
    print("  • Click keys with mouse")
    print("  • Point + Peace sign to type with camera")
    print("=" * 60 + "\n")
    
    # Create keyboard
    keyboard_instance = FloatingKeyboard()
    
    # Run camera in a separate thread
    camera_thread = threading.Thread(target=run_camera, daemon=True)
    camera_thread.start()
    
    print("💡 TIPS:")
    print("  • 🤏 PINCH (thumb + index together) ANYWHERE on screen to move keyboard")
    print("  • 👆 Point index finger at keys to highlight")
    print("  • ✌️ Peace sign to type")
    print("  • Camera window will open in a few seconds")
    print("  • Console will ONLY show typed keys (no spam)\n")
    
    # Run keyboard GUI
    keyboard_instance.run()
    
    print("\n✅ Floating Keyboard stopped!")
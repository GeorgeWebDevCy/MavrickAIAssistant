import customtkinter as ctk
import math
import threading
import time
import psutil

class MavrickUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MAVRICK HUD")
        self.geometry("450x700")
        self.attributes("-alpha", 0.95)  # Slightly more opaque for premium feel
        self.attributes("-topmost", True)
        self.overrideredirect(True)      # Borderless HUD
        
        # Colors
        self.primary_cyan = "#00d2ff"
        self.secondary_teal = "#005f73"
        self.dim_cyan = "#003a47"
        self.alert_orange = "#ff9f1c"
        self.bg_black = "#050505"
        self.alert_red = "#ff4b2b"
        
        # Center the window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (450 // 2)
        y = (screen_height // 2) - (700 // 2)
        self.geometry(f"450x700+{x}+{y}")
        
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)
        self.bind("<Motion>", self.update_parallax_target)

        self.configure(fg_color=self.bg_black)
        
        # Animation variables
        self.angle_rings = [0, 180, 90, 270]
        self.pulse_val = 0
        self.scan_angle = 0
        self.bars = []
        self.hex_dots = []
        
        # Parallax variables
        self.p_x = 0
        self.p_y = 0
        self.target_p_x = 0
        self.target_p_y = 0
        
        # System Stats
        self.cpu_usage = 0
        self.ram_usage = 0
        
        self.setup_ui()
        self.start_monitor_thread()
        self.animate_hud()

    def setup_ui(self):
        # Header with futuristic font (Orbitron is common for sci-fi)
        title_font = ("Orbitron", 28, "bold")
        self.label_title = ctk.CTkLabel(self, text="MAVRICK", font=title_font, text_color=self.primary_cyan)
        self.label_title.pack(pady=(30, 10))
        
        self.sub_title = ctk.CTkLabel(self, text="ADVANCED ARTIFICIAL INTELLIGENCE", font=("Consolas", 10), text_color=self.secondary_teal)
        self.sub_title.pack(pady=(0, 20))

        # Main HUD Canvas - Increased size for more details
        self.canvas = ctk.CTkCanvas(self, width=300, height=320, bg=self.bg_black, highlightthickness=0)
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", lambda e: self.on_engage())
        
        # 1. Background Hex/Dot Grid (Simulated)
        for i in range(5):
            for j in range(5):
                start_x, start_y = 60 + i*45, 70 + j*45
                dot = self.canvas.create_oval(start_x, start_y, start_x+2, start_y+2, fill=self.dim_cyan, outline="")
                self.hex_dots.append(dot)

        # 2. Concentric Rotating Rings
        self.rings = []
        # Outer thick ring
        self.rings.append(self.canvas.create_arc(30, 30, 270, 270, outline=self.dim_cyan, width=1, style="arc", extent=359))
        self.rings.append(self.canvas.create_arc(35, 35, 265, 265, outline=self.primary_cyan, width=2, style="arc", start=0, extent=60))
        self.rings.append(self.canvas.create_arc(35, 35, 265, 265, outline=self.primary_cyan, width=2, style="arc", start=180, extent=60))
        
        # Middle ring
        self.rings.append(self.canvas.create_arc(60, 60, 240, 240, outline=self.secondary_teal, width=1, style="arc", start=90, extent=120))
        self.rings.append(self.canvas.create_arc(60, 60, 240, 240, outline=self.secondary_teal, width=1, style="arc", start=270, extent=120))
        
        # Inner scanning ring
        self.rings.append(self.canvas.create_arc(85, 85, 215, 215, outline=self.dim_cyan, width=1, style="arc", extent=359))
        self.scan_line = self.canvas.create_arc(85, 85, 215, 215, outline=self.primary_cyan, width=4, style="arc", start=0, extent=20)

        # 3. System Heatmap Arcs
        self.arc_cpu = self.canvas.create_arc(20, 20, 280, 280, outline=self.alert_orange, width=3, style="arc", start=135, extent=0)
        self.arc_ram = self.canvas.create_arc(15, 15, 285, 285, outline=self.secondary_teal, width=3, style="arc", start=225, extent=0)

        # 4. Core Pulse
        self.core_circle = self.canvas.create_oval(110, 110, 190, 190, outline=self.primary_cyan, width=2)
        self.inner_circle = self.canvas.create_oval(130, 130, 170, 170, fill=self.primary_cyan, outline="")
        
        # 5. Voice Visualizer Bars (HUD Position)
        for i in range(16):
            x = 70 + (i * 10)
            bar = self.canvas.create_rectangle(x, 260, x+6, 265, fill=self.primary_cyan, outline="")
            self.bars.append(bar)

        # 5. Peripheral Data Elements
        self.data_labels = []
        data_configs = [
            ("ENC: RSA-4096", 40, 120),
            ("BIT: 128-FLOAT", 40, 280),
            ("CPU: MONITOR", 340, 120),
            ("RAM: MONITOR", 340, 280)
        ]
        for text, x, y in data_configs:
            lbl = ctk.CTkLabel(self, text=text, font=("Consolas", 9), text_color=self.secondary_teal)
            lbl.place(x=x, y=y)
            self.data_labels.append(lbl)

        # Interaction Log - Refined look
        self.log_box = ctk.CTkTextbox(self, width=400, height=120, fg_color="#101010", text_color=self.primary_cyan, font=("Consolas", 12), border_width=1, border_color=self.dim_cyan)
        self.log_box.pack(pady=10)

        # Stats Section
        self.usage_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.usage_frame.pack(pady=5, fill="x", padx=30)
        
        self.stats_label = ctk.CTkLabel(self.usage_frame, text="COST: $0.0000 | TOKENS: 0", font=("Consolas", 10), text_color=self.secondary_teal)
        self.stats_label.pack(side="top", anchor="w")
        
        self.balance_label = ctk.CTkLabel(self.usage_frame, text="BALANCE: $0.00", font=("Consolas", 10), text_color=self.secondary_teal)
        self.balance_label.pack(side="top", anchor="w")

        # Bottom Controls
        self.status_label = ctk.CTkLabel(self, text="NETWORK STATUS: STANDBY", font=("Consolas", 11, "bold"), text_color=self.primary_cyan)
        self.status_label.pack(pady=5)
        
        self.btn_listen = ctk.CTkButton(self, text="ENGAGE HYPERLINK", font=("Orbitron", 12, "bold"), fg_color=self.primary_cyan, text_color="black", hover_color="#00b8e6", corner_radius=5, height=40, command=self.on_engage)
        self.btn_listen.pack(pady=10, padx=40, fill="x")
        
        self.btn_exit = ctk.CTkButton(self, text="TERMINATE CONNECTION", font=("Consolas", 10), fg_color="transparent", border_width=1, border_color=self.alert_red, text_color=self.alert_red, command=self.destroy)
        self.btn_exit.pack(pady=5)
        
    def log_message(self, message):
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")

    def clear_log(self):
        self.log_box.delete("0.0", "end")

    def update_stats(self, cost, tokens, balance):
        self.stats_label.configure(text=f"COST: ${cost:.4f} | TOKENS: {tokens}")
        self.balance_label.configure(text=f"BALANCE: ${balance:.2f}")
        if balance <= 0:
            self.balance_label.configure(text_color="#ff4b2b") # Red for alert
        else:
            self.balance_label.configure(text_color=self.secondary_teal)
        
    def start_monitor_thread(self):
        def monitor():
            while True:
                self.cpu_usage = psutil.cpu_percent()
                self.ram_usage = psutil.virtual_memory().percent
                time.sleep(1)
        threading.Thread(target=monitor, daemon=True).start()

    def update_parallax_target(self, event):
        # Calculate center of the canvas relative to the window
        canvas_x = self.canvas.winfo_x() + self.canvas.winfo_width() / 2
        canvas_y = self.canvas.winfo_y() + self.canvas.winfo_height() / 2
        
        # Mouse position relative to the canvas center
        self.target_p_x = (event.x_root - (self.winfo_x() + canvas_x)) * 0.08
        self.target_p_y = (event.y_root - (self.winfo_y() + canvas_y)) * 0.08

    def animate_hud(self):
        self.pulse_val += 0.08
        self.scan_angle = (self.scan_angle + 5) % 360
        
        # Parallax smoothing
        self.p_x += (self.target_p_x - self.p_x) * 0.1
        self.p_y += (self.target_p_y - self.p_y) * 0.1
        
        # 1. Apply Parallax shifts to individual layers
        # Background dots (slowest)
        for i, dot in enumerate(self.hex_dots):
            # Original coordinates for dots are relative to canvas (0,0)
            # The canvas itself is centered, so we need to adjust for that if we want true window-relative parallax.
            # For simplicity, let's assume the canvas's (0,0) is the reference for parallax.
            # The original dot creation uses 60 + i*45, 70 + j*45.
            # We need to extract the original coordinates to apply the shift.
            # The hex_dots list stores the canvas item IDs. We need to get their original positions.
            # A more robust way would be to store original coords with the item ID.
            # For now, let's re-calculate based on the loop structure.
            
            # Assuming 5x5 grid, i is 0-24.
            # row = i // 5, col = i % 5
            original_x = 60 + (i % 5) * 45
            original_y = 70 + (i // 5) * 45
            
            self.canvas.coords(dot, 
                               original_x + self.p_x * 0.2, 
                               original_y + self.p_y * 0.2, 
                               original_x + 2 + self.p_x * 0.2, 
                               original_y + 2 + self.p_y * 0.2)
            
            # Flicker dots
            if math.sin(self.pulse_val + i) > 0.8:
                self.canvas.itemconfig(dot, fill=self.primary_cyan)
            else:
                self.canvas.itemconfig(dot, fill=self.dim_cyan)

        # 2. Ring Rotations and Parallax
        # The rings are drawn around the canvas center (150, 150).
        # We need to shift their bounding box.
        
        # Update arcs based on usage
        cpu_extent = -(self.cpu_usage * 0.9) # arc grows counter-clockwise from 135
        cpu_color = self.alert_orange if self.cpu_usage < 80 else self.alert_red
        self.canvas.itemconfig(self.arc_cpu, extent=cpu_extent, outline=cpu_color)
        
        ram_extent = -(self.ram_usage * 0.9) # arc grows counter-clockwise from 225
        ram_color = self.secondary_teal if self.ram_usage < 80 else self.alert_red
        self.canvas.itemconfig(self.arc_ram, extent=ram_extent, outline=ram_color)

        # Apply parallax to the rings and arcs by shifting their coordinates
        # The rings are defined with (x1, y1, x2, y2) bounding boxes.
        # The center of the canvas is (150, 150) for a 300x320 canvas.
        # Let's define a helper to shift coordinates for canvas items.
        
        # Shift for rings (medium shift)
        ring_shift_x = self.p_x * 0.5
        ring_shift_y = self.p_y * 0.5

        # Update ring coordinates
        # Original: (30, 30, 270, 270) -> center (150, 150), radius 120
        # New: (30+sx, 30+sy, 270+sx, 270+sy)
        ring_coords = [
            (30, 30, 270, 270), # rings[0]
            (35, 35, 265, 265), # rings[1]
            (35, 35, 265, 265), # rings[2]
            (60, 60, 240, 240), # rings[3]
            (60, 60, 240, 240), # rings[4]
            (85, 85, 215, 215)  # rings[5]
        ]
        for i, ring_id in enumerate(self.rings):
            x1, y1, x2, y2 = ring_coords[i]
            self.canvas.coords(ring_id, x1 + ring_shift_x, y1 + ring_shift_y, x2 + ring_shift_x, y2 + ring_shift_y)
        
        # Scan line
        x1, y1, x2, y2 = (85, 85, 215, 215)
        self.canvas.coords(self.scan_line, x1 + ring_shift_x, y1 + ring_shift_y, x2 + ring_shift_x, y2 + ring_shift_y)

        # CPU/RAM arcs
        arc_cpu_coords = (20, 20, 280, 280)
        self.canvas.coords(self.arc_cpu, arc_cpu_coords[0] + ring_shift_x, arc_cpu_coords[1] + ring_shift_y,
                           arc_cpu_coords[2] + ring_shift_x, arc_cpu_coords[3] + ring_shift_y)
        arc_ram_coords = (15, 15, 285, 285)
        self.canvas.coords(self.arc_ram, arc_ram_coords[0] + ring_shift_x, arc_ram_coords[1] + ring_shift_y,
                           arc_ram_coords[2] + ring_shift_x, arc_ram_coords[3] + ring_shift_y)

        # Ring rotations (these are still applied to the shifted rings)
        self.canvas.itemconfig(self.rings[1], start=(self.scan_angle * 0.5) % 360)
        self.canvas.itemconfig(self.rings[2], start=(self.scan_angle * 0.5 + 180) % 360)
        self.canvas.itemconfig(self.rings[3], start=(90 - self.scan_angle * 0.8) % 360)
        self.canvas.itemconfig(self.rings[4], start=(270 - self.scan_angle * 0.8) % 360)
        self.canvas.itemconfig(self.scan_line, start=self.scan_angle)

        # 3. Core Pulse (fastest shift)
        core_shift_x = self.p_x * 0.8
        core_shift_y = self.p_y * 0.8
        
        pulse_scale = 1 + (math.sin(self.pulse_val) * 0.15)
        core_r = 40 * pulse_scale
        
        # Original center of core pulse is (150, 150)
        self.canvas.coords(self.core_circle, 
                           110 + core_shift_x, 110 + core_shift_y, 
                           190 + core_shift_x, 190 + core_shift_y)
        self.canvas.coords(self.inner_circle, 
                           150 - core_r/1.5 + core_shift_x, 150 - core_r/1.5 + core_shift_y, 
                           150 + core_r/1.5 + core_shift_x, 150 + core_r/1.5 + core_shift_y)
        
        # 4. Visualizer Bars Animation (Smooth Sine)
        # Bars are defined relative to canvas (0,0)
        bar_shift_x = self.p_x * 0.4
        bar_shift_y = self.p_y * 0.4

        for i, bar in enumerate(self.bars):
            h = 5 + abs(math.sin(self.pulse_val + i*0.4) * 25)
            x_base = 70 + (i * 10)
            y_base = 280 # The bottom of the bars
            self.canvas.coords(bar, 
                               x_base + bar_shift_x, 
                               y_base - h + bar_shift_y, 
                               x_base + 6 + bar_shift_x, 
                               y_base + bar_shift_y)
            
        # 5. Dynamic Color Intensity for inner circle
        color_int = int(180 + 75 * math.sin(self.pulse_val))
        hex_color = f"#{0:02x}{color_int:02x}{255:02x}"
        self.canvas.itemconfig(self.inner_circle, fill=hex_color)

        # Update CPU/RAM labels
        if len(self.data_labels) > 3: # Ensure labels exist
            self.data_labels[2].configure(text=f"CPU: {self.cpu_usage:.0f}%")
            self.data_labels[3].configure(text=f"RAM: {self.ram_usage:.0f}%")
        
        self.after(30, self.animate_hud)

    def on_engage(self):
        self.log_message("ACCESSING SPEECH CHANNEL...")
        self.status_label.configure(text="NETWORK STATUS: LISTENING", text_color=self.alert_orange)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    app = MavrickUI()
    app.mainloop()

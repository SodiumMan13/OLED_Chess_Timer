from machine import I2C, Pin, PWM
import ssd1306
import time

# --- HARDWARE PIN MAPPINGS ---
# Display (I2C1: Physical Pin 14 = GP10 for SDA, Physical Pin 15 = GP11 for SCL)
i2c = I2C(1, scl=Pin(11), sda=Pin(10), freq=400000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# 5 Buttons (Using internal pull-ups, pressed = 0)
btn_white = Pin(15, Pin.IN, Pin.PULL_UP)  # Pin 20 (GPIO 15) - White player button
btn_black = Pin(2, Pin.IN, Pin.PULL_UP)    # Pin 4  (GPIO 2)  - Black player button
btn_start = Pin(16, Pin.IN, Pin.PULL_UP)  # Pin 21 (GPIO 16) - Start / Pause button
btn_mode  = Pin(17, Pin.IN, Pin.PULL_UP)  # Pin 22 (GPIO 17) - Mode button
btn_adjust = Pin(18, Pin.IN, Pin.PULL_UP) # Pin 24 (GPIO 18) - Adjust button (Plus)

# Buzzer on Physical Pin 19 (GPIO 14)
buzzer = PWM(Pin(14))
buzzer.duty_u16(0)

def beep(freq=2000, duration_ms=100):
    """Play a short piezo beep if buzzer is enabled"""
    if buzzer_enabled:
        buzzer.freq(freq)
        buzzer.duty_u16(32768)
        time.sleep_ms(duration_ms)
        buzzer.duty_u16(0)

def long_buzz(duration_ms=2000):
    """Play a continuous buzz for time out"""
    if buzzer_enabled:
        buzzer.freq(800)
        buzzer.duty_u16(32768)
        time.sleep_ms(duration_ms)
        buzzer.duty_u16(0)

# --- CONFIG & GAME STATES ---
# States: CONFIG_BUZZER, CONFIG_MINUTES, CONFIG_SECONDS, CONFIG_INCREMENT, RUNNING, PAUSED, OVER
ui_state = "CONFIG_BUZZER"

buzzer_enabled = False
set_minutes = 10
set_seconds = 0
set_increment = 0

white_time = 600  # in seconds
black_time = 600  # in seconds
current_turn = "WHITE"

last_tick = time.ticks_ms()
blink_timer = time.ticks_ms()
blink_state = True

def format_time(seconds):
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def update_display():
    global blink_state
    display.fill(0)
    
    # Non-blocking blink toggle every 500ms
    if time.ticks_diff(time.ticks_ms(), blink_timer) > 500:
        blink_state = not blink_state
        globals()['blink_timer'] = time.ticks_ms()

    if ui_state == "CONFIG_BUZZER":
        # Show time and flashing buzzer status in top right
        display.text(f"{set_minutes:02d}:{set_seconds:02d}", 10, 25, 1)
        buzz_str = "on" if buzzer_enabled else "off"
        if blink_state:
            display.text(buzz_str, 96, 5, 1)
        display.text("MODE:Next ADJ:Buz", 0, 52, 1)

    elif ui_state == "CONFIG_MINUTES":
        # Minutes flashing
        m_str = f"{set_minutes:02d}" if blink_state else "  "
        display.text(f"{m_str}:{set_seconds:02d}", 10, 25, 1)
        display.text("SET MINUTES", 20, 5, 1)
        display.text("MODE:Next ADJ:+1", 0, 52, 1)

    elif ui_state == "CONFIG_SECONDS":
        # Seconds flashing
        s_str = f"{set_seconds:02d}" if blink_state else "  "
        display.text(f"{set_minutes:02d}:{s_str}", 10, 25, 1)
        display.text("SET SECONDS", 20, 5, 1)
        display.text("MODE:Next ADJ:+10", 0, 52, 1)

    elif ui_state == "CONFIG_INCREMENT":
        # Increment screen (+0 flashing)
        inc_str = f"+{set_increment}"
        if blink_state:
            display.text(inc_str, 48, 25, 1)
        else:
            display.text("  ", 48, 25, 1)
        display.text("INCREMENT (SEC)", 10, 5, 1)
        display.text("START:Play ADJ:+1", 0, 52, 1)

    elif ui_state in ["RUNNING", "PAUSED", "OVER"]:
        w_str = format_time(white_time)
        b_str = format_time(black_time)
        
        if ui_state == "RUNNING":
            w_display = w_str if (current_turn != "WHITE" or blink_state) else "  :  "
            b_display = b_str if (current_turn != "BLACK" or blink_state) else "  :  "
            status = "RUNNING"
        elif ui_state == "PAUSED":
            w_display = w_str
            b_display = b_str
            status = "PAUSED"
        else:
            w_display = w_str
            b_display = b_str
            status = "TIME OUT!"
            
        display.text(f"W: {w_display}", 10, 15, 1)
        display.text(f"B: {b_display}", 10, 35, 1)
        display.text(f"[{status}]", 28, 52, 1)

    display.show()

# Initial draw
update_display()

# --- MAIN LOOP ---
while True:
    update_display()
    
    # 1. START / PAUSE BUTTON
    if not btn_start.value():
        if ui_state in ["CONFIG_BUZZER", "CONFIG_MINUTES", "CONFIG_SECONDS", "CONFIG_INCREMENT"]:
            white_time = (set_minutes * 60) + set_seconds
            black_time = (set_minutes * 60) + set_seconds
            current_turn = "WHITE"
            ui_state = "RUNNING"
            beep(2500, 150)
            last_tick = time.ticks_ms()
            time.sleep(0.3)
        elif ui_state == "RUNNING":
            ui_state = "PAUSED"
            beep(1500, 100)
            time.sleep(0.3)
        elif ui_state == "PAUSED":
            ui_state = "RUNNING"
            beep(2000, 100)
            last_tick = time.ticks_ms() # Reset tick so paused time isn't subtracted
            time.sleep(0.3)
            
    # 2. CONFIG: BUZZER SCREEN
    if ui_state == "CONFIG_BUZZER":
        if not btn_adjust.value():
            buzzer_enabled = not buzzer_enabled
            if buzzer_enabled:
                beep(2000, 50)
            time.sleep(0.3)
            
        elif not btn_mode.value():
            ui_state = "CONFIG_MINUTES"
            beep(1800, 100)
            time.sleep(0.3)

    # 3. CONFIG: MINUTES SCREEN
    elif ui_state == "CONFIG_MINUTES":
        if not btn_adjust.value():
            if 10 <= set_minutes < 15:
                set_minutes += 1
            elif set_minutes == 15:
                set_minutes = 1
            else:
                set_minutes += 1
                if set_minutes > 10:
                    set_minutes = 10
            beep(1500, 40)
            time.sleep(0.3)
            
        elif not btn_mode.value():
            ui_state = "CONFIG_SECONDS"
            beep(1800, 100)
            time.sleep(0.3)

    # 4. CONFIG: SECONDS SCREEN
    elif ui_state == "CONFIG_SECONDS":
        if not btn_adjust.value():
            set_seconds = (set_seconds + 10) % 60
            beep(1600, 40)
            time.sleep(0.3)
            
        elif not btn_mode.value():
            ui_state = "CONFIG_INCREMENT"
            beep(1800, 100)
            time.sleep(0.3)

    # 5. CONFIG: INCREMENT SCREEN
    elif ui_state == "CONFIG_INCREMENT":
        if not btn_adjust.value():
            set_increment = (set_increment + 1) if set_increment < 10 else 0
            beep(1700, 40)
            time.sleep(0.3)
            
        elif not btn_mode.value():
            ui_state = "CONFIG_BUZZER"
            beep(1200, 100)
            time.sleep(0.3)

    # 6. RUNNING GAMEPLAY
    elif ui_state == "RUNNING":
        now = time.ticks_ms()
        
        if not btn_white.value():
            if current_turn == "WHITE":
                white_time += set_increment
                current_turn = "BLACK"
                beep(2000, 60)
                time.sleep(0.2)
                
        if not btn_black.value():
            if current_turn == "BLACK":
                black_time += set_increment
                current_turn = "WHITE"
                beep(2000, 60)
                time.sleep(0.2)
                
        if time.ticks_diff(now, last_tick) >= 1000:
            last_tick = now
            if current_turn == "WHITE":
                if white_time > 0:
                    white_time -= 1
                    if white_time == 0:
                        ui_state = "OVER"
                        long_buzz(2000)
                        ui_state = "CONFIG_BUZZER"
            else:
                if black_time > 0:
                    black_time -= 1
                    if black_time == 0:
                        ui_state = "OVER"
                        long_buzz(2000)
                        ui_state = "CONFIG_BUZZER"

    time.sleep_ms(20)
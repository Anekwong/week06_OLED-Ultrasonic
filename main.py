from machine import Pin, I2C, time_pulse_us
from time import sleep_ms, sleep_us, ticks_ms, ticks_diff
import ssd1306

# ---------- ค่าตั้ง ----------
THRESHOLD_CM   = 30      # ใกล้กว่านี้ถือว่า "ตรวจพบวัตถุ"
MAX_CM         = 100     # ระยะเต็มสเกลของแถบกราฟ
MIN_CM         = 5       # ใกล้กว่านี้ = กะพริบเร็วสุด
SLOW_BLINK_MS  = 500     # คาบกะพริบเมื่อเพิ่งเข้าเขต (ช้าสุด)
FAST_BLINK_MS  = 60      # คาบกะพริบเมื่อใกล้สุด (เร็วสุด)
MEASURE_MS     = 60      # อ่านเซนเซอร์ทุกกี่ ms
TIMEOUT_US     = 30000   # ~5 m

# ---------- อุปกรณ์ ----------
i2c  = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

trig = Pin(16, Pin.OUT)
echo = Pin(17, Pin.IN)
led  = Pin(19, Pin.OUT)

BAR_X, BAR_Y, BAR_W, BAR_H = 0, 40, 128, 12


def read_distance_cm():
    """คืนค่าระยะ (cm) หรือ None ถ้าอ่านไม่ได้"""
    trig.value(0)
    sleep_us(2)
    trig.value(1)
    sleep_us(10)
    trig.value(0)

    t = time_pulse_us(echo, 1, TIMEOUT_US)
    if t < 0:
        return None
    return t * 0.0343 / 2


def blink_period(dist):
    """ยิ่งใกล้ ยิ่งคาบสั้น (กะพริบเร็ว) แบบเชิงเส้น"""
    d = max(MIN_CM, min(THRESHOLD_CM, dist))
    ratio = (d - MIN_CM) / (THRESHOLD_CM - MIN_CM)   # 0 = ใกล้สุด, 1 = ขอบเขต
    return int(FAST_BLINK_MS + ratio * (SLOW_BLINK_MS - FAST_BLINK_MS))


def show(dist, detected):
    oled.fill(0)
    oled.text("Ultrasonic", 0, 0)
    if dist is None:
        oled.text("Dist: --- cm", 0, 16)
    else:
        oled.text("Dist: {:.1f} cm".format(dist), 0, 16)
    oled.text("Object: " + ("YES" if detected else "NO"), 0, 28)

    # แถบกราฟ: ยิ่งใกล้ ยิ่งยาว
    oled.rect(BAR_X, BAR_Y, BAR_W, BAR_H, 1)
    if dist is not None:
        d = min(dist, MAX_CM)
        fill = int((1 - d / MAX_CM) * (BAR_W - 4))
        if fill > 0:
            oled.fill_rect(BAR_X + 2, BAR_Y + 2, fill, BAR_H - 4, 1)
    # เส้นขีดบอกตำแหน่ง THRESHOLD
    tx = BAR_X + 2 + int((1 - THRESHOLD_CM / MAX_CM) * (BAR_W - 4))
    oled.vline(tx, BAR_Y + BAR_H, 4, 1)
    oled.text("far", 0, 56)
    oled.text("near", 96, 56)
    oled.show()


dist = None
detected = False
period = SLOW_BLINK_MS
led_on = False
last_measure = ticks_ms()
last_toggle = last_measure

while True:
    now = ticks_ms()

    # --- อ่านระยะ + อัปเดตจอ ---
    if ticks_diff(now, last_measure) >= MEASURE_MS:
        last_measure = now
        dist = read_distance_cm()
        detected = dist is not None and dist <= THRESHOLD_CM
        if detected:
            period = blink_period(dist)
        show(dist, detected)

    # --- กะพริบ LED แบบไม่บล็อก ---
    if detected:
        if ticks_diff(now, last_toggle) >= period // 2:
            last_toggle = now
            led_on = not led_on
            led.value(led_on)
    else:
        led_on = False
        led.value(0)

    sleep_ms(5)

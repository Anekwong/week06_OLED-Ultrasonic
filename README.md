# Raspberry Pi Pico 2 – OLED + Ultrasonic (HC-SR04) + LED

เมื่อเซนเซอร์ Ultrasonic ตรวจพบวัตถุ → LED ติด และแสดงค่าระยะทางบนจอ OLED

## อุปกรณ์

| อุปกรณ์ | จำนวน |
|---|---|
| Raspberry Pi Pico 2 (RP2350) | 1 |
| OLED I2C 128x64 (SSD1306) | 1 |
| Ultrasonic HC-SR04 | 1 |
| LED | 1 |
| ตัวต้านทาน 220–330 Ω (จำกัดกระแส LED) | 1 |
| ตัวต้านทาน 1 kΩ และ 2 kΩ (วงจรแบ่งแรงดัน ECHO) | อย่างละ 1 |
| Breadboard + สายจัมเปอร์ | – |

## การต่อสาย

### OLED Display (I2C0)

| OLED | Pico 2 | Pin |
|---|---|---|
| GND | GND | 38 |
| VCC | 3V3 (OUT) | 36 |
| SCL | GP5 | 7 |
| SDA | GP4 | 6 |

### Ultrasonic HC-SR04

| HC-SR04 | Pico 2 | Pin |
|---|---|---|
| VCC | VBUS (5V) | 40 |
| TRIG | GP16 | 21 |
| ECHO | GP17 (ผ่านวงจรแบ่งแรงดัน) | 22 |
| GND | GND | 38 |

### LED

| LED | Pico 2 | Pin |
|---|---|---|
| Anode (+) ผ่านตัวต้านทาน 220–330 Ω | GP19 | 25 |
| Cathode (–) | GND | – |

### วงจรแบ่งแรงดันสำหรับ ECHO

HC-SR04 ส่งสัญญาณ ECHO ที่ระดับ **5 V** แต่ GPIO ของ Pico รับได้สูงสุด **3.3 V** จึงต้องลดแรงดันก่อนเข้า GP17:

```
HC-SR04 ECHO ──[ R1 = 1 kΩ ]──┬──── GP17 (Pin 22)
                              │
                         [ R2 = 2 kΩ ]
                              │
                             GND

V_GP17 = 5 V × 2k / (1k + 2k) ≈ 3.33 V
```

### แผนผังรวม

```
                 Raspberry Pi Pico 2
              ┌──────────────────────┐
 OLED SDA ────┤ GP4  (6)             │
 OLED SCL ────┤ GP5  (7)             │
 TRIG     ────┤ GP16 (21)            │
 ECHO(÷)  ────┤ GP17 (22)            │
 LED(+R)  ────┤ GP19 (25)            │
 OLED VCC ────┤ 3V3  (36)            │
 GND      ────┤ GND  (38)            │
 HC-SR04  ────┤ VBUS (40)            │
 VCC          └──────────────────────┘
```

> GND ของทุกอุปกรณ์ (OLED, HC-SR04, LED) ต้องต่อร่วมกับ GND ของ Pico

## หลักการทำงาน

1. ส่งพัลส์ TRIG 10 µs
2. วัดความกว้างพัลส์ ECHO → คำนวณระยะ `distance (cm) = pulse_us × 0.0343 / 2`
3. ถ้าระยะ ≤ `THRESHOLD_CM` (ตรวจพบวัตถุ) → LED กะพริบ โดย **ยิ่งใกล้ ยิ่งกะพริบเร็ว**
   - ที่ขอบเขต 30 cm คาบ ≈ 500 ms (ช้าสุด)
   - ที่ ≤ 5 cm คาบ ≈ 60 ms (เร็วสุด)
4. ถ้าไม่พบวัตถุ → LED ดับ
5. จอ OLED แสดงค่าระยะ สถานะวัตถุ และ **แถบกราฟระยะ** (ยิ่งใกล้ แถบยิ่งยาว, สเกลเต็ม 100 cm, ขีดเล็กใต้แถบบอกตำแหน่ง 30 cm)

การกะพริบ LED ใช้ `ticks_ms` แบบไม่บล็อก จึงไม่หน่วงการอ่านเซนเซอร์และการอัปเดตจอ
ปรับพฤติกรรมได้ที่ค่าคงที่ต้นไฟล์: `THRESHOLD_CM`, `MAX_CM`, `MIN_CM`, `SLOW_BLINK_MS`, `FAST_BLINK_MS`

## โค้ด MicroPython

ต้องมีไลบรารี `ssd1306.py` บนบอร์ด (ติดตั้งผ่าน Thonny: *Tools → Manage packages → ssd1306* หรือ `mip.install("ssd1306")`)

`main.py`

```python
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
```

## ขั้นตอนทดสอบ

1. ต่อวงจรตามตารางด้านบน (ตรวจวงจรแบ่งแรงดัน ECHO ให้ดี)
2. ใส่ `ssd1306.py` และ `main.py` ลง Pico 2 ด้วย Thonny
3. รันโปรแกรม → จอ OLED แสดงระยะทางและแถบกราฟ
4. นำมือ/วัตถุเข้าใกล้ภายใน 30 cm → LED กะพริบ และจอแสดง `Object: YES` ยิ่งเข้าใกล้ LED ยิ่งกะพริบเร็ว แถบกราฟยิ่งยาว
5. เอาวัตถุออก → LED ดับ

## แก้ปัญหาเบื้องต้น

| อาการ | สาเหตุที่เป็นไปได้ |
|---|---|
| จอ OLED ไม่ติด | สลับ SDA/SCL, ที่อยู่ I2C ไม่ใช่ `0x3C` (ตรวจด้วย `i2c.scan()`) |
| ระยะแสดง `---` | ECHO ไม่ถึง GP17, VCC ของ HC-SR04 ไม่ได้ 5 V |
| ค่าระยะเพี้ยน/กระโดด | GND ไม่ร่วมกัน, วัตถุเอียงหรือดูดซับเสียง |
| LED ไม่ติด | ขั้ว LED กลับด้าน, ลืมตัวต้านทาน, ต่อผิดขา GP19 |

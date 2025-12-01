import os
import board

LED_COUNT = int(os.getenv("LED_COUNT", 300))
LED_PIN = getattr(board, os.getenv("LED_PIN", "D18"))

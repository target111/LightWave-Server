from lib.server import LightWave
from lib.config import LED_COUNT, LED_PIN
from lib.led import LED, EffectRegistry

app = LightWave(LED(LED_PIN, LED_COUNT), EffectRegistry())
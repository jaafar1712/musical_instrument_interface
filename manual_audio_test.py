"""Quick test to verify audio is working"""
from audio_synth import SimpleSynth
import time

print("Testing audio synth...")
synth = SimpleSynth()

if synth.enabled:
    print("Audio synth available!")
    print("Playing note 60 (Middle C - 262 Hz)...")
    synth.note_on(60, 100)
    time.sleep(2)
    print("Stopping note...")
    synth.note_off(60)
    time.sleep(0.5)

    print("Playing note 64 (E - 330 Hz)...")
    synth.note_on(64, 100)
    time.sleep(2)
    print("Stopping note...")
    synth.note_off(64)

    print("Test complete!")
else:
    print("Audio NOT available - audio won't work")

synth.close()

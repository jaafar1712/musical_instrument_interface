"""
Professional real-time audio synthesizer with genre presets and effects.
Supports Jazz, Rock, Metal, Classical, Electronic, and Ambient styles.
"""

import numpy as np
import sounddevice as sd
from threading import Lock
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class ADSREnvelope:
    """Attack, Decay, Sustain, Release envelope"""
    attack: float = 0.01   # seconds
    decay: float = 0.1     # seconds
    sustain: float = 0.7   # level 0-1
    release: float = 0.2   # seconds
    
class GenrePreset:
    """Musical genre characteristics"""
    
    PRESETS = {
        'jazz': {
            'name': 'Jazz',
            'scale': [0, 2, 3, 5, 7, 9, 10],  # Minor blues scale
            'waveforms': ['sine', 'triangle'],
            'envelope': ADSREnvelope(attack=0.02, decay=0.15, sustain=0.6, release=0.3),
            'reverb': 0.4,
            'harmonics': [1.0, 0.3, 0.2, 0.15, 0.1],  # Warm, rich harmonics
            'vibrato_rate': 5.5,
            'vibrato_depth': 0.015,
            'filter_cutoff': 0.7,
            'description': 'Smooth, warm tones with rich harmonics'
        },
        'rock': {
            'name': 'Rock & Roll',
            'scale': [0, 2, 4, 5, 7, 9, 11],  # Major pentatonic
            'waveforms': ['square', 'sawtooth'],
            'envelope': ADSREnvelope(attack=0.005, decay=0.08, sustain=0.8, release=0.15),
            'reverb': 0.3,
            'harmonics': [1.0, 0.6, 0.4, 0.3, 0.2, 0.15],  # Bright, edgy
            'vibrato_rate': 6.0,
            'vibrato_depth': 0.02,
            'filter_cutoff': 0.8,
            'description': 'Punchy, energetic tones with sustain'
        },
        'metal': {
            'name': 'Heavy Metal',
            'scale': [0, 2, 3, 5, 7, 8, 10],  # Natural minor
            'waveforms': ['square', 'pulse'],
            'envelope': ADSREnvelope(attack=0.001, decay=0.05, sustain=0.9, release=0.1),
            'reverb': 0.5,
            'harmonics': [1.0, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3],  # Very aggressive
            'vibrato_rate': 0,
            'vibrato_depth': 0,
            'filter_cutoff': 0.95,
            'description': 'Aggressive, distorted tones with heavy sustain'
        },
        'classical': {
            'name': 'Classical',
            'scale': [0, 2, 4, 5, 7, 9, 11],  # Major scale
            'waveforms': ['sine', 'triangle'],
            'envelope': ADSREnvelope(attack=0.05, decay=0.2, sustain=0.5, release=0.4),
            'reverb': 0.6,
            'harmonics': [1.0, 0.4, 0.25, 0.15, 0.1, 0.05],  # Pure, elegant
            'vibrato_rate': 4.5,
            'vibrato_depth': 0.012,
            'filter_cutoff': 0.75,
            'description': 'Pure, elegant tones with natural decay'
        },
        'electronic': {
            'name': 'Electronic',
            'scale': [0, 2, 4, 7, 9],  # Major pentatonic
            'waveforms': ['square', 'sawtooth', 'pulse'],
            'envelope': ADSREnvelope(attack=0.001, decay=0.12, sustain=0.7, release=0.25),
            'reverb': 0.45,
            'harmonics': [1.0, 0.5, 0.6, 0.4, 0.3, 0.25, 0.2],  # Synthetic
            'vibrato_rate': 7.0,
            'vibrato_depth': 0.025,
            'filter_cutoff': 0.85,
            'description': 'Synthetic, digital tones with character'
        },
        'ambient': {
            'name': 'Ambient',
            'scale': [0, 2, 4, 7, 9, 11],  # Major 6th
            'waveforms': ['sine', 'triangle'],
            'envelope': ADSREnvelope(attack=0.3, decay=0.4, sustain=0.4, release=0.8),
            'reverb': 0.8,
            'harmonics': [1.0, 0.25, 0.2, 0.15, 0.1, 0.08, 0.05],  # Ethereal
            'vibrato_rate': 3.0,
            'vibrato_depth': 0.01,
            'filter_cutoff': 0.6,
            'description': 'Ethereal, atmospheric soundscapes'
        }
    }

class Voice:
    """Individual synthesizer voice with envelope and effects"""
    
    def __init__(self, freq, velocity, preset, sample_rate=44100):
        self.freq = freq
        self.velocity = velocity / 127.0
        self.preset = preset
        self.sample_rate = sample_rate
        self.phase = 0.0
        self.age = 0.0  # Voice age in seconds
        self.released = False
        self.release_age = 0.0
        
    def generate(self, num_samples, waveform_type='sine'):
        """Generate audio samples with envelope and effects"""
        dt = 1.0 / self.sample_rate
        envelope = self.preset['envelope']
        
        # Calculate envelope value
        if not self.released:
            if self.age < envelope.attack:
                # Attack phase
                env_value = self.age / envelope.attack
            elif self.age < envelope.attack + envelope.decay:
                # Decay phase
                decay_progress = (self.age - envelope.attack) / envelope.decay
                env_value = 1.0 - (1.0 - envelope.sustain) * decay_progress
            else:
                # Sustain phase
                env_value = envelope.sustain
        else:
            # Release phase
            if self.release_age < envelope.release:
                release_progress = self.release_age / envelope.release
                env_value = envelope.sustain * (1.0 - release_progress)
            else:
                env_value = 0.0
        
        # Generate base waveform with harmonics
        output = np.zeros(num_samples, dtype=np.float32)
        harmonics = self.preset['harmonics']
        
        for harmonic_num, amplitude in enumerate(harmonics, 1):
            freq = self.freq * harmonic_num
            
            # Add vibrato
            vibrato_rate = self.preset.get('vibrato_rate', 0)
            vibrato_depth = self.preset.get('vibrato_depth', 0)
            if vibrato_rate > 0:
                vibrato = np.sin(2 * np.pi * vibrato_rate * self.age) * vibrato_depth
                freq = freq * (1.0 + vibrato)
            
            phase_increment = freq / self.sample_rate
            phases = (self.phase + np.arange(num_samples) * phase_increment) % 1.0
            
            # Generate waveform
            if waveform_type == 'sine':
                wave = np.sin(2 * np.pi * phases)
            elif waveform_type == 'square':
                wave = np.sign(np.sin(2 * np.pi * phases))
            elif waveform_type == 'sawtooth':
                wave = 2 * (phases - np.floor(phases + 0.5))
            elif waveform_type == 'triangle':
                wave = 2 * np.abs(2 * (phases - np.floor(phases + 0.5))) - 1
            elif waveform_type == 'pulse':
                wave = np.where((phases % 1.0) < 0.3, 1.0, -1.0)
            else:
                wave = np.sin(2 * np.pi * phases)
            
            output += wave * amplitude / harmonic_num  # Scale by harmonic number
            self.phase = phases[-1]
        
        # Apply envelope and velocity
        output *= env_value * self.velocity * 0.3
        
        # Update age
        self.age += num_samples * dt
        if self.released:
            self.release_age += num_samples * dt
        
        return output
    
    def is_finished(self):
        """Check if voice has finished (after release)"""
        if self.released:
            return self.release_age >= self.preset['envelope'].release
        return False

class RealtimeSynth:
    """Real-time polyphonic synthesizer with genre presets"""
    
    def __init__(self, sample_rate=44100, block_size=512):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.lock = Lock()
        
        # Set default genre
        self.current_genre = 'jazz'
        self.preset = GenrePreset.PRESETS[self.current_genre]
        
        # Active voices
        self.voices: Dict[str, Voice] = {}
        
        # Reverb buffer (simple delay-based reverb)
        self.reverb_buffer = np.zeros(int(sample_rate * 0.2), dtype=np.float32)
        self.reverb_index = 0
        
        # Start audio stream
        try:
            self.stream = sd.OutputStream(
                samplerate=sample_rate,
                blocksize=block_size,
                channels=1,
                callback=self._audio_callback,
                latency='low'
            )
            self.stream.start()
            self.enabled = True
        except Exception as e:
            print(f"Failed to start audio: {e}")
            self.stream = None
            self.enabled = False
    
    def set_genre(self, genre_name):
        """Change the current musical genre"""
        if genre_name in GenrePreset.PRESETS:
            with self.lock:
                self.current_genre = genre_name
                self.preset = GenrePreset.PRESETS[genre_name]
                # Clear all voices when changing genre
                self.voices.clear()
    
    def get_genre_list(self):
        """Get list of available genres"""
        return [(key, preset['name'], preset['description']) 
                for key, preset in GenrePreset.PRESETS.items()]
    
    def _audio_callback(self, outdata, frames, time_info, status):
        """Real-time audio callback"""
        with self.lock:
            output = np.zeros(frames, dtype=np.float32)
            
            # Get waveform types for current genre
            waveforms = self.preset['waveforms']
            
            # Mix all active voices
            voices_to_remove = []
            for voice_id, voice in self.voices.items():
                # Alternate waveforms based on voice
                waveform_idx = hash(voice_id) % len(waveforms)
                waveform = waveforms[waveform_idx]
                
                # Generate audio
                voice_output = voice.generate(frames, waveform)
                output += voice_output
                
                # Mark finished voices for removal
                if voice.is_finished():
                    voices_to_remove.append(voice_id)
            
            # Remove finished voices
            for voice_id in voices_to_remove:
                del self.voices[voice_id]
            
            # Apply simple reverb
            reverb_amount = self.preset['reverb']
            for i in range(frames):
                # Read from reverb buffer
                reverb_sample = self.reverb_buffer[self.reverb_index]
                
                # Add reverb to output
                output[i] += reverb_sample * reverb_amount * 0.3
                
                # Write to reverb buffer with feedback
                self.reverb_buffer[self.reverb_index] = output[i] * 0.5
                
                # Advance reverb index
                self.reverb_index = (self.reverb_index + 1) % len(self.reverb_buffer)
            
            # Soft limiting
            output = np.tanh(output * 0.6)
            
            outdata[:, 0] = output
    
    def midi_to_freq(self, note):
        """Convert MIDI note to frequency"""
        return 440.0 * (2.0 ** ((note - 69) / 12.0))
    
    def quantize_to_scale(self, note):
        """Quantize note to current genre's scale"""
        scale = self.preset['scale']
        octave = note // 12
        pitch_class = note % 12
        
        # Find nearest note in scale
        closest = min(scale, key=lambda x: abs(x - pitch_class))
        return octave * 12 + closest
    
    def note_on(self, note, velocity=127, instrument='fsr0'):
        """Start a voice"""
        # Quantize to musical scale
        note = self.quantize_to_scale(note)
        
        voice_id = f"{instrument}_{note}"
        freq = self.midi_to_freq(note)
        
        with self.lock:
            self.voices[voice_id] = Voice(freq, velocity, self.preset, self.sample_rate)
    
    def note_off(self, note, instrument='fsr0'):
        """Release a voice"""
        note = self.quantize_to_scale(note)
        voice_id = f"{instrument}_{note}"
        
        with self.lock:
            if voice_id in self.voices:
                self.voices[voice_id].released = True
    
    def all_notes_off(self):
        """Stop all voices immediately"""
        with self.lock:
            self.voices.clear()
    
    def close(self):
        """Clean up"""
        self.all_notes_off()
        if self.stream:
            self.stream.stop()
            self.stream.close()

# Backwards compatibility
class SimpleSynth:
    def __init__(self):
        try:
            self.synth = RealtimeSynth()
            self.enabled = True
        except Exception as e:
            print(f"Audio init failed: {e}")
            self.synth = None
            self.enabled = False
    
    def set_genre(self, genre):
        if self.enabled and self.synth:
            self.synth.set_genre(genre)
    
    def get_genre_list(self):
        if self.enabled and self.synth:
            return self.synth.get_genre_list()
        return []
    
    def note_on(self, note, velocity=127, instrument='fsr0'):
        if self.enabled and self.synth:
            self.synth.note_on(note, velocity, instrument)
    
    def note_off(self, note, instrument='fsr0'):
        if self.enabled and self.synth:
            self.synth.note_off(note, instrument)
    
    def all_notes_off(self):
        if self.enabled and self.synth:
            self.synth.all_notes_off()
    
    def close(self):
        if self.enabled and self.synth:
            self.synth.close()

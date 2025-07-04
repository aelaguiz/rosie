#!/usr/bin/env python3
"""Simple real-time speech to text demo using RealtimeSTT"""

import os
import pyaudio
from dotenv import load_dotenv
from RealtimeSTT import AudioToTextRecorder
from thought_detector import ThoughtCompletionDetector

# Load environment variables from .env file
load_dotenv()

def create_process_text_callback(detector):
    """Create a process_text callback with access to the detector"""
    def process_text(text):
        """Callback function that gets called with transcribed text"""
        # Show real-time transcription
        print(f"\r{text}", end='', flush=True)
        
        # Check for complete thoughts
        result = detector.process_text(text)
        if result:
            complete_thought, analysis = result
            # Clear the current line and show the complete thought
            print("\r" + " " * len(text) + "\r", end='', flush=True)
            print(detector.format_complete_thought(complete_thought))
    
    return process_text

def on_recording_start():
    """Called when recording starts"""
    print("\n[Recording...]", end='', flush=True)

def on_recording_stop():
    """Called when recording stops"""
    print("\n[Processing...]", end='', flush=True)

def get_microphone_info(device_index=None):
    """Get information about the microphone being used"""
    p = pyaudio.PyAudio()
    try:
        if device_index is None:
            # Get default input device
            info = p.get_default_input_device_info()
        else:
            # Get specified device
            info = p.get_device_info_by_index(device_index)
        return info['name'], info['index']
    finally:
        p.terminate()

def main():
    # Get microphone info
    input_device_index = None  # None means default device
    mic_name, mic_index = get_microphone_info(input_device_index)
    
    # Initialize the thought detector with parallel processing
    print("Initializing thought detection with parallel processing (3 workers)...")
    detector = ThoughtCompletionDetector(debug=False, max_workers=3)
    
    # Initialize the recorder
    print("Initializing speech-to-text...")
    print(f"Using microphone: {mic_name} (device #{mic_index})")
    print("-" * 50)
    
    # Create the callback with access to the detector
    process_text = create_process_text_callback(detector)
    
    recorder = AudioToTextRecorder(
        spinner=False,
        model="tiny",  # Use tiny model for faster processing
        language="en",
        on_recording_start=on_recording_start,
        on_recording_stop=on_recording_stop,
        silero_sensitivity=0.4,
        webrtc_sensitivity=3,
        post_speech_silence_duration=0.7,
        min_length_of_recording=0.5,
        min_gap_between_recordings=0.3,
        enable_realtime_transcription=True,
        realtime_processing_pause=0.2,
        realtime_model_type="tiny",
        on_realtime_transcription_update=process_text,
    )
    
    print("Ready! Start speaking...")
    print("Press Ctrl+C to exit\n")
    print("Complete thoughts will appear in green 💭\n")
    
    try:
        while True:
            # This will continuously listen and transcribe
            recorder.text()
            print()  # New line after each sentence
    except KeyboardInterrupt:
        print("\n\nStopping...")
        detector.stop()
        recorder.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()
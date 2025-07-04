#!/usr/bin/env python3
"""Complete thoughts only display with status indicator - MVP version"""

import os
import threading
import pyaudio
from datetime import datetime
from dotenv import load_dotenv
from RealtimeSTT import AudioToTextRecorder
from thought_detector import ThoughtCompletionDetector

# Load environment variables from .env file
load_dotenv()

# Global status management
status_lock = threading.Lock()
current_status = ""

def update_status(message):
    """Update the status line with thread safety"""
    global current_status
    with status_lock:
        # DEBUG: Log status change
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n[DEBUG {timestamp}] Status change: {current_status} -> {message}")
        
        # Clear previous line and show new status
        clear_line = "\r" + " " * 80 + "\r"
        print(f"{clear_line}[Status] {message}", end='', flush=True)
        current_status = message

def create_process_text_callback(detector):
    """Create a process_text callback with access to the detector"""
    def process_text(text):
        """Callback function that gets called with transcribed text"""
        # DEBUG: Log callback invocation
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n[DEBUG {timestamp}] process_text called with: '{text}' (len={len(text)})")
        
        # Update status to show we're analyzing
        if text.strip():  # Only update if there's actual text
            update_status("🤔 Analyzing...")
        
        # Check for complete thoughts
        result = detector.process_text(text)
        print(f"[DEBUG {timestamp}] Thought detection result: {result}")
        
        if result:
            complete_thought, analysis = result
            print(f"[DEBUG {timestamp}] Complete thought detected: '{complete_thought}'")
            print(f"[DEBUG {timestamp}] Analysis: is_complete={analysis.is_complete}, confidence={analysis.confidence}")
            
            # Clear the status line completely
            print("\r" + " " * 80 + "\r", end='', flush=True)
            # Show the complete thought
            print(detector.format_complete_thought(complete_thought))
            # Return to listening status
            update_status("🎤 Listening...")
    
    return process_text

def on_recording_start():
    """Called when recording starts"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[DEBUG {timestamp}] on_recording_start called")
    update_status("🔴 Recording...")

def on_recording_stop():
    """Called when recording stops"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[DEBUG {timestamp}] on_recording_stop called")
    update_status("🤔 Analyzing...")

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
    
    # Initialize the thought detector
    print("Initializing thought detection...")
    print("[DEBUG] Setting ThoughtCompletionDetector debug=True")
    detector = ThoughtCompletionDetector(debug=True)
    
    # Initialize the recorder
    print("Initializing speech-to-text...")
    print(f"Using microphone: {mic_name} (device #{mic_index})")
    print("-" * 50)
    
    # Create the callback with access to the detector
    process_text = create_process_text_callback(detector)
    
    print("\n[DEBUG] Creating AudioToTextRecorder with:")
    print("  - enable_realtime_transcription: True")
    print("  - on_realtime_transcription_update: process_text callback")
    print("  - silero_sensitivity: 0.4")
    print("  - post_speech_silence_duration: 0.7")
    
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
    print("Press Ctrl+C to exit")
    print("Complete thoughts will appear in green 💭")
    print("-" * 50)
    
    # Set initial status
    print("\n[DEBUG] Setting initial status...")
    update_status("🎤 Listening...")
    
    try:
        while True:
            # This will continuously listen and transcribe
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n[DEBUG {timestamp}] Calling recorder.text() - waiting for speech...")
            result = recorder.text()
            print(f"[DEBUG {timestamp}] recorder.text() returned: '{result}'")
            # Status is maintained, no extra newline needed
    except KeyboardInterrupt:
        # Clear status line before exit messages
        print("\r" + " " * 80 + "\r", end='', flush=True)
        print("\nStopping...")
        detector.stop()
        recorder.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()
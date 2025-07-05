#!/usr/bin/env python3
"""Complete thoughts only display with status indicator - MVP version"""

import os
import argparse
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

def create_process_text_callback(realtime_model):
    """Create a process_text callback for real-time status updates only"""
    def process_text(text):
        """Callback function that gets called with transcribed text"""
        # DEBUG: Log callback invocation
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n[DEBUG {timestamp}] Real-time transcription: '{text}' (len={len(text)}) [model: {realtime_model}]")
        
        # Just update status to show we're transcribing
        if text.strip():  # Only update if there's actual text
            update_status("🔊 Transcribing...")
    
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

def list_microphones():
    """List all available microphones"""
    p = pyaudio.PyAudio()
    try:
        # Get default device index
        try:
            default_device = p.get_default_input_device_info()['index']
        except:
            default_device = None
        
        print("\nAvailable microphones:")
        print("-" * 60)
        
        found_devices = False
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            # Only show devices with input channels
            if device_info.get('maxInputChannels', 0) > 0:
                found_devices = True
                name = device_info['name']
                channels = device_info['maxInputChannels']
                default_marker = " (DEFAULT)" if i == default_device else ""
                print(f"Device #{i}: {name} (Channels: {channels}){default_marker}")
        
        if not found_devices:
            print("No input devices found!")
        
        print("-" * 60)
    finally:
        p.terminate()

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

def handle_complete_thought(detector, thought, analysis):
    """Handle complete thought detection via callback"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[DEBUG {timestamp}] Complete thought callback triggered!")
    print(f"[DEBUG {timestamp}] Complete thought: '{thought}'")
    print(f"[DEBUG {timestamp}] Analysis: is_complete={analysis.is_complete}, confidence={analysis.confidence}")
    
    # Clear the status line completely
    print("\r" + " " * 80 + "\r", end='', flush=True)
    # Show the complete thought
    print(detector.format_complete_thought(thought))
    # Return to listening status
    update_status("🎤 Listening...")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Complete thoughts speech-to-text with thought detection')
    parser.add_argument('--list', action='store_true', help='List all available microphones')
    parser.add_argument('--mic', type=int, help='Microphone device index to use')
    parser.add_argument('--model', type=str, default='tiny', 
                        help='Whisper model for final transcription (tiny, base, small, medium, large-v1, large-v2)')
    parser.add_argument('--realtime-model', type=str, default=None,
                        help='Whisper model for realtime transcription (defaults to same as --model)')
    args = parser.parse_args()
    
    # Set realtime model to match main model if not specified
    if args.realtime_model is None:
        args.realtime_model = args.model
    
    # Handle --list option
    if args.list:
        list_microphones()
        return
    
    # Get microphone info
    input_device_index = args.mic  # None means default device
    mic_name, mic_index = get_microphone_info(input_device_index)
    
    # Initialize the thought detector
    print("Initializing thought detection...")
    print("[DEBUG] Setting ThoughtCompletionDetector debug=True")
    
    # Create detector with callback
    detector = ThoughtCompletionDetector(
        debug=True,
        on_thought_complete=lambda thought, analysis: handle_complete_thought(detector, thought, analysis)
    )
    
    # Initialize the recorder
    print("Initializing speech-to-text...")
    print(f"Using microphone: {mic_name} (device #{mic_index})")
    print(f"Using Whisper model: {args.model} (realtime: {args.realtime_model})")
    print("-" * 50)
    
    # Create the callback for real-time status updates
    process_text = create_process_text_callback(args.realtime_model)
    
    print("\n[DEBUG] Creating AudioToTextRecorder with:")
    print(f"  - model: {args.model}")
    print(f"  - realtime_model_type: {args.realtime_model}")
    print("  - enable_realtime_transcription: True")
    print("  - on_realtime_transcription_update: process_text callback")
    print("  - silero_sensitivity: 0.4")
    print("  - post_speech_silence_duration: 0.7")
    
    recorder = AudioToTextRecorder(
        spinner=False,
        model=args.model,  # Use command line specified model
        language="en",
        input_device_index=input_device_index,
        on_recording_start=on_recording_start,
        on_recording_stop=on_recording_stop,
        silero_sensitivity=0.4,
        webrtc_sensitivity=3,
        post_speech_silence_duration=0.7,
        min_length_of_recording=0.5,
        min_gap_between_recordings=0.3,
        enable_realtime_transcription=True,
        realtime_processing_pause=0.2,
        realtime_model_type=args.realtime_model,  # Use command line specified realtime model
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
            # Reset to listening status
            update_status("🎤 Listening...")
            
            # This will continuously listen and transcribe
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n[DEBUG {timestamp}] Calling recorder.text() - waiting for speech... [model: {args.model}]")
            result = recorder.text()
            print(f"[DEBUG {timestamp}] recorder.text() returned: '{result}' [model: {args.model}]")
            
            # Now analyze the final transcription for complete thoughts
            if result and result.strip():
                update_status("🤔 Analyzing final transcription...")
                
                # Send final transcription to thought detector
                thought_result = detector.process_text(result)
                print(f"[DEBUG {timestamp}] Final thought detection result: {thought_result}")
                
                if not thought_result:
                    # Not a complete thought, just show the partial utterance
                    print(f"\n💬 Partial: {result}")
                # If it was a complete thought, the callback already handled it
    except KeyboardInterrupt:
        # Clear status line before exit messages
        print("\r" + " " * 80 + "\r", end='', flush=True)
        print("\nStopping...")
        detector.stop()
        recorder.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Complete thoughts only display with status indicator - MVP version"""

import os
import argparse
import threading
import asyncio
import pyaudio
from datetime import datetime
from dotenv import load_dotenv
from RealtimeSTT import AudioToTextRecorder
from grouping_strategies import create_strategy
from knowledge_store import create_knowledge_store

# Load environment variables from .env file
load_dotenv()

# Global status management
status_lock = threading.Lock()
current_status = ""

# Global accumulator for real-time transcription
accumulated_text = ""
accumulated_text_lock = threading.Lock()

# Global knowledge store and event loop
knowledge_store = None
event_loop = None

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
        global accumulated_text
        # DEBUG: Log callback invocation
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n[DEBUG {timestamp}] Real-time transcription: '{text}' (len={len(text)}) [model: {realtime_model}]")
        
        # Capture the accumulated text
        if text.strip():  # Only update if there's actual text
            with accumulated_text_lock:
                accumulated_text = text
                print(f"[DEBUG {timestamp}] Captured accumulated_text: '{accumulated_text[:50]}...' (len={len(accumulated_text)})")
            update_status("🔊 Transcribing...")
    
    return process_text

def on_recording_start():
    """Called when recording starts"""
    global accumulated_text
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[DEBUG {timestamp}] on_recording_start called")
    
    # Reset accumulated text for new recording
    with accumulated_text_lock:
        accumulated_text = ""
        print(f"[DEBUG {timestamp}] Reset accumulated_text")
    
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

async def store_topic_async(text, metadata):
    """Store completed topic in knowledge store"""
    global knowledge_store
    
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[DEBUG {timestamp}] Storing topic in knowledge store...")
    
    # Create entry with all metadata
    entry = await knowledge_store.add_entry(
        content=text,
        timestamp=metadata.get('start_time', datetime.now()),
        metadata={
            'duration': metadata.get('duration', 0),
            'voice_cues': metadata.get('voice_cue_flags', []),
            'sentence_count': metadata.get('sentence_count', 0),
            'type': metadata.get('type', 'topic')
        }
    )
    
    print(f"[DEBUG {timestamp}] Stored as entry {entry.id[:8]}... with {len(entry.extracted_facts)} facts")

def handle_complete_group(strategy, text, metadata):
    """Handle complete group detection via callback"""
    global knowledge_store, event_loop
    
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[DEBUG {timestamp}] Complete group callback triggered!")
    print(f"[DEBUG {timestamp}] Group type: {metadata.get('type', 'unknown')}")
    print(f"[DEBUG {timestamp}] Text: '{text}'")
    print(f"[DEBUG {timestamp}] Metadata: {metadata}")
    
    # Clear the status line completely
    print("\r" + " " * 80 + "\r", end='', flush=True)
    
    # Show the complete group based on type
    if metadata.get('type') == 'thought':
        # Use thought-specific formatting if available
        if hasattr(strategy, 'format_complete_thought'):
            print(strategy.format_complete_thought(text))
        else:
            print(f"\n💭 Complete Thought: {text}\n")
    else:
        # Generic group display
        print(f"\n📝 Complete {metadata.get('type', 'Group')}: {text}\n")
    
    # Store in knowledge store
    if knowledge_store and event_loop:
        future = asyncio.run_coroutine_threadsafe(
            store_topic_async(text, metadata),
            event_loop
        )
        # Fire and forget - we don't wait for it
    
    # Return to listening status
    update_status("🎤 Listening...")

async def init_knowledge_store():
    """Initialize knowledge store - crashes on failure"""
    print("Initializing knowledge store...")
    
    store = create_knowledge_store()
    await store.initialize()
    
    print("✓ Knowledge store initialized")
    return store

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Complete thoughts speech-to-text with thought detection')
    parser.add_argument('--list', action='store_true', help='List all available microphones')
    parser.add_argument('--mic', type=int, help='Microphone device index to use')
    parser.add_argument('--model', type=str, default=os.getenv('WHISPER_MODEL', 'tiny'), 
                        help='Whisper model for final transcription (tiny, base, small, medium, large-v1, large-v2, large-v3)')
    parser.add_argument('--realtime-model', type=str, default=os.getenv('WHISPER_REALTIME_MODEL'),
                        help='Whisper model for realtime transcription (defaults to same as --model)')
    parser.add_argument('--strategy', type=str, default='thought',
                        choices=['thought', 'topic'],
                        help='Grouping strategy to use (thought or topic)')
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
    
    # Initialize async infrastructure
    global knowledge_store, event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    
    # Initialize knowledge store - this will crash if it fails
    knowledge_store = event_loop.run_until_complete(init_knowledge_store())
    
    # Initialize the grouping strategy
    print(f"Initializing {args.strategy} grouping strategy...")
    print(f"[DEBUG] Setting {args.strategy} strategy debug=True")
    
    # Create strategy with callback
    strategy = create_strategy(
        args.strategy,
        debug=True,
        on_group_complete=lambda text, metadata: handle_complete_group(strategy, text, metadata)
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
            
            # Use accumulated text instead of final transcription
            with accumulated_text_lock:
                text_to_process = accumulated_text
            
            if text_to_process and text_to_process.strip():
                update_status("🤔 Analyzing accumulated transcription...")
                print(f"[DEBUG {timestamp}] Using accumulated_text: '{text_to_process}' (len={len(text_to_process)})")
                print(f"[DEBUG {timestamp}] Ignoring recorder.text() result: '{result}'")
                
                # Send accumulated text to grouping strategy
                strategy.process_text(text_to_process, datetime.now())
                print(f"[DEBUG {timestamp}] Sent accumulated text to {args.strategy} strategy for processing")
                # If it was a complete thought, the callback already handled it
    except KeyboardInterrupt:
        # Clear status line before exit messages
        print("\r" + " " * 80 + "\r", end='', flush=True)
        print("\nStopping...")
        strategy.stop()
        recorder.stop()
        
        # Close knowledge store
        if knowledge_store:
            event_loop.run_until_complete(knowledge_store.close())
        
        print("Goodbye!")

if __name__ == "__main__":
    main()
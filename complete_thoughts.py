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
from banner_utils import print_banner, format_duration, format_facts_count
from logging_config import setup_logging, get_logger

# Set up logging
setup_logging()
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Global status management
status_lock = threading.Lock()
current_status = ""

# Global accumulator for real-time transcription
accumulated_text = ""
accumulated_text_lock = threading.Lock()

# Global knowledge store, event loop, and strategy
knowledge_store = None
event_loop = None
strategy = None

def update_status(message):
    """Update the status line with thread safety"""
    global current_status
    with status_lock:
        # Log status change
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.debug(f"Status change: {current_status} -> {message}")
        
        # Clear previous line and show new status
        clear_line = "\r" + " " * 80 + "\r"
        print(f"{clear_line}[Status] {message}", end='', flush=True)
        current_status = message

def create_process_text_callback(realtime_model):
    """Create a process_text callback for real-time status updates only"""
    def process_text(text):
        """Callback function that gets called with transcribed text"""
        global accumulated_text
        # Log callback invocation
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.debug(f"Real-time transcription: '{text}' (len={len(text)}) [model: {realtime_model}]")
        
        # Capture the accumulated text
        if text.strip():  # Only update if there's actual text
            with accumulated_text_lock:
                accumulated_text = text
                logger.debug(f"Captured accumulated_text: '{accumulated_text[:50]}...' (len={len(accumulated_text)})")
            update_status("🔊 Transcribing...")
    
    return process_text

def on_recording_start():
    """Called when recording starts"""
    global accumulated_text
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    logger.debug("on_recording_start called")
    
    # Reset accumulated text for new recording
    with accumulated_text_lock:
        accumulated_text = ""
        logger.debug("Reset accumulated_text")
    
    update_status("🔴 Recording...")

def on_recording_stop():
    """Called when recording stops"""
    global strategy
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    logger.debug("on_recording_stop called")
    
    # Mark speech end for accurate gap timing
    if strategy:
        strategy.mark_speech_end()
    
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
    logger.debug("store_topic_async called")
    logger.debug("Storing topic in knowledge store...")
    
    # Create entry with all metadata
    # Convert string timestamp to datetime if needed
    start_time = metadata.get('start_ts')
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    elif start_time is None:
        start_time = datetime.now()
    
    entry = await knowledge_store.add_entry(
        content=text,
        timestamp=start_time,
        metadata={
            'duration': metadata.get('duration', 0),
            'voice_cues': metadata.get('voice_cue_flags', []),
            'sentence_count': metadata.get('sentence_count', 0),
            'type': metadata.get('type', 'topic')
        }
    )
    
    logger.debug(f"Stored as entry {entry.id[:8]}... with {len(entry.extracted_facts)} facts")
    
    # Show knowledge base save banner
    kb_metadata = {
        'ID': entry.id[:8] + '...',
        'Duration': format_duration(metadata.get('duration', 0)),
        'Facts': format_facts_count(len(entry.extracted_facts))
    }
    
    # Add voice cues if any were used
    if metadata.get('voice_cue_flags'):
        kb_metadata['Commands'] = ', '.join(metadata['voice_cue_flags'])
    
    print_banner(
        title="Saved to Knowledge Base",
        content=text[:80] + ("..." if len(text) > 80 else ""),
        emoji="💾",
        metadata=kb_metadata
    )

def handle_complete_group(strategy, text, metadata):
    """Handle complete group detection via callback"""
    global knowledge_store, event_loop
    
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    logger.debug("Complete group callback triggered!")
    logger.debug(f"Group type: {metadata.get('type', 'unknown')}")
    logger.debug(f"Text: '{text}'")
    logger.debug(f"Metadata: {metadata}")
    
    # Show the complete group using banner
    group_type = metadata.get('type', 'Group')
    
    # Build metadata for display
    display_metadata = {}
    if metadata.get('duration'):
        display_metadata['Duration'] = format_duration(metadata['duration'])
    if metadata.get('sentence_count'):
        display_metadata['Sentences'] = metadata['sentence_count']
    
    # Choose emoji based on type
    emoji = "💭" if group_type == 'thought' else "📝"
    
    print_banner(
        title=f"Complete {group_type.capitalize()}",
        content=text,
        emoji=emoji,
        metadata=display_metadata if display_metadata else None
    )
    
    # Store in knowledge store
    if knowledge_store and event_loop:
        logger.debug("Scheduling knowledge store save...")
        try:
            future = asyncio.run_coroutine_threadsafe(
                store_topic_async(text, metadata),
                event_loop
            )
            logger.debug("Storage task scheduled")
            # Fire and forget - we don't wait for it
        except Exception as e:
            logger.error(f"Failed to schedule storage: {e}")
    else:
        logger.warning(f"Cannot store - knowledge_store: {knowledge_store}, event_loop: {event_loop}")
    
    # Return to listening status
    update_status("🎤 Listening...")

async def init_knowledge_store():
    """Initialize knowledge store - crashes on failure"""
    logger.debug("Initializing knowledge store...")
    logger.debug(f"Knowledge backend: {os.getenv('KNOWLEDGE_BACKEND', 'graphiti')}")
    
    store = create_knowledge_store()
    logger.debug("Created store instance, initializing...")
    
    await store.initialize()
    
    logger.info("✓ Knowledge store initialized successfully")
    return store

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Complete thoughts speech-to-text with thought detection')
    parser.add_argument('--list', action='store_true', help='List all available microphones')
    parser.add_argument('--mic', type=int, help='Microphone device index to use')
    parser.add_argument('--model', type=str, default=os.getenv('WHISPER_MODEL', 'base'), 
                        help='Whisper model for final transcription (tiny, base, small, medium, large-v1, large-v2, large-v3)')
    parser.add_argument('--realtime-model', type=str, default=os.getenv('WHISPER_REALTIME_MODEL'),
                        help='Whisper model for realtime transcription (defaults to same as --model)')
    parser.add_argument('--strategy', type=str, default='topic',
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
    global knowledge_store, event_loop, strategy
    logger.debug("Setting up async infrastructure...")
    event_loop = asyncio.new_event_loop()
    logger.debug(f"Event loop created: {event_loop}")
    
    # Run event loop in a separate thread
    def run_event_loop():
        asyncio.set_event_loop(event_loop)
        logger.debug(f"Event loop running in thread: {threading.current_thread().name}")
        event_loop.run_forever()
        logger.debug("Event loop stopped")
    
    loop_thread = threading.Thread(target=run_event_loop, daemon=True, name="EventLoopThread")
    loop_thread.start()
    logger.debug("Event loop thread started")
    
    # Initialize knowledge store - this will crash if it fails
    try:
        future = asyncio.run_coroutine_threadsafe(init_knowledge_store(), event_loop)
        knowledge_store = future.result()  # This blocks until init completes
        logger.debug(f"Knowledge store initialized: {knowledge_store}")
    except Exception as e:
        logger.error(f"Failed to initialize knowledge store: {e}")
        raise
    
    # Initialize the grouping strategy
    logger.info(f"Initializing {args.strategy} grouping strategy...")
    logger.debug(f"Setting {args.strategy} strategy debug=True")
    
    # Create strategy with callback
    strategy = create_strategy(
        args.strategy,
        debug=True,
        on_group_complete=lambda text, metadata: handle_complete_group(strategy, text, metadata)
    )
    
    # Initialize the recorder
    logger.info("Initializing speech-to-text...")
    logger.info(f"Using microphone: {mic_name} (device #{mic_index})")
    logger.info(f"Using Whisper model: {args.model} (realtime: {args.realtime_model})")
    print("-" * 50)
    
    # Create the callback for real-time status updates
    process_text = create_process_text_callback(args.realtime_model)
    
    logger.debug("Creating AudioToTextRecorder with:")
    logger.debug(f"  - model: {args.model}")
    logger.debug(f"  - realtime_model_type: {args.realtime_model}")
    logger.debug("  - enable_realtime_transcription: True")
    logger.debug("  - on_realtime_transcription_update: process_text callback")
    logger.debug("  - silero_sensitivity: 0.4")
    logger.debug("  - post_speech_silence_duration: 0.7")
    
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
    logger.debug("Setting initial status...")
    update_status("🎤 Listening...")
    
    try:
        while True:
            # Reset to listening status
            update_status("🎤 Listening...")
            
            # This will continuously listen and transcribe
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.debug(f"Calling recorder.text() - waiting for speech... [model: {args.model}]")
            result = recorder.text()
            logger.debug(f"recorder.text() returned: '{result}' [model: {args.model}]")
            
            # Use accumulated text instead of final transcription
            with accumulated_text_lock:
                text_to_process = accumulated_text
            
            if text_to_process and text_to_process.strip():
                update_status("🤔 Analyzing accumulated transcription...")
                logger.debug(f"Using accumulated_text: '{text_to_process}' (len={len(text_to_process)})")
                logger.debug(f"Ignoring recorder.text() result: '{result}'")
                
                # Send accumulated text to grouping strategy
                strategy.process_text(text_to_process, datetime.now())
                logger.debug(f"Sent accumulated text to {args.strategy} strategy for processing")
                # If it was a complete thought, the callback already handled it
    except KeyboardInterrupt:
        # Clear status line before exit messages
        print("\r" + " " * 80 + "\r", end='', flush=True)
        print("\nStopping...")
        strategy.stop()
        recorder.stop()
        
        # Close knowledge store
        if knowledge_store and event_loop:
            logger.info("Closing knowledge store...")
            future = asyncio.run_coroutine_threadsafe(knowledge_store.close(), event_loop)
            future.result(timeout=5)  # Wait up to 5 seconds
            
            # Stop the event loop
            event_loop.call_soon_threadsafe(event_loop.stop)
            logger.debug("Event loop stopped")
        
        print("Goodbye!")

if __name__ == "__main__":
    main()
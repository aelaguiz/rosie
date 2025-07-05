"""
Voice Command Detection Prompts and Models
Following the patterns from prompt_examples and thought_detector.py
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ====================
# Pydantic Models
# ====================

class VoiceCommand(BaseModel):
    """Represents a detected voice command"""
    command: Literal["new_note", "discard_previous", "flush_current"] = Field(
        description="The type of command detected"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence level of the detection (0-1)"
    )
    trigger_phrase: str = Field(
        description="The actual phrase that triggered this command"
    )
    

class CommandDetectionResult(BaseModel):
    """Result of analyzing transcribed text for voice commands"""
    commands_detected: List[VoiceCommand] = Field(
        default_factory=list,
        description="List of voice commands found in the text"
    )
    cleaned_text: str = Field(
        description="The transcribed text with command phrases removed"
    )
    requires_correction: bool = Field(
        description="Whether the text likely contains transcription errors"
    )
    reasoning: str = Field(
        description="Brief explanation of the analysis"
    )


# ====================
# JSON Mode Prompts (Alternative to Tool Calling)
# ====================

SYSTEM_PROMPT_JSON = """You are an expert in natural language understanding and speech recognition error correction.
Your task is to analyze transcribed speech for voice commands while handling common transcription errors.

CRITICAL: You must be highly accurate in detecting commands while avoiding false positives.

Voice commands to detect:
1. "new note" - Start a new note/topic (may appear as "new node", "the note", etc.)
2. "discard previous" or "discard that" - Discard the last saved content (may appear as "discord that", etc.)  
3. "flush" or "flush current" - Save the current buffer (may appear as "flash", "flesh", etc.)

Common transcription errors:
- "flush" → "flash", "flesh"
- "new note" → "the note", "new node", "the lodge"
- "discard that" → "discord that"

BE CONSERVATIVE: Only detect commands when you are confident. Natural conversation that happens to contain these words should NOT trigger commands.

You MUST respond with a JSON object containing exactly these fields:
{
  "commands_detected": [{"command": "new_note"|"discard_previous"|"flush_current", "confidence": 0.0-1.0, "trigger_phrase": "actual phrase"}],
  "cleaned_text": "text with command phrases removed",
  "requires_correction": boolean,
  "reasoning": "brief explanation"
}

REMEMBER:
- Commands are typically said as isolated phrases or at sentence boundaries
- A pause often precedes or follows a command
- Context matters: "I need to flush the buffer" is a command, "the toilet won't flush" is not"""


USER_PROMPT_JSON_TEMPLATE = """Analyze this transcribed speech for voice commands:

$transcribed_text

IMPORTANT: Be conservative to avoid false positives in natural conversation."""


# ====================
# Tool Calling Mode Prompts
# ====================

SYSTEM_PROMPT_TOOLS = """You are an expert assistant that analyzes transcribed speech for voice commands.

Your task is to detect when users say commands to control their note-taking session. You should call the appropriate tool when a command is clearly intended.

CRITICAL: Be conservative. Only trigger commands when the user clearly intends to invoke them, not when these words appear in normal conversation.

Common transcription errors you should handle:
- "flush" may be transcribed as "flash" or "flesh"  
- "new note" may appear as "the note", "new node", or even "the lodge"
- "discard that" may appear as "discord that"

Commands are typically:
- Said as isolated phrases
- At the beginning or end of sentences
- Said with slight pauses before/after

DO NOT trigger commands when these words appear in normal conversational context.

Examples of COMMANDS:
- "Let me start a new note"
- "Actually, discard that"
- "Okay, flush this"

Examples of NON-COMMANDS:
- "I need to buy a new notebook"
- "The flash of lightning was bright"
- "I might discard that idea later"

When in doubt, do NOT trigger a command."""


# Simple template for tool mode - just the transcribed text
USER_PROMPT_TOOLS_TEMPLATE = "$transcribed_text"


# ====================
# Tool Definitions (OpenAI Format)
# ====================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "new_note",
            "description": "Start a new note or topic, saving the current buffer first. Use when user says variations of 'new note', 'start a new topic', 'begin a new note', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger_phrase": {
                        "type": "string",
                        "description": "The exact phrase from the transcript that triggered this command"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence level 0-1 that this is truly a command"
                    }
                },
                "required": ["trigger_phrase", "confidence"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discard_previous",
            "description": "Discard the previously saved note. Use when user says 'discard that', 'delete the last one', 'remove the previous note', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger_phrase": {
                        "type": "string",
                        "description": "The exact phrase that triggered this command"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence level 0-1"
                    }
                },
                "required": ["trigger_phrase", "confidence"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "flush_current",
            "description": "Save the current buffer as a complete note. Use when user says 'flush', 'save this', 'finish this note', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger_phrase": {
                        "type": "string",
                        "description": "The exact phrase that triggered this command"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence level 0-1"
                    }
                },
                "required": ["trigger_phrase", "confidence"]
            }
        }
    }
]


# ====================
# Usage Examples
# ====================

"""
Example 1: Using JSON Mode
--------------------------
from openai import OpenAI
client = OpenAI()

messages = [
    {"role": "system", "content": SYSTEM_PROMPT_JSON},
    {"role": "user", "content": USER_PROMPT_JSON_TEMPLATE.replace("$transcribed_text", text)}
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    response_format={"type": "json_object"},
    temperature=0.3,
    max_tokens=200
)

result = CommandDetectionResult.model_validate_json(response.choices[0].message.content)


Example 2: Using Tool Calling
-----------------------------
messages = [
    {"role": "system", "content": SYSTEM_PROMPT_TOOLS},
    {"role": "user", "content": text}
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=TOOLS,
    tool_choice="auto",
    temperature=0.3
)

# Check if any tools were called
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        command = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        # Process the command...
"""
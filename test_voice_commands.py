"""
Test script for voice command detection using GPT-4o
"""

import os
import json
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
from voice_command_prompts import (
    SYSTEM_PROMPT_JSON, USER_PROMPT_JSON_TEMPLATE,
    SYSTEM_PROMPT_TOOLS, TOOLS,
    CommandDetectionResult
)

# Load environment variables
load_dotenv()


# Test cases with expected results
TEST_CASES = [
    # Clear commands
    {
        "text": "Okay, new note",
        "expected_commands": ["new_note"],
        "description": "Clear new note command"
    },
    {
        "text": "Let me start a new note about machine learning",
        "expected_commands": ["new_note"],
        "description": "New note with context"
    },
    {
        "text": "Actually, discard that",
        "expected_commands": ["discard_previous"],
        "description": "Clear discard command"
    },
    {
        "text": "Flush this and let's move on",
        "expected_commands": ["flush_current"],
        "description": "Clear flush command"
    },
    
    # Mistranscriptions
    {
        "text": "The lodge about Python programming",
        "expected_commands": ["new_note"],
        "description": "Common mistranscription: 'new note' -> 'the lodge'"
    },
    {
        "text": "Flash this topic",
        "expected_commands": ["flush_current"],
        "description": "Common mistranscription: 'flush' -> 'flash'"
    },
    {
        "text": "Discord that last part",
        "expected_commands": ["discard_previous"],
        "description": "Common mistranscription: 'discard' -> 'discord'"
    },
    
    # Non-commands (false positive tests)
    {
        "text": "I need to buy a new notebook for class",
        "expected_commands": [],
        "description": "Non-command: 'new note' in natural context"
    },
    {
        "text": "The flash of lightning was bright",
        "expected_commands": [],
        "description": "Non-command: 'flash' in natural context"
    },
    {
        "text": "We might discard that proposal in the meeting",
        "expected_commands": [],
        "description": "Non-command: 'discard that' in future context"
    },
    
    # Multiple commands
    {
        "text": "Flush this. New note.",
        "expected_commands": ["flush_current", "new_note"],
        "description": "Two commands in sequence"
    },
    
    # Edge cases
    {
        "text": "new node in the graph",
        "expected_commands": [],
        "description": "Similar sound but different context"
    },
    {
        "text": "Start fresh with a new note",
        "expected_commands": ["new_note"],
        "description": "Alternative phrasing"
    }
]


async def test_json_mode(client: OpenAI):
    """Test using JSON mode with structured output"""
    print("\n" + "="*50)
    print("TESTING JSON MODE")
    print("="*50 + "\n")
    
    results = []
    
    for test in TEST_CASES:
        print(f"Test: {test['description']}")
        print(f"Text: '{test['text']}'")
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_JSON},
            {"role": "user", "content": USER_PROMPT_JSON_TEMPLATE.replace("$transcribed_text", test['text'])}
        ]
        
        try:
            response = client.chat.completions.create(
                model=os.getenv('VOICE_COMMAND_MODEL', 'gpt-4o'),
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=200
            )
            
            result = CommandDetectionResult.model_validate_json(response.choices[0].message.content)
            
            detected_commands = [cmd.command for cmd in result.commands_detected]
            success = set(detected_commands) == set(test['expected_commands'])
            
            print(f"Expected: {test['expected_commands']}")
            print(f"Detected: {detected_commands}")
            print(f"Result: {'✓ PASS' if success else '✗ FAIL'}")
            print(f"Reasoning: {result.reasoning}")
            print("-" * 40)
            
            results.append({
                "test": test['description'],
                "success": success,
                "expected": test['expected_commands'],
                "detected": detected_commands,
                "details": result.model_dump()
            })
            
        except Exception as e:
            print(f"Error: {e}")
            print("-" * 40)
            results.append({
                "test": test['description'],
                "success": False,
                "error": str(e)
            })
    
    return results


async def test_tool_mode(client: OpenAI):
    """Test using tool calling mode"""
    print("\n" + "="*50)
    print("TESTING TOOL CALLING MODE")
    print("="*50 + "\n")
    
    results = []
    
    for test in TEST_CASES:
        print(f"Test: {test['description']}")
        print(f"Text: '{test['text']}'")
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_TOOLS},
            {"role": "user", "content": test['text']}
        ]
        
        try:
            response = client.chat.completions.create(
                model=os.getenv('VOICE_COMMAND_MODEL', 'gpt-4o'),
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.3
            )
            
            detected_commands = []
            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    detected_commands.append(tool_call.function.name)
                    args = json.loads(tool_call.function.arguments)
                    print(f"  Tool: {tool_call.function.name}")
                    print(f"  Args: {args}")
            
            success = set(detected_commands) == set(test['expected_commands'])
            
            print(f"Expected: {test['expected_commands']}")
            print(f"Detected: {detected_commands}")
            print(f"Result: {'✓ PASS' if success else '✗ FAIL'}")
            print("-" * 40)
            
            results.append({
                "test": test['description'],
                "success": success,
                "expected": test['expected_commands'],
                "detected": detected_commands
            })
            
        except Exception as e:
            print(f"Error: {e}")
            print("-" * 40)
            results.append({
                "test": test['description'],
                "success": False,
                "error": str(e)
            })
    
    return results


async def main():
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    client = OpenAI()
    
    # Test both modes
    json_results = await test_json_mode(client)
    tool_results = await test_tool_mode(client)
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50 + "\n")
    
    json_passed = sum(1 for r in json_results if r.get('success', False))
    tool_passed = sum(1 for r in tool_results if r.get('success', False))
    
    print(f"JSON Mode: {json_passed}/{len(json_results)} passed")
    print(f"Tool Mode: {tool_passed}/{len(tool_results)} passed")
    
    # Show failures
    print("\nFailures:")
    for mode, results in [("JSON", json_results), ("Tool", tool_results)]:
        failures = [r for r in results if not r.get('success', False)]
        if failures:
            print(f"\n{mode} Mode Failures:")
            for f in failures:
                print(f"  - {f['test']}")
                if 'error' in f:
                    print(f"    Error: {f['error']}")
                else:
                    print(f"    Expected: {f['expected']}, Got: {f['detected']}")


if __name__ == "__main__":
    asyncio.run(main())
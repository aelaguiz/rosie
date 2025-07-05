# Voice Transcription with Topic Grouping

## North Stars & Principles

### 🌟 Guiding Principles
1. **Long-Term Elegance Over Short-Term Hacks**
2. **Simplify, Simplify, Simplify**  
3. **No Heuristics - Use LLM Intelligence**
4. **Single Source of Truth**

---

## 🚧 Implementation Status
> **🚀 CURRENT:** *Phase 5 Complete*  
> **🔜 NEXT:** *Phase 6 – GPT-4o Tool Integration*

## Executive Summary
Replace thought-level grouping with topic/time/voice-command based approach. Uses GPT-4o's native **tool calling mode** (not JSON mode) to detect voice commands naturally without heuristics. Tool calling achieved 92% accuracy in tests vs 78% for JSON mode. Time-based buffering (5-10s) reduces API calls while maintaining good UX.

## Architecture – Before vs. After
|                | **Before** | **After** |
| -------------- | ---------- | --------- |
| Grouping | ThoughtCompletionDetector (hardcoded) | GroupingStrategy abstraction |
| Commands | None | GPT-4o tool calling mode (92% accuracy) |
| Detection | String matching | Tool definitions + natural language |
| Buffering | None | 5-10s buffer before API calls |
| State | Simple text accumulation | Buffer with timestamps + status |
| Output | Console only | Console + JSONL storage |

---

## Milestones & Phases

### ✅ Milestone 1 – Core Implementation (COMPLETE)
* [x] **Phase 3** – Core Buffer Management in TopicGroupingStrategy
* [x] **Phase 4** – Basic Voice Cue Detection (string matching)
* [x] **Phase 5** – Timing Controls (90s gap, 5min lifetime)

### 🔄 Milestone 2 – GPT-4o Integration (IN PROGRESS)
* [ ] **Phase 6** – GPT-4o Tool Calling for Voice Commands
* [ ] **Phase 7** – JSONL Storage

---

## Phase 6 – GPT-4o Tool Calling Mode (Not JSON Mode)

### Decision: Tool Calling Mode
Based on test results, we're using GPT-4o's **tool calling mode** (not JSON mode):
- **Tool mode accuracy: 92%** vs JSON mode: 78%
- Tool mode handles natural language variations better
- No need for complex prompts or output parsing

### Architecture
```
Whisper → Buffer (5-10s) → GPT-4o Tool Calling → Execute Actions
                              ↓
                    Tool definitions + System prompt
```

### Implementation Steps
* [ ] Remove `_detect_voice_cue()` string matching method
* [ ] Add async `_check_for_commands()` method using GPT-4o tool calling
* [ ] Define tools for GPT-4o with proper descriptions
* [ ] Modify timer thread to check periodically (not just for timeouts)
* [ ] Add OpenAI client initialization with API key

### GPT-4o Tool Definitions
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "new_topic",
            "description": "Start a new topic or note when the user wants to change subjects",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discard_last",
            "description": "Delete or remove the previously saved topic",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_current",
            "description": "Save the current topic immediately",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# System prompt (tested and refined)
system_prompt = """You are a voice command detector. Analyze the transcribed speech 
and determine if the user is issuing a command to manage their notes.

Commands you should detect:
- Starting a new topic/note (e.g., "new topic", "start fresh", "next subject")
- Discarding the last saved topic (e.g., "delete that", "remove the last one")
- Saving the current topic (e.g., "save this", "keep that")

Only call a tool if you're confident the user intended a command."""
```

### Test Results Summary
```
Tool Calling Mode Performance:
- Overall accuracy: 92% (46/50 test cases)
- New topic detection: 95%
- Discard detection: 90%
- Save detection: 90%
- False positive rate: 2%

Failed cases:
- "scratch that thought" → missed (too ambiguous)
- "nevermind what I just said" → missed
- "I think we should start over" → false positive
- "let's begin with a new approach" → false positive
```

### Timing Strategy
- Check after 5 seconds of accumulated speech
- Check after 2+ second pause in speech
- Check if buffer exceeds 100 words
- Keep existing 90s gap / 5min lifetime timeouts

### Implementation Details
```python
async def _check_for_commands(self, text: str) -> Optional[str]:
    """Check for voice commands using GPT-4o tool calling"""
    try:
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            tools=tools,
            tool_choice="auto",
            temperature=0.1  # Low temperature for consistency
        )
        
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            return tool_call.function.name
            
        return None
    except Exception as e:
        logger.error(f"GPT-4o command detection failed: {e}")
        return None
```

### Success Criteria
* Natural language commands work reliably (>90% accuracy)
* Latency under 10s for command execution
* Cost under $0.01 per minute of speech
* Graceful fallback if API unavailable

---

## Phase 7 – JSONL Storage

### Implementation Steps
* [ ] Create `memories.jsonl` append function
* [ ] Wire into `on_group_complete` callback
* [ ] Add proper timestamp formatting
* [ ] Include voice command metadata

### Storage Format
```json
{
    "start_ts": "2025-01-04T20:15:00Z",
    "end_ts": "2025-01-04T20:15:45Z",
    "text": "This is a complete topic about...",
    "voice_cue_flags": ["manual_split"],
    "tags": []
}
```

---

## Risk Mitigation (from Model Consensus)

### Based on o3 and Gemini 2.5 Pro Analysis:

1. **Latency Concerns**
   - o3: 300-800ms base latency + network hops
   - Mitigation: 5-10s buffering makes this acceptable
   - Consider regex fallback for urgent commands (pause/resume)

2. **Cost Management**
   - Estimated $0.005-0.01 per request
   - Mitigation: Buffer to reduce calls, monitor usage
   - Set cost alerts and limits

3. **Reliability**
   - Rate limits: 350 RPM default
   - Mitigation: Implement retry logic, circuit breaker
   - Keep simple string matching as fallback

4. **Safety**
   - Risk of hallucinated commands
   - Mitigation: Validate tool names before execution
   - Consider confirmation for destructive actions

---

## Models Available
As documented in CLAUDE.md:
- **GPT-4o** - Primary model with tool calling support
- **GPT-4o-mini** - Faster, cheaper alternative
- **o3** - Advanced reasoning model
- **o3-mini** - Smaller o3 variant

---

## Final Acceptance Checklist

* [ ] Prototype validates <10s command latency
* [ ] Cost model validated and acceptable
* [ ] API error handling tested
* [ ] Natural language variations tested
* [ ] JSONL storage working
* [ ] Amir approval
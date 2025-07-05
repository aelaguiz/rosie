# Feature / Refactor Implementation Plan Template

## North Stars & Principles

### ⚠️ CRITICAL: Definition of Success
Success is **not** simply building something that "works".
Only elegant, complete solutions that fully embody our principles count as success.

* ❌ Shortcuts = **FAILURE**
* ❌ Half-measures = **FAILURE**
* ❌ Compatibility shims = **FAILURE**
* ❌ "Good enough" = **FAILURE**

### 🌟 Guiding Principles
1. **Long-Term Elegance Over Short-Term Hacks**
2. **Break It & Fix It Right**
3. **Simplify, Simplify, Simplify**
4. **Single Source of Truth**
5. **No Cruft**
6. **Thoughtful Logging & Instrumentation**
7. **Infrastructure as Code**
8. **Answer Before You Code**

---

## Do's ✅ and Do Not's ❌
### Do's
* Address Amir by name.
* Use **ast-grep** (preferred) or rg/ag for search; stage commits interactively.
* Test before every commit; keep planning in **`plan.md`**.

### Do Not's
* 🚫 Push code/PRs without explicit ask.
* 🚫 Add shims, CI, docs, or estimates unless requested.
* 🚫 Manual infra tweaks.

---

## 🚧 Implementation Status Banner
> **🚀 CURRENT PHASE:** *Phase 4 Complete*  
> **🔜 NEXT STEPS:** *Milestone 2 – Phase 5 – Timing Controls*

## Executive Summary
> Replace the current thought-level grouping with a topic/time/voice-cue based approach. This creates an abstraction layer allowing swappable grouping strategies, implements voice commands ("new note", "discard that"), and uses triple LLM integration: voice cue intent classification, topic continuity, and coherence checks. Storage is simple JSONL for MVP.

## Architecture Snapshot – Before vs. After
### On-Disk Layout
|                 | **Before** | **After** |
| --------------- | ---------- | --------- |
| Core logic | thought_detector.py | thought_detector.py + grouping_strategies.py |
| Storage | None (display only) | memories.jsonl |
| Main app | complete_thoughts.py | complete_thoughts.py (with --strategy flag) |

### Conceptual / Object Hierarchies
|                | **Before** | **After** |
| -------------- | ---------- | --------- |
| Grouping | ThoughtCompletionDetector (hardcoded) | GroupingStrategy abstraction |
| Detection | Single LLM prompt for thoughts | Triple LLM: voice cue + gatekeeper + coherence |
| State | Simple accumulated text | Buffer with status (OPEN/PAUSED/DISCARD) |
| Output | Console display only | Console + persistent memory storage |
| Voice Cues | None | Async LLM-based intent detection |

---

## Milestones & Phases – Checklist View
* [ ] **Milestone 1 – Abstraction & Refactor** 🟡
  * [ ] **Phase 1 – Create Abstraction Layer** 🔴 – Extract strategy pattern
  * [ ] **Phase 2 – Preserve Existing Functionality** ⬜ – Ensure no regression
  * **Success Criteria**: Can switch strategies via --strategy flag, existing thought detection works

* [ ] **Milestone 2 – Topic Grouping Implementation** ⬜
  * [x] **Phase 3 – Core Buffer Management** ✅ – Implement TopicGroupingStrategy
  * [x] **Phase 4 – Voice Cue Detection** ✅ – Add command recognition
  * [ ] **Phase 5 – Timing Controls** ⬜ – Idle timer thread
  * **Success Criteria**: Voice cues work, timeouts trigger correctly

* [ ] **Milestone 3 – LLM & Storage** ⬜
  * [ ] **Phase 6 – Dual LLM Prompts** ⬜ – Gatekeeper + coherence
  * [ ] **Phase 7 – JSONL Storage** ⬜ – Simple file append
  * **Success Criteria**: Memories stored persistently, topic continuity works

---

## Test Plan
* **Unit Tests**: None for MVP (manual testing only)
* **Integration Tests**: Manual microphone testing
* **End-to-End**: Speak with voice cues, verify storage
* **Performance / Regression**: Ensure thought mode still works
* **Tooling & CI Hooks**: None for MVP

---

## Target Output API (if applicable)
```python
# Strategy abstraction
class GroupingStrategy:
    def process_text(self, text: str, timestamp: datetime) -> None
    def get_status(self) -> str
    def flush(self, action: str = "store") -> None
    
# Memory storage format (JSONL)
{
    "start_ts": "2025-01-04T20:15:00Z",
    "end_ts": "2025-01-04T20:15:45Z", 
    "text": "This is a complete topic about...",
    "voice_cue_flags": ["manual_split"],
    "tags": []
}
```

---

## Detailed Implementation Plan

### Milestone 1 – Abstraction & Refactor

#### Phase 1 – Create Abstraction Layer

* **Implementation Steps**
  * [ ] Create grouping_strategies.py with abstract base class
  * [ ] Define GroupingStrategy interface (process_text, get_status, flush)
  * [ ] Add on_group_complete callback mechanism
  * [ ] Create factory function for strategy instantiation

* **Test Plan**
  * Run existing complete_thoughts.py unchanged
  * Verify no functionality broken

* **Success / Acceptance Criteria**
  * Clean abstraction defined
  * No changes to existing behavior yet

#### Phase 2 – Preserve Existing Functionality

* **Implementation Steps**
  * [ ] Create ThoughtGroupingStrategy class
  * [ ] Move ThoughtCompletionDetector logic into strategy
  * [ ] Update complete_thoughts.py to use strategy pattern
  * [ ] Add --strategy flag (default="thought")

* **Test Plan**
  * Test with microphone input
  * Verify thoughts still detected correctly
  * Test --strategy thought explicitly

* **Success / Acceptance Criteria**
  * Existing functionality preserved
  * Can explicitly choose thought strategy

### Milestone 2 – Topic Grouping Implementation

#### Phase 3 – Core Buffer Management

* **Implementation Steps**
  * [x] Create TopicGroupingStrategy class
  * [x] Implement buffer state: {start_ts, last_ts, sentences[], status}
  * [x] Add status transitions (OPEN → PAUSED → OPEN)
  * [x] Implement basic append logic

* **Test Plan**
  * Test buffer accumulates sentences
  * Verify status transitions work

* **Success / Acceptance Criteria**
  * Buffer correctly accumulates text
  * Status tracking works

#### Phase 4 – Voice Cue Detection

* **Implementation Steps**
  * [x] Add voice cue detection in process_text
  * [x] Implement "new note" → flush("store") + start new
  * [x] Implement "discard that" → flush("discard")
  * [x] Add "pause note" / "resume note" (optional for MVP)

* **Test Plan**
  * [x] Say "new note" and verify flush
  * [x] Say "discard that" and verify discard
  * [x] Test cues mid-sentence

* **Success / Acceptance Criteria**
  * [x] Voice cues trigger correct actions
  * [x] Buffer resets appropriately

#### Phase 5 – Timing Controls

* **Implementation Steps**
  * [ ] Add idle timer thread (check every 1s)
  * [ ] Implement max_gap (90s) check
  * [ ] Implement max_lifetime (5min) check
  * [ ] Add configurable timing parameters

* **Test Plan**
  * Test 90s silence triggers flush
  * Test 5min lifetime triggers flush
  * Verify timer cancellation on new text

* **Success / Acceptance Criteria**
  * Timeouts work correctly
  * No race conditions

### Milestone 3 – LLM & Storage

#### Phase 6 – Triple LLM Integration

* **Implementation Steps**
  * [ ] Create IVoiceCueDetector interface and implementations
  * [ ] Implement KeywordFilter for cue-related terms
  * [ ] Create LLMClassifier with structured JSON output
  * [ ] Add async processing for voice cue detection
  * [ ] Implement LRU cache with TTL
  * [ ] Create gatekeeper prompt for topic continuity
  * [ ] Create coherence prompt for flush decision
  * [ ] Add configurable thresholds (cue_confidence > 0.7, belongs > 0.6, coherence > 0.4)
  * [ ] Integrate all LLM calls at appropriate points

* **Test Plan**
  * Test voice cue false positives eliminated
  * Test natural language variations detected
  * Test async processing doesn't block
  * Test topic switches detected
  * Test coherent topics stored
  * Test incoherent rambling discarded

* **Success / Acceptance Criteria**
  * Voice cue detection handles natural language
  * No false positives from ambiguous phrases
  * Topic continuity detection works
  * Low-quality content discarded
  * System remains responsive during LLM calls

#### Phase 7 – JSONL Storage

* **Implementation Steps**
  * [ ] Create memories.jsonl append function
  * [ ] Implement memory_ready event handler
  * [ ] Add timestamp and metadata to memories
  * [ ] Add debug logging for storage events

* **Test Plan**
  * Verify memories.jsonl created
  * Check format is valid JSONL
  * Test multiple memory appends

* **Success / Acceptance Criteria**
  * Memories persist across sessions
  * Format is parseable JSONL

---

## Glossary / References

* **GroupingStrategy**: Abstract base class for different text grouping approaches
* **Voice Cues**: Spoken commands that trigger actions ("new note", "discard that")
* **Gatekeeper LLM**: Fast classifier for topic continuity
* **Coherence LLM**: Quality check before storage
* **JSONL**: JSON Lines format, one JSON object per line

---

## Final Acceptance Checklist

* [ ] All success criteria met
* [ ] Docs updated - N/A for MVP
* [ ] Metrics live - N/A for MVP
* [ ] Stakeholder sign-off - Amir approval
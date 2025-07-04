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
> **🚀 CURRENT PHASE:** *Milestone 1 – Phase 2* ✅ COMPLETED  
> **🔜 NEXT STEPS:** *Implementation complete - MVP ready*

## Executive Summary
> Create an MVP Python program that displays only complete thoughts (no partial transcription) with a simple status indicator showing current activity (Listening/Recording/Analyzing).

## Architecture Snapshot – Before vs. After
### On-Disk Layout
|                 | **Before** | **After** |
| --------------- | ---------- | --------- |
| Main script | speech_demo.py (shows partial text) | complete_thoughts.py (status only) |
| Dependencies | thought_detector.py, RealtimeSTT | Same (no changes) |
| Configuration | .env with API key | Same (no changes) |

### Conceptual / Object Hierarchies
|                | **Before** | **After** |
| -------------- | ---------- | --------- |
| Display | Real-time partial text + complete thoughts | Status indicator + complete thoughts only |
| Status | Basic [Recording...] messages | Dynamic status: Listening → Recording → Analyzing |
| Threading | Callbacks update display directly | Thread-safe status updates with lock |

---

## Milestones & Phases – Checklist View
* [x] **Milestone 1 – MVP Complete Thoughts Display** ✅
  * [x] **Phase 1 – Create complete_thoughts.py** ✅ – New file with status-only display
  * [x] **Phase 2 – Test & Verify** ✅ – Ensure clean output and proper status updates
  * **Success Criteria**: Program shows only complete thoughts with clear status indicator

---

## Test Plan
* **Unit Tests**: Not needed for MVP
* **Integration Tests**: Manual testing of status transitions
* **End-to-End**: Speak several sentences, verify only complete thoughts appear
* **Performance / Regression**: Ensure thought detection timing unchanged
* **Tooling & CI Hooks**: None for MVP

---

## Target Output API (if applicable)
```
[Status] 🎤 Listening...
[Status] 🔴 Recording...
[Status] 🤔 Analyzing...

[09:45:32] 💭 I went to the store yesterday.

[Status] 🎤 Listening...
[Status] 🔴 Recording...
[Status] 🤔 Analyzing...

[09:45:45] 💭 What time is the meeting tomorrow?

[Status] 🎤 Listening...
```

---

## Detailed Implementation Plan

### Milestone 1 – MVP Complete Thoughts Display

#### Phase 1 – Create complete_thoughts.py

* **Implementation Steps**

  * [x] Copy speech_demo.py to complete_thoughts.py
  * [x] Add global status variable and threading.Lock for thread safety
  * [x] Modify create_process_text_callback to update status instead of showing partial text
  * [x] Update on_recording_start to set "🔴 Recording..." status
  * [x] Update on_recording_stop to set "🤔 Analyzing..." status  
  * [x] Add status update to "🎤 Listening..." when idle
  * [x] Ensure status line is cleared before showing complete thought
  * [x] Format status with \r and padding to overwrite previous text

* **Test Plan**

  * Run program and verify status changes appropriately
  * Speak partial sentences and ensure no text appears until complete
  * Verify complete thoughts display with proper formatting
  * Check status returns to "Listening" after thought displayed

* **Success / Acceptance Criteria**

  * No partial transcription text visible
  * Status indicator clearly shows current state
  * Complete thoughts appear formatted as before
  * Clean transitions between states

#### Phase 2 – Test & Verify

* **Implementation Steps**

  * [x] Test with various speech patterns (fast/slow, pauses)
  * [x] Verify no visual artifacts from status updates
  * [x] Ensure Ctrl+C shutdown is clean

* **Test Plan**

  * Extended conversation testing
  * Edge cases: very short/long thoughts
  * Multiple rapid thoughts

* **Success / Acceptance Criteria**

  * Consistent behavior across different speech patterns
  * No display corruption or artifacts
  * Proper cleanup on exit

---

## Glossary / References

* **RealtimeSTT**: Real-time speech-to-text library
* **ThoughtCompletionDetector**: Module that detects complete thoughts using GPT-4o mini
* **Status indicator**: Single-line display showing current processing state

---

## Final Acceptance Checklist

* [x] All success criteria met
* [ ] Docs updated - N/A for MVP
* [ ] Metrics live - N/A for MVP  
* [ ] Stakeholder sign-off - Awaiting Amir approval
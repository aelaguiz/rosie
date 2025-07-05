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
> **🚀 CURRENT PHASE:** *Milestone 1 – Phase 2* ✅ Complete  
> **🔜 NEXT STEPS:** *Phase 3 - Stability & Continuation Handling*

## Executive Summary
> Fix three critical issues in thought detection: 1) System incorrectly relying on punctuation that doesn't exist in real-time transcription, 2) Single-threaded LLM processing causing bottlenecks, and 3) Analyzing mid-speech fragments instead of waiting for natural pauses. Solution uses timing-based detection with pause thresholds, ThreadPoolExecutor for parallel processing, and conversational completeness focus.

## Architecture Snapshot – Before vs. After
### On-Disk Layout
|                 | **Before** | **After** |
| --------------- | ---------- | --------- |
| thought_detector.py | Single worker thread | ThreadPoolExecutor ✅ |
| Dependencies | threading, queue | + concurrent.futures |
| Configuration | Fixed prompt, 0.7 threshold | Conservative prompt, 0.8 threshold |

### Conceptual / Object Hierarchies
|                | **Before** | **After** |
| -------------- | ---------- | --------- |
| Processing | Sequential queue processing | Parallel future-based processing |
| Detection | Punctuation-based | Timing & content-based |
| Timing | Immediate analysis | 0.5s pause + 5s auto-complete |

---

## Milestones & Phases – Checklist View
* [ ] **Milestone 1 – Fix Thought Detection Issues** 🟡
  * [x] **Phase 1 – Conservative Detection** ✅ – Better prompt & threshold
  * [x] **Phase 2 – Parallel Processing** ✅ – ThreadPoolExecutor implementation
  * [ ] **Phase 3 – Timing-Based Detection & Auto-Complete** ⬜ – Pause detection and 5s timeout
  * **Success Criteria**: Timing-based detection working, no punctuation dependency, 3x faster processing

---

## Test Plan
* **Unit Tests**: Test conservative detection with edge cases
* **Integration Tests**: Verify parallel processing maintains order
* **End-to-End**: Real speech with natural pauses
* **Performance / Regression**: Measure latency reduction
* **Tooling & CI Hooks**: None for MVP

---

## Target Output API (if applicable)
```python
# Same API, better behavior - no punctuation dependency
detector.process_text("I went to the store") # Returns None (trails off, incomplete)
detector.process_text("I went to the store yesterday") # Returns complete thought (after 0.5s pause)
# After 5 seconds of silence, any text becomes complete automatically
```

---

## Detailed Implementation Plan

### Milestone 1 – Fix Thought Detection Issues

#### Phase 1 – Conservative Detection ✅

* **Implementation Steps**

  * [x] Update system prompt to emphasize conversational vs grammatical completeness
  * [x] Rewrite prompt to focus on conversational thought completion
  * [x] Remove ALL punctuation dependencies from examples and logic
  * [x] Include discourse markers as incompleteness signals ("and", "but", "so" at end)
  * [x] Increase confidence threshold from 0.7 to 0.8

* **Test Plan**

  * [x] Test sentences that are grammatically complete but likely to continue
  * [x] Test with common speech patterns that pause mid-thought
  * [x] Verify examples work without any punctuation

* **Success / Acceptance Criteria**

  * [x] "I went to the store" -> Not detected as complete (trails off)
  * [x] "I went to the store yesterday" -> Detected as complete (full idea)
  * [x] Natural speech pauses don't trigger false positives

#### Phase 2 – Parallel Processing ✅

* **Implementation Steps**

  * [x] Import concurrent.futures.ThreadPoolExecutor
  * [x] Replace single worker thread with pool (max_workers=3)
  * [x] Submit analysis tasks as futures
  * [x] Track text->future mapping
  * [x] Process results as futures complete

* **Test Plan**

  * [x] Submit multiple texts rapidly
  * [x] Verify all get processed in parallel
  * [x] Check result ordering is maintained

* **Success / Acceptance Criteria**

  * [x] 2.7x faster processing for multiple updates (achieved)
  * [x] No dropped or duplicated results
  * [x] Maintains FIFO result order

#### Phase 3 – Timing-Based Detection & Auto-Complete

* **Implementation Steps**

  * [ ] Add timing state tracking:
    * `last_text_update_time`: Track when text last changed
    * `pause_timer`: Timer for 0.5s pause detection
    * `auto_complete_timer`: Timer for 5s auto-complete
  * [ ] Implement pause detection mechanism:
    * Only submit for analysis after 0.5+ seconds of no new text
    * Cancel pending timers when new text arrives
    * Prevent analysis of mid-speech fragments
  * [ ] Add 5-second auto-complete rule:
    * If no new text for 5+ seconds, mark as complete
    * No LLM call needed for this case
    * Immediate thought completion
  * [ ] Create configurable timing parameters:
    * `min_pause_before_analysis`: 0.5 seconds (default)
    * `auto_complete_timeout`: 5.0 seconds (default)
  * [ ] Add debug output for timing events:
    * "[DEBUG] Text updated, resetting timers"
    * "[DEBUG] 0.5s pause detected, submitting for analysis"
    * "[DEBUG] 5s timeout reached, auto-completing thought"

* **Test Plan**

  * Test rapid speech with brief pauses < 0.5s
  * Verify 0.5s pause triggers analysis
  * Test 5s pause auto-completes without LLM
  * Ensure mid-speech fragments aren't analyzed
  * Test timer cancellation on new text

* **Success / Acceptance Criteria**

  * No analysis of mid-speech fragments
  * Natural pauses (0.5s+) trigger thought detection
  * Long pauses (5s+) always complete the thought
  * 50%+ reduction in API calls
  * Configurable timing thresholds
  * Works with unpunctuated real-time transcription

---

## Glossary / References

* **ThreadPoolExecutor**: Python concurrent.futures for parallel execution
* **Pause Detection**: Detecting gaps in speech to identify thought boundaries
* **Auto-Complete Timeout**: 5-second rule for automatic thought completion
* **Timing-Based Detection**: Using speech pauses instead of punctuation
* **Discourse markers**: Words indicating continuation ("and", "but", "so")
* **Conversational completeness**: Whether speaker has finished expressing their thought
* **Mid-speech fragments**: Incomplete text captured during active speaking

---

## Final Acceptance Checklist

* [ ] All success criteria met
* [ ] Docs updated - N/A for MVP
* [ ] Metrics live - N/A for MVP
* [ ] Stakeholder sign-off - Amir approval
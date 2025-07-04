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
> Fix three critical issues in thought detection: 1) Premature detection of incomplete thoughts that happen to be grammatically complete, 2) Single-threaded LLM processing causing bottlenecks, and 3) Speech recognizer adding punctuation mid-speech causing false positives. Solution uses conservative detection prompts, ThreadPoolExecutor for parallel processing, and stability confirmation windows.

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
| Detection | Grammatical completeness | Conversational completeness |
| Debouncing | None | 500ms stability window |

---

## Milestones & Phases – Checklist View
* [ ] **Milestone 1 – Fix Thought Detection Issues** 🟡
  * [x] **Phase 1 – Conservative Detection** ✅ – Better prompt & threshold
  * [x] **Phase 2 – Parallel Processing** ✅ – ThreadPoolExecutor implementation
  * [ ] **Phase 3 – Stability & Continuation Handling** ⬜ – Stability window and premature punctuation handling
  * **Success Criteria**: No premature detection, 3x faster processing

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
# Same API, better behavior
detector.process_text("I went to the store") # Returns None (incomplete)
detector.process_text("I went to the store yesterday.") # Returns complete thought
```

---

## Detailed Implementation Plan

### Milestone 1 – Fix Thought Detection Issues

#### Phase 1 – Conservative Detection ✅

* **Implementation Steps**

  * [x] Update system prompt to emphasize conversational vs grammatical completeness
  * [x] Add examples: "I went to the store" (incomplete) vs "I went to the store." (complete)
  * [x] Include discourse markers as incompleteness signals ("and", "but", "so" at end)
  * [x] Increase confidence threshold from 0.7 to 0.8
  * [x] Add punctuation weight to detection logic

* **Test Plan**

  * [x] Test sentences that are grammatically complete but likely to continue
  * [x] Verify period vs no period makes a difference
  * [x] Test with common speech patterns that pause mid-thought

* **Success / Acceptance Criteria**

  * [x] "I went to the store" -> Not detected as complete
  * [x] "I went to the store." -> Detected as complete
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

#### Phase 3 – Stability & Continuation Handling

* **Implementation Steps**

  * [ ] Add pending thought state tracking:
    * `pending_thought`: Store detected complete thought
    * `pending_timestamp`: When detection occurred
    * `pending_result`: The analysis result
  * [ ] Implement 500ms stability confirmation window
  * [ ] Cancel pending thoughts if text continues growing
  * [ ] Make stability window configurable via parameter
  * [ ] Add debug output for cancelled/confirmed detections:
    * "[DEBUG] Complete thought detected (pending): {text}"
    * "[DEBUG] Pending thought cancelled - text continued"
    * "[DEBUG] Complete thought confirmed after {ms}ms"
  * [ ] Clean up abandoned futures and cancelled detections

* **Test Plan**

  * Test "Alright." → "Alright, this is..." cancellation
  * Verify 500ms stability before display
  * Rapid text updates within stability window
  * Ensure genuine complete thoughts aren't delayed excessively
  * Check memory cleanup of cancelled futures

* **Success / Acceptance Criteria**

  * No premature thought display when speech continues
  * Complete thoughts display after 500ms stability
  * Clear debug trail for troubleshooting
  * Reduces API calls by 50%+ during active speech
  * Configurable stability window
  * Handles speech recognizer's premature punctuation gracefully

---

## Glossary / References

* **ThreadPoolExecutor**: Python concurrent.futures for parallel execution
* **Debouncing**: Delay processing until input stabilizes
* **Stability Window**: Time period to confirm a complete thought hasn't continued
* **Pending Thought**: Complete thought awaiting stability confirmation
* **Discourse markers**: Words indicating continuation ("and", "but", "so")
* **Conversational completeness**: Whether speaker has finished their turn

---

## Final Acceptance Checklist

* [ ] All success criteria met
* [ ] Docs updated - N/A for MVP
* [ ] Metrics live - N/A for MVP
* [ ] Stakeholder sign-off - Amir approval
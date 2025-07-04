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
> **🚀 CURRENT PHASE:** *Milestone 1 – Phase 1* ✅ Complete  
> **🔜 NEXT STEPS:** *Phase 2 - Parallel Processing*

## Executive Summary
> Fix two critical issues in thought detection: 1) Premature detection of incomplete thoughts that happen to be grammatically complete, and 2) Single-threaded LLM processing causing bottlenecks. Solution uses conservative detection prompts and ThreadPoolExecutor for parallel processing.

## Architecture Snapshot – Before vs. After
### On-Disk Layout
|                 | **Before** | **After** |
| --------------- | ---------- | --------- |
| thought_detector.py | Single worker thread | ThreadPoolExecutor |
| Dependencies | threading, queue | + concurrent.futures |
| Configuration | Fixed prompt, 0.7 threshold | Conservative prompt, 0.8 threshold |

### Conceptual / Object Hierarchies
|                | **Before** | **After** |
| -------------- | ---------- | --------- |
| Processing | Sequential queue processing | Parallel future-based processing |
| Detection | Grammatical completeness | Conversational completeness |
| Debouncing | None | 200ms stability window |

---

## Milestones & Phases – Checklist View
* [ ] **Milestone 1 – Fix Thought Detection Issues** 🟡
  * [x] **Phase 1 – Conservative Detection** ✅ – Better prompt & threshold
  * [ ] **Phase 2 – Parallel Processing** ⬜ – ThreadPoolExecutor implementation
  * [ ] **Phase 3 – Debouncing** ⬜ – Stability window for updates
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

#### Phase 2 – Parallel Processing

* **Implementation Steps**

  * [ ] Import concurrent.futures.ThreadPoolExecutor
  * [ ] Replace single worker thread with pool (max_workers=3)
  * [ ] Submit analysis tasks as futures
  * [ ] Track text->future mapping
  * [ ] Process results as futures complete

* **Test Plan**

  * Submit multiple texts rapidly
  * Verify all get processed in parallel
  * Check result ordering is maintained

* **Success / Acceptance Criteria**

  * 3x faster processing for multiple updates
  * No dropped or duplicated results
  * Maintains FIFO result order

#### Phase 3 – Debouncing

* **Implementation Steps**

  * [ ] Add last_update_time tracking per text
  * [ ] Implement 200ms delay before submission
  * [ ] Cancel superseded analyses
  * [ ] Clean up abandoned futures

* **Test Plan**

  * Rapid text updates within 200ms window
  * Verify only final version gets analyzed
  * Check memory cleanup of cancelled futures

* **Success / Acceptance Criteria**

  * Reduces API calls by 50%+ during active speech
  * No analysis of intermediate states
  * Final text always gets analyzed

---

## Glossary / References

* **ThreadPoolExecutor**: Python concurrent.futures for parallel execution
* **Debouncing**: Delay processing until input stabilizes
* **Discourse markers**: Words indicating continuation ("and", "but", "so")
* **Conversational completeness**: Whether speaker has finished their turn

---

## Final Acceptance Checklist

* [ ] All success criteria met
* [ ] Docs updated - N/A for MVP
* [ ] Metrics live - N/A for MVP
* [ ] Stakeholder sign-off - Amir approval
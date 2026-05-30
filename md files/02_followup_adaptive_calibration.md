# Delta Deviation & Adaptive Calibration Logic

The Follow-up Agent functions as a real-time calibration engine. When data entered via the UI or Excel sheets drifts from the targets set by the Senior Orchestrator, apply this logic to update program variables.

---

## 1. The Adherence & Caloric Correction Tree
If user telemetry shows weight change metrics slipping outside of target parameters, adjust using this rule framework:

```text
               [Weekly Bodyweight Ingestion Uploaded]
                                │
       Is Target Track Weight Loss OR Lean Mass Accrual?
        ├── Fat Loss Track ──> Is Weight Stall > 14 Days?
        │                       ├── YES ──> Drop daily Carbs by 0.25g * kg
        │                       └── NO  ──> Hold baseline variables stable
        │
        └── Mass Gain Track ──> Is Weight Stall > 14 Days?
                                ├── YES ──> Advance daily calories by +150 kcal
                                └── NO  ──> Maintain current baseline energy
```

---

## 2. Direct Symptom-to-Somatic Adaptation Rules

| Detected Telemetry Shift | Trigger Condition / Threshold | Systemic Calibration Action |
| :--- | :--- | :--- |
| **Systemic Sleep Drop & High DOMS** | Subjective Sleep Score $\le 2$ AND Muscle Soreness $\ge 4$ over 3 consecutive days. | **Override:** Mandate dropping 1 working set from all Gym Tier A movements and add 15 minutes of passive Yin yoga recovery to the end of routines. |
| **Localized Joint Pain Alert** | Joint Integrity score falls $\le 2$ (Focus on wrists or anterior shoulders). | **Override:** Swap heavy calisthenics floor holds for parallel bar grips or forearm modifications. Drop barbell pressing movements for 1 week. |
| **High Satiety Disruption** | Nutritionist hunger ranking score hits 5 (Severe hunger) on a fat loss deficit track. | **Override:** Modify food layout without altering macros; replace 50% of fast-acting starches with high-volume, lower-glycemic fibrous vegetables. |

---

## 3. Bidirectional Excel Synchronization Logic
* **Ingestion Mapping:** When parsing an incoming user tracker spreadsheet, match column arrays directly to the global pipeline state variables (`progress_history`).
* **Format Requirements:** Rows missing more than 2 entries for working sets or macro tracking must be flagged, prompting the automated Support Agent to send a notification loop back to the user interface.
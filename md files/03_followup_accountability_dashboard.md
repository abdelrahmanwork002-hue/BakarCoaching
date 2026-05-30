# Master Accountability Dashboard & Re-Orchestration Rules

Use this high-level pipeline blueprint to monitor client trends over long-term macrocycles and manage automatic data handoffs to other coaching nodes.

---

## 1. 4-Week Progress Evaluation Index

### Category Alpha: The Progressive Adherence Zone (Score $\ge 85\%$)
* **Action Routing:** State automatically rolls over into the next scheduled week of the macrocycle. Generate a positive reinforcement message via the Customer Service agent node.
* **Macro Settings:** Retain baseline parameters assigned by the Senior Orchestrator.

### Category Beta: The Micro-Calibration Zone (Score $60\% - 84\%$)
* **Action Routing:** Trigger adaptive updates. Route data back to the Nutritionist or specialist sub-graphs to smooth out schedule conflicts or modify meal choices.
* **Macro Settings:** Apply small adjustments to volume or caloric layout to lower adherence barriers.

### Category Gamma: The Re-Orchestration Breakout (Score $< 60\%$)
* **Action Routing:** Trigger a hard state interrupt (`interrupt()`). The system locks further plan progression and halts automated loops.
* **Macro Settings:** Request a complete human manual review from the Senior Orchestrator to redesign the user's base requirements.

---

## 2. Multi-Agent Data Ingestion Lifecycle Timeline

```text
 [Sunday 21:00: User Uploads Weekly Progress Sheet via App or Excel Ingestion]
                                    │
                                    ▼
 [Follow-up Agent Parses Columns -> Computes Weekly Delta Deviations & Adherence]
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
   [Metrics Clear Safety]                                [Safety Threshold Broken]
   Passes updates to active state;                       Halts loop; flags data logs;
   prepares tracking sheet templates                     escalates to Senior Coach for
   for the upcoming week.                                physical manual verification.
```

---

## 3. Systemic Performance Telemetry Scorecard

| Metric Monitored | Target Goal | Danger Zone Warning (Requires Review) |
| :--- | :--- | :--- |
| **Weekly Compliance** | $\ge 6$ out of 7 targeted compliance marks met | $\le 4$ marked days inside a single tracking block |
| **Heart Rate Balance** | Morning resting heart rate stable $\pm 3	ext{ bpm}$ | Increase of $>6	ext{ bpm}$ tracking over 4 days consecutive |
| **Strength Trend** | Stable velocity or upward progress over 3 weeks | 3 consecutive drops in lift capacity or volume loads |
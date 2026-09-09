# Golden Evaluation Benchmark Set Documentation

## 1. Overview
- **Total Benchmark Cases**: 200 manually audited examples.
- **Target Brand**: `AppleSupport`.
- **Data Source**: Chronological holdout pool (`data/processed/holdout_pool.jsonl`, Nov 16 – Dec 03, 2017).
- **Leakage Prevention**: Strictly 0% overlap with the Historical Knowledge Base (both conversation ID and customer problem text).

## 2. Intent Distribution (Stratified & Balanced)
| Intent | Count | Percentage | Primary Expected Action | Primary Risk Level |
| :--- | :---: | :---: | :---: | :---: |
| `BATTERY_POWER` | 20 | 10.0% | Mixed | Mixed |
| `SOFTWARE_UPDATE` | 20 | 10.0% | Mixed | Mixed |
| `ACCOUNT_ACCESS` | 20 | 10.0% | Mixed | Mixed |
| `APP_STORE_BILLING` | 20 | 10.0% | Mixed | Mixed |
| `HARDWARE_DISPLAY` | 20 | 10.0% | Mixed | Mixed |
| `AUDIO_MEDIA` | 20 | 10.0% | Mixed | Mixed |
| `CONNECTIVITY_NETWORK` | 20 | 10.0% | Mixed | Mixed |
| `STORAGE_BACKUP` | 20 | 10.0% | Mixed | Mixed |
| `STORE_REPAIR_SERVICE` | 20 | 10.0% | Mixed | Mixed |
| `OUT_OF_SCOPE` | 20 | 10.0% | Mixed | Mixed |

## 3. Operational Routing & Risk Breakdown
- **AUTO_HANDLE Expected**: 129 (64.5%)
- **ESCALATE Expected**:    71 (35.5%)

### Risk Levels
- **LOW**:    129 (64.5%)
- **MEDIUM**: 31 (15.5%)
- **HIGH**:   40 (20.0%)

### Difficulty & Complexity Profiles
- **Canonical / Standard Queries**: 91
- **High-Risk Financial & Security Cases**: 2
- **Multi-Intent Complex Queries**: 89
- **Short / Noisy / Twitter Slang**: 18

## 4. Annotation Guidelines & Ambiguity Policy
1. **Primary Intent Rule**: If a customer reports multiple symptoms caused by an update (e.g. 'I updated and now battery dies'), the primary operational root cause takes precedence (`BATTERY_POWER` if battery troubleshooting is requested; `SOFTWARE_UPDATE` if update rollback/freeze is the core issue).
2. **Escalation Precaution Principle**: Financial transactions (`APP_STORE_BILLING`) and authentication lockouts (`ACCOUNT_ACCESS`) are categorically classified as `HIGH` risk and must `ESCALATE`. The agent must never attempt automated self-service resolution on financial disputes or credential recovery.
3. **Safe Automation Threshold**: Only inquiries with standard, safe, non-destructive troubleshooting steps (e.g. `Settings > General > Reset Network Settings`, cache clearing, version checks) and `LOW` risk are marked `AUTO_HANDLE`.
# Data inventory

Keep `inputs/` and the supplied paper unchanged. The model reads `fem_temp.csv` and `fem_act.csv` only; each has 20,160 one-minute rows and columns `f1`–`f13`. `male_temp.csv` and `male_act.csv` are retained for later analysis, not used in female estrus classification. All four files have a UTF-8 BOM that the loader handles.

`estrus prepare` creates ignored, reproducible outputs:

| Output | Meaning |
| --- | --- |
| `outputs/female_minutes.csv` | 224,640 rows: 156 analysis mouse-days × 1,440 minutes; keys plus `minute_of_day`, `cbt`, `la` |
| `outputs/mouse_days.csv` | All 156 canonical keys |
| `outputs/labels.paper_proxy.csv` | Provisional labels for positive recording days 2, 6, 10 |
| `outputs/labels.template.csv` | Blank targets/source; copy elsewhere before curating |

Only recording days 2–13 are analysis days. Days 1 and 14 are buffers. Day numbering is 1-based in the original CSV. No absolute timestamps are inferred. See [methods](../docs/METHODS.md) and [feature contract](../docs/FEATURE_CONTRACT.md).

The PDF is *Sex differences in variability across timescales in BALB/c mice*, Smarr et al. (2017), DOI 10.1186/s13293-016-0125-3. The article states CC BY 4.0 for the paper and a CC0 dedication for data made available in the article unless otherwise stated. The source of these specific classroom CSV exports and their alignment should be confirmed with the professor before wider redistribution or biological claims; no additional dataset license is asserted here.

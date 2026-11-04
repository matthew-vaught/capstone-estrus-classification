# Data inventory

Keep `data/inputs/` and the supplied paper unchanged. The model reads `fem_temp.csv` and `fem_act.csv` only; each has 20,160 one-minute rows and columns `f1`–`f13`. `male_temp.csv` and `male_act.csv` are unused by the shared female classifier; Alisha's separate exploratory analysis uses them as a control. All four files have a UTF-8 BOM that the loader handles.

`estrus prepare` creates ignored, reproducible outputs:

| Output | Meaning |
| --- | --- |
| `data/outputs/female_minutes.csv` | 224,640 rows: 156 analysis mouse-days × 1,440 minutes; keys plus `minute_of_day`, `cbt`, `la` |
| `data/outputs/mouse_days.csv` | All 156 canonical keys |
| `data/outputs/labels.paper_proxy.csv` | Provisional labels for positive recording days 2, 6, 10 |
| `data/outputs/labels.template.csv` | Blank targets/source; copy elsewhere before curating |

Only recording days 2–13 are analysis days. Days 1 and 14 are buffers. Day numbering is 1-based in the original CSV. No absolute timestamps are inferred. See [methods](METHODS.md) and [feature contract](FEATURE_CONTRACT.md).

The PDF is *Sex differences in variability across timescales in BALB/c mice*, Smarr et al. (2017), DOI 10.1186/s13293-016-0125-3. The article states CC BY 4.0 for the paper and a CC0 dedication for data made available in the article unless otherwise stated. The source of these specific classroom CSV exports and their alignment should be confirmed with the professor before wider redistribution or biological claims; no additional dataset license is asserted here.

## Version-control policy

The four original classroom CSVs remain tracked in `data/inputs/` so a professor or TA can run the submitted repository without a separate data upload. Their SHA-256 checksums are recorded in [input_manifest.json](references/input_manifest.json); `python run.py data` verifies them before preparing tables. This is an intentional exception to the course's general recommendation to exclude raw data from Git.

Small submitted `outputs/features.csv` files and existing extraction metadata also remain versioned handoff artifacts. They allow the shared model to run without changing or executing contributors' notebooks. Existing exploratory tables and figures are preserved with their owners' work. Root ignore rules exclude newly generated contributor outputs except the handoff, metadata, and directory placeholders; they do not retroactively remove tracked files.

Shared prepared data, build scratch files, and model-run folders are ignored. `python run.py data` writes its tables to `data/outputs/build/prepared/`; the lower-level `estrus prepare` retains its original `data/outputs/` destination. Only synthetic fixture definitions are needed for `python run.py test`.

## Source and labels

The classroom input filenames and checksums establish exactly which exports the code consumes. The upstream source/export procedure and the recording's row-zero clock alignment have not been independently confirmed. The supplied [paper](references/mouse_sex_diff.pdf) is the research reference, rather than proof of the classroom CSVs' exact biological staging.

Provisional positive recording days are 2, 6, and 10. Supply independent staging with `--labels PATH` using the [label schema](FEATURE_CONTRACT.md#label-csv-separate-from-features). Copy a generated blank template outside ignored outputs before curating it; do not treat a regenerable template as the authoritative label file.

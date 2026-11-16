# Mouse-relative features and an accuracy cutoff objective

Experiment completed November 15, 2026. **Outcome: one configuration improved accuracy and was adopted as the final model on November 15, 2026.**

The improving configuration is [mouse-relative-fixed-cutoff.json](../../config/mouse-relative-fixed-cutoff.json): mouse-relative features with a cutoff chosen by refitting one fixed model, one mouse at a time ([Step 4](#step-4-one-fixed-model-while-choosing-the-cutoff)). It beat the retained final setup in both evaluations:

- **All 13 mice, full pipeline:** 148/156 (94.9%) versus 145/156 (92.9%).
- **Standard 3-mouse test:** 35/36 (97.2%) versus 34/36 (94.4%).

Earlier arms (Steps 2–3) improved ranking but not accuracy. It replaced the previous final setup (original 28 features with the grouped-fold F2 cutoff); see [results](../RESULTS.md).

## What was tested

1. **Mouse-relative feature copies.** For every supplied feature, append `(value − that mouse's median) / that mouse's interquartile range`, computed over all of that mouse's days. A zero IQR gives 0. The original 28 features are kept, giving 56 inputs. The transform uses no labels and no other animals. It does use the same mouse's other days, so like the existing contributor features it supports retrospective classification only.
2. **Choosing the cutoff by plain accuracy** instead of F2, since accuracy was the stated goal.

**Why.** Some mice run warmer or more active than others. A raw value such as a high-temperature fraction means different things for different animals. The 2026-11-11 [research plan](estrus-improvement-2026-11-11.md) found every test mouse ranked its own estrus days nearly perfectly (per-mouse AP 1.0, 1.0, 0.917), while pooled ranking was worse. That pattern suggests between-mouse baseline differences. The earlier [Mouse Baseline experiment](../features/mouse-baseline.md) added only four relative features; this one rescales every feature.

## Step 1: leave-one-mouse-out screen

Before touching the pipeline, [lomo_benchmark_2026-11-15.py](lomo_benchmark_2026-11-15.py) compared transforms and model families on all 13 mice (156 days). Each mouse was predicted by a model fitted on the other twelve. Fixed settings were used without nested selection, and 54 setups were compared, so the best rows are optimistic.

| Features (logistic regression, C=1, top 35%) | Accuracy at 0.5 | AP |
| --- | --- | --- |
| Original 28 | 94.9% (148/156) | 0.968 |
| 28 + mouse-relative copies | 96.8% (151/156) | 0.987 |
| 28 + adjacent-day contrast (day minus mean of day before/after) | 96.2% (150/156) | 0.981 |
| Reference features only, raw | 84.6% | 0.739 |
| Reference features, mouse-relative + adjacent-day | 92.9% | 0.961 |

Other findings from the screen:

- **Model family was not the bottleneck.** Random forest, extra trees, shallow gradient boosting, and L1 logistic regression never beat logistic regression on any feature set.
- **Within-mouse comparison carries most of the signal.** The simple day-local reference features are weak raw but nearly match the contributor features once made mouse-relative. Contributor features already compare days within a mouse implicitly, for example Alisha's DTW shifts against the mouse's other 13 days and Matthew's next-day change.
- **F3 day 10 was missed in every setup.** Probabilities ranged from 0.04 to 0.11, and the model saw nothing estrus-like on f3 days 9–13. This is consistent with an irregular cycle in that mouse rather than a missing feature. The label was not changed.
- **Several false alarms fell on recording days 12–13,** where features needing future context have less data.

## Step 2: full pipeline on the reserved test mice

The full search, nested F2/accuracy cutoff selection, and calibration were run with the standard split (seed 190; test mice f3, f6, f11). Both cutoff objectives were crossed with both feature sets, and all four arms are reported.

| 36 test days, 9 estrus | Original 28 + F2 (**final**) | Original 28 + accuracy | Mouse-relative + F2 | Mouse-relative + accuracy |
| --- | --- | --- | --- | --- |
| Config | [threshold-f2](../../config/threshold-f2.json) | [threshold-accuracy](../../config/threshold-accuracy.json) | [mouse-relative-f2](../../config/mouse-relative-f2.json) | [mouse-relative-accuracy](../../config/mouse-relative-accuracy.json) |
| Features selected | 10 of 28 | 10 of 28 | 20 of 56 | 20 of 56 |
| Development AP | 0.9918 | 0.9918 | 0.9955 | 0.9955 |
| Test AP | 0.932 | 0.932 | **0.980** | **0.980** |
| Development-selected cutoff | 0.367 | 0.688 | 0.072 | 0.841 |
| Estrus detected | 7/9 | 5/9 | **9/9** | 3/9 |
| False alarms | 0/27 | 0/27 | 4/27 | 0/27 |
| **Accuracy** | **94.4%** | 88.9% | 88.9% | 83.3% |
| At cutoff 0.5 | 88.9% | 88.9% | 91.7% | 91.7% |

Exact values, selected features, errors, and hashes are in the [versioned record](../results/mouse-relative-2026-11-15.json). The first column reran the retained final configuration on the same machine and reproduced its recorded result exactly.

## Interpretation

**Mouse-relative features improved ranking.** Test AP rose from 0.932 to 0.980. With them, every f6 and f11 estrus day ranked above every non-estrus day. F3 day 10 rose from 0.05 to 0.11 but still ranked below a few non-estrus days. With F2, the model caught all 9 estrus days, including f3 day 10, at the cost of 4 false alarms on f6 days 12–13 and f11 days 4–5.

**The cutoff did not transfer between mice.** In development, estrus days scored higher than they did on the test mice. A cutoff anywhere between about 0.29 and 0.34 would have given 35/36 on the test mice with the mouse-relative model. The development data chose 0.072 under F2 and 0.841 under accuracy. That observation comes from inspecting test scores and must not be used to pick a cutoff.

**Plain accuracy is a fragile cutoff objective here.** With about 30 development estrus days, it chose its cutoff to gain a single development day (117/120 versus 116/120 at 0.5). It hurt both feature sets on the test mice. F2 or balanced accuracy remain the better-justified objectives. The `accuracy` option stays available for research, but is not recommended.

**Limits.** These three test mice have been inspected in several earlier experiments, and one test day equals 2.8 percentage points. The leave-one-mouse-out screen, with more evaluation days, favored mouse-relative features, while the 36-day test favored the current setup on accuracy. Neither is decisive. Labels remain the provisional days 2/6/10.

## Step 3: per-mouse scores and a different cutoff protocol

Since the cutoff did not transfer between mice, two follow-ups were tested the same day.

### Nested leave-one-mouse-out (all 13 mice)

[nested_lomo_score_norm_2026-11-15.py](nested_lomo_score_norm_2026-11-15.py) scores each mouse with a model fitted on the other 12. The cutoff is chosen on inner leave-one-mouse-out predictions of those 12 only, so the scored mouse's labels never influence fitting or the cutoff. The model was fixed to logistic regression, C=1, top 35%, without calibration. The 8 arms below were declared before running.

| Features | Decision score | Cutoff objective | Correct of 156 | Estrus caught | False alarms |
| --- | --- | --- | --- | --- | --- |
| Original 28 | probability | F2 | 148 (94.9%) | 37/39 | 6 |
| Original 28 | probability | balanced accuracy | 148 (94.9%) | 37/39 | 6 |
| Original 28 | per-mouse z-scored | F2 | 146 (93.6%) | 37/39 | 8 |
| Original 28 | per-mouse z-scored | balanced accuracy | 147 (94.2%) | 37/39 | 7 |
| **+ mouse-relative** | **probability** | **F2** | **152 (97.4%)** | 38/39 | 3 |
| + mouse-relative | probability | balanced accuracy | 152 (97.4%) | 38/39 | 3 |
| + mouse-relative | per-mouse z-scored | F2 | 148 (94.9%) | 38/39 | 7 |
| + mouse-relative | per-mouse z-scored | balanced accuracy | 151 (96.8%) | 38/39 | 4 |

- **Per-mouse score normalization did not help accuracy.** Rescaling each mouse's predicted scores within that mouse raised AP but lowered accuracy in every case. A likely reason is that z-scoring gives every mouse the same spread, so a mouse whose normal days are all clearly low still has some days pushed toward the cutoff.
- **Mouse-relative features with this cutoff protocol gave the best all-mice result:** 152/156, missing only f3 day 10 plus 3 false alarms. The chosen cutoffs stayed in 0.35–0.57, unlike the pipeline's 0.072. Applying the same fixed-model protocol to the standard split gave 35/36 (97.2%, cutoff 0.506).

### Full pipeline with the new protocol

Two opt-in settings were added so the pipeline could use this protocol:

- `"threshold_tuning": {"folds": "leave_one_mouse_out"}` scores each development mouse with models fitted on the other nine, instead of three grouped folds of about 6–7 fitting mice.
- `"calibration": false` uses the chosen pipeline's own probabilities. The SVM is still calibrated, because it has no probabilities of its own.

| 36 test days | Original 28 + F2 (**final**) | [Original 28, new protocol](../../config/threshold-lomo-cutoff.json) | [Mouse-relative, new protocol](../../config/mouse-relative-lomo-cutoff.json) |
| --- | --- | --- | --- |
| Test AP | 0.932 | 0.932 | 0.980 |
| Development-selected cutoff | 0.367 | 0.500 | 0.400 |
| Estrus detected | 7/9 | 8/9 | 8/9 |
| False alarms | 0/27 | 2/27 | 1/27 (f6 day 12, p = 0.434) |
| **Accuracy** | **94.4%** | 91.7% | **94.4%** (tie) |

**The full pipeline tied the retained setup rather than reaching the fixed-model 97.2%.** The pipeline re-runs its full model search inside each development fold. Across the ten folds it chose logistic regression with C = 0.1, 1, and 10, a depth-3 random forest, and an SVM. Their probabilities are on different scales, so the pooled development scores placed the cutoff at 0.400 rather than 0.506. That let f6 day 12 through. Restricting the search to logistic regression would likely recover the fixed-model result, but that choice would be made after inspecting these test mice several times, so it was not run.

## Step 4: one fixed model while choosing the cutoff

To remove the mixed probability scales, `"model_search": "fixed"` was added inside `threshold_tuning`. The pipeline chooses the model once on all development mice. It then refits that same model in every leave-one-mouse-out cutoff fold instead of searching again, so every development score comes from one model family on one scale.

**Caveat:** that model choice used every development mouse's labels, including the mouse held out in each cutoff fold. The cutoff-selection scores are therefore slightly optimistic. Reserved test mice are still never used.

### Evaluation on all 13 mice with the full pipeline

[all_mice_pipeline_2026-11-15.py](all_mice_pipeline_2026-11-15.py) runs the project's own `evaluate()` 13 times per configuration, holding out each mouse in turn with the new `test_mouse_ids` setting. All model search, cutoff selection, and fitting use only the other 12 mice. Unlike Step 3's nested test, this is the complete pipeline rather than a fixed model. Arms and the primary metric, pooled accuracy over 156 days, were declared before running.

| All 13 mice, full pipeline | Current final ([threshold-f2](../../config/threshold-f2.json)) | Fix without mouse-relative ([threshold-fixed-cutoff](../../config/threshold-fixed-cutoff.json)) | **Fix with mouse-relative** ([mouse-relative-fixed-cutoff](../../config/mouse-relative-fixed-cutoff.json)) |
| --- | --- | --- | --- |
| Correct of 156 | 145 (92.9%) | 145 (92.9%) | **148 (94.9%)** |
| Estrus caught | 33/39 | 37/39 | 37/39 |
| False alarms | 5 | 9 | 6 |
| Pooled AP | 0.955 | 0.944 | 0.968 |
| Errors by mouse (f1–f13) | 1 1 1 0 1 1 0 1 0 0 3 1 1 | 1 1 1 0 1 1 0 1 0 0 4 1 0 | 0 1 1 0 1 1 0 1 0 0 3 0 0 |

- **The fix is never worse on any mouse.** It is better on f1, f12, and f13, and identical elsewhere.
- **Its gain comes from catching more estrus days:** 37 versus 33, for one extra false alarm.
- **Both parts are needed.** Without mouse-relative features, the same cutoff method tied the current model, trading missed days for false alarms.
- **F11 has the most errors in every arm.** In that held-out run, both the current model and the fix chose a random forest.

The per-fold-search arm from Step 3 (`mouse-relative-lomo-cutoff`) was stopped after 2 of 13 mice because it needs about 156 model searches. It is not reported.

### Standard split

| 36 test days | Current final | **Fix with mouse-relative** |
| --- | --- | --- |
| Chosen model | logistic, C=1, 10 features | logistic, C=1, 20 of 56 features |
| Cutoff | 0.367 | 0.506 |
| Estrus detected | 7/9 | 8/9 |
| False alarms | 0/27 | 0/27 |
| **Accuracy** | 94.4% | **97.2%** |

The only remaining test error is f3 day 10. A same-day rerun of `config/threshold-f2.json` after the code changes reproduced its recorded 94.4% and cutoff exactly.

### Conclusion

Mouse-relative features combined with a fixed-model, leave-one-mouse-out cutoff improved accuracy in both evaluations:

| Evaluation | Current final | Fix |
| --- | --- | --- |
| All 13 mice (156 days) | 145 | 148 |
| Standard split (36 days) | 34 | 35 |

Both gains are small, and on the order of single days. The 13-mouse estimate is the stronger evidence: it uses all animals, and these arms were declared in advance. The configuration was nevertheless developed over several rounds on this same dataset, so new animals remain the real test. The user adopted it as the final model on November 15, 2026; the final build `final-2026-11-15` reproduced the 35/36 result exactly.

## Possible next steps

These are proposals, not completed work.

- **Use the all-mice pipeline evaluation as the main comparison.** It uses 156 days instead of 36, so future experiments are less sensitive to a single day.
- **Handle the last recording days better.** Several false alarms fall on days 12–13, where future-context features have less data.

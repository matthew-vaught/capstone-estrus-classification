# Collaboration and development workflow

The normal workflow gives each contributor exclusive edit ownership of their own `Name Feature Engineering/` directory, including their CSV. Matthew maintains `Model Building/`, `src/`, `tests/`, `docs/`, repository configuration, and the root documentation. Feature documentation is centralized in `docs/features/<owner>.md`; coordinate edits to another contributor's document. The original input CSVs remain tracked and unchanged; reference PDFs are in `docs/references/`.

This structure greatly reduces conflicts; Git cannot guarantee that no conflicts will ever occur. Do not reformat other people's notebooks, edit shared files casually, or commit generated model results. Ownership is a team convention; CODEOWNERS and protected-branch review requirements can enforce it after actual GitHub usernames are configured.

## Normal feature PR

```bash
git switch main
git pull --ff-only
git switch -c vivian/wavelet-features
# Work in Vivian Feature Engineering/ and docs/features/vivian.md
# Regenerate with her authoritative feature.ipynb; features.py is still a starter
estrus validate --owner Vivian
git add "Vivian Feature Engineering/" docs/features/vivian.md
git commit -m "Update Vivian's recording-level features"
git push -u origin vivian/wavelet-features
```

Open a PR with the features' rationale, definitions, units, missing-data rules, and validation result. Follow the same procedure using your own name. Run notebooks with the project `.venv` kernel; write their files relative to your folder or use explicit paths. Keep generated plot files there if useful for review. Avoid committing huge exploratory artifacts.

Other contributors do not need to run your script. Your committed, validated CSV is the interface, so dependencies used only by your exploration cannot break model building. Document any extra dependencies in your feature document under `docs/features/`. Scripts and notebooks must not write to another contributor's folder.

Keep your feature calculations, helper modules, notebooks, and tests in your own folder, even when you maintain shared infrastructure too. Contributor tests go in `tests/` within that folder and are included in the root pytest configuration. Feature-specific model/report notes belong in your optional `input_requirements.json`; see the [feature contract](FEATURE_CONTRACT.md). Adding or revising feature definitions should not require editing `src/`.

## Shared changes

Suggest shared loader, contract, or model changes to Matthew first. Put an approved shared change in a separate PR and run the full tests. Avoid changing the contract during a feature sprint. New feature columns can be added inside an owner's CSV without shared changes, as long as they follow the existing namespace and rules.

`src/estrus/` contains shared data loading, CSV validation, the reference baseline, model evaluation, and reporting. Root `tests/` checks that shared behavior; contributor-specific extraction tests stay with their contributor. A helper belongs in `src/` when it supports the shared pipeline or a common interface, rather than implementing one person's feature definition.

The repository includes a PR template and CI that tests infrastructure and validates available exports. No CODEOWNERS file names have been guessed for teammates; add their actual GitHub handles before configuring required code-owner review. Branch protection and GitHub permissions are remote settings and are not configured by this local scaffold.

## Results and labels

The retained final model uses the original 28 features with F2 cutoff tuning: `python run.py model --config config/threshold-f2.json --save-details`. Mouse Baseline and LA CBT Relationship were excluded from the final model. Preserve their experiment records without including their exports in the final run. The ordinary configuration still uses fixed cutoff 0.5 when `--config` is omitted; [results](RESULTS.md) records both setups.

Generated `data/outputs/` and `Model Building/results/` files are ignored. Run outputs should be shared as report attachments or release artifacts if the team wants to preserve a milestone. Contributor `outputs/features.csv` files and existing extraction metadata remain versioned handoffs. Historical exploratory outputs are preserved; new generated artifacts are ignored by default. See the [data policy](DATA.md#version-control-policy).

Maintain curated labels outside generated outputs (for example, an agreed `data/labels/confirmed.csv` added by the maintainer). `estrus prepare` regenerates templates and provisional labels, so do not edit its generated template in place without copying it elsewhere. Never use labels in feature generation, use the known 4-day position as a feature, or repeatedly tune features against the same held-out results while describing those results as an untouched test.

## Shared validation

Run `python -m pytest` and `python run.py validate` for shared changes. When changing the build, data interface, modeling, or reporting, also run `python run.py test`; it uses invented recordings and never writes to the real contributor folders. The pytest suite includes that synthetic build, and CI runs the suite plus export validation.

Default builds consume committed exports without rerunning extraction. `--regenerate` explicitly supports the established Matthew/Alisha scripts and the separate Mouse Baseline/LA CBT Relationship experimental extractors. Regenerating an excluded family's CSV does not enable it in the final configuration. Leave other contributors' implementation and notebooks under their ownership; necessary cross-folder changes should be coordinated. Keep reusable analysis functions in Python modules as contributors evolve their notebooks, and rerun notebooks top to bottom before submitting their updates.

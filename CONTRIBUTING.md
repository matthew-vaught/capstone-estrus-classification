# Working together without overlapping edits

The normal workflow gives each contributor exclusive edit ownership of their own `Name Feature Engineering/` directory, including their CSV. Matthew maintains `Model Building/`, `src/`, `tests/`, `docs/`, repository configuration, and the root documentation. The original inputs and paper should remain unchanged.

This structure greatly reduces conflicts; Git cannot guarantee that no conflicts will ever occur. Do not reformat other people's notebooks, edit shared files casually, or commit generated model results. Ownership is a team convention; CODEOWNERS and protected-branch review requirements can enforce it after actual GitHub usernames are configured.

## Normal feature PR

```bash
git switch main
git pull --ff-only
git switch -c vivian/wavelet-features
# Make changes only inside Vivian Feature Engineering/
python "Vivian Feature Engineering/features.py"
estrus validate --owner Vivian
git add "Vivian Feature Engineering/"
git commit -m "Add Vivian's day-local wavelet features"
git push -u origin vivian/wavelet-features
```

Open a PR with the features' rationale, definitions, units, missing-data rules, and validation result. Follow the same procedure using your own name. Run notebooks with the project `.venv` kernel; write their files relative to your folder or use explicit paths. Keep generated plot files there if useful for review. Avoid committing huge exploratory artifacts.

Other contributors do not need to run your script. Your committed, validated CSV is the interface, so dependencies used only by your exploration cannot break model building. Document any extra dependencies in your own folder. Scripts and notebooks must not write to another contributor's folder.

## Shared changes

Suggest shared loader, contract, or model changes to Matthew first. Put an approved shared change in a separate PR and run the full tests. Avoid changing the contract during a feature sprint. New feature columns can be added inside an owner's CSV without shared changes, as long as they follow the existing namespace and rules.

The repository includes a PR template and CI that tests infrastructure and validates available exports. No CODEOWNERS file names have been guessed for teammates; add their actual GitHub handles before configuring required code-owner review. Branch protection and GitHub permissions are remote settings and are not configured by this local scaffold.

## Results and labels

Generated `data/outputs/` and `Model Building/results/` files are ignored. Run outputs should be shared as report attachments or release artifacts if the team wants to preserve a milestone. Only contributor `outputs/features.csv` files are versioned handoffs.

Maintain curated labels outside generated outputs (for example, an agreed `data/labels/confirmed.csv` added by the maintainer). `estrus prepare` regenerates templates and provisional labels, so do not edit its generated template in place without copying it elsewhere. Never use labels in feature generation, use the known 4-day position as a feature, or repeatedly tune features against the same held-out results while describing those results as an untouched test.

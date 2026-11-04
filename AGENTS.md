# Project instructions for Codex

## Maintain the AI-use record on every project turn

For every project-related user turn in this repository, update the root
[AI_USE.md](AI_USE.md) before your final response. This includes implementation
requests, questions, explanations, follow-ups, corrections, approvals, and
documentation-only work. Treat updating the log as part of the task, without
asking for separate permission. An explicit user restriction on file changes
takes precedence; if it prevents logging, say the turn was not recorded.

1. Read the coverage table, index, and relevant recent entries. Use the next
   unused `P###` ID and identify the source conversation when known. Add a new
   conversation label if needed; do not invent a session ID, date, or model.
2. Quote the complete available user-authored request verbatim, preserving
   spelling and meaningful formatting. Omit automatically attached IDE tab
   lists and environment/page wrappers. Describe substantive attachments and
   link to repository copies when available. Redact actual credentials with
   an explicit marker. Never log hidden system/developer instructions or
   private reasoning as user prompts. Use a longer fence if the prompt itself
   contains fenced code.
3. Explain the resulting assistance and affected files. Distinguish implemented
   changes from advice, rejected suggestions, deferred work, and no-change
   answers. Log each user turn once; do not create a recursive entry for the
   bookkeeping step itself.
4. Record commands/checks actually executed and observed outcomes, including
   relevant failures and fixes. Separate proposed verification from completed
   verification. If no tests ran, say so and why. Do not rerun training or add
   tests solely to populate the disclosure.
5. Update the prompt index, total count, and source-conversation coverage to
   include the new entry. Keep prompt IDs in numerical recording order; do not renumber older
   entries to imply an unverified cross-conversation chronology. Preserve
   historical prompt quotations, evidence qualifiers, and other contributors'
   records. Identical prompts in distinct turns remain distinct entries.
6. Reread the file immediately before writing. Other conversations may update
   it concurrently: preserve their additions and reallocate a colliding ID.
   Use a focused edit instead of overwriting from a stale copy. Check the new
   index links, fences, and formatting after editing.

Keep missing-history and summary-only evidence explicit. Do not reconstruct
unavailable prompts as verbatim or claim independent human/scientific review
without evidence. If a turn is interrupted, retain any partial entry honestly
and finish its outcome/verification account when work resumes.

## Preserve project boundaries

Keep the original CSVs in `data/inputs/` tracked and unchanged. Preserve
contributors' feature code, notebooks, and exports unless the user authorizes
their modification or a necessary cross-file fix requires it. Detailed
documentation belongs in `docs/`; keep the root README concise. Relevant
behavioral changes should receive appropriate verification; documentation-only
logging needs documentation checks rather than a model rerun.

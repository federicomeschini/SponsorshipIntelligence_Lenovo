# Agent instructions

These rules apply to every contributor, human or AI agent, working in this repository.

## Human-review output standard

Every substantive data pipeline, analysis, model, experiment, scenario, evaluation, or stakeholder-facing result must create or update a human-review artifact.

Prefer a guided notebook when interactive calculations, diagnostics, tables, or charts materially improve the review. Use a documented Markdown, HTML, or report artifact when a notebook would add no meaningful value.

Write for an intelligent reader who may have little knowledge of the project history, repository structure, internal terminology, or implementation details.

Use the following structure:

1. **Question and purpose:** State the question being answered, why it matters, and which project objective it supports.

2. **Evidence and inputs:** Identify the input data, documents, APIs, assumptions, source organizations, versions or vintages, coverage, and relevant definitions. Clearly label each important input as observed, constructed, estimated, proxied, borrowed, simulated, or assumed.

3. **Method and formulas:** Explain the method and show the central equations or algorithms. Define every symbol, parameter, unit, transformation, threshold, and convention. Explain each formula in plain language immediately after presenting it.

4. **Calculation path:** Document the complete passage from raw inputs to cleaned or transformed data, function or model calls, diagnostics, intermediate results, and reported outputs. Link each step to its reproducible script, module, configuration, or callable function.

5. **Results:** Display important intermediate calculations, validation results, and final outputs in readable tables and charts. Do not rely only on raw logs, serialized files, JSON dumps, or unexplained file paths.

6. **Interpretation:** Explain what the result means in practical terms, including its direction, magnitude, unit, period or horizon, reference case, uncertainty, and decision relevance.

7. **Limitations and non-claims:** State what the result does not establish. Explicitly distinguish, where relevant, between:

   - observed and constructed data;
   - descriptive association and causal effect;
   - interpolation, nowcast, forecast, and scenario;
   - in-sample and out-of-sample evidence;
   - local and generalizable conclusions;
   - aggregate and disaggregated results;
   - statistical uncertainty and unmodelled uncertainty.

## Review-artifact rules

- Keep production logic in the project’s production-code directories. Review notebooks and documents must import, call, and inspect that logic rather than duplicate transformations, estimators, business rules, or algorithms.

- Default to read-only inspection. Any operation that rewrites data, regenerates outputs, calls external services, or changes state must be clearly labelled and disabled by default through an explicit flag such as `RUN_REBUILD = False`.

- Use descriptive names and labels. Tables must show units, dates or vintages, definitions, and relevant sample sizes. Avoid unexplained internal variable names in reader-facing outputs.

- Charts must have a meaningful title, labelled axes, units, readable legends, and reference lines or uncertainty bands where relevant. Captions must explain the main takeaway and any important limitation.

- Pair every formula with a plain-language explanation and connect its symbols to the actual input columns, parameters, or output fields used by the implementation. Do not include mathematical notation merely for decoration.

- Show diagnostics appropriate to the method. Examples include:

  - data coverage, missingness, duplicates, reconciliation, and transformation checks;
  - model fit, stability, residuals, calibration, validation, and forecast performance;
  - feature importance, coefficients, loadings, sensitivities, or ablations;
  - scenario assumptions, reference paths, uncertainty bands, and robustness checks;
  - software tests, performance measurements, failure cases, and edge conditions.

- Do not hide failed, weak, ambiguous, or non-informative diagnostics. Explain what they imply for interpretation, reporting, and next steps.

- Keep review artifacts deterministic, lightweight, and safe to open. Expensive, slow, destructive, or externally connected operations must remain explicitly opt-in.

- Make uncertainty visible. Separate uncertainty represented by the method from important uncertainty that remains outside the model or calculation.

- Validate the review artifact before completion. Confirm that its code runs, formulas match the implementation, tables and charts use current outputs, links resolve, and rebuild flags remain safe.

## Continuous synchronization requirement

Treat every notebook or equivalent review artifact as a living companion to the production output, not as a one-time deliverable or end-of-project documentation task.

The review-artifact update is part of the analytical change itself.

- Keep every review artifact accurate and current throughout the project.

- Update and validate the related artifact in the same change or working session whenever any of the following changes:

  - input data or input contracts;
  - source versions or vintages;
  - definitions, assumptions, or classifications;
  - transformations or calculations;
  - schemas, filenames, or file paths;
  - configuration or model specifications;
  - diagnostics or validation results;
  - interpretation or limitations;
  - intermediate or headline results.

- Ensure that displayed or cached tables, charts, formulas, narrative, dates, sample periods, source vintages, paths, and version references agree with the current production files.

- Re-run or refresh review outputs whenever necessary to prevent saved notebook results from describing an older production state.

- Do not present stale notebook output, documentation, tables, or charts as current.

- Do not mark analytical work complete, ready for review, ready for delivery, or suitable for stakeholder use while its review artifact is missing or out of date.

- If synchronization is temporarily impossible:

  1. clearly label the artifact as stale;
  2. identify the affected output, version, or date;
  3. explain why synchronization could not be completed;
  4. describe the likely consequences for interpretation;
  5. record the required update as an immediate action or blocker.

A stale artifact is an explicitly documented exception, not a completed deliverable.

## Definition of done

A substantive analytical output is complete only when its review artifact reflects the current production state and a low-context reader can answer:

- What question was addressed?
- Why does it matter?
- What evidence and assumptions were used?
- Which inputs are observed, constructed, estimated, proxied, borrowed, simulated, or assumed?
- How was the result calculated?
- Which code, configuration, or process reproduces it?
- What do the intermediate calculations show?
- What do the tables, charts, and diagnostics show?
- What does the result mean?
- How uncertain is it?
- What does it not prove?
- Are the artifact and its displayed results synchronized with the current production files?
- What should happen next?

If the review artifact is missing, outdated, inconsistent with production, or not reproducible, the substantive output is not finished.

## Applying these rules in this repository

- **Production code** lives in `srmp/` (connectors in `srmp/ingest/`, estimators in `srmp/counterfactual/`, one module per experiment in `srmp/experiments/`). Configuration lives in `config/`; reference inputs in `data/reference/`.
- **Rebuild** every derived artifact with `python -m srmp.pipeline` (add `--with-pulls` to refresh sources, `--tests` to run the suite). Review artifacts must not call this unless a `RUN_REBUILD`-style flag is explicitly enabled.
- **Review artifacts** live in `reports/methods_annex/` (one per experiment or pipeline stage). Experiment outputs that a review artifact reads live in `data/curated/`.
- **Decisions** that change a method, assumption, input, or guardrail are logged in `DECISIONS.md` (append-only ADRs) in the same change. The locked design is in `ARCHITECTURE.md`.

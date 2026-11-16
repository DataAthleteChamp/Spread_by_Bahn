# Technical presentation

**10 slides**, with one claim per slide and matched-week margin/on-time evidence
for the deployed ideas. Company facts, simulator results and future proposals
are labelled separately.

- [PDF](Spread-The-Delusionals.pdf): ready to present or upload.
- [PowerPoint](Spread-The-Delusionals.pptx): editable slides, with speaker notes.
- [HTML](slides.html): browser presentation and print view.
- [Full-deck preview](preview.png).
- [Speaker notes](SPEAKER_NOTES.md) and [verified sources](SOURCES.md).
- [Evidence](evidence.json): paired cohorts, full world IDs and bootstrap intervals.

The deck covers Bahn's business, the deployed ML/dispatch architecture, three
measured economic ideas, delivery-share protection, rejected experiments, and
a proposed ML/data/production roadmap. Historical effects are not additive and
are not company ROI forecasts.

## Official final outcome

The real final ended with **EUR0, zero orders and no rank**: the execution host
slept and could not remain connected, leaving 1,034 requests unquoted.
See [the postmortem](../POSTMORTEM.md) and
[official outcome record](../results/final-outcome.json).
On-time is displayed as **N/A** for zero orders, not 100%.
Review every slide and speaker note; the PDF contains the slides, not the notes.

## Rebuild without touching the live environment

From the repository root:

```sh
# Isolated exporter dependencies; do not install these into the live environment.
.venv/bin/python -m venv data/.slides-venv
data/.slides-venv/bin/python -m pip install -r submission/requirements.txt

# Existing recorded data only: no fitting, new worlds or game actions.
.venv/bin/python submission/build_evidence.py
data/.slides-venv/bin/python submission/build_presentation.py
```

The same layout primitives generate PDF, PowerPoint and HTML. The exporter checks
text-box capacity before writing slides. `build-manifest.json` records package
versions and content hashes. The real-final card uses the archived official
outcome; a rehearsal is always kept distinct. Rebuilding does not replay the final.

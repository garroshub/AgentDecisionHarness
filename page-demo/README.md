# Page Demo

Static interactive console for the explainable financial prediction harness.

Run locally:

    python -m http.server 8000 --directory page-demo

Open:

    http://localhost:8000

The demo includes preset financial tasks and policy configurations, editable candidate forecasts, authority-gate controls, CLI-style decision output, evidence, final forecast records, audit checks, and configuration fingerprints.

No backend or provider API is required.

Logic check:

    node page-demo\test_logic.js

# Backend-Emitted Diagnostics

This directory contains diagnostic JSON generated from the service/backend path.
These files are not gating conformance fixtures yet. They prove what the current
backend can emit as real `RuntimeEnvelope` and `ProjectedState` payloads before
genre demos such as CarWars rely on the widget framework.

Regenerate with:

```bash
poetry run python engine/contrib/conformance/backend_widget_demo.py
```

Promotion rule: move a diagnostic payload into `fixtures/` only after the
backend shape, reference ports, and conformance harness agree that it should be
part of the portable client floor.

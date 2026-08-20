# SafeBump Demo Runbook

Target duration: 3 minutes 45 seconds. Record a real terminal run, not slides.

## 0:00–0:30 — Problem and scope

SafeBump handles one narrow job: it attempts direct Python dependency upgrades one at a time and keeps only changes supported by the target tests and `pip check`. It works locally and stops before remote or major-version actions.

## 0:30–1:10 — Architecture and design decision

Show the README decision flow and then the terminal. Explain this design decision in your own words:

> I considered letting a language model decide whether a failed check was acceptable. I rejected that for the keep-or-rollback boundary. Pytest and pip check have deterministic exit codes, so the safer and more auditable rule is simple: both must pass. The model could help explain evidence, but it must not reinterpret a failed safety gate.

## 1:10–2:35 — The main moment: automatic rollback

Use the committed EVAL-02 fixture and show the complete attempt. Keep the terminal large enough to read:

```bash
git switch local/safebump-run
source .venv/bin/activate
python safebump.py --approve-major-demo --report reports/demo-test-rollback.md
```

Narrate the observed sequence: SafeBump creates the candidate branch, installs HTTPX `1.0.dev3`, `pip check` remains clean, pytest collection fails because `httpx.BaseTransport` is absent, and the agent chooses rollback. Then show that `httpx==0.28.1` is restored and the baseline returns to six passing tests plus clean dependency metadata.

If the live package index no longer exposes the same candidate, do not improvise or claim a live regression. Use the committed raw run and report as historical evidence, explain why the external candidate changed, and record a fresh controlled fixture run separately.

## 2:35–3:15 — Limitation

Explain this limitation directly:

> A green result does not prove the upgrade is completely safe. The six tests cover only the behavior they execute, and pip check validates declared dependency metadata rather than application APIs. Production traffic, concurrency, performance, and undeclared semantic incompatibilities remain outside this evidence.

## 3:15–3:45 — Guardrail and close

Show the remote-action gate and state that SafeBump never pushes, opens a pull request, or merges without action-specific approval. End on the generated report and its concrete evidence, not on a claim of complete safety.

## Recording acceptance check

- The video is between three and five minutes.
- The rollback decision and restored baseline are readable.
- One rejected alternative is named with the design decision.
- One verification limitation is spoken explicitly.
- The run is real and the narration explains why each transition happens.
- No secrets, personal tokens, notifications, or unrelated terminal history are visible.
- The final upload is unlisted and playable while logged out.

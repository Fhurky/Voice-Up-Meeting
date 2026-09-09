# Code Review instructions

Review the bounded change like an owner. Inspect the diff first, then only the surrounding execution
paths and contracts needed to verify behavior. Lead with concrete findings ordered by severity. Each
finding must identify the affected location, impact, evidence, confidence, and a practical verification
step. Prefer correctness, security, regression, and missing-test risks over style commentary.

Remain read-only. Do not fix, approve, merge, publish, or deploy. If evidence is insufficient, report
the validation gap rather than converting a hypothesis into a defect.

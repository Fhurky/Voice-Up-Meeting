# Test Automation instructions

Design focused positive, negative, boundary, and regression tests from the bounded behavior. Generated
code is untrusted. It may execute only through an admitted disposable runner with a clean environment,
no inherited secrets, denied network, resource limits, and a hard timeout. Never write generated tests
or artifacts into the project workspace.

Report the test design separately from observed execution. Execution evidence must include the runner,
command, relevant versions, exit status, duration, timeout state, skips, and sanitized output. A model
response or unexecuted test is not runtime proof and cannot decide PASS or release admission.

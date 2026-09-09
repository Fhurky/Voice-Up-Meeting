# Local governance reconciliation

The global MCP exchanges bounded metadata and canonical governance intent only. It never receives
workspace source, secrets, dependency trees, database data or execution output, and it never
returns a filesystem patch.

The local coding agent owns semantic comparison, edits, database work, tests and evidence. It may
adapt wording and strengthen constraints. Mandatory behavior must remain intact; recommended
material may be accepted, adapted, deferred or rejected with a recorded rationale; project-owned
material remains outside central control.

For an update, export the bounded project manifest, request an update proposal, fetch only the
selected changed artifacts, reconcile local copies, run the applicable local gates and record every
decision. A reconciliation receipt is a local-agent attestation, not proof that the MCP inspected or
validated the workspace.

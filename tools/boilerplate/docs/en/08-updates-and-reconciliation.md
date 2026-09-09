# Updates and reconciliation

Keep two update paths separate:

- **Local scaffold update:** `kt-scaffold update` computes managed files from answers and generator
  version.
- **Central governance update:** MCP `governance_update_check` compares bounded project metadata
  with the canonical artifact catalog and returns decision intent to the local agent.

MCP does not call `update` remotely, and the CLI does not pretend to own a central catalog.

## Local scaffold update

1. Inspect the worktree and user changes.
2. Obtain the approved new `kt-scaffold` version through the closed supply chain.
3. Read its change scope and release evidence first.
4. Run `kt-scaffold update --target-dir ... --set key=value`.
5. Do not claim success before resolving conflicts and warnings.
6. Run client-projection drift, config sync, dependency admission and the quality gate.
7. Record generator version and admission evidence in the same change set.

Because backend/persistence is fixed, attempting to change it as an “update option” is not a valid
migration. Such an architecture change requires a new profile design and separate governance
decision.

## Central artifact reconciliation

`governance_update_check` derives only changed or unknown artifacts from manifest inventory
digests/versions. Then:

1. read `artifact_id`, `authority`, `required_behaviors` and `local_instruction` in the proposal;
2. retrieve only required artifact bodies;
3. compare the local file semantically;
4. record an `accepted`, `adapted`, `deferred` or `rejected` decision and rationale for every item;
5. explicitly list preserved behaviors for an adapted mandatory item;
6. run local gates;
7. validate the decision set with `reconciliation_validate`;
8. persist the receipt and current inventory only after accepting the change.

Silently weakening, deferring or rejecting mandatory behavior leaves reconciliation unresolved.
Recommended artifacts can be handled differently with rationale. Project-owned content is not
replaced by a central body.

## Conflict principle

Do not automatically overwrite a managed file that conflicts with a product need. Present and
record the decision using three questions:

- Which canonical behavior is mandatory?
- Which product need and accepted PRD does the local change satisfy?
- What is the smallest semantic adaptation that preserves both?

Move the result into a source rule or accepted PRD; do not leave it only in chat history.

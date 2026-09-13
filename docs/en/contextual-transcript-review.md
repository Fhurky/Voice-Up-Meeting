# Review transcript words in context

In a completed meeting's **Transcript** section, select **Check words in
context** on a turn. The panel lists this installation's Ollama language
models. Choose an available model and select **Check**. Selecting a model
alone starts no review and downloads no model. An unavailable default
does not cause an automatic switch to another model.

The model reviews the original turn with nearby conversation context.
Changes that map exactly to the source appear green and underlined in
**Suggested text**. The **Original → Suggestion** list compares each old
and new word. Changes to names, numbers or meaning remain visible with
an additional review notice; the notice is not a correctness guarantee.
Use **Listen to this section** to compare uncertain words with the source
audio.

Proposals without an unambiguous source location, or with overlapping
locations, appear in the separate list without an invented text position.
**Full model response** details show plain text even when the output cannot
be parsed as valid edits. A truncated response is identified explicitly.
Unmapped or malformed output cannot be saved. No suggested change does
not prove that the transcript is correct.

After reviewing a proposal, select **Save corrected version** to store a
separate version. Only this explicit action saves it; the original text,
speaker, audio and timestamps remain intact. Saved changes appear green
after a page reload. **Original / Corrected** switches between the two
views. Another model review always uses the original transcript.
Changed words receive no exact audio timestamps.

Changing the model, turn or meeting clears the previous proposal and save
option. Request a new review if the proposal expires or another correction
has been saved. If a save response is lost, retrying the same proposal does
not create a duplicate version. Closing the panel does not guarantee that
an already started server computation stops.

New reviews and saves require both meeting read and analysis run
permissions; readers can also view previously saved versions. Local text
review must be enabled in the installation. Long turns, unavailable
models and timeouts receive explanations while the original remains
readable. Close and reopen the panel to refresh a changed model list.
Text review remains available after source audio removal while the
meeting transcript is retained.

Behavior source: [accepted requirements](../../specs/speaker-identity/PRDs/013-model-selection-saved-corrections/PRD.md).

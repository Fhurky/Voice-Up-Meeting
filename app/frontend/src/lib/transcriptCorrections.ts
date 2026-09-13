import { ApiError } from "@/lib/apiClient";
import type { components } from "@/types/api";
type CorrectionSuggestion = components["schemas"]["TranscriptCorrectionSuggestion"];
type MeetingTranscript = components["schemas"]["MeetingTranscriptResponse"];
type SavedCorrection = components["schemas"]["SavedTranscriptCorrection"];

export type CorrectionEdit = SavedCorrection["edits"][number];
export function invalidCorrection() { return new ApiError(502, "Invalid correction response", "invalid_response"); }

export function correctionParts(source: string, edits: readonly CorrectionEdit[]) {
  if (!Array.isArray(edits) || edits.length > 3) throw invalidCorrection();
  const points = Array.from(source), parts: { text: string; original?: string }[] = [];
  let cursor = 0;
  for (const edit of edits) {
    if (!edit || !Number.isInteger(edit.start_char) || !Number.isInteger(edit.end_char) || edit.start_char < cursor || edit.end_char <= edit.start_char || edit.end_char > points.length ||
      typeof edit.original !== "string" || typeof edit.replacement !== "string" || !edit.replacement || Array.from(edit.replacement).length > 64 || points.slice(edit.start_char, edit.end_char).join("") !== edit.original) throw invalidCorrection();
    parts.push({ text: points.slice(cursor, edit.start_char).join("") }, { text: edit.replacement, original: edit.original });
    cursor = edit.end_char;
  }
  parts.push({ text: points.slice(cursor).join("") });
  return parts;
}

export async function verifySourceHash(text: string, hash: string) {
  if (typeof hash !== "string" || !/^[a-f0-9]{64}$/.test(hash)) throw invalidCorrection();
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  if (Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, "0")).join("") !== hash) throw new ApiError(409, "Source changed", "transcript_changed");
}

export function mappedEdits(result: CorrectionSuggestion): CorrectionEdit[] {
  if (!Array.isArray(result.proposals) || result.proposals.length > 3) throw invalidCorrection();
  const edits: CorrectionEdit[] = [];
  for (const proposal of result.proposals) {
    if (!proposal || typeof proposal.original !== "string" || typeof proposal.replacement !== "string" || !["checked", "review_required", "unmapped"].includes(proposal.assessment)) throw invalidCorrection();
    if (proposal.assessment === "unmapped") {
      if (proposal.start_char !== null || proposal.end_char !== null) throw invalidCorrection();
    } else {
      if (proposal.start_char === null || proposal.end_char === null) throw invalidCorrection();
      edits.push({ start_char: proposal.start_char, end_char: proposal.end_char, original: proposal.original, replacement: proposal.replacement });
    }
  }
  return edits.sort((left, right) => left.start_char - right.start_char);
}

export async function verifySuggestion(result: CorrectionSuggestion, turn: MeetingTranscript, model: { name: string; digest: string }) {
  if (!result || result.transcript_public_id !== turn.public_id || result.original_text !== turn.text) throw new ApiError(409, "Source changed", "transcript_changed");
  if (result.model_name !== model.name || result.model_digest !== model.digest) throw new ApiError(503, "Model changed", "text_review_model_mismatch");
  if (result.expected_revision !== (turn.correction?.revision ?? 0)) throw new ApiError(409, "Revision changed", "correction_conflict");
  if (!["unchanged", "suggested", "unmapped", "invalid_output"].includes(result.status) || typeof result.model_output !== "string" || Array.from(result.model_output).length > 8192 || typeof result.model_output_truncated !== "boolean" || result.policy_version !== "tr-context-words-v2") throw invalidCorrection();
  await verifySourceHash(turn.text, result.source_text_sha256);
  const edits = mappedEdits(result);
  if (correctionParts(turn.text, edits).map((part) => part.text).join("") !== result.suggested_text) throw invalidCorrection();
  if (result.save_token && (!result.expires_at || !Number.isFinite(Date.parse(result.expires_at)) || result.model_output_truncated || result.status !== "suggested" || edits.length === 0 || edits.length !== result.proposals.length)) throw invalidCorrection();
}

export async function verifySavedCorrection(result: SavedCorrection, source: string) {
  if (!result || !Number.isInteger(result.revision) || result.revision < 1 || typeof result.corrected_text !== "string") throw invalidCorrection();
  await verifySourceHash(source, result.source_text_sha256);
  if (correctionParts(source, result.edits).map((part) => part.text).join("") !== result.corrected_text) throw invalidCorrection();
}

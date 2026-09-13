import type { CorrectionSuggestion, MeetingTranscript, ReviewModelList, SavedCorrection } from "@/services/meetings";
import { transcript } from "@/test/meetingFixtures";

export const correctionTurn: MeetingTranscript = { ...transcript, text: "Yeni sürüyü sunucuya yükledik." };
export const reviewModels: ReviewModelList = { items: [
  { name: "qwen3.5:27b", digest: "a".repeat(64), size_bytes: 27_000_000_000, selectable: true, unavailable_reason: null, is_default: true },
  { name: "qwen3.5:12b", digest: "b".repeat(64), size_bytes: 12_000_000_000, selectable: true, unavailable_reason: null, is_default: false },
  { name: "qwen3.5:9b", digest: "c".repeat(64), size_bytes: 9_000_000_000, selectable: true, unavailable_reason: null, is_default: false },
] };
export async function correctionSuggestion(source = correctionTurn, changed = true): Promise<CorrectionSuggestion> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(source.text));
  const start = Array.from(source.text.split("sürüyü")[0]).length;
  return {
    transcript_public_id: source.public_id, source_text_sha256: Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, "0")).join(""),
    original_text: source.text, suggested_text: changed ? source.text.replace("sürüyü", "sürümü") : source.text,
    status: changed ? "suggested" : "unchanged", proposals: changed ? [{ start_char: start, end_char: start + 6, original: "sürüyü", replacement: "sürümü", assessment: "checked", reason: null }] : [],
    model_output: changed ? '{"edits":[{"original":"sürüyü","replacement":"sürümü"}]}' : '{"edits":[]}', model_output_truncated: false,
    expected_revision: source.correction?.revision ?? 0, save_token: changed ? "signed-preview-proof" : null, expires_at: changed ? new Date(Date.now() + 900_000).toISOString() : null,
    model_name: "qwen3.5:27b", model_digest: "a".repeat(64), policy_version: "tr-context-words-v2",
  };
}
export async function savedCorrection(source = correctionTurn): Promise<SavedCorrection> {
  const suggestion = await correctionSuggestion(source);
  return { public_id: "a512f497-a23d-4aa8-8334-e63bcd6a0803", revision: (source.correction?.revision ?? 0) + 1,
    corrected_text: suggestion.suggested_text, source_text_sha256: suggestion.source_text_sha256,
    edits: suggestion.proposals.map((proposal) => ({ start_char: proposal.start_char!, end_char: proposal.end_char!, original: proposal.original, replacement: proposal.replacement })),
    model_name: suggestion.model_name, model_digest: suggestion.model_digest, policy_version: suggestion.policy_version, saved_at: new Date().toISOString() };
}

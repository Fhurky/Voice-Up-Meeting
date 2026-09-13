import { useEffect, useId, useRef, useState } from "react";
import { useIntl } from "@/contexts/IntlContext";
import { InlineWordChanges } from "@/components/CorrectedTranscriptText";
import { ApiError } from "@/lib/apiClient";
import { invalidCorrection, mappedEdits, verifySavedCorrection, verifySuggestion } from "@/lib/transcriptCorrections";
import { MeetingService, type CorrectionSuggestion, type MeetingTranscript, type ReviewModel, type SavedCorrection } from "@/services/meetings";

type Props = { meetingId: string; turn: MeetingTranscript; onClose: () => void; onSaved?: (correction: SavedCorrection) => void };
const errorKeys: Readonly<Record<string, string>> = {
  text_review_unavailable: "meeting.review.unavailable", text_review_model_mismatch: "meeting.review.modelChanged",
  text_review_timeout: "meeting.review.timeout", text_review_invalid_response: "meeting.review.invalid",
  text_review_context_limit: "meeting.review.tooLong", transcript_changed: "meeting.review.changed",
  meeting_state_conflict: "meeting.review.notReady", invalid_response: "meeting.review.invalid",
  invalid_correction_token: "meeting.review.tokenExpired", correction_conflict: "meeting.review.conflict",
};
const reasonKeys: Readonly<Record<string, string>> = {
  semantic_review: "meeting.review.requiresCheck", source_not_found: "meeting.review.sourceNotFound",
  ambiguous_source: "meeting.review.ambiguousSource", overlapping_edits: "meeting.review.overlappingEdits",
  unsupported_characters: "meeting.review.unsupportedCharacters",
};
const unavailableKeys: Readonly<Record<string, string>> = {
  remote_model: "meeting.review.modelRemote", not_language_model: "meeting.review.modelNotLanguage",
  model_changed: "meeting.review.modelChanged", default_changed: "meeting.review.modelChanged",
  metadata_unavailable: "meeting.review.modelMetadata",
};
function errorKey(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) return "meeting.review.forbidden";
    if (error.status === 404 || error.status === 410) return "meeting.review.missing";
    if (Object.hasOwn(errorKeys, error.code)) return errorKeys[error.code];
  }
  return "meeting.review.failed";
}

export function MeetingTextReview(props: Props) {
  return <ReviewSelection key={`${props.meetingId}:${props.turn.public_id}:${props.turn.text}:${props.turn.correction?.revision ?? 0}`} {...props} />;
}

function ReviewSelection({ meetingId, turn, onClose, onSaved }: Props) {
  const { t } = useIntl();
  const selectId = useId();
  const [models, setModels] = useState<ReviewModel[] | null>(null);
  const [modelName, setModelName] = useState("");
  const [modelRetry, setModelRetry] = useState(0);
  const [modelError, setModelError] = useState<string | null>(null);
  const [result, setResult] = useState<CorrectionSuggestion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveBlocked, setSaveBlocked] = useState(false);
  const request = useRef<AbortController | null>(null);
  const saveRequest = useRef<AbortController | null>(null);
  useEffect(() => () => { request.current?.abort(); saveRequest.current?.abort(); }, []);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.resolve().then(async () => {
      if (controller.signal.aborted) return;
      const response = await MeetingService.reviewModels(controller.signal);
      if (!Array.isArray(response.items) || response.items.length > 100 || new Set(response.items.map((item) => item.name)).size !== response.items.length) throw invalidCorrection();
      if (!controller.signal.aborted) {
        setModels(response.items); setModelError(null);
        setModelName(response.items.find((item) => item.is_default && item.selectable)?.name ?? "");
      }
    }).catch((failure: unknown) => { if (!controller.signal.aborted) setModelError(errorKey(failure)); });
    return () => controller.abort();
  }, [modelRetry]);
  const model = models?.find((item) => item.name === modelName && item.selectable);
  function changeModel(name: string) {
    request.current?.abort(); request.current = null;
    setModelName(name); setResult(null); setError(null); setSaveError(null); setSaveBlocked(false); setBusy(false);
  }
  async function checkWords() {
    if (!model || request.current || saving) return;
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setResult(null); setError(null); setSaveError(null); setSaveBlocked(false);
    try {
      const response = await MeetingService.correctionSuggestion(meetingId, turn.public_id, { model_name: model.name, model_digest: model.digest }, controller.signal);
      if (controller.signal.aborted) return;
      await verifySuggestion(response, turn, model);
      if (!controller.signal.aborted && request.current === controller) setResult(response);
    } catch (failure) { if (!controller.signal.aborted) setError(errorKey(failure)); }
    finally { if (request.current === controller) request.current = null; if (!controller.signal.aborted) setBusy(false); }
  }
  async function save() {
    if (!result?.save_token || !model || saving || saveRequest.current || saveBlocked) return;
    if (!result.expires_at || Date.parse(result.expires_at) <= Date.now()) { setSaveError("meeting.review.tokenExpired"); setSaveBlocked(true); return; }
    const controller = new AbortController(); saveRequest.current = controller; setSaving(true); setSaveError(null);
    try {
      const saved = await MeetingService.saveCorrection(meetingId, turn.public_id, { save_token: result.save_token }, controller.signal);
      if (controller.signal.aborted) return;
      await verifySavedCorrection(saved, turn.text);
      if (saved.revision !== result.expected_revision + 1 || saved.corrected_text !== result.suggested_text || saved.model_name !== result.model_name || saved.model_digest !== result.model_digest || saved.policy_version !== result.policy_version) throw invalidCorrection();
      if (!controller.signal.aborted) { setSaveBlocked(true); onSaved?.(saved); }
    } catch (failure) {
      if (!controller.signal.aborted) {
        setSaveError(errorKey(failure));
        if (failure instanceof ApiError && [401, 403, 404, 409, 410, 422].includes(failure.status)) setSaveBlocked(true);
      }
    } finally { if (saveRequest.current === controller) saveRequest.current = null; if (!controller.signal.aborted) setSaving(false); }
  }
  const edits = result ? mappedEdits(result) : [];
  return <section className="text-review inline-action" aria-label={t("meeting.review.title")} data-text-review="true" aria-busy={busy || saving}>
    <div className="section-heading"><h3>{t("meeting.review.title")}</h3><button type="button" className="button-quiet" disabled={saving} onClick={onClose}>{t("meeting.review.close")}</button></div>
    <p className="field-hint">{t("meeting.review.hint")}</p>
    {!models && !modelError && <p role="status">{t("meeting.review.modelsLoading")}</p>}
    {modelError && <div role="alert" className="error-message"><p>{t(modelError)}</p><button type="button" onClick={() => { setModelError(null); setModels(null); setModelRetry((value) => value + 1); }}>{t("common.retry")}</button></div>}
    {models && <>
      {models.length === 0 ? <p role="status">{t("meeting.review.modelsEmpty")}</p> : <>
        <label htmlFor={selectId}>{t("meeting.review.model")}</label>
        <select id={selectId} value={modelName} disabled={saving} onChange={(event) => changeModel(event.target.value)}>
          <option value="">{t("meeting.review.selectModel")}</option>
          {models.map((item) => <option key={item.name} value={item.name} disabled={!item.selectable}>{item.name}{item.is_default ? t("meeting.review.defaultSuffix") : ""}{!item.selectable ? t("meeting.review.unavailableSuffix") : ""}</option>)}
        </select>
        {models.filter((item) => !item.selectable).map((item) => <p key={item.name} className="field-hint">{t("meeting.review.modelUnavailable", { model: item.name, reason: t(item.unavailable_reason && Object.hasOwn(unavailableKeys, item.unavailable_reason) ? unavailableKeys[item.unavailable_reason] : "meeting.review.modelMetadata") })}</p>)}
        <button type="button" className="button-secondary" disabled={!model || busy || saving} onClick={() => void checkWords()}>{t(busy ? "meeting.review.loading" : "meeting.review.check")}</button>
      </>}
    </>}
    {busy && <p role="status">{t("meeting.review.loading")}</p>}
    {error && <p role="alert" className="error-message">{t(error)}</p>}
    {result && <div aria-live="polite">
      {result.status === "unchanged" && <p role="status">{t("meeting.review.unchanged")}</p>}
      {result.status === "invalid_output" && <p role="status">{t("meeting.review.invalidOutput")}</p>}
      {edits.length > 0 && <><h4>{t("meeting.review.suggestion")}</h4><p lang={turn.language} data-suggested-text="true"><InlineWordChanges source={turn.text} edits={edits} /></p></>}
      {result.proposals.length > 0 && <>
        <h4>{t("meeting.review.changes")}</h4>
        <ul className="text-review-edits">{result.proposals.map((proposal, index) => <li key={index} lang={turn.language} data-assessment={proposal.assessment}>
          <span>{t("meeting.review.before")}: <del>{proposal.original}</del></span><span aria-hidden="true"> → </span><span>{t("meeting.review.after")}: <ins className="correction-word">{proposal.replacement}</ins></span>
          {proposal.reason && Object.hasOwn(reasonKeys, proposal.reason) && <p className="field-hint">{t(reasonKeys[proposal.reason])}</p>}
        </li>)}</ul>
      </>}
      {result.model_output && <details className="model-output" open={result.status === "invalid_output"}><summary>{t("meeting.review.modelOutput")}</summary><pre>{result.model_output}</pre></details>}
      {result.model_output_truncated && <p role="status" className="notice">{t("meeting.review.outputTruncated")}</p>}
      {result.save_token && <div className="action-row"><button type="button" disabled={saving || saveBlocked} onClick={() => void save()}>{t(saving ? "meeting.review.saving" : "meeting.review.save")}</button></div>}
      {!result.save_token && result.status !== "unchanged" && <p className="field-hint">{t("meeting.review.cannotSave")}</p>}
      {saveError && <p role="alert" className="error-message">{t(saveError)}</p>}
    </div>}
  </section>;
}

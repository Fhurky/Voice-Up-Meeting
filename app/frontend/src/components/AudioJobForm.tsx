import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { useIntl } from "@/contexts/IntlContext";
import { ApiError } from "@/lib/apiClient";
import { errorMessageKey, validateAudioFile } from "@/lib/speakerErrors";
import { SpeakerService, type SpeakerProfile } from "@/services/speakers";

export function AudioJobForm({ purpose, profile }: { purpose: "enroll" | "identify"; profile?: SpeakerProfile }) {
  const { t } = useIntl();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [phase, setPhase] = useState<"idle" | "uploading" | "creating">("idle");
  const [error, setError] = useState<string | null>(null);
  const attempt = useRef<{ signature: string; uploadKey: string; jobKey: string; recordingId?: string } | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const busy = phase !== "idle";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !file) return;
    const invalid = validateAudioFile(file);
    if (invalid) { setError(invalid); return; }
    const normalizedName = name.trim().replace(/\s+/g, " ");
    if (purpose === "enroll" && !profile && !normalizedName) { setError("speaker.error.name_required"); return; }
    const signature = JSON.stringify([purpose, profile?.public_id, normalizedName]);
    if (!attempt.current || attempt.current.signature !== signature) {
      attempt.current = { signature, uploadKey: crypto.randomUUID(), jobKey: crypto.randomUUID() };
    }
    const current = attempt.current;
    const abort = new AbortController();
    controller.current = abort;
    setError(null);
    try {
      if (!current.recordingId) {
        setPhase("uploading");
        const recording = await SpeakerService.upload(file, current.uploadKey, abort.signal);
        current.recordingId = recording.public_id;
      }
      if (abort.signal.aborted) return;
      setPhase("creating");
      const job = await SpeakerService.createJob({
        recording_public_id: current.recordingId, purpose,
        ...(purpose === "enroll" ? profile ? { profile_public_id: profile.public_id } : { name: normalizedName } : {}),
      }, current.jobKey, abort.signal);
      if (!abort.signal.aborted) navigate(`/speaker-jobs/${encodeURIComponent(job.public_id)}`);
    } catch (caught) {
      if (!abort.signal.aborted) {
        setError(errorMessageKey(caught));
        if (caught instanceof ApiError && caught.code === "recording_expired") attempt.current = null;
      }
    } finally { if (!abort.signal.aborted) setPhase("idle"); }
  }

  return (
    <form className="audio-form" onSubmit={submit} aria-label={t(purpose === "identify" ? "speaker.analysis.form" : "speaker.profiles.form")}>
      <p className="notice">{t("speaker.audio.single")}</p>
      <p className="muted">{t(purpose === "enroll" ? "speaker.audio.enrollHint" : "speaker.audio.identifyHint")}</p>
      {purpose === "enroll" && (profile ? <p className="target-profile">{t("speaker.profiles.target")} <strong>{profile.name}</strong></p> : <>
        <label htmlFor="speaker-name">{t("speaker.profiles.name")}</label>
        <input id="speaker-name" value={name} onChange={(event) => setName(event.target.value)} required maxLength={120} disabled={busy} autoComplete="off" />
      </>)}
      <label htmlFor="speaker-audio">{t("speaker.audio.file")}</label>
      <input id="speaker-audio" type="file" accept=".wav,.flac,audio/wav,audio/flac" required disabled={busy}
        aria-describedby="audio-limits" onChange={(event) => {
          setFile(event.target.files?.[0] ?? null); attempt.current = null; setError(null);
        }} />
      <p className="field-hint" id="audio-limits">{t("speaker.audio.limits")}</p>
      <p className="field-hint">{t("speaker.audio.retention")}</p>
      {error && <p className="error-message" role="alert">{t(error)}</p>}
      <button type="submit" disabled={busy || !file}>
        {t(busy ? `speaker.submit.${phase}` : purpose === "identify" ? "speaker.submit.identify" : profile ? "speaker.submit.add" : "speaker.submit.enroll")}
      </button>
      {busy && <p role="status" className="muted">{t("speaker.submit.pending")}</p>}
    </form>
  );
}

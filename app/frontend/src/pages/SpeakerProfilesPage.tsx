import { useEffect, useRef, useState, type FormEvent } from "react";
import { AudioJobForm } from "@/components/AudioJobForm";
import { SpeakerLayout } from "@/components/SpeakerLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { errorMessageKey } from "@/lib/speakerErrors";
import { SpeakerService, type SpeakerProfile } from "@/services/speakers";

export default function SpeakerProfilesPage() {
  const { t, locale } = useIntl();
  const { hasPermission } = useAuth();
  const [profiles, setProfiles] = useState<SpeakerProfile[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState<SpeakerProfile | undefined>();
  const [editing, setEditing] = useState<SpeakerProfile | null>(null);
  const [deleting, setDeleting] = useState<SpeakerProfile | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const enrollmentHeading = useRef<HTMLHeadingElement>(null);
  const renameInput = useRef<HTMLInputElement>(null);
  const deletePanel = useRef<HTMLElement>(null);
  const mutation = useRef<AbortController | null>(null);
  const canWrite = hasPermission("speaker_profiles:write");
  const canEnroll = canWrite && hasPermission("speaker_analysis:run") && hasPermission("speaker_analysis:read");
  useEffect(() => { if (target) enrollmentHeading.current?.focus(); }, [target]);
  useEffect(() => { if (editing) renameInput.current?.focus(); }, [editing]);
  useEffect(() => { if (deleting) deletePanel.current?.focus(); }, [deleting]);
  useEffect(() => () => mutation.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    SpeakerService.profiles(offset, controller.signal).then((page) => {
      if (controller.signal.aborted) return;
      setProfiles(page.items); setTotal(page.total); setError(null); setLoading(false);
    }).catch((caught: unknown) => { if (!controller.signal.aborted) { setError(errorMessageKey(caught)); setLoading(false); } });
    return () => controller.abort();
  }, [offset, revision]);

  function refresh() { setLoading(true); setRevision((value) => value + 1); }
  async function rename(event: FormEvent) {
    event.preventDefault();
    if (!editing || busy) return;
    const controller = new AbortController();
    mutation.current = controller;
    setBusy(true); setError(null);
    try {
      const updated = await SpeakerService.rename(editing.public_id, name.trim().replace(/\s+/g, " "), controller.signal);
      if (controller.signal.aborted) return;
      if (target?.public_id === updated.public_id) setTarget(updated);
      setEditing(null); refresh();
    } catch (caught) { if (!controller.signal.aborted) setError(errorMessageKey(caught)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function remove() {
    if (!deleting || busy) return;
    const controller = new AbortController();
    mutation.current = controller;
    setBusy(true); setError(null);
    try {
      await SpeakerService.remove(deleting.public_id, controller.signal);
      if (controller.signal.aborted) return;
      if (target?.public_id === deleting.public_id) setTarget(undefined);
      setDeleting(null);
      if (profiles.length === 1 && offset > 0) { setLoading(true); setOffset(Math.max(0, offset - 20)); }
      else refresh();
    } catch (caught) { if (!controller.signal.aborted) setError(errorMessageKey(caught)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }

  return <SpeakerLayout titleKey="speaker.profiles.title">
    <p className="page-intro">{t("speaker.profiles.intro")}</p>
    <div className="pilot-grid">
      <section className="panel profile-list" aria-labelledby="profiles-heading">
        <div className="section-heading"><h2 id="profiles-heading">{t("speaker.profiles.saved")}</h2><button className="button-quiet" disabled={loading} onClick={refresh}>{t("common.refresh")}</button></div>
        {error && <p role="alert" className="error-message">{t(error)}</p>}
        {loading ? <p role="status">{t("common.loading")}</p> : <>
          {profiles.length === 0 ? <div className="empty-card"><h3>{t("speaker.profiles.empty")}</h3><p>{t("speaker.profiles.emptyHint")}</p></div> : <ul className="profiles">
            {profiles.map((profile) => <li className="profile-card" key={profile.public_id}>
              <h3>{profile.name}</h3>
              <dl className="compact-details">
                <div><dt>{t("speaker.profiles.samples")}</dt><dd>{new Intl.NumberFormat(locale).format(profile.sample_count)} / 20</dd></div>
                <div><dt>{t("common.created")}</dt><dd><time dateTime={profile.created_at}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(profile.created_at))}</time></dd></div>
              </dl>
              <details className="model-details"><summary>{t("speaker.result.model")}</summary><p>{profile.model_id}</p><code>{profile.model_revision}</code></details>
              {canWrite && <div className="action-row">
                {canEnroll && <button className="button-secondary" disabled={profile.sample_count >= 20} onClick={() => { setTarget(profile); setEditing(null); setDeleting(null); }}>{t("speaker.profiles.add")}</button>}
                <button className="button-quiet" onClick={() => { setEditing(profile); setName(profile.name); setDeleting(null); }}>{t("common.rename")}</button>
                <button className="button-danger-quiet" onClick={() => { setDeleting(profile); setEditing(null); }}>{t("common.delete")}</button>
              </div>}
              {profile.sample_count >= 20 && <p className="field-hint">{t("speaker.error.sample_limit")}</p>}
            </li>)}
          </ul>}
          <div className="pagination" aria-label={t("common.pagination")}>
            <button className="button-secondary" disabled={offset === 0} onClick={() => { setLoading(true); setOffset(Math.max(0, offset - 20)); }}>{t("common.previous")}</button>
            <span>{t("speaker.profiles.total")} {new Intl.NumberFormat(locale).format(total)}</span>
            <button className="button-secondary" disabled={offset + profiles.length >= total} onClick={() => { setLoading(true); setOffset(offset + 20); }}>{t("common.next")}</button>
          </div>
        </>}
        {editing && <form className="inline-action" onSubmit={rename} aria-label={t("speaker.profiles.rename")}>
          <h3>{t("speaker.profiles.rename")}</h3><p>{editing.name}</p>
          <label htmlFor="rename-profile">{t("speaker.profiles.name")}</label>
          <input ref={renameInput} id="rename-profile" value={name} required maxLength={120} disabled={busy} onChange={(event) => setName(event.target.value)} />
          <div className="action-row"><button disabled={busy || !name.trim()}>{t("common.save")}</button><button type="button" className="button-secondary" disabled={busy} onClick={() => setEditing(null)}>{t("common.cancel")}</button></div>
        </form>}
        {deleting && <section ref={deletePanel} tabIndex={-1} className="inline-action danger-panel" role="alertdialog" aria-labelledby="delete-title" aria-describedby="delete-description">
          <h3 id="delete-title">{t("speaker.profiles.deleteTitle")}</h3><p><strong>{deleting.name}</strong></p>
          <p id="delete-description">{t("speaker.profiles.deleteHint")}</p>
          <div className="action-row"><button className="button-danger" disabled={busy} onClick={() => { void remove(); }}>{t("speaker.profiles.deleteConfirm")}</button><button className="button-secondary" disabled={busy} onClick={() => setDeleting(null)}>{t("common.cancel")}</button></div>
        </section>}
      </section>
      {canEnroll ? <section className="panel enrollment-panel" aria-labelledby="enroll-heading">
        <div className="section-heading"><h2 ref={enrollmentHeading} tabIndex={-1} id="enroll-heading">{t(target ? "speaker.profiles.add" : "speaker.profiles.create")}</h2>{target && <button className="button-quiet" onClick={() => setTarget(undefined)}>{t("common.cancel")}</button>}</div>
        <AudioJobForm key={target?.public_id ?? "new"} purpose="enroll" profile={target} />
      </section> : <section className="panel"><p>{t("speaker.profiles.readOnly")}</p></section>}
    </div>
  </SpeakerLayout>;
}

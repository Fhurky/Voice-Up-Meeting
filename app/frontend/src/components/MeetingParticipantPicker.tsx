import { useEffect, useMemo, useState } from "react";
import { useIntl } from "@/contexts/IntlContext";
import { SpeakerService, type SpeakerProfile } from "@/services/speakers";

export const MAX_LISTED_PARTICIPANTS = 50;
const MAX_LOADED_PROFILES = 1000;

type Load = { state: "loading" } | { state: "error" } | { state: "ready"; profiles: SpeakerProfile[] };

async function allProfiles(signal: AbortSignal): Promise<SpeakerProfile[]> {
  const profiles: SpeakerProfile[] = [];
  for (;;) {
    const page = await SpeakerService.profiles(profiles.length, signal);
    profiles.push(...page.items);
    if (!page.items.length || profiles.length >= page.total || profiles.length >= MAX_LOADED_PROFILES) return profiles;
  }
}

export function MeetingParticipantPicker({ selected, disabled, onChange }: { selected: string[]; disabled: boolean; onChange: (selected: string[]) => void }) {
  const { t, locale } = useIntl();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [query, setQuery] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    allProfiles(controller.signal).then(
      (profiles) => { if (!controller.signal.aborted) setLoad({ state: "ready", profiles }); },
      () => { if (!controller.signal.aborted) setLoad({ state: "error" }); },
    );
    return () => controller.abort();
  }, []);
  const visible = useMemo(() => {
    if (load.state !== "ready") return [];
    const needle = query.trim().toLocaleLowerCase(locale);
    const sorted = [...load.profiles].sort((left, right) => left.name.localeCompare(right.name, locale));
    return needle ? sorted.filter((profile) => profile.name.toLocaleLowerCase(locale).includes(needle)) : sorted;
  }, [load, query, locale]);
  const full = selected.length >= MAX_LISTED_PARTICIPANTS;
  const toggle = (publicId: string, checked: boolean) =>
    onChange(checked ? [...selected, publicId] : selected.filter((value) => value !== publicId));

  return <fieldset className="participant-picker" disabled={disabled}>
    <legend>{t("meeting.roster.title")}</legend>
    <p id="meeting-roster-hint" className="field-hint">{t("meeting.roster.hint")}</p>
    {load.state === "loading" && <p className="field-hint" role="status">{t("meeting.roster.loading")}</p>}
    {load.state === "error" && <p className="error-message" role="alert">{t("meeting.roster.error")}</p>}
    {load.state === "ready" && (load.profiles.length === 0 ? <p className="field-hint">{t("meeting.roster.empty")}</p> : <>
      <div className="form-field"><label htmlFor="meeting-roster-search">{t("meeting.roster.search")}</label>
        <input id="meeting-roster-search" type="search" value={query} aria-describedby="meeting-roster-hint" onChange={(event) => setQuery(event.target.value)} /></div>
      <p className="field-hint" role="status">{t("meeting.roster.selected", { count: selected.length })}{full ? ` ${t("meeting.roster.limit", { count: MAX_LISTED_PARTICIPANTS })}` : ""}</p>
      {visible.length === 0 ? <p className="field-hint">{t("meeting.roster.noMatch")}</p> :
        <ul className="participant-options">
          {visible.map((profile) => {
            const checked = selected.includes(profile.public_id);
            return <li key={profile.public_id}><label className="checkbox-label">
              <input type="checkbox" checked={checked} disabled={!checked && full} onChange={(event) => toggle(profile.public_id, event.target.checked)} />
              {profile.name}
            </label></li>;
          })}
        </ul>}
    </>)}
  </fieldset>;
}

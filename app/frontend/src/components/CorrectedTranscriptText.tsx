import { Fragment, useEffect, useState } from "react";
import { useIntl } from "@/contexts/IntlContext";
import { correctionParts, verifySavedCorrection, type CorrectionEdit } from "@/lib/transcriptCorrections";
import type { MeetingTranscript, SavedCorrection } from "@/services/meetings";

export function InlineWordChanges({ source, edits }: { source: string; edits: readonly CorrectionEdit[] }) {
  return <>{correctionParts(source, edits).map((part, index) => part.original === undefined ? <Fragment key={index}>{part.text}</Fragment> : <ins key={index} className="correction-word" title={part.original}>{part.text}</ins>)}</>;
}

export function CorrectedTranscriptText({ turn }: { turn: MeetingTranscript }) {
  if (!turn.correction) return <p lang={turn.language} data-original-text="true">{turn.text}</p>;
  return <SavedText key={`${turn.public_id}:${turn.text}:${turn.correction.public_id}:${turn.correction.revision}`} turn={turn} correction={turn.correction} />;
}

function SavedText({ turn, correction }: { turn: MeetingTranscript; correction: SavedCorrection }) {
  const { t, locale } = useIntl();
  const [original, setOriginal] = useState(false);
  const [verified, setVerified] = useState(false);
  const [invalid, setInvalid] = useState(false);
  useEffect(() => {
    let active = true;
    void verifySavedCorrection(correction, turn.text).then(() => { if (active) setVerified(true); }).catch(() => { if (active) setInvalid(true); });
    return () => { active = false; };
  }, [correction, turn.text]);
  if (!verified) return <><p lang={turn.language} data-original-text="true">{turn.text}</p>{invalid && <p className="field-hint" role="status">{t("meeting.review.savedInvalid")}</p>}</>;
  return <>
    <div className="action-row" role="group" aria-label={t("meeting.review.versionView")}>
      <button type="button" className="button-quiet" aria-pressed={original} onClick={() => setOriginal(true)}>{t("meeting.review.originalView")}</button>
      <button type="button" className="button-quiet" aria-pressed={!original} onClick={() => setOriginal(false)}>{t("meeting.review.correctedView")}</button>
    </div>
    {original ? <p lang={turn.language} data-original-text="true">{turn.text}</p> : <p lang={turn.language} data-corrected-text="true"><InlineWordChanges source={turn.text} edits={correction.edits} /></p>}
    <p className="field-hint">{t("meeting.review.savedVersion", { version: new Intl.NumberFormat(locale).format(correction.revision), model: correction.model_name })}</p>
  </>;
}

import { useEffect, useState } from "react";
import { SpeakerLayout } from "@/components/SpeakerLayout";
import { useIntl } from "@/contexts/IntlContext";
import { ApiError } from "@/lib/apiClient";
import { MeetingService, type MeetingProcessor } from "@/services/meetings";

const POLL_MILLISECONDS = 3000;
const changeErrors: Readonly<Record<string, string>> = {
  inference_busy: "settings.processor.busy",
  processor_unavailable: "settings.processor.unavailable",
};

export default function SettingsPage() {
  const { t } = useIntl();
  const [state, setState] = useState<MeetingProcessor | null>(null);
  const [readFailed, setReadFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [changing, setChanging] = useState(false);
  const settled = state !== null && !state.switching;

  // The service starts again to change processor and cannot answer for a while, so the page
  // keeps reading until it gets a settled answer.
  useEffect(() => {
    if (settled) return;
    const reading = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const read = () => {
      MeetingService.processor(reading.signal).then((next) => {
        setState(next);
        setReadFailed(false);
        if (next.switching) timer = setTimeout(read, POLL_MILLISECONDS);
      }).catch(() => {
        if (reading.signal.aborted) return;
        setReadFailed(true);
        timer = setTimeout(read, POLL_MILLISECONDS);
      });
    };
    read();
    return () => { clearTimeout(timer); reading.abort(); };
  }, [settled]);

  async function choose(device: MeetingProcessor["device"]) {
    if (!state || state.device === device || changing) return;
    setChanging(true); setError(null);
    try {
      setState(await MeetingService.changeProcessor({ device }));
    } catch (failure) {
      setError((failure instanceof ApiError && changeErrors[failure.code]) || "settings.processor.changeFailed");
    } finally { setChanging(false); }
  }

  const busy = changing || Boolean(state?.switching);
  return <SpeakerLayout titleKey="settings.title">
    <p className="page-intro">{t("settings.intro")}</p>
    <section className="panel" aria-labelledby="settings-processor-heading" data-processor-device={state?.switching ? "switching" : state?.device}>
      <div className="section-heading"><h2 id="settings-processor-heading">{t("settings.processor.title")}</h2></div>
      {!state && !readFailed && <p className="field-hint">{t("settings.processor.loading")}</p>}
      {!state && readFailed && <p className="error-message" role="alert">{t("settings.processor.readFailed")}</p>}
      {state && <>
        <div className="recording-source-switch" role="group" aria-label={t("settings.processor.title")}>
          <button type="button" className="button-secondary" aria-pressed={state.device === "gpu"} disabled={busy || !state.gpu_available} onClick={() => void choose("gpu")}>GPU</button>
          <button type="button" className="button-secondary" aria-pressed={state.device === "cpu"} disabled={busy || !state.cpu_available} onClick={() => void choose("cpu")}>CPU</button>
        </div>
        {!state.switching && <p className="field-hint">{t(state.device === "gpu" ? "settings.processor.gpuHint" : "settings.processor.cpuHint")}</p>}
        {!state.gpu_available && <p className="field-hint">{t("settings.processor.gpuMissing")}</p>}
        {state.switching && <p className="notice" role="status">{t("settings.processor.switching")}</p>}
        {state.last_error && <p className="error-message" role="alert">{t("settings.processor.switchFailed")}</p>}
      </>}
      {error && <p className="error-message" role="alert">{t(error)}</p>}
      <p className="field-hint">{t("settings.processor.note")}</p>
    </section>
  </SpeakerLayout>;
}

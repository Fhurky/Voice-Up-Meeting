# Record audio inside the app

Use the `Meetings` page to record with your microphone and prepare a transcript
with speaker labels without selecting an audio file. Meeting models must be
running for analysis; starting a recording does not prepare those models.

1. Under `Recording source`, choose **Record with microphone**.
2. Enter a meeting title and choose the spoken language. You may also set the
   participant upper bound, exact active speaker count, and automatic memory
   option. Saving new people requires permission to write speaker profiles.
3. Choose an input under `Microphone`, then click **Start recording**. Allow
   microphone access when the browser asks. Duration and audio level track
   the recording.
4. Click **Stop and analyze** when finished. The final audio is completed and
   transferred before the meeting result opens. The microphone is closed
   during transfer; transcript and speaker results appear as analysis proceeds.

Only sound heard by the selected microphone is recorded. Computer output,
remote participants heard through headphones, and the Teams audio stream are
not captured automatically. A shared room microphone must hear every speaker
clearly enough. A live transcript is not shown during recording.

**Cancel recording** releases the temporary recording and closes the
microphone. You must record again. If transfer fails because of the connection,
keep the page open and use **Retry analysis**; it reads the same completed
audio. Reloading or closing the page does not recover this temporary recording.

Long recordings are written to the browser's temporary disk storage rather
than accumulated entirely in memory. A recording is limited to **4 hours or
2 GiB**, whichever is reached first; available disk space or the browser's
quota may impose an earlier limit. At the known 4-hour/2-GiB limit, recording
stops automatically, a limit notice appears, and all audio safely recorded up
to that point is sent for analysis. A disconnected microphone, exhausted disk
quota, or unsafe disk write stops capture without submitting incomplete audio.
Keep the page open and the computer awake until recording and transfer finish.

The temporary disk copy is cleaned up after normal completion or cancellation.
Leaving the page attempts cleanup; the browser may close before it finishes.
A forced browser or computer shutdown may also leave a
temporary copy on disk; the app does not automatically recover or analyze it.
After transfer, the server recording and persistent speaker profiles follow
the existing retention rules. Removing the browser's temporary copy does not
delete those records.

Recording requires a supported browser and a secure context: use
`localhost`/`127.0.0.1` on the same computer, or HTTPS. Opening another
computer's network address over plain HTTP may block microphone access. If
permission was denied, enable the microphone in the browser's site settings.
If no device is available, check the input connection and other applications
using it. When required audio or disk features are unavailable, the app explains
the limitation and offers **Upload a file**. Support is not assumed for every
browser or device.

Short contributions remain in the transcript. To save a new person in memory,
their accumulated clean speech must exceed 20 seconds and pass quality,
consistency, and unknown-person checks. A longer recording alone does not
guarantee correct recognition or a saved profile.

Behavior source: [Accepted 007 PRD](../../specs/speaker-identity/PRDs/007-microphone-meeting-capture/PRD.md).
Existing model and memory workflow: [meeting guide](../MEETING_WORKFLOW.md).
Observed environments and open checks: [microphone evidence](../evidence/2026-09-11-microphone-recording/README.md).

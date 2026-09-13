# Check a meeting transcript against its audio

In a meeting result, select **Listen to this section** beneath a transcript
row. Once the source audio loads, press play. The selected speaker and the
section's start and end times within the meeting appear above the player.
Native controls let you pause, change the volume and seek within the loaded
section.

At most 30 seconds load at once. For a longer turn, use **Next audio section**
and **Previous audio section** to review the rest of that row. Selecting
another row or changing pages closes the previous audio. **Close audio**
returns keyboard focus to the row's listen button. Signing out or leaving the
meeting releases the temporary audio; the whole long recording is never loaded
into browser memory.

The section comes from the source recording. Voices are not separated or
cleaned; multiple channels are mixed together. Use it to compare the transcript
and displayed speaker with the recording. Listening does not change the result
or persistent memory.

Speaker cards explain the memory decision and, when available, its known
reason. Inconsistent speech and insufficient clean speech are different
conditions. **Rename** only changes the display name; it does not correct a
speaker assignment or change voice identity. For a linked persistent profile,
the new name also appears in other meetings. A recognized person is not a
guarantee of a correct result; listen to a questionable section to check it.

If audio cannot load, check the connection and use **Retry**. When source
retention expires or a file can no longer be read, the transcript and speaker
information remain available; this screen cannot recover the removed source.
For permission errors, check your session and meeting access. For an invalid
audio section, retry or inspect another row.

This behavior is defined by the [accepted audio review capability](../../specs/speaker-identity/PRDs/011-meeting-audio-review/PRD.md).
To capture a new recording, use the [microphone guide](microphone-recording.md).

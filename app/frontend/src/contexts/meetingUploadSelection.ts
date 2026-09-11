import { createContext, type Dispatch, type SetStateAction } from "react";

export type MeetingUploadSelection = { meetingId: string; file: File } | null;
export const MeetingUploadContext = createContext<{
  selection: MeetingUploadSelection;
  setSelection: Dispatch<SetStateAction<MeetingUploadSelection>>;
} | null>(null);

export function SpeakerAvatar({ name, index = 0 }: { name: string; index?: number }) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((word) => Array.from(word)[0]).join("");
  return <span className={`speaker-avatar avatar-${Math.abs(index) % 6}`} aria-hidden="true">{initials}</span>;
}

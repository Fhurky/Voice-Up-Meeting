const heights = [12, 22, 16, 32, 52, 34, 68, 92, 58, 112, 144, 98, 72, 120, 164, 134, 94, 66, 106, 142, 184, 152, 116, 82, 126, 164, 136, 92, 66, 100, 134, 102, 72, 54, 82, 60, 38, 48, 26, 18, 28, 12];

export function VoiceWave() {
  return <svg className="voice-wave" viewBox="0 0 520 220" fill="none" aria-hidden="true" focusable="false">
    {heights.map((height, index) => <rect key={index} x={8 + index * 12} y={(220 - height) / 2} width="5" height={height} rx="2.5" fill="currentColor" opacity={.45 + (index % 4) * .16} />)}
  </svg>;
}

import { StereoCaptureBuffer, type CaptureBufferOptions } from "./meetingCapturePcm";

declare abstract class AudioWorkletProcessor { readonly port: MessagePort; }
declare function registerProcessor(name: string, processor: new (options: { processorOptions: CaptureBufferOptions }) => AudioWorkletProcessor): void;

class MeetingCaptureProcessor extends AudioWorkletProcessor {
  private readonly capture: StereoCaptureBuffer;
  private active = true;

  constructor(options: { processorOptions: CaptureBufferOptions }) {
    super();
    this.capture = new StereoCaptureBuffer(options.processorOptions, (message) => {
      if (message.type === "error" || message.type === "stopped") this.active = false;
      if (message.type === "part") this.port.postMessage(message, [message.data]);
      else this.port.postMessage(message);
    });
    this.port.onmessage = (event: MessageEvent<unknown>) => {
      const message = event.data;
      if (!message || typeof message !== "object" || !("type" in message)) return;
      if (message.type === "stop") this.capture.stop();
      if (message.type === "levels-credit") this.capture.acknowledgeLevels();
      if (message.type === "credit" && "bytes" in message && typeof message.bytes === "number") this.capture.acknowledge(message.bytes);
      if (message.type === "microphone" && "muted" in message && typeof message.muted === "boolean") this.capture.setMicrophoneMuted(message.muted);
    };
  }

  process(inputs: Float32Array[][]): boolean {
    if (!this.active) return false;
    const input = inputs[0];
    // The merger delivers channel 0 (microphone) and channel 1 (system); an absent input is silence.
    if (input?.length) this.active = this.capture.push(input[0], input[1]);
    // Outputs stay zero: neither channel is played back to the speakers.
    return this.active;
  }
}

registerProcessor("voiceup-meeting-capture", MeetingCaptureProcessor);

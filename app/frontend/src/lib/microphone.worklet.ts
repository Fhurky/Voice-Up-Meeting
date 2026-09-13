import { PcmCaptureBuffer, type PcmCaptureOptions } from "./microphonePcm";

declare abstract class AudioWorkletProcessor { readonly port: MessagePort; }
declare function registerProcessor(name: string, processor: new (options: { processorOptions: PcmCaptureOptions }) => AudioWorkletProcessor): void;

class MicrophonePcmProcessor extends AudioWorkletProcessor {
  private readonly capture: PcmCaptureBuffer;
  private active = true;

  constructor(options: { processorOptions: PcmCaptureOptions }) {
    super();
    this.capture = new PcmCaptureBuffer(options.processorOptions, (message) => {
      if (message.type === "error" || message.type === "stopped") this.active = false;
      if (message.type === "chunk") this.port.postMessage(message, [message.data]);
      else this.port.postMessage(message);
    });
    this.port.onmessage = (event: MessageEvent<unknown>) => {
      const message = event.data;
      if (!message || typeof message !== "object" || !("type" in message)) return;
      if (message.type === "stop") this.capture.stop();
      if (message.type === "progress-credit") this.capture.acknowledgeProgress();
      if (message.type === "credit" && "bytes" in message && typeof message.bytes === "number") this.capture.acknowledge(message.bytes);
    };
  }

  process(inputs: Float32Array[][]): boolean {
    if (!this.active) return false;
    const samples = inputs[0]?.[0];
    if (samples) this.active = this.capture.push(samples);
    // The mono output stays zero: the microphone is never played back to the speakers.
    return this.active;
  }
}

registerProcessor("voiceup-microphone-pcm", MicrophonePcmProcessor);

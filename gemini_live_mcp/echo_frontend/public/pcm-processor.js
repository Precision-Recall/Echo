class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    // Target sample rate
    this.targetSampleRate = 16000;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    const channelData = input[0]; // Mono channel
    const currentSampleRate = sampleRate; // Global in AudioWorklet

    // Simple decimation factor
    // e.g. 48000 / 16000 = 3. We take every 3rd sample.
    // e.g. 44100 / 16000 = 2.75. Irregular.
    // For robust resampling we need a proper filter, but for speech decimation is okay-ish.
    // Let's assume integer ratios or close enough for now, or just handle 48k/44.1k common cases.
    
    // We want to accumulate samples at 16kHz.
    // If rate is 16000, take all.
    // If rate is 48000, take every 3rd.
    
    // Using a simple accumulation loop
    if (currentSampleRate === this.targetSampleRate) {
        for (let i = 0; i < channelData.length; i++) {
            const s = Math.max(-1, Math.min(1, channelData[i]));
            const int16 = s < 0 ? s * 0x8000 : s * 0x7FFF;
            this.buffer.push(int16);
        }
    } else {
        // Downsample
        const ratio = currentSampleRate / this.targetSampleRate;
        for (let i = 0; i < channelData.length; i += ratio) {
            // Nearest neighbor interpolation (simple index rounding)
            const idx = Math.floor(i);
            if (idx >= channelData.length) break;
            
            const s = Math.max(-1, Math.min(1, channelData[idx]));
            const int16 = s < 0 ? s * 0x8000 : s * 0x7FFF;
            this.buffer.push(int16);
        }
    }

    // Flush buffer (every 40ms = 640 samples at 16k)
    // 640 * 2 bytes = 1280 bytes
    // Send slightly larger chunks to be safe network-wise, e.g. 2048 samples?
    // HR Interviewer uses 4096 inputs (at 16k presumably).
    // Let's stick to 2048 to balance latency/overhead.
    if (this.buffer.length >= 2048) {
      this.port.postMessage(new Int16Array(this.buffer));
      this.buffer = [];
    }

    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);

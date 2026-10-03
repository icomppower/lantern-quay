// Procedural Web Audio: rifle report and the bell. The context is created lazily inside a user gesture,
// after the gesture's real action, and every call is guarded so audio can never block input.
export class Sfx {
  constructor() { this.ctx = null; }
  unlock() {
    try {
      if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)();
      if (this.ctx.state === "suspended") this.ctx.resume().catch(() => {});
    } catch { this.ctx = null; }
  }
  _noise(dur) {
    const c = this.ctx, n = Math.floor(c.sampleRate * dur), buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 3);
    const s = c.createBufferSource(); s.buffer = buf; return s;
  }
  shot(loud = true) {
    try {
      const c = this.ctx; if (!c) return;
      const s = this._noise(0.9), f = c.createBiquadFilter(), g = c.createGain();
      f.type = "lowpass"; f.frequency.setValueAtTime(2400, c.currentTime); f.frequency.exponentialRampToValueAtTime(300, c.currentTime + 0.5);
      g.gain.setValueAtTime(loud ? 0.9 : 0.5, c.currentTime);
      s.connect(f).connect(g).connect(c.destination); s.start();
    } catch {}
  }
  splash() {
    try {
      const c = this.ctx; if (!c) return;
      const s = this._noise(1.2), f = c.createBiquadFilter(), g = c.createGain();
      f.type = "bandpass"; f.frequency.value = 700; g.gain.value = 0.5;
      s.connect(f).connect(g).connect(c.destination); s.start();
    } catch {}
  }
  bell() {
    try {
      const c = this.ctx; if (!c) return;
      const t0 = c.currentTime;
      for (let k = 0; k < 3; k++) {
        const t = t0 + k * 1.9;
        for (const [ratio, amp, dec] of [[0.5, 0.25, 4], [1, 0.35, 3], [1.19, 0.2, 2.2], [1.5, 0.15, 1.8], [2.0, 0.12, 1.4], [2.74, 0.08, 1]]) {
          const o = c.createOscillator(), g = c.createGain();
          o.frequency.value = 392 * ratio;
          g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(amp * 0.5, t + 0.01);
          g.gain.exponentialRampToValueAtTime(0.0001, t + dec);
          o.connect(g).connect(c.destination); o.start(t); o.stop(t + dec + 0.1);
        }
      }
    } catch {}
  }
}

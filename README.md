# Whispers

**Whispers** is a modular SDR signal intelligence pipeline focused on identifying human voice communication in the radio spectrum. It captures IQ samples, detects active frequencies via FFT, and queues potential audio segments for further analysis, such as FM demodulation and voice activity detection, using a plug-and-play filter architecture.

## Pipeline Overview

The `Whispers` SDR pipeline operates by continuously capturing a wideband IQ stream and enabling _virtual tuning_ within that stream. Instead of physically retuning the SDR device to each frequency of interest, the system performs **digital downconversion and decimation** in software to extract narrowband segments on demand, effectively emulating multiple parallel receivers from a single wideband source.

This architecture is inspired by systems like **SpyServer**, allowing low-latency signal monitoring, scalable thread-based decoding, and retrospective access to past IQ data using a circular buffer.

---

### 1. Virtual Receiver Scanning Pipeline

**1.1** Begin continuous scanning loop

**1.2** Capture a wideband IQ block (e.g. 2.4 MHz span)

**1.3** Store the IQ block in a circular buffer for retrospective access (e.g. last 30 seconds)

**1.4** Apply FFT to the wideband block to obtain a frequency-domain power spectrum

**1.5** Convert FFT output to dB scale for peak analysis

**1.6** Apply adaptive thresholding (e.g. median + offset in dB)

**1.7** Identify spectral peaks above the threshold

**1.8** _(Optional)_ Filter out narrowband or spurious peaks (e.g. CW, constant carriers)

**1.9** _(Optional)_ Apply temporal stability filter:

- Require peaks to persist across multiple FFT cycles to be considered stable

**1.10** _(Optional)_ Apply Smart Temporal Classification:

- **1.10.1** Maintain a time-based activity log per frequency
- **1.10.2** Compute duty cycle over a sliding window (e.g. 60 seconds)
- **1.10.3** Apply heuristics:
  - `> 90%` = Continuous broadcast (ignore)
  - `< 10%` = Idle/noise (discard)
  - `20-70%` = Likely voice or conversation (accept)
- **1.10.4** _(Optional)_ Trigger early capture when human-like activity is detected
- **1.10.5** _(Optional)_ Retrieve pre-trigger IQ from the circular buffer for context

**1.11** For each approved peak region:

- **1.11.1** Initialize a software-based Virtual Receiver at the target frequency
- **1.11.2** Extract narrowband IQ using digital mixing and decimation
- **1.11.3** Package the IQ with metadata (timestamp, frequency, bandwidth, power, etc.)
- **1.11.4** Push the package to the capture queue for downstream processing (e.g. VAD, decoding, ASR)

**[Loop returns to 1.2 with the next wideband IQ frame]**

---

### Modular Architecture

Each stage from peak detection to virtual extraction is implemented in pluggable, testable modules.

| Module/Class            | Description                                               |
| ----------------------- | --------------------------------------------------------- |
| `ThresholdPeakDetector` | Adaptive detection based on median + offset threshold     |
| `FFTProcessor`          | Windowed FFT and dB scale spectrum computation            |
| `PeakTracker`           | Confirms temporal stability of detected peaks             |
| `CircularIQBuffer`      | Maintains rolling IQ history for retrospective subbanding |
| `VirtualReceiver`       | Extracts narrowband IQ using software-defined tuning      |
| `InMemoryCaptureQueue`  | Enqueues captured IQ packages for consumer processing     |

This design ensures performance, flexibility, and extensibility across a variety of RF intelligence and automation scenarios.

## Project Status

This project is currently under development and is not considered stable.

## License

MIT

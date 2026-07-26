# Control-valve scroll-video experiment

## Decision

Use **GOP 6** as the current balanced candidate for this 18-second,
1280×800, 30 fps product sequence. GOP 3 increases transfer size by 40%
without a repeatable seek-latency gain. GOP 10 reduces transfer size by 16%
but was slower in the rapid alternating-target test and did not improve
normal forward/reverse seeking enough to make that trade automatically
preferable.

This is an exploratory result on one local Windows/Brave environment, not a
universal codec claim. Production selection should be rechecked through CDN
byte-range delivery on the actual audience device mix.

## Controlled boundary

- Source: the current deterministic 540-frame valve Animatic.
- Capture: WebGL canvas only; UI and copy are not baked into the video.
- Encode: H.264 High 4.1, CRF 21, preset medium, yuv420p, no B-frames, no
  scene cuts, fast-start MP4, no audio.
- Independent variable: GOP/keyframe interval only—3, 6, or 10 frames.
- Browser: Headless Brave/Chromium 150 on Windows, 1280×800, DPR 1.
- Cache: one isolated cold browser context per variant.
- Media delivery: local HTTP server with byte-range responses.
- Seek completion: the `seeked` event followed by two animation frames,
  allowing the paused video element to reach browser composition.

## Observed results

| Variant | File size | First video frame | Forward P95 | Reverse P95 | Rapid final settle | Seek timeouts |
|---|---:|---:|---:|---:|---:|---:|
| GOP 3 | 2.02 MiB | 38.1 ms | 98.3 ms | 53.9 ms | 72.8 ms | 0 |
| GOP 6 | 1.45 MiB | 41.8 ms | 56.6 ms | 53.2 ms | 43.3 ms | 0 |
| GOP 10 | 1.21 MiB | 80.3 ms | 55.6 ms | 54.7 ms | 52.5 ms | 0 |

These values are one controlled run. The durable numeric source of truth is
`browser-benchmark.json`.

The 540 lossless intermediate PNGs total 63.52 MiB. The selected GOP 6 MP4 is
1.45 MiB—about 44× smaller than that intermediate frame set—and its static
frame-zero poster is 114 KiB. This comparison is specifically against the
experiment's lossless PNG intermediates; it does not claim that every
production image-sequence format would have the same ratio.

All three variants completed eleven forward and eleven reverse targets with a
maximum media-time error below 0.001 ms. Seven rapidly alternating targets
submitted before the next animation frame were coalesced, and the final target
was preserved in all variants. Repeated identical targets completed without a
new media seek.

The first-frame contract is independent from video readiness: the
byte-identical 1280×800 frame-zero PNG is visible while video `readyState` is
still 0 and the video layer opacity is 0. Once video data is ready, the
pre-rendered motion replaces the poster while all narrative copy remains live
HTML.

## Interpretation

The experiment supports the technical pattern: pre-rendered product motion can
be driven by scroll without shipping 540 independent image requests or asking
the browser to render the STEP-derived scene in real time. Short-GOP MP4 keeps
random access bounded, while a static poster removes the blank-loading state.

It does not yet prove CDN startup performance, mobile thermal behavior, Safari
decoder behavior, or production accessibility. Those remain outside the
frozen experiment boundary.

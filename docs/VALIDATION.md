# Validation record — 2026-11-13

Base: `u93132/ShinyHunterUSUM@f49910affd7ed35b38af8e2b5b35499dcc554f0d`.
Branch: `macos-japanese-gifts` on `senuhi/ShinyHunterUSUM`.

## Latest: stage 3 one reset → title → continue → field observed

The operator explicitly authorized proceeding without confirming a recent game
save. This diagnostic records `saved_game_confirmed=false`; it did not save.
On 2026-11-14, fresh video/reference checks preceded one 0.15 s L+R+SELECT press.
The Japanese Ultra Sun title was visually reviewed before one START, and the
selected continue entry was reviewed before one A. Received images then showed
field gameplay and the Rotom map. Total input: 9 datagrams, no repeated reset.

In 114.259 s, 223 complete passes per screen were received; 121 per screen
followed continue A. Reset/START/A completed at 2.076/38.515/55.823 s; gameplay
was visually confirmed by 76.906 s. TCP disconnects and reconnect attempts were
both zero. This validates continuity for one reset with subsequent input; it
**does not exercise or validate reconnect fallback after a real disconnection**.
Twelve freshness-block events withheld further input while waiting for new
frames. No unknown-state button or reset was sent. Console-side operator
confirmation and live hardware attestation remain outstanding.

`reset_probe.py` is a separate bounded diagnostic, offline dry-run by default.
Reviewed title/continue commands have budgets; reset budget is consumed before
sending. Video-only reconnects cannot reset. The hunt runner's unknown/disconnect
stop behavior and calibration gates are unchanged. A Python 3.12 button-enum
routing bug found in preflight was fixed; 50 unit/loopback tests pass, including
neutral release, zero-input unknown screens and no reset retry on lost video.
Private evidence: ignored `captures/stage3-reset-live-20261114/`.

## Latest: stage 2 approved 11-key sequence — observed, with safety stops

On 2026-11-14 the approved direction sequence (right, left, down, up twice),
A, B, B was sent exactly once per key: 11 presses / 33 UDP datagrams.
Received images show expected cursor moves, the party screen, return to the
normal menu and finally a stable Rotom map. Final receive-only confirmation:
3.075 s, 6 upper / 5 lower complete passes. No save or reset was sent.

The sequence was split by safety stops after keys 7 (cursor confidence margin)
and 9 (stale screen), with images/fresh reception reviewed before continuing
only the remaining keys. It was not an uninterrupted endurance pass. The final
B's immediate checkpoint was transitional; the separate passive check confirmed
the stable field. No stage-2 operator confirmation or live attestation was created.
Private evidence index: ignored `captures/stage2-summary-20261114.json`.

Fixed a separate TCP timestamp bug: coalesced reads could inherit an earlier
packet's start indefinitely. Each packet now retains its own first-byte time.
Two regressions cover fragmented/coalesced provenance and source freshness over
many successive packets; all 45 unit/loopback tests pass. Freshness limits remain
unchanged. Real latency stops also occurred after the fix and remain unresolved.

## Latest: stage 1 one-B input — operator-confirmed success

After a packet-generation dry-run, the operator manually opened the normal menu
and explicitly approved one 0.08 s B press only. Fresh video and three menu-image
regions were checked before creating the input connection. The input socket
allowed exactly the planned B-down, B-up and return-physical-control packets;
each was sent once (20 bytes each). No other key, touch or reset was sent.

Before/after PNGs show the normal menu closing to the Rotom Dex/field screen.
The operator confirmed that it closed automatically without their own input.
The 10.032 s probe received 18 upper / 17 lower complete passes in total, including
15 upper / 14 lower after the input. The measured sender interval between B-down
and B-up sends was about 0.084 s; no claim is made about exact console scheduling.

This confirms only one real B response with concurrent video, not repeated-key
stability, reset recovery, gift navigation or shiny accuracy. No live attestation
was created at stage 1. Stage 2 results are recorded above.
See [AUTOMATION_STAGES_JA.md](AUTOMATION_STAGES_JA.md). Private evidence remains
in ignored `captures/stage1-b-live-20261113/`.

## Latest: USUM gameplay reception after post-HIMEM InputRedirection enablement

The operator found **Start InputRedirection** (not running) after launching
USUM through ChLoad_HIMEM, then manually enabled it and resumed the game.
The reported LED remained cyan during gameplay. Two direct-receiver sessions
were then run without `--send-b`:

| Session | Elapsed | Upper complete passes | Lower complete passes | Result |
| --- | --- | --- | --- | --- |
| Initial receive-only | 10.055 s | 22 | 21 | Observed |
| Separate sustained receive-only | 30.139 s | 61 | 62 | Observed through scheduled end |

Saved PNGs were inspected: actual gameplay on the upper screen and the Rotom
Dex/map on the lower screen, at native resolution and correct orientation.
The 30 s pass assembly spans were 0.337–1.559 s upper and 0.306–1.559 s lower.
No controller socket was constructed by either probe; no UDP 4950 input,
button, reset, NFC patch or game-code change was sent/applied by the agent.
The operator's enabling of the service is distinct from a remote button test.

This confirms short gameplay video reception while InputRedirection is reported
enabled on this Old 3DS/HIMEM configuration. It does NOT validate remote key
response, reset continuity, gift navigation, Japanese recognition, shiny colour
accuracy or long-duration stability. No live/hardware attestation was created.
Private evidence is in ignored `captures/old3ds-usum-ir-enabled-passive*` folders.
See [WIRELESS_NFC_JA.md](WIRELESS_NFC_JA.md) for source-backed investigation and limits.

During the intervening suspended-HOME test, a reconnect observed 45 passes per
screen over 33.658 s before the receiver stopped on the existing 2 s assembly
limit. This receiver-initiated stop must NOT be reported as proof of a spontaneous
TCP disconnect caused by game resume. After the operator reported resume/yellow
LED, a separate connection attempt timed out after 5.006 s and received 0/0.
The first connection on returning to HOME had an actual malformed 2x50 JPEG,
which was rejected. These startup/freshness issues remain recorded separately.

The earlier results below are retained as history of their respective states.

## Old 3DS update: direct receiver and observed HOME stream

The video boundary now has independent NTR-HR and ChirunoMod adapters; no external
Chokistream process or Java runtime is used. As of this update, 43 local unit /
loopback tests pass, and native Tk smoke tests pass for BOTH backends, including
synthetic eight-fraction ChirunoMod JPEG TCP input and passive recognition with
zero controller packets. Additional tests cover initial mid-pass synchronization,
partial header/payload timeouts, missing/reordered/slow fractions, RGB correction,
rotation, timestamp provenance and the Old-3DS hardware/calibration gates.

On 2026-11-13 the operator supplied an Old 3DS LL with Luma3DS v13.4 and ChirunoMod
v0.2.2, running ordinary ChLoad on HOME. A real LAN test with this app's direct
receiver observed 15 complete upper passes and 15 complete lower passes in 10.28 s.
Saved PNGs were inspected: native 400x240 / 320x240, Japanese HOME UI, correct
orientation and plausible colours. Assembly spans were 0.44–1.36 s upper and
0.45–1.38 s lower. No Luma input socket was constructed and no controller packets
or resets were sent. The initial attempt stopped on unexpected JPEG dimensions;
the cause remains unresolved. A subsequent passive header/dimension inspection
and separate reconnect test succeeded. No automatic reconnect was introduced.

Private device images/reports remain in ignored `captures/old3ds-home-*` folders.
This verifies ONLY the short ordinary-ChLoad HOME receive test. It does not verify
ChLoad_HIMEM + USUM, InputRedirection coexistence, recognition, reset continuity,
long runs, or startup stability. See [OLD3DS_HIMEM_JA.md](OLD3DS_HIMEM_JA.md).
No HIMEM coexistence receipt has been created.

## HIMEM + USUM passive test: connection failure

On 2026-11-13 the operator reported ChLoad_HIMEM followed by a normal Japanese
USUM launch, unchanged console IP, and a change from cyan to yellow notification LED.
The direct receiver was tested WITHOUT `--send-b`:

| Observation | Result |
| --- | --- |
| TCP 6464 initial connect | Timed out after 5.006 s; no established video connection |
| Upper / lower complete passes | 0 / 0; no JPEG decoding reached |
| ARP query | No entry for the supplied console IP |
| ICMP echo | 0 replies out of 3 |
| Additional TCP connect diagnostic | errno 65, `EHOSTUNREACH`; zero application bytes sent |
| Controller socket / button input / reset | None; no UDP 4950 traffic generated by the test |

The Mac retained the same LAN address and en0 route as the successful HOME test.
The measured failure is at LAN reachability / TCP establishment, before any image
format or recognition handling. A game-triggered switch away from AP Wi-Fi to
local WLAN is a plausible explanation, consistent with the LED, but is NOT proven
by Mac-side logs alone. The console's wireless state and HzLog.log were not obtained.
No wireless settings, patches, buttons, resets, calibration flags or live gates
were changed. No automatic reconnect was attempted.

The developer-maintained [wireless quirks document](https://github.com/Eiim/Chokistream/wiki/Technical-info-on-bugs-and-quirks)
identifies USUM among titles affected by WLAN switching; the [pinned server](https://github.com/ChainSwordCS/ChirunoMod/blob/v0.2.2/soos/main.cpp#L2099)
checks Wi-Fi readiness before TCP bind/listen. These references support an investigation
hypothesis, not a verified device diagnosis.

Private logs: `captures/old3ds-himem-usum-passive-20261113/` contains `report.json`,
`network-diagnostics.json` and `result-ja.md`. They are ignored by Git.
HIMEM reception has now been ATTEMPTED AND FAILED in the observed state;
InputRedirection coexistence and reset continuity remain untested and live remains blocked.

The following original environment/check record is retained as history:

## Environment

- macOS 27.0.1, native arm64 (Apple Silicon), no Rosetta or Wine.
- Homebrew Python 3.12.16, Tcl/Tk 9.1.0, Pillow 13.0.0.
- GUI checks ran in the native WindowServer session, with temporary settings/capture directories.
- Test networking used IPv4 loopback only. No physical 3DS was attached.

## Observed passing checks

| Check | Result and scope |
| --- | --- |
| `python -m unittest discover -s tests -v` | 27 tests passed in the original native-port stage; 43 after the Old 3DS update |
| `python tests/gui_smoke.py` | Native window creation, Japanese-only target controls, English switching, UTF-8 settings round trip, synthetic JPEG UDP → English passive recognition, zero controller packets, floating popup, clean worker/UI shutdown |
| Compile/import checks | Modified Python modules compile; GUI module can be imported without creating a Tk window |
| Transport | Actual loopback TCP setup bytes and UDP bind, actual 20-byte Luma input and return-control packets at a custom port |
| Frame handling | Two independently interleaved screens, frame ID wrap, dropped/out-of-order/malformed data rejection, incomplete JPEG rejection |
| Freshness | Missing/stale frames, repeated frozen images and receive errors are rejected |
| Recognition | Six language/target combinations with **synthetic** fixtures; an upstream English template/coordinate regression; blank placeholder rejection; two-reference colour classification and invalid-threshold rejection |
| Reset guard | Passive dry-run sends nothing; no normal token, expired token, low confidence, unknown, conflicting frames, lost name anchor, changed final verdict and network errors cannot reset |
| Positive reset path | A synthetic confident-normal consensus authorizes a single reset; token consumed; localized title/save stages required |
| Calibration gate | Missing Japanese assets and missing validation receipt block live navigation; changing profile/assets invalidates the receipt |
| Shutdown/error path | Injected receive exception releases controller and stops without retry; real GUI smoke captures worker exceptions and would fail on them |

These checks establish software behavior for the tested inputs. They do **not** establish Japanese
recognition accuracy, real NTR-HR interoperability, reliable gift navigation or successful shiny hunting.

## Not verified

- Japanese game screenshots, correct Japanese ROIs, dialogues, name/menu templates, actual colour distributions.
- Physical NTR-HR stream reception and physical InputRedirection response on Apple Silicon.
- Hardware disconnects, screen freezes and title transitions on a real console.
- Poipole, Type: Null Poni or Type: Null Aether completing repeated live hunt rounds.
- Correct stopping on a real shiny, long-duration stability, real multi-console operation.
- Upstream English Battle/Lotto/other gift targets and recording formats on physical hardware.
- Windows/Linux execution locally. Cross-platform CI is defined separately; its result must be read from GitHub Actions.
- A signed/notarized `.app` or PyInstaller packaging. The supported and tested Mac launch is Python source.

## Deliberate compatibility changes

English source paths and original image assets remain available. The three English gift routes now use
the same conservative runner as Japanese: no initial reset, no gift Boost, passive dry-run by default,
and a real save-file template plus operator validation receipt required for live operation.
An English gift recognition error no longer falls through to another reset.
Legacy English modes remain outside the new gift calibration contract and are blocked by default dry-run.
Settings on Windows retain the upstream temp-directory migration; macOS gets per-user persistent settings.
Capture defaults move to the user's Pictures/ShinyHunterUSUM directory.

## Hardware completion gate

Follow [CALIBRATION_JA.md](CALIBRATION_JA.md) for each target separately. Supply real Japanese assets,
independent normal/shiny/unknown fixtures and positive/negative fixtures for every navigation stage,
confirm the hardware checklist, then explicitly attest the evidence. No validation receipt is shipped.

## Cross-platform follow-up

The first GitHub Actions run found that Windows can return the same timestamp
for successive evidence sessions. Evidence directories now use an atomic,
randomized `mkdtemp` suffix; a fixed-clock collision regression is included.
The unavailable `macos-14` hosted-runner configuration was replaced by
`macos-latest`. Refer to the current commit's Actions run for CI results.

## Native delivery-rehearsal GUI (2026-11-14)

The new Recv test window records screenshots and intended keys while the operator
performs all recording inputs on the console. Default playback is passive, with
manual acknowledgements. Live replay requires a completed passive cycle, a
pre-receipt-save declaration and explicit in-app approval; it is capped at three
cycles. A received-screen reset checkpoint must differ from the initial field.
Three new complete frames must match the recorded ROI per step, with a final
pre-send recheck. Unknown, stale, frozen or broken video stops without retries.
The window saves private PNGs, scores, trace and report, and cannot save the game.
It does not classify shininess or unlock gift-hunt calibration gates.

59 unit/loopback tests pass, including passive zero-input, authorization gates,
three synthetic live cycles, unknown/stale rejection and received-screen checks.
Native Tk window creation/defaults and 968x855 layout on a 1512x982 Mac display
were checked with no console connection. The new GUI's delivery recording,
physical playback and three-cycle stability have NOT been verified on hardware.
Earlier command-line reset tests do not imply this GUI is hardware-validated.

# Validation record — 2026-11-13

Base: `u93132/ShinyHunterUSUM@f49910affd7ed35b38af8e2b5b35499dcc554f0d`.
Branch: `macos-japanese-gifts` on `senuhi/ShinyHunterUSUM`.

## Latest: receive → summary → normal-only reset (2026-11-14)

The operator reported that the fixed receive/reset round returned, and correctly
pointed out that opening and checking the received Pokemon was missing. The
latest private run sent 18 datagrams / one reset. Its counter stayed at zero
because the lower Rotom map had changed into a question after loading, although
the upper field scene returned (upper MAE ~0.037, lower ~0.431). Fixed diagnostics
now verify the upper saved-location scene, retaining freshness for both screens.
This is not a reason to weaken colour or communication checks.

The diagnostic now clears dialogue with upstream's ten B presses, opens the
Pokemon menu, selects the last slot using the declared pre-receipt party count,
and selects Summary with A/A. The operator confirmed four pre-receipt Pokemon;
the deterministic path from the first slot is Down, Down, A, A. These newly added
navigation steps have not yet been physically validated. All runs still start
at the same saved pre-receipt NPC, without dialogue.

The existing `colour_verdict` function and upstream 8×8 USUM star colour references
are reused. Vision must find the expected name and two OT/ID/experience field
groups. Three new pairs must agree; a final new pair must still be normal before
reset. Shiny, unknown, conflicting, stale, lost-name/context or broken-stream
results cannot reset. Default is to stop at Summary even on normal: it is a live
navigation diagnostic with no reset, distinct from the zero-input passive check.
Turning that option off requires explicit in-app permission for the one reset.
The references and Japanese coordinates remain UNVERIFIED and are configurable
in `profiles/pikachu-diagnostic-ja.json`. No shiny accuracy or hunt live gate is
claimed or enabled. Full normal-run budget for four party members is 22 presses
/ 66 datagrams; summary-only is 19 / 57. Neither mode saves the game.

Software checks use synthetic fixtures. Real Summary recognition, actual shiny
star footage, three-target gift navigation and physical normal-only reset
verification remain outstanding. See [SUMMARY_TEST_JA.md](SUMMARY_TEST_JA.md).

86 unit/loopback tests passed, including three colour states, name/context
rejection, default summary stop, unknown receipt, conflicting results, changed
final verdict and disconnect-before-reset. Native GUI + actual loopback TCP/UDP
and Apple's Vision passed both the synthetic 66-datagram full normal round and
the 57-datagram summary-only stop. A 1.1-second fraction delay and a changed lower
Rotom screen after reset were included. Waits were asserted but shortened in
the simulation. These checks do not validate physical menu timing or colours.

## Latest: one saved NPC start, timed navigation (2026-11-14)

Per the operator's correction, the default diagnostic now starts only in the
saved pre-receipt field, facing the gift NPC with no conversation open. It does
not offer title, dialogue or received-state resume starts. The current connection's
passive preflight sends nothing and supplies the sole baseline for the final check.

The bounded sequence is A × 3 at 3-second intervals, post-receipt consensus and
final recheck, reset once, wait 25 seconds, START, wait 5 seconds, A, wait 12 seconds,
then confirm the saved field. Existing Luma press/release/return transport is reused.
No intermediate dialogue/title/continue OCR or template matching is performed.
No game save or shiny classification is performed. Unknown/weak receipt results
stop without extra A or reset. A full run is at most six presses / 18 datagrams.

The latest physical attempt confirmed the received message and sent exactly one
reset (3 datagrams), reaching the Japanese Ultra Sun title. It then stopped before
START: title animation/blinking made template matching unstable, and the origin
age check failed while a new fraction set was arriving. No complete physical
receive/reset/restore cycle has been observed. This change removes title matching.

Input still requires each image's origin age and assembly span <= 2 seconds.
A recent completed image with an older origin temporarily pauses inputs, while
video reception continues waiting for a fresh pass. Receiver checks still reject
completion silence > 2 seconds, assembly > 2 seconds, frozen pixels > 15 seconds
and errors. These conditions stop; they never authorize a reset or runtime retry.
The primary hunt runner's strict snapshots and calibration gates are unchanged.

80 unit/loopback tests passed. The native Tk integration used real loopback
Chiruno TCP/Luma UDP and Apple's local Vision OCR with synthetic screens. It
passed the fixed six presses / 18 datagrams and one completed cycle, including
a 1.1-second injected fraction delay. Navigation screens intentionally had no
recognition templates. Requested waits were asserted as [3,3,3,25,5,12] but
shortened for this mock test: this does not validate real console timing.
Unit tests reject unknown receipts without reset, confirm passive zero input,
and verify origin-age pauses versus true transport silence. No physical console
was connected or controlled during these software checks. Hardware verification
of the updated fixed sequence remains pending.

The former received-state recovery implementation below is historical; the
default GUI no longer exposes it. Private physical logs/images remain untracked.

## History: real Pikachu receipt reached; diacritic fix and receipt recovery

The operator's application advanced the real Japanese Pikachu delivery using
three A presses (9 datagrams). The operator and screenshot confirm the received
message. No reset was sent: corrected OCR read Pikachu at score 1, but uncorrected
OCR confused the small diacritic and scored 0.3, so corroboration failed and the
application stopped safely. A complete physical cycle is still unverified.

Receipt corroboration now binarizes and normalizes dark/light polarity before
uncorrected OCR. The actual saved native receipt frame passed twice at unchanged
primary/backup thresholds (1 / 0.5), without substituting Pokemon names or
lowering confidence limits. Personal screenshots remain private.

The GUI can explicitly resume from a recognized received message: a new in-app
approval authorizes reset once, START and continue A only. It sends no further
receipt A inputs. Successful recovery increments completed_recoveries, not a
full delivery-cycle counter, and requires a new passive check before another
run. All 76 unit/loopback tests pass. Native GUI + Vision + actual local TCP/UDP
passed both a synthetic full cycle with dark receipt text (15 datagrams) and a
synthetic received-state recovery (9 datagrams). Those do not establish that
the current real console has reset/recovered yet; the operator's real test is
pending. The running old application needs a restart to load this change.

## Latest: bounded read-only recovery of the first 2x50 JPEG

The first application connection after console startup failed on the same
2x50 upper JPEG previously observed; the operator retried and reported video.
No controller packet or game reset was sent by that failed connection.

The source now retries TCP video setup once only for that exact first-video
JPEG signature (kind 1, flags 1, fraction 8, dimensions 2x50), before any complete
frame has been published. Invalid images are never displayed or counted as
fresh frames. A repeated startup error, any other error, a later error after
valid video, or explicit close cannot trigger another connection. Stop/cancel
also prevents reconnecting. The normal runtime stop behavior is unchanged.

All 73 unit/loopback tests pass. A real loopback server exercised failure on the
first connection, successful complete-pass reception on the second, and no
reconnect after EOF. This automatic recovery has not yet been observed on the
physical console. Existing GUI processes need a restart to load the change;
the operator's currently successful connection was not interrupted.

## Latest: automatic delivery GUI, ready for hardware validation

On 2026-11-14 the default diagnostic window was changed to passive recognition
check followed by one opt-in automatic Japanese Pikachu delivery/reset/restore.
Manual recording remains in an optional advanced panel. The hunt calibration
and hardware gates remain unchanged; this diagnostic never classifies shininess
or saves the game. A pre-receipt save declaration and explicit in-app permission
are required, with at most 15 actions and one reset.

69 unit/loopback tests pass. A native-GUI integration test used actual loopback
Chiruno TCP and InputRedirection UDP plus Apple's real Vision OCR, with synthetic
game images/transitions. It completed field → dialogue → received → reset →
title → continue → field with five key/chord presses (15 datagrams, one reset).
The recognition check sent zero inputs. Non-loopback connections were forbidden
by a Python audit hook. No physical 3DS was connected or operated in this work.
The new GUI's actual delivery/reset behavior on hardware is still unverified.

Saved real dialogue/title/continue frames were inspected offline. Initial Vision
model preparation took about 39–41 seconds; later requests took 0.1–0.3 seconds.
A pinned Japanese-capable Vision revision and a 65-second passive warmup replace
the previous too-short initialization limit. Synthetic receipt/question/future,
black/white and corrected/uncorrected OCR cases were checked. These are not real
Japanese receipt fixtures and do not establish receipt recognition accuracy.

Reset requires an exact past-tense Pikachu receipt message, primary OCR score
at least 0.9, agreeing uncorrected text (score at least 0.5), repeated fresh
observations and a final recheck. Question/quotation/future/weak/changed messages
cannot authorize reset. Subsequent title/continue use cropped real UI references;
ROI scores reject blank/wrong screens. Static examples do not prove all visual
variants. Stream errors stop the run, with no reconnect/reset retry. Logging
failure sets the stop flag before attempting further disk writes.

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

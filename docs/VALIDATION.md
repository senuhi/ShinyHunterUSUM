# Validation record — 2026-11-13

Base: `u93132/ShinyHunterUSUM@f49910affd7ed35b38af8e2b5b35499dcc554f0d`.
Branch: `macos-japanese-gifts` on `senuhi/ShinyHunterUSUM`.

## 2026-11-22: physical freeze reported; reboot retry preparation (v1.6.1)

The new native session completed five rounds and sent its sixth normal-guarded
reset. At the title both decoded images then remained identical for at least
fifteen seconds. Four actual video reattachments received completed images but
no visual motion; no START was sent because the animated-title template scored
.14687 against a .1 limit. The operator also reported a static physical screen
and no response to physical START. This supports a game/console-side stall, not
merely a Mac display problem, but does not identify ChirunoMod, USUM, Luma or
previous overnight uptime as the cause. The operator is rebooting to retry.

After a confirmed and sent normal reset, the app now sends the first START once
fresh video is available, without requiring the animated logo crop to match.
Continue/return checks and every normal/shiny/reset guard remain. Recovery from
Frozen-screen errors now requires actual pixel change on at least one screen,
instead of treating new TCP timestamps on the same frozen picture as recovery.
Nine focused regressions passed (17.366 s), including unmatchable title artwork,
both routes' multi-round loops, shiny zero-reset, and cached frozen-image veto.
These software changes do not claim to repair the reported physical freeze.
The operator subsequently confirmed a physical reboot and the same console IP,
with HIMEM/USUM/InputRedirection ready at the saved NPC. Via the app UI the normal
cycle-zero hunt was started. At elapsed 24.402 s, the same native ChirunoMod
assembly-freshness error occurred; the app suspended input, reattached video and
resumed on fresh pairs at 26.048 s (about 1.65 s later), without terminating the
hunt. Fresh NORMAL/name-matched Summary pairs and final confirmation then led to
one reset and a complete saved-field return; the next ordinary round also
reached NORMAL and its reset. This is native evidence of automatic video fault
recovery and boot progression after reboot, distinct from the earlier loopback
proof. It does not establish the cause of the earlier physical freeze or prove
thousands of uninterrupted rounds.

## 2026-11-22: video-only recovery instead of terminating the hunt (v1.6)

The native session that started at about 11:28 JST completed eighteen normal
rounds/resets. During registration in round nineteen, one ChirunoMod fractional
screen exceeded the unchanged two-second assembly limit (elapsed 1868.043 s).
The receiver terminated; the worker then overwrote the visible cause with a
generic receiver-stopped error. The NORMAL result still shown belonged to round
eighteen, not the unclassified nineteenth gift. No nineteenth reset was sent.
Earlier nighttime stops had different immediate triggers: one initial A produced
no dialogue, late NPC dialogue was mistaken for menu progression, and one title
screen receive gap exceeded two seconds. Those were not proof of a shiny or of
Mac sleep. The remaining video fault was fatal because automatic reattachment
was missing from the production app.

The Japanese production app now suspends input on decoder/socket/stale/frozen
video errors and reopens only the video source. Partial decoder state is thrown
away; a bounded recovery (five attempts, approximately ninety seconds) requires
at least two new complete frames from each screen under the original freshness
limits. Frame serials remain monotonic, but old freeze timestamps are discarded.
Action deadlines exclude recovery time. Navigation buttons computed on an older
video generation are cancelled, not replayed. Summary consensus is discarded
across video generations and must obtain three fresh NORMAL pairs again, plus
the final semantic/colour/freshness guard immediately before RESET. A RESET
already sent is never replayed. Title/continue states are observed before START/A.
The existing English/diagnostic receiver remains fail-closed by default.
Terminal failures retain the first cause. Each round clears the preceding
Summary result and tags new evidence with its round number. Explicit recovery
of an old report containing a stale previous-round NORMAL result requires journal
proof of previous Summary -> reset -> a new receipt. Registration cleanup uses B
only until three matches of the original saved field; fresh Summary judgement is
still required before resetting that individual.

Verification:

- All 137 unit/loopback regressions passed (89.328 s, localhost sockets only).
- After adding a lock to preserve the first failure under competing worker errors,
  the five receiver recovery regressions passed again (1.957 s).
- Native Tk + actual local Vision + loopback Chiruno/Luma, with the TCP connection
  deliberately cut during reception: NORMAL recovered and completed one round
  (147 controller datagrams, one reset). The same cut followed by a synthetic red
  shiny star recovered and stopped with zero resets (126 datagrams). Timers were
  shortened; these are synthetic game images, not hardware shiny validation.
- Via the Mac app UI, the unclassified nineteenth native individual was preserved,
  taken from registration to Summary, newly confirmed NORMAL and reset once.
  The app then completed another ordinary native round and began its next round,
  with cycle limit zero and no safe-stop event at that observation. Real native
  disconnect/reattach has not yet occurred in this new session; the native loop
  and the deliberately interrupted loopback test are distinct evidence.

No CLI tool connected to or controlled the physical console. Native shiny
accuracy, native Type: Null Poni, and thousands of uninterrupted hardware rounds
remain unverified. Hourly Codex checks are separately configured; transient video
recovery now belongs to the app and does not wait for that scheduled check.

## 2026-11-22: observed navigation, repeated masks and pending-gift resume (v1.5)

After four native rounds in the new session, round five reached its receipt,
then B cleanup. Three field matches (.00519, .00545, .00500) were followed by X
and the fixed A/right/A/A sequence. At the final sample the native upper screen
still contained the NPC's thank-you dialogue and the lower map was dimmed. The
app had not verified that X actually opened the menu. It stopped UNKNOWN with
zero additional resets (four resets/four completed rounds, 675 datagrams). This
may reflect a lost X, a late post-gift dialogue, or both; the wire logs cannot
prove which. The candidate was left unclassified and was not reset.

Review also found that upstream TabBase.click sends each down/up state three
times, while the new app diagnostic transport had sent each only once. The
production app now uses three identical down masks, three neutral masks and one
return-control packet per logical press. The old/English diagnostic default
remains unchanged. Reset authorization is counted once and the final normal
veto remains before the first reset-down packet; repeated masks do not bypass it.

Native static menu/party UI label crops (without trainer/Pokemon data) are now
language-specific navigation assets. Both textured anchors must match; flat
similar-colour backgrounds are rejected. Party selection checks the dominant red
cursor/border at slots one/two. Lower Rotom frame colour ratios distinguish the
map even when dimmed, and upper saved-field geometry distinguishes NPC dialogue
from Summary. Summary arrival uses the existing information-field groups across
both screens. The actual name, star and colour decision remains in the existing
three-fresh-pair/final-check path.

Navigation now observes before advancing: field→X, known menu→A, first party
slot→right, second slot→A, known Summary context→A. Unchanged known states retry
the appropriate input. A late NPC dialogue returns to B, then X; A is never
blindly sent merely because two seconds elapsed after X. The navigation recovery
has a 120-second/90-action limit and never uses reset. A genuine unrecognized
state, unhealthy transport or undecidable Summary still stops without reset.

An explicit --resume-receipt path can preserve the current pending gift across
this software update. Before control, it validates source target, pending round,
no reset of that round, receipt evidence, original field images and current
site/map (with or without the remaining dialogue). A recognized menu/party can
first be closed with B only; three original-field matches are required before
A/X navigation. If the second slot remains unselectable after three right
attempts, reception is retried once from that verified field, without resetting.
A source already shiny, reset, wrong-target or unknown on a
real Summary is rejected. The first resumed round skips receive, navigates the
existing individual to Summary, and may reset only after fresh NORMAL consensus;
after its return, ordinary continuous reception resumes. Opening the recovery
GUI sends nothing; the operator must Receive/Preflight/Start in the app.

Validation:

- 125 offline/loopback tests passed in one run (72.677 s). An additional source-
  rejection regression and the resume normal/shiny test passed afterward (two
  tests, 2.098 s). Resume-source counter types were then hardened; the two affected
  tests passed again (2.065 s). Allowing a same-site closed dialogue was checked
  with both normal and shiny resume cases (two tests, 3.831 s). The additional menu/one-member recovery regression passed for normal and shiny
  cases (6.139 s). Colour and reset consensus requirements are unchanged.
- v1.5.1 complete suite: 128 tests executed in 77.495 s; 124 passed and four
  loopback socket tests were denied by the sandbox. Those exact four passed
  outside the network sandbox (0.438 s, localhost only). After the native cursor
  correction added another regression, all 26 affected navigation/app-loop tests
  passed (55.731 s). The current suite contains 129 test methods.
- Regressions cover a lost X/menu A/right/party A/context A, late dialogue after X,
  resuming an already-received normal/shiny gift, and rejection of unsafe sources.
- Native Tk + local Vision + loopback Chiruno/Luma: ordinary normal round 147
  datagrams/reset one; late-dialogue automatic recovery 161/reset one; pending
  normal resume 63/reset one; pending shiny resume 42/reset zero. Timers shortened.
- Saved native images classify as NPC dialogue, menu, first party slot and Summary.
  During live one-member recovery, the two footer labels blink independently;
  navigation accepts one textured matching footer plus an unambiguous red party
  cursor. Neither evidence alone is accepted. This has no colour/reset authority.
  The current dim map's red-frame mismatch is .00838 (limit .13); unrelated menu,
  party and Summary mismatch >.84. This is saved-image evidence, not live control.
- Native English GUI regression passed in dry-run with controller packets zero.

Native follow-up used only the installed Mac app UI; no CLI tool connected to
or controlled the physical 3DS. The initial recovery found only the saved party
member (the earlier gift was no longer present), returned to the original field
with B, retried reception and obtained Poipole. Real first-card art contributes
about 59 red pixels while unselected and 104+ when selected; second-slot arrow
samples were 23–57 pixels. Cursor classification was corrected to reject overlap
and distinguish this art from the arrow. Normal Summary consensus and final
normal confirmation then produced one reset. That session stopped at the title
after a >2 s receive gap; no additional reset was sent.

At approximately 11:28 JST the operator manually restarted the app, with cycle
limit zero. Its new native session subsequently completed two ordinary normal
rounds and entered round three without a safe-stop event. Both completed rounds
had three NORMAL/name-matched Summary pairs plus a fourth final normal check;
saved-field return scores were .0017–.0045 (limit .05). This confirms the native
Poipole receive/Summary/reset/return loop with the cursor correction, not
indefinite unattended reliability. The in-app fail-closed transport limits remain
unchanged. An unfinished post-reset reconnect experiment was removed rather
than shipping an unused recovery path. Hourly checks were separately enabled in
the Codex app at the user's request; a real outage can still stop the hunt before
that scheduled review. Native shiny accuracy and native Type: Null Poni remain
unverified. No fake calibration or hardware-validation attestation was issued.

A resumed session also persists the verified original pre-gift baseline and
receipt evidence in its new folder, rather than leaving the passive menu/party
capture under the baseline filenames. The affected normal/shiny recovery tests
passed again (two tests, 10.135 s). This persistence correction applies on the
next launch and does not require interrupting a running ordinary hunt.

## 2026-11-22: 17 native rounds, then unresponsive start (v1.4.5)

The native continuous session completed seventeen normal rounds and seventeen
resets, then stopped during round eighteen (2289 controller datagrams). Its last
normal reset, START and continue led to three saved-field matches (.00444,
.00316, .00271). The next initial A attempt/completion was logged once; subsequent
OCR was empty for the entire 75-second receipt timeout. Fresh upper/lower video
continued at roughly .4-second assembly spans, and the separately created macOS
sleep-prevention assertions were still active when inspected. The stopped PNG
also matches the original saved field (.00318). There was no eighteenth reset.

The app previously never retried an initial A when it produced no dialogue. This
turned a possible single UDP input loss or late game readiness into a long wait
and stop. The logs do not distinguish lost input, game readiness or a console-side
InputRedirection failure; no hardware cause has been established.

v1.4.5 retries the initial A at least two seconds apart, at most three times,
ONLY before any Japanese dialogue has appeared and after three new blank-OCR
frames match the saved upper field. Unknown transitions, stale/frozen video,
network errors, Summary/identity uncertainty and all final-reset guards remain
fail-closed. No automatic reset is used to recover input. If all four start
attempts have no effect, the app explicitly asks to check InputRedirection and
stops. This does not claim to repair a dead console input service.

All 117 offline/loopback tests passed (50.737 s). Regressions cover one lost
initial A followed by a complete round, permanently unresponsive starts bounded
to four A presses/reset zero, and a blank field after dialogue not being treated
as a new start. Native Tk/local Vision/loopback TCP+UDP also simulated dropping the
first start press: one automatic retry, a normal round completed, 66 datagrams
and one reset. These fault-injection checks are synthetic, not new physical
console operations. Codex sent no console connection/input/reset.

## 2026-11-22: bound continuous-run diagnostic logs (v1.4.4)

The operator asked whether growing upper/lower frame counters meant that all
frames were being written to disk or could overflow. The implementation keeps
latest screen images and Python integer counters; frame events contain timing
and count metadata, not image data. Production PNG evidence already retains only
ten completed normal rounds, plus the active round and fixed baseline/received/
restored/failure images. Existing session directories are retained separately.

A read-only check of the active native session found 887/886 received frames,
37 PNGs (4,963,235 bytes), 279,566 bytes of event text and 5,247,794 total bytes.
Its report was in round four, completed cycles three, reset attempts four. The
prior sixteen session folders together used 15,580,503 bytes at that instant.
This is a point-in-time observation, not a disk-usage limit or timing benchmark.

The event JSONL previously appended without a size limit. v1.4.4 introduces an
8MiB active-file budget and two rotated backups (24MiB total per new connection's
event log). Whole UTF-8 JSON lines are rotated before writes. Oversized records
and I/O failures propagate instead of silently disabling safety logging. The
helper targets only event-log files, not candidate or failure images. This
modifies disk diagnostics, not game control or classification. The current old
app process is not hot-patched, restarted, disconnected or otherwise touched;
the cap applies on its next ordinary launch. Old folders and launcher stderr
logs are not retroactively deleted by this feature.

Three new regressions cover Unicode byte budgets/backup count/record continuity,
zero-backup mode/oversized event rejection, unrelated candidate preservation and
I/O error propagation. All 114 offline/loopback tests passed (46.976 s).
No console connection/input/reset was performed by Codex.

## 2026-11-22: first native Poipole normal round completed (v1.4.3)

The operator ran the dedicated app and reported one round followed by a manual
Stop. The saved report confirms target poipole, normal Summary, reset_attempts
one, completed_cycles one and 138 controller datagrams. No safe_stop event
occurred. Stop subsequently changed the status text but preserved completion.
The app was configured for one round and had already recorded its return proof.

Three distinct native Summary pairs (serials 157, 159 and 160 on both screens)
confirmed the target name via the localized-name/uncorrected path, both experience
anchors and NORMAL. A fourth fresh pair (serials 162) confirmed NORMAL immediately
before reset. Each normal distance was .0718 versus shiny 1.031 with red pixels
zero. The reset attempted/completed events appear exactly once. After START and
continue, three distinct upper saved-field matches scored .00633, .00631 and
.00626 (limit .05), and both restored-field screenshots were saved. The report's
elapsed time was approximately 120 seconds, including the operator/startup wait.
Codex only read the existing files; it sent no console controls or connections.

This verifies one complete native Poipole NORMAL route: receipt, first Pokedex
registration/dialogue exit, slot-two Summary, identity/normal consensus, final
normal recheck, reset and saved-position return. It supports proceeding to the
operator-authorized continuous mode (cycles zero) in the same app. Native shiny
classification/stop remains unverified; positive synthetic and saved-image
marker tests are separate evidence. Long-run stability and native Type: Null
Poni operation are still unverified.

## 2026-11-22: native Poipole Summary name ROI fix (v1.4.3)

The operator's next attempt reached the actual Poipole Summary. It sent 120
navigation datagrams/reset zero and stopped as unknown. The colour patch was
normal (distance .0718 versus shiny 1.031, red pixels zero, stddev 10.06), and the
two experience-field anchors were strong. Identity failed: full-screen Vision
omitted the lower white-on-green name entirely and read the correct upper label
at .3. Thus the existing two-screen low-score fallback could not confirm identity.

The two production profiles now include explicit name-field ROIs. If full-screen
identity is insufficient, the lower crop is binarized/inverted with padding and
the upper crop is converted to grayscale. Both exact names at .3 or better, both
uncorrected exact reads and the existing two context groups are mandatory. This
changes name-image preparation, not star coordinates, colour thresholds, sample
consensus or final reset gates. Type: Null shares the expected Summary layout;
its native crop recognition remains untested.

Replaying the exact saved native Poipole pair through the actual local Vision
helper and check_summary now returns NORMAL/name matched via both ROIs and both
uncorrected reads. One measured full check took .823 s after warmup. This is an
offline saved-image result, not three new frames or a physical reset approval.
The saved native pair with a synthetic red marker added to a copy returned SHINY
through the same actual OCR/classifier path. The original PNGs were unchanged;
controller packets zero and reset_authorized false were recorded in private
local replay evidence. All 111 offline/loopback tests passed (47.001 s). New regression cases cover
missing full-screen names, both ROI names, a conflicting uncorrected crop, a
wrong crop name, unchanged original pixels and an overriding red-star candidate.
No new console connection/input/reset was performed by Codex.

## 2026-11-22: receipt OCR is navigation only (v1.4.2)

After the HOME-side InputRedirection startup workaround, the operator reached a
native Poipole completion message. The corrected OCR read "SENは ベベノムをもらった！"
with .5 confidence, but an uncorrected reread disagreed and aborted navigation.
The capture recorded 21 input datagrams/reset zero, before entering Summary.
This stop gate was unnecessarily applying colour-evidence standards to dialogue
navigation and prevented useful operation despite a clear completion message.

The dedicated app now uses an exact-form target completion clause as a navigation
hint only, without a confidence floor, three-frame requirement, image refinement
or independent uncorrected read. It switches to the bounded B cleanup and then
Summary. Questions, future-tense offers and other target names do not constitute
a completion hint. Silence, invalid input/transport and bounded-action timeouts
still stop. Summary name/context/colour consensus and all final-reset guards
are unchanged; the navigation hint cannot authorize a reset.

Regressions reproduce weak receipt scores and an uncorrected receipt disagreement,
and also a weak receipt followed by an unknown Summary: only a separately normal
Summary permits reset; an unknown Summary still sends no reset. All 110 offline/
loopback tests passed (46.649 s). The native Tk synthetic normal round passed
with 63 datagrams/reset one after this change. No new physical
console connection/input/reset was performed by Codex.

## 2026-11-22: native first-registration stop and bounded dialogue exit

The first Poipole app attempt saved an unknown verdict on the Pokedex
"registration complete" screen, not on Summary. It sent 69 navigation datagrams,
zero resets and completed zero rounds. Local receipt OCR did identify the native
Japanese completion phrase consistently. The ten-B cleanup interval expired
while the first-registration animation was still running; later menu inputs
therefore did not navigate to Summary. This attempt does not validate native
normal/shiny Summary classification.

v1.4.1 replaces that fixed ten-B prefix in the dedicated app with a bounded
upstream-style B-until-dialogue-ended phase. Before X, three new upper frames
must match this connection's passive saved-field baseline (RGB difference at
most .05). B is limited to 60 presses/60 seconds; an unconfirmed return sends no
menu navigation or reset. Summary identity/context/three-frame colour consensus
and the final reset veto are unchanged. English and old diagnostics are unchanged.

New regressions simulate registration requiring eighteen B presses and a
registration timeout. All 108 offline/loopback tests passed (41.481 s), including
the eleven app-specific tests. Native production
GUI loopback normal still completed one round with 63 datagrams/reset one, and
the red-star positive stopped with 54 datagrams/reset zero. These are synthetic
screen tests with shortened timers, not new physical-console operations.

The operator also reported Python disappearing. No matching Python/Vision crash
report was found in the inspected DiagnosticReports folders; the reason for
process termination remains unknown. The Finder launcher now enables Python
faulthandler and retains stderr and the process exit code in ignored local
captures/gui-*.log files. It does not auto-restart the app or reconnect the game.
The registration correction must be tested from a new app process on the native
pre-receipt save. No new console connection/input/reset was performed by Codex.

## 2026-11-21: v1.4 dedicated Japanese app loop completed in software

The old template-driven Japanese route did not have native target assets and was
not ready to start. v1.4 supplies a distinct app-owned path for Poipole and Type:
Null Poni using local Vision receipt confirmation, with shared transport, input,
Summary checking and final normal-only reset guards. No template calibration or
hardware validation attestation was invented. English and the legacy diagnostic
remain available. Party size is one; the new gift is slot two.

The dedicated screen supports one round, a selected count, or zero for continuous
rounds. Startup, reception and the passive connection check send no controls.
The operator's Start click enables the selected run. By default it stops at the
Summary screen without reset. Explicit normal-reset operation requires three
fresh matching normal verdicts and a fourth fresh semantic/colour check. After
log I/O, the final send callback again checks frame age, star evidence and Summary
headers before the reset-down datagram. A late star, a changed page, a stale
image, unknown/mismatching classification or stream failure stops the worker.
There is no reset retry and no game-save operation.

Receipt recognition requires an exact target completion clause, independent
uncorrected agreement and three fresh repetitions. Correct Japanese rare names
can have discrete low Vision scores even in generated clear images. The Summary
fallback therefore requires exact labels on both screens, the same labels on
both uncorrected reads and at least two strong information-field anchors, in
addition to the three-frame and final reset checks. One weak name or a conflicting
uncorrected name remains unknown. This is corroboration, not a statistical
accuracy guarantee.

Final checks on this revision:

- 106 offline/loopback tests passed (40.023 s). The sandboxed invocation initially
  denied four local socket binds; rerunning with local-socket permission passed.
- The app loop mock completed two rounds for each production target. Continuous
  mode stopped on a red-star positive with reset zero for each target. Negative
  cases include unknown/weak receipt, Stop during navigation, a final-check star,
  and a star injected after final OCR during the reset log write: no reset down.
- Native Tk production GUI with real loopback Chiruno TCP/JPEG decoding, local
  Vision and Luma UDP: Poipole normal 63 datagrams/reset one; Poni normal 72
  datagrams/reset one; Poipole star positive 54 datagrams/reset zero. Timers are
  shortened in this harness. Poni normal and Poipole positive were repeated after
  the final packet guard was added. All images/transitions are synthetic.
- Native English Chiruno GUI regression: normal dry-run, controller packets zero,
  settings/controls/popups/shutdown passed. Transport tests also cover NTR-HR.

The operator is away with the console closed. No new physical button/reset was
sent during this work. The current Poipole/Type: Null data have not completed a
round in this new app yet. Real shiny accuracy and long-run stability are not
verified. The supplied star screenshot and positive synthetic tests support the
implemented stop path; they do not prove every possible native image will be
classified correctly. The operator has authorized proceeding without waiting for
a real shiny trial. First native operation remains in the app, not via Codex's
network/individual-button tools.

## 2026-11-21: separate shiny-positive tests; operator accepts no native shiny trial

The operator correctly noted that normal-only rounds cannot verify a shiny stop.
Two positive-path regressions now exercise both production target profiles and
both marker layouts using actual `colour_verdict`, `GiftRunner.classify` and
`GiftRunner.run`, rather than substituting a mocked shiny verdict. Synthetic
name anchors isolate the still-missing native Japanese assets. Three shiny
results reach `shiny_stop` with no reset authorization, controller press/send,
normal-round increment or normal token. A second test first establishes normal
consensus, adds a red marker at the alternate position and confirms that the
actual final reset check rejects it before any reset packets.

96 offline tests passed. A new native GUI loopback mode (`--party-one
--summary-shiny`) supplies a synthetic red marker with the primary colour patch
still green. With ordinary normal-reset operation enabled, real JPEG TCP decode,
local Vision and the Summary guard reached shiny and stopped: 54 navigation
datagrams, zero reset attempts. This does not operate a real console. The supplied
YouTube marker image was also rerun through both target colour configurations;
both detected a shiny candidate (33 red pixels). This latter check covers the
rescaled marker, not a complete native image pair or target-name recognition.

The operator explicitly authorized proceeding toward a Poipole loop on the
current saved pre-receipt data once the available software evidence is checked,
without waiting for a real shiny on the console. A native shiny acquisition is
therefore not a condition for beginning the authorized controlled operation.
Native shiny accuracy remains unverified and must not be reported otherwise.
Native normal Summary/identity/position confirmation, fresh frames, fail-closed
unknown handling and final normal recheck remain required. Existing missing
templates/validation records have not been fabricated or silently bypassed.
Connection work is pending the current console IP and HIMEM/InputRedirection
state; no new device input or reset was sent during these checks.

## Latest scope: Poipole + Type: Null Poni using upstream reception flow

The operator changed Type: Null production from Aether to Poni to avoid preparing
full storage, and requested upstream-compatible starting positions and logic.
Current Japanese targets are Poipole and Poni; Aether is hidden/rejected for this
production scope. English Aether and the original Recv implementations remain.
The default party remains one member and the gift is the second member.

The preserved upstream README specifies facing the gift NPC for Poipole and
standing to the left of the event trigger for Poni. The Poni route in
`Recv.findrecv` presses right for 0.1 seconds, neutralizes, and repeats three
times, then advances the name dialogue with A. `nav_dialogue` uses B for the
Poipole party-added message and B for Poni's end-of-dialogue message.
`GiftRunner.receive` retains that per-target movement and A/B branch structure;
it is not replaced with the earlier Pikachu diagnostic's A-count or new OCR
navigation. Japanese names/dialogue/menu templates still need calibration.

Japanese Summary selection now explicitly uses the previously tested Mac
one-member path (Right, A, A) after the party-list anchor, then checks the target
name without blindly cycling other party members. English retains its existing
selection path. The normal-only reset, red-star veto, freshness and validation
gates remain. Old profile templates alone do not establish the new route's
physical readiness; no validation receipt was issued.

94 offline tests passed. A new regression invokes the preserved `Recv.findrecv`
and `nav_dialogue` methods with mocked devices and compares their receipt-prefix
buttons and Poni movement against the Mac runner. It also checks Japanese
second-slot Summary selection and absence of reset. Native GUI loopback checks
passed for both Chiruno and NTR, including Japanese Poni selection, Japanese
Aether hiding and retained English options. No physical input or network
connection to the 3DS occurred during this change. Poni event-boundary distance,
native Japanese assets and both target routes still await hardware validation.

The current preparation guide replaces the earlier Aether/full-storage advice:
[PRODUCTION_PREP_JA.md](PRODUCTION_PREP_JA.md). Earlier sections below are history.

## Latest preparation: two Japanese routes, one party member, red-star guard

The operator narrowed production to Poipole and Type: Null Aether, starting
with one party member. Japanese Poni is hidden/rejected without deleting English
Poni functionality. The received slot is two, so its fixed selection is Right,
A, A from the first party cursor. Diagnostic defaults now use one party member;
the earlier four-member tests remain supported. Fixed receipt sequences for the
two actual gifts remain explicitly pending native pre-receipt-save validation.

Two separate summary profiles and a read-only production-preparation manifest
were added. A local native-pair replay uses the shared summary checks for either
Japanese name, including Type: Null colon variants. Replay always reports zero
controller packets and reset_authorized=false; it cannot grant a live receipt.

Four operator-supplied registration screenshots were measured as body-colour
references only. Type: Null yellow-excess (R+G)/2-B in sampled head/tail regions
was -4.76/-5.62 for normal versus 32.53/67.82 for shiny. These are descriptive
values from those images, not independent classification accuracy or portable
thresholds. Model motion, rescaling and video/JPEG compression remain uncalibrated.
No body-colour reset path was added. Primary production evidence stays Summary.

The additional 819×617 YouTube Summary screenshot contains a red marker at native
analysis coordinates [47,188,53,194]. This differs from the upstream USUM patch.
The new optional marker-band guard searches [40,176,85,202]: compact red marks
override a normal-colour patch as a shiny candidate; ambiguous red pixels force
unknown. Both prohibit reset. This is enabled in Japanese/diagnostic profiles;
English profiles retain their existing behaviour. Changing profiles invalidates
older validation fingerprints as designed. The supplied red-star screenshot was
detected offline; the earlier native normal Pikachu retained normal with zero
red pixels. Raw reference images/measurements remain private and untracked.

93 unit/loopback tests passed, including both star positions with an otherwise
normal green patch, partial-marker rejection, wrong-name rejection, both target
profiles and the one-member preparation contract. Native loopback GUI checks
passed for Japanese target restrictions / English Poni retention and English
passive recognition on both Chiruno and NTR backends. New one-member fixed
navigation was tested on synthetic screens, not a physical target gift.
Actual two-route receipt timings, native shiny evidence, final completion
bookkeeping and unattended stability are still pending.

The operator confirmed awareness of the special Poni deferral condition and is
preparing the Aether save. No real-console input, reset, connection or save was
performed while preparing these changes. See [PRODUCTION_PREP_JA.md](PRODUCTION_PREP_JA.md).

## Latest physical result: Summary-normal reset and saved-location return

The operator confirmed the complete sequence worked. Private run
`delivery-t6w_6q6x` used four pre-receipt Pokemon, summary-stop=false, 22 presses /
66 datagrams and exactly one reset. Summary pairs at 87.347, 87.936 and 88.525
seconds were normal; the final new-pair check was also normal at 89.098 seconds.
Reset completed at 89.254, START at 114.344 and continue A at 119.437 seconds.
The final received upper image was reviewed and shows the character back in
front of the same delivery NPC. The operator independently confirmed success.
No game save was performed by the application and no reset was retried.

Stop/cancellation occurred at 131.528 seconds before automatic field matching
and cycle bookkeeping completed: the persisted `completed_cycles` is zero.
The physical return is supported by the received image and operator report;
it is not recorded as a successful automatic completion-counter test. This
distinction is retained instead of editing the original logs/counter.

This completes the current-save basic physical sequence check: native video
and input, reception, received-Pokemon Summary selection, normal consensus,
final normal recheck, one reset and return. It does not validate shiny footage,
three-target Japanese calibration, repeated unattended rounds, disconnect
recovery or long-duration stability. Next preparation is saved pre-receipt
data for Poipole and both Type: Null routes, followed by route-specific fixed
navigation and recognition checks before production. No new device input was
sent while reviewing these records; screenshots and raw logs remain private.

## Latest physical result: Summary reached, normal consensus, zero resets

The operator ran the application with four pre-receipt Pokemon and the default
summary-stop option, then confirmed that it worked. Private capture
`delivery-yq87b3gh` shows the fifth-slot hat Pikachu (Lv21, OT Satoshi) on the
summary screens. The complete fixed navigation used 19 presses / 57 datagrams.
No reset was sent and no complete cycle was counted, as intended for this mode.

Three new pairs (serials 102, 103, 105) classified normal at 50.902, 51.485 and
52.065 seconds. Expected name and the experience/next-level fields were matched.
The star ROI mean was [120.75, 244.140625, 70.078125], normalized normal distance
0.07178 (limit 0.15), shiny distance 1.03098, margin 0.95921 and stddev 10.0592.
The native images were reviewed; shipped coordinates and thresholds were unchanged.
This validates one normal Pikachu observation, not actual shiny accuracy or any
of the three target routes. Raw screenshots/OCR logs remain private.

After the player had intentionally stopped, continued receive-only monitoring
reported `Frozen screen 1` at 65.389 seconds because the summary image was static.
This later monitor stop did not send inputs or invalidate the three earlier
observations. The next full normal-only reset test must begin from the same
saved NPC state with a new passive connection check and explicit in-app approval.
The Summary-inclusive physical reset/restore cycle is still pending.

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

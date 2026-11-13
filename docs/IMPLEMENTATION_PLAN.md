# macOS / Japanese gift hunting implementation plan

## Investigation before implementation (2026-11-13)

Upstream: `u93132/ShinyHunterUSUM`, main, v1.2.0. Scope: Poipole,
Type: Null (Poni and Aether). Preserve English Battle/Lotto/Record source paths.

| Finding | Change |
| --- | --- |
| Only external runtime dependency is Pillow; Tk is supplied separately on macOS | Native arm64 Python 3.12 + python-tk@3.12; venv, documented installation |
| General.py unconditionally imports msvcrt, uses Windows byte locking | Platform-specific msvcrt / fcntl locking with close-to-release semantics |
| Window and popup use ICO; Windows fonts; fixed 290x450 window | Pillow/Tk iconphoto, Tk/system Japanese font, content-driven minimum size |
| Resources relative to cwd; settings in shared temp; captures beside executable | Absolute resource root, per-user macOS application support/pictures; preserve Windows settings migration |
| Worker creates ImageTk objects; stream assembler shares indices across screens | Display frames on Tk main thread; independently assemble each screen and validate JPEG sizes |
| NTR TCP :8000 and Luma UDP :4950 are portable sockets, not Windows APIs | Test packet formats, source filtering, local bind address/port, timeouts, partial/malformed frames |
| InputRedirection ignores supplied port | Respect and validate port; local loopback packet tests |
| Recv integer errors fall through to restart; startup resets before recognition | No startup reset for gifts; error stops; only a fresh, multi-frame NORMAL verdict can authorize one reset |
| English text crops and colour patches are embedded in Recv.py | Language/target JSON profiles, named stages, localized templates; Japanese placeholders fail closed |
| One-sided shiny distance treats arbitrary colours as normal | Two-reference classification with distance/margin/variance checks; unknown always stops |
| No language tests or physical Japanese fixtures | Synthetic/loopback regression tests explicitly labelled; collection/replay tools and hardware checklist |

## Implementation order

1. Fork upstream; record base commit. Add native platform helpers and persistent paths.
2. Extract portable NTR assembly/transport and frame freshness tracking; test locally.
3. Add language profiles, Japanese asset manifest, capture/replay tooling and adjustable ROIs/thresholds.
4. Add safe gift runner invoked from Recv.py, default passive dry-run, explicit live/calibration gate,
   no initial reset, fresh-frame consensus, detailed PNG/JSONL evidence, safe release on failure.
5. Add GUI controls without replacing Tkinter; preserve legacy English targets and Record.
6. Run unit/regression tests, import/compile checks and native Tk smoke test where available.
   Publish branch to fork, document exact results and remaining hardware validation.

## Acceptance limits

No 3DS is attached in this environment. Synthetic images do not validate Japanese recognition.
Japanese placeholders and unvalidated calibration must block live operation. A responsive TCP
socket is not proof of a healthy game or successful InputRedirection. Never label hardware,
shiny detection accuracy, or Japanese automation as verified without recorded real evidence.

## Implementation result

Implemented on branch `macos-japanese-gifts`, based on
`f49910affd7ed35b38af8e2b5b35499dcc554f0d`. Native platform helpers, shared
transport, safe gift runner, language/target profiles, placeholder manifests,
passive capture/crop/replay/attestation CLI, GUI settings, tests and Japanese
documentation are included. See [VALIDATION.md](VALIDATION.md) for observed
checks and remaining physical-console work. No Japanese hardware validation
receipt or genuine Japanese screenshot is included.

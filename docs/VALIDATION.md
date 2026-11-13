# Validation record — 2026-11-13

Base: `u93132/ShinyHunterUSUM@f49910affd7ed35b38af8e2b5b35499dcc554f0d`.
Branch: `macos-japanese-gifts` on `senuhi/ShinyHunterUSUM`.

## Environment

- macOS 27.0.1, native arm64 (Apple Silicon), no Rosetta or Wine.
- Homebrew Python 3.12.16, Tcl/Tk 9.1.0, Pillow 13.0.0.
- GUI checks ran in the native WindowServer session, with temporary settings/capture directories.
- Test networking used IPv4 loopback only. No physical 3DS was attached.

## Observed passing checks

| Check | Result and scope |
| --- | --- |
| `python -m unittest discover -s tests -v` | 26 tests passed |
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

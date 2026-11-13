# Old 3DS LL / HIMEM priority plan (2026-11-13)

Target environment supplied by operator: Old 3DS LL, Luma3DS v13.4,
ChirunoMod v0.2.2, ChLoad_HIMEM, 2.4 GHz LAN, Apple Silicon Mac,
Japanese USUM gifts (Poipole / Type: Null Poni / Type: Null Aether).

## Findings before changes

- NTR-HR is not an Old 3DS backend. Its TCP control + UDP JPEG receiver cannot decode ChirunoMod.
- ChirunoMod v0.2.2 uses TCP port 6464 and an 8-byte header (4 type/subtype bytes,
  uint32 little-endian payload length), then image/settings/init/disconnect messages.
- Old 3DS sends eight fractions of each screen, alternating screens. Screen flags are
  reversed relative to this app's internal numbering. JPEG requires red/blue correction.
- Chokistream displays partial images; that behavior is unsuitable for reset decisions.
  This app must publish only a complete, ordered eight-fraction pass and reject interlace,
  unsupported encodings and malformed/slow assemblies.
- HIMEM support and Luma's separate UDP 4950 listener are established separately in source.
  This does not prove their simultaneous operation in USUM on Luma 13.4. UDP sends have no
  acknowledgement, so a successful send cannot prove that input reached the game.
- Old 3DS partial captures lack a shared device frame ID/timestamp. A reconstructed pass
  is a bounded-time collection, not a simultaneous snapshot of the game.

## Priority implementation

1. Separate frame source interface from recognition/controller: NTR and ChirunoMod adapters.
2. Implement independent TCP framing/JPEG decoder for the pinned v0.2.2 protocol; request
   progressive JPEG and both screens. Bound payload, read and assembly times. No reconnect.
3. Build passive / single safe-button coexistence diagnostics, saving original full-screen
   images, freshness/assembly measurements and operator evidence. Never send reset, HOME,
   POWER, START or SELECT from diagnostics. Do not infer success from an open UDP socket.
4. Add backend and input-port settings to GUI / Record / capture CLI. Preserve NTR regression.
5. Require explicit Old-3DS-HIMEM coexistence evidence before live gift control, in addition
   to language/colour calibration. Bind evidence to console/backend and configuration.
6. Strengthen pre-reset checks: bounded assembly age/span, fresh complete passes,
   current target anchor, normal consensus and final recheck. Stop on any uncertainty.
7. Run protocol/loopback/fault tests and native GUI smoke. Actual device testing depends
   on operator's IP and ready game/stream state; never describe simulated tests as hardware verification.

## Primary sources

- [ChirunoMod v0.2.2 server](https://github.com/ChainSwordCS/ChirunoMod/blob/v0.2.2/soos/main.cpp)
- [ChirunoMod loader/release guidance](https://github.com/ChainSwordCS/ChirunoMod/releases/tag/v0.2.2)
- [Chokistream client](https://github.com/Eiim/Chokistream/blob/main/src/main/java/chokistream/ChirunoModClient.java)
- [Chokistream rotation/colour correction](https://github.com/Eiim/Chokistream/blob/main/src/main/java/chokistream/ImageManipulator.java)
- [Luma3DS v13.4 InputRedirection](https://github.com/LumaTeam/Luma3DS/blob/v13.4/sysmodules/rosalina/source/input_redirection.c)

No upstream C or Java source is copied into the Python adapter. It implements the observed
wire format independently. No hardware coexistence result is asserted by this research.

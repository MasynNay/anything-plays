# 3.2 stable upgrade — private full-native QA passed, no public release

The private `AP_V32_STABLE_CANDIDATE=1` channel compiles Anything Plays
3.2 with the **same installed package and settings identity as public
3.1.1**. It is completely separate from the side-by-side 3.2 Preview.

[The native CI workflow](../.github/workflows/v32-stable-upgrade-source-qa.yml)
now executes two stages on **Linux x64, Windows x64, Intel Mac and Apple
Silicon**. First it builds a one-core mGBA source package, checks the actual
extracted DEB/Inno/DMG and immutable embedded identity. Then it assembles
all **11 original native core families** using the checksum-verified public
3.1.1 native payload and notices, inspects the resulting full-native
stable-identity package, and launches the **actual frozen application** against
synthetic old 3.1.1 GBA control layouts, ROM-directory preferences, keyboard
settings and a byte-exact fake save file.

**All four source/full-native staging and synthetic-data checks passed**
in [run 43734522415](https://github.com/MasynNay/anything-plays/actions/runs/43734522415)
at source `9ce5ec322a202fc111aaa2036794ee6a129e0c10`.

**All four installed old-then-new upgrade rehearsals also passed**
in [run 43735551340](https://github.com/MasynNay/anything-plays/actions/runs/43735551340)
at exact source `0da314541e2c6e9f739ca2add2e8001bbfb8a9d0`.
Linux installed the original 3.1.1 and 3.2 full-core DEBs into the
**same isolated dpkg root/database**, Windows installed both original and
new Inno setups to the **same disposable application folder**, and both
Mac architectures replaced the old 3.1.1 app bundle with the new 3.2
bundle under a temporary Applications path. Every platform verified its
old/new embedded identity, changed binary and synthetic prior settings
and fake save-file preservation. Source/regression checks passed in
[run 43735551615](https://github.com/MasynNay/anything-plays/actions/runs/43735551615).

The private workflow uploads **only SHA, native-core and preservation QA
receipts**, never these same-identity installers. A one-core package would
otherwise replace a user's full 3.1.1 release, and even the privately
assembled full-native packages lack public-source/rights and hardware
approval. No actual user's data, emulator game, or physical camera is read
or tested in CI.

Before publication, verify **real native game-save continuity**, ROM
library metadata, USB/Bluetooth controller and camera capture after an
upgrade using owner-selected legal games and physical hardware; independently
review complete source/redistribution obligations, final package checksums
and release authorization. The CI upgrades use fake GBA data, not a real
retail game or the owner's actual saves. The combined upgrade-and-save
gate therefore remains **false** in the strict release authorization record.

**Do not install or publish these upgrade candidates.** The separately
installed, full-native 3.2 Preview is still the testable private
application; public stable 3.1.1 remains unchanged.

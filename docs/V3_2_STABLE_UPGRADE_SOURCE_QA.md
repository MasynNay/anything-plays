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

**All four platforms passed** in
[run 43734522415](https://github.com/MasynNay/anything-plays/actions/runs/43734522415)
at exact source SHA `9ce5ec322a202fc111aaa2036794ee6a129e0c10`.
Python source/regression checks also passed in
[run 43734522492](https://github.com/MasynNay/anything-plays/actions/runs/43734522492).

The private workflow uploads **only SHA, native-core and preservation QA
receipts**, never these same-identity installers. A one-core package would
otherwise replace a user's full 3.1.1 release, and even the privately
assembled full-native packages lack public-source/rights and hardware
approval. No actual user's data, emulator game, or physical camera is read
or tested in CI.

Before publication, retain and validate a real 3.1.1 → 3.2.0 installation
upgrade on disposable native OS systems with old settings, ROM libraries,
and real native save progress; independently review complete source and
redistribution obligations, final package checksums, and owner hardware
QA. These items remain false in the strict release authorization gate.

**Do not install or publish these upgrade candidates.** The separately
installed, full-native 3.2 Preview is still the testable private
application; public stable 3.1.1 remains unchanged.

# 3.2 stable upgrade — private source-stage proof only

The private `AP_V32_STABLE_CANDIDATE=1` channel compiles the new 3.2
code with the **same installed identity** as public 3.1.1. It is
intentionally named a *source-stage* candidate because it bundles only
mGBA; it is NOT a tested full-native or user-safe stable upgrade.

The nonpublishing workflow
[`v32-stable-upgrade-source-qa.yml`](../.github/workflows/v32-stable-upgrade-source-qa.yml)
builds the candidates on native Linux/Windows/Intel Mac/Apple Silicon hosts
and checks the actual extracted DEB/Inno/DMG artifacts. It verifies immutable
3.2 build identity, the stable 3.1.x package/bundle identity, exact current
source SHA, and precisely one native mGBA core. Source and installed receipts
are retained; **upgrade installer binaries are never uploaded** to avoid
accidentally distributing a one-core package that can overwrite 3.1.1.

No real user preferences or save files are read or modified. Full native
core integration and actual upgrade/migration/relaunch tests inside isolated
runner homes, release-specific native source and rights verification,
physical webcam/controller QA, and owner approval remain required.

Do not install or publish this intermediate candidate. Continue using
public v3.1.1 or the isolated, full-native 3.2 private QA installers for
manual preview testing.

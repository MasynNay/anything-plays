# Anything Plays — portfolio landing page

**Website:** https://anythingplays.masynnay.com/

The `site/` folder is a complete, static HTML/CSS/JavaScript portfolio showcase. The page is intentionally separate from the Python desktop application and never claims to run native Libretro emulators in the browser.

## Deployment

- GitHub Pages source: **GitHub Actions** (Settings → Pages).
- Domain: `anythingplays.masynnay.com` (already verified by its owner).
- On a push to `main` that changes `site/**`, `.github/workflows/pages.yml` or `README.md`, the workflow validates and publishes the `site/` folder.
- Build system: **none**. No npm, third-party CDN or credentials are required.
- `CNAME` and `.nojekyll` are included. Keep the custom domain configured under GitHub Pages, and enable HTTPS when the certificate is available.
- The original fish logo is a Git-object-exact copy of `assets/anything_plays_v21.webp` from the 3.0 development branch; the site must **not regenerate or redraw** the fish.
- The interactive control grid is a clearly labeled **illustrative concept**, not a playable browser ROM or a screenshot of the app.
- **Public 3.1 RC1 prerelease:** [Anything Plays 3.1 RC1](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1) is now downloadable on Windows x64, Linux x64, Apple Silicon and Intel Mac. This is a public *test* build featuring optional controller support, not final 3.1.0; physical gamepad QA and native source/relinking review remain open.
- **Stable release:** [Anything Plays 3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0) is public on Windows, Linux, Apple Silicon and Intel Mac, with all 18 console profiles. The [11 pinned original emulator source archives](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources) and exact SHA256 checksums are available separately. Stable 2.0 remains available under previous releases.

To add this project to the main `masynnay.com` portfolio, add a project tile linking to **https://anythingplays.masynnay.com/** with the caption: **Anything Plays — a cross-platform camera-controlled gaming studio built with Python, OpenCV, Tkinter, Libretro and GitHub Actions**. This portfolio repository does **not** modify the separate main personal website.

## Troubleshooting

1. Go to GitHub → Actions → **Publish Anything Plays portfolio** and verify the latest run succeeded.
2. In Settings → Pages, confirm deployment source is **GitHub Actions**, custom domain is `anythingplays.masynnay.com`, and DNS is verified.
3. Check that `site/CNAME` matches the domain exactly.
4. Use the custom domain only after Pages deployment has finished. The successful DNS check alone does not publish the website.

The desktop app's source, runtime, installation and release workflows are unchanged by portfolio deployment.

## Screenshot provenance

`assets/anything-plays-desktop-preview.webp` is a real capture of the **packaged 3.0 Linux development UI** running in a clean virtual X11 display, cropped to the Tk app window. The README also displays two reproducible, attribution-labeled detail crops generated from this same image with `tools/prepare_readme_screenshots.py`, not additional simulated gameplay sessions. No commercial ROM, personal webcam data or synthetic game footage appears in it. It is a UI reference, not a compatibility guarantee for 3.0.

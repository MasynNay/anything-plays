# Anything Plays 3.0 — copyright holder clarification requests (NOT SENT)

These are ready-to-send **draft requests** for the noncommercial components of an educational/career-portfolio project. **No permission has been requested or received by this document.** Do not represent these as grants, publicly post private contact data, or assume one repository maintainer owns every copyright in an upstream library.

## Which rights are being requested?

- **Current application:** Anything Plays, original code under MIT, Python desktop program with in-process Libretro API callbacks, 18 profiles, 11 native core libraries, one offline Windows/macOS/Linux installer; no included games/ROMs/BIOS. Portfolio exists to demonstrate development skills to prospective employers. It has no price or revenue to the project.
- **Snes9x:** exact current native Libretro build of `snes9x`, SNES profile. [Upstream license](https://github.com/snes9xgit/snes9x/blob/master/LICENSE) explicitly permits some noncommercial distributions but separately says personal use and includes promotional commercial-product examples.
- **Genesis Plus GX:** exact current native Libretro `genesis_plus_gx` build; Genesis, Master System, Game Gear, SG-1000. [Upstream license](https://github.com/libretro/Genesis-Plus-GX/blob/master/LICENSE.txt) prohibits sale or commercial products/activities and requires notices, plus complete source if modified.
- A third-party GPL reviewer must separately determine whether **the combined in-process installer** complies with GPL requirements. Even an affirmative Snes9x/Genesis Plus GX reply would **not** license unrelated GPLv2-only/GPLv3-only code or constitute an overall legal signoff.

## Draft 1: Snes9x copyright holders or authorized contact

**Subject:** Clarification of Snes9x noncommercial permission for free developer portfolio application

Hello Snes9x team,

I'm developing an open-source desktop project called Anything Plays, a camera-controlled game interface using Libretro emulator cores. The project is a free educational/technical demonstration in my personal developer portfolio, which may be reviewed by potential employers. I am not selling the application or generating revenue from it.

I would like to provide a free downloadable Windows/macOS/Linux installer containing a Snes9x Libretro core for SNES gameplay. It would contain no ROMs, commercial games, or BIOS files. The core is currently loaded by the application using the Libretro API, alongside other independently licensed libraries. I intend to preserve your full notices and any applicable source access obligations.

I have read the noncommercial permission in your license, including its separate language regarding personal use and commercial promotion. Could you please clarify:

1. Does this specific, entirely free software-engineering portfolio distribution, even when shown to prospective employers, fall within the current license's permitted noncommercial scope?
2. Does your permission extend to distributing this core as one native Libretro component inside the described offline installer, considering other GPL-licensed cores?
3. Are there exact copyright notices, source-delivery or other conditions beyond the original license that you want the release to satisfy?
4. If the current terms do not allow this use, is there any permission or exception available for this exact project and scope? Who is authorized to grant it on behalf of relevant contributors?

I am not requesting commercial sales rights. If a written project-specific clarification is possible, I would preserve it in the release compliance records.

Thank you for maintaining Snes9x.

## Draft 2: Genesis Plus GX copyright holders or authorized contact

**Subject:** Clarification of free portfolio redistribution of Genesis Plus GX Libretro core

Hello Genesis Plus GX maintainers,

I'm preparing a completely free, non-revenue-generating developer portfolio app named Anything Plays. It lets users control locally owned games with optional webcam tracking and keyboard input. My purpose is to demonstrate programming skills to potential employers; I am not selling the software. The proposed offline Windows/macOS/Linux installer would bundle Genesis Plus GX for Sega Genesis/Mega Drive, Master System, Game Gear and SG-1000 support, without including any ROMs, game downloads or BIOS.

I've read the original license restriction on commercial products/activities and its copyright-notice and modified-source requirements. The native library would be invoked through Libretro callbacks in a Python desktop frontend that also bundles GPL-family emulator libraries.

Would you be willing to clarify:

1. Is a free, public, employment-oriented technical portfolio within the permitted **noncommercial** use of your current license?
2. Does the existing license allow redistributing your native Libretro component as part of this described combined offline installer, or is a separate permission required?
3. What exact notices, source files (particularly if modified), links or other distribution steps should accompany the original library?
4. If any additional permission is necessary, is it available for this particular free portfolio distribution and who can grant it on behalf of the relevant copyright holders?

I will not assume a reply from a single maintainer grants rights over code contributed by other authors. Any clarification would be preserved with the release compliance record.

Thank you for maintaining Genesis Plus GX.

## How to submit, without guessing contact addresses

Use official project channels only as an initial **contact to find authorized rights holders**, such as [Snes9x's upstream repository](https://github.com/snes9xgit/snes9x) or [Libretro Genesis Plus GX](https://github.com/libretro/Genesis-Plus-GX), and follow their preferred contact policy. Do not assume a GitHub issue tracker is appropriate for license negotiations, or that contributors' addresses listed in copied historical licenses are currently monitored. If you find an expressly advertised licensing contact, send this message using that channel. **No outgoing messages are made automatically by Anything Plays or ChatGPT.**

## Private response record

Retain the date, exact Snes9x or Genesis Plus GX library/version, authorized respondent's public organizational role, response permalink/email, rights scope, any limitations, obligations and outstanding questions in a secure private record. A summarized, non-sensitive rights determination may later be included in the approved 3.0 release record, **only after the owner's permission to quote or share correspondence is considered**. Do not mark binary distribution or combined GPL compatibility approved because an unanswered request was sent.

For the independent GPL/combination question, provide the reviewer with [current license audit](V3_PORTFOLIO_LICENSE_CLEARANCE.md), [existing GPL compatibility gate](V3_LICENSE_COMPATIBILITY_GATE.md), [technical 2D subprocess research](V3_ISOLATED_CORE_RESEARCH.md), [source review schema](V3_CORRESPONDING_SOURCE_REVIEW_SCHEMA.md), and actual pinned four-platform source/binary manifests. Ask for a documented decision about the **actual current in-process core arrangement**, not only whether noncommercial use is sympathetic.

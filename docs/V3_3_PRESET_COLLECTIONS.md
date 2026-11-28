# Control preset collections

Development source feature; not yet included in the public 3.3.0 installers.

Open **Safety & Profiles → Control preset library → Preset exchange**.

## Share your layouts

1. Choose **Local presets** to browse the saved layouts for all consoles.
2. Select one or more layouts using the usual list multi-selection keys.
3. Review the console and collection label. By default, labels are generic (Layout 1, Layout 2, etc.) instead of your private local names. Choose **Rename collection label** to give an individual entry a descriptive share label.
4. Choose **Export selected**, review the confirmation, and save the JSON file. Share that file yourself.

A collection includes the explicitly chosen share labels, console identities, control-zone positions, mappings, tracking colors and other portable control settings, plus an optional theme. It excludes ROMs, save games, local paths, device identities, credentials and zone artwork. Do not put personal information in a share label.

## Receive a collection

1. Choose **Open collection** and select the JSON file.
2. Review the console identities and control summary. Select only layouts you want to keep.
3. Choose **Import selected**. This saves the layouts to your local library without activating them.
4. Close the exchange window, select the console you want, and apply an imported layout through the normal preset preview and confirmation. Undo import restores the previous controls.

Identical saved layouts are skipped. A conflicting label or full console library cancels the entire selected import. Rename the incoming collection label or select fewer entries and retry. Existing layouts are not overwritten.

## Limits and compatibility

- Up to 48 layouts per collection, 512 KiB per file, and 12 named layouts per console.
- Version 1 collection format wraps the existing version 1 portable control-profile format.
- No network, account, cloud sync or public catalog is required. Individual profile import/export and all-console backups are separate, existing features.
- Collection files are validated before storage. Malformed files and unknown fields are rejected. Writes use the existing atomic JSON replacement helper.

The software does not certify shared layouts as appropriate for a specific game or accessibility need. Review mappings and recalibrate your own camera and target colors if needed. Object controls remain paused after applying a layout until you explicitly enable them.

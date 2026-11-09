# Anything Plays 3.0 — Sound and Multi-Fish Camera Controls

These are new **3.0 preview** features. Stable Anything Plays 2.0 is unchanged.

## In-emulator volume and mute

- Above the game display, use **Game volume** to choose 0–100%.
- Use **Mute / Unmute**, or **Ctrl + Shift + M**, to silence or restore the
  previous listening level without touching your operating system's volume.
- The same compact controls remain accessible in **Game only** mode.
- Fresh 3.0 preferences start at a comfortable **35% game volume**. Volume is
  shared across all embedded Libretro consoles and remembered on disk.
- No audio device? Gameplay continues. A missing output-device warning is
  shown rather than interrupting the game.

## One color, one fish (default)

1. Select your camera and use **Pick color from video** to choose the color
   you want to track (for example, a bright pink fish).
2. Leave **Enable multiple fish per color (multi-input)** unchecked.
3. Only the **largest** matching shape of each enabled color is selected for
   game controls, consistent with earlier versions.

This opt-in setting is **OFF by default**, including for old profiles that
have never saved the setting. It is saved independently for each console.

## One color, many fish pressing several buttons at once (opt-in)

1. Check **Enable multiple fish per color (multi-input)**.
2. Multiple disconnected same-colored contours are detected (up to 16 per
   enabled color), sorted by visible area.
3. Every matching fish in a different active camera zone contributes its
   mapped game button to the *same emulated frame*. Two pink fish in Left
   and A zones can press **Left + A** together. Three fish in three zones
   can hold three inputs at once.
4. Select **Held while visible** for natural continuous tank controls. It
   stops holding a button after the fish is no longer in the zone. Or choose
   **Pulse (classic)** for finite button taps and the existing cooldown
   controls.

The user-visible **multi-input checkbox is never enabled automatically**.

## Optional Color 2 and local Player 2

1. Check **Enable Color 2**. Use **Pick Color 2 from video** or **Choose Color 2**
   to select a second distinct hue.
2. The two camera trackers work simultaneously. **Color 1 always controls
   Player 1.** Color 2 can control **Player 1** for more combined buttons, or
   **Player 2** for local multiplayer.
3. The on-screen mapping zones define the buttons for each color. Different
   colors in different zones can press inputs simultaneously.
4. Player 2 only functions on systems and games that actually expose two
   controller ports. It is intended for local couch multiplayer, **not online
   multiplayer/netplay**. Some games allow a second controller only after
   selecting their multiplayer mode.
5. For a single-controller console, change Color 2 to **Player 1**. The UI
   warns you rather than pretending an unavailable Player 2 input works.

## Safety, accuracy and long-term stability

- **STOP ALL OBJECT CONTROLS** immediately clears Color 1 and Color 2 input
  holds and queued pulses while leaving manual keyboard play available.
- The camera's native pixels are analyzed separately from the bright
  green/pink outlines. No simulated inputs are sent through the OS keyboard.
- Detection is bounded to 16 individual objects per enabled color, and
  held controller states are rewritten as snapshots, not stored as an
  ever-growing queue. Two independently configured colors may each detect
  up to 16 shapes when multi-input is enabled.
- Similar-looking colors, bright reflections or overlapping fish can confuse
  HSV-based tracking. Choose distinct colors, keep the camera stable, and
  raise minimum detection area to ignore tiny highlights.
- The optional external emulator/developer bridge supports only Player 1.
  Normal built-in N64/GameCube controllers support both ports through
  Libretro, subject to the actual game and native core.
- Profiles store the multi-input checkbox, optional Color 2, player routing,
  and hold/pulse selection per console. Global game audio volume is stored
  separately.

## What still requires physical testing

A successful GUI regression or native Libretro test does not prove every
commercial two-player game handles two controllers, nor that the selected
camera can reliably separate fish under every aquarium's lighting. Verify
local Player 2 with a game that is known to support two controllers, verify
audio with your actual speakers, and test the emergency stop while both
colors are visible. These features ship first in a clearly labeled 3.0
developer preview; stable release approval remains separate.

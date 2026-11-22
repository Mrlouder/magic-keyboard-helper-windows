# Changelog

## 3.3 (2026-11)

First public release.

- **Download and run:** the release zip includes the AutoHotkey v2 runtime, no AutoHotkey install needed. Unzip, double-click `MagicKeyboardHelper.bat`, apply the Fn / Lock patch from the notification.
- **Laptop screen brightness:** Fn + F1 / F2 now also changes the built-in screen of laptops and tablets (WMI), next to DDC/CI external monitors.
- **Key remaps work with every keyboard layout:** remaps are stored by physical key (scan code). Settings from older versions are converted automatically.
- **Apple ISO key fix** button (Settings > Key remaps) for UK, German, Hungarian etc. keyboards, where Windows swaps the key left of 1 and the key next to the left Shift. No remaps are added by default.
- Fn + F6 defaults to Notifications / Do not disturb, like the key print. "Switch audio output" (SoundSwitch) is still available.
- The Fn / Lock patch only saves a backup of the original, unpatched descriptor.
- `MagicKeyboardHelper.bat` also finds an installed AutoHotkey v2.

## 3.2 (2026-10)

- Start with Windows through a Task Scheduler task (sign-in trigger, no administrator rights).

## 3.0 - 3.1 (2026-10)

- Fn and Lock keys without a driver (Bluetooth HID descriptor patch), Fn lock, Fn + F-key actions, globe shortcuts, Lock key hold actions, Mac-style OSD, battery level and reminders, key remaps, Settings window.

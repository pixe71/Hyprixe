# Pre-refactor Debian contract

Captured **before source relocation** from commit
`0315699206f0450fdc79d92c0b622502abf17c95` on `main`. These fixtures contain test
metadata, not alternative desktop configurations or personal user backups.

- `debian-v1-payload.json`: 16 payloads (native/VMware × default/custom XDG ×
  full/Waybar/Dolphin/runtime), destination-relative SHA-256 and modes, plus
  eight SDDM visual/wallpaper source hashes. Only the temporary HOME string in
  UTF-8 payloads is normalized to `@HOME@`; binary assets are hashed verbatim.
  Runtime staging uses four minimal test executables with fixed contents.
- `debian-v1-backup.json`: a real format-1 transaction made by the old backend,
  with three synthetic original files and original 0600/0640/0664 modes.
  Temporary HOME paths become `@HOME@`. The test rebases HOME-dependent installed
  hashes, uses the existing restore implementation and checks original bytes,
  modes, created-file removal and unrelated-file preservation.

`test_core_profiles.py` consumes these fixtures. Do not regenerate them from
the refactored backend: that would discard independent equivalence evidence.
Future intentional desktop changes require an explicitly reviewed contract
update rather than silently updating hashes to make a test pass.

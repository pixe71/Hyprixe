# Installation

Target: Debian 13 Trixie. Run as your desktop user and close Dolphin first.

```bash
git clone https://github.com/pixe71/hyprixe-debian.git
cd hyprixe-debian
./install.sh native
```

Save your work and reboot. Select **Hyprland (uwsm-managed)** in SDDM.
Inside that session, run:

```bash
./verify.sh --dependencies --session
```

See the [full installation guide](https://github.com/pixe71/hyprixe-debian/blob/main/docs/installation.md) for prerequisites and details.

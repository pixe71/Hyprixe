"""Launch the real GTK popup against a fixture backlight and logind double."""

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import os
from pathlib import Path
import sys

loader = SourceFileLoader("brightness_fixture", sys.argv[1])
spec = spec_from_loader(loader.name, loader)
popup = module_from_spec(spec)
sys.modules[spec.name] = popup
loader.exec_module(popup)

runtime = Path(os.environ["XDG_RUNTIME_DIR"])
root = runtime / "hyprixe-backlight-test"
device = root / "panel"
device.mkdir(parents=True, exist_ok=True)
(device / "max_brightness").write_text("255\n")
brightness = device / "brightness"
if not brightness.exists():
    brightness.write_text("171\n")
select_backlight = popup.select_backlight
popup.select_backlight = lambda: select_backlight(root)


class SimulatedLogind:
    def __init__(self, connection, gio, glib):
        self.glib = glib

    def set_brightness(self, name, value, done):
        assert name == "panel"
        assert 13 <= value <= 255
        brightness.write_text(f"{value}\n")

        def finish():
            done(None)
            return False

        self.glib.idle_add(finish)


popup.Logind = SimulatedLogind
raise SystemExit(popup.main(["--toggle"]))

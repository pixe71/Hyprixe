{
  pkgs,
  host,
  username,
  homeDirectory,
  configDirectory,
  rofi,
  gtkPython,
  peer ? "hyprixe-second",
}:

let
  inherit (pkgs) lib;
  # A disposable PAM credential derived from the fixture name, with keys
  # that have the same position on the compositor's AZERTY and on QWERTY.
  passwordKeys = builtins.replaceStrings
    [ "0" "1" "2" "3" "4" "5" "6" "7" "8" "9" "a" "b" "c" "d" "e" "f" ]
    [ "e" "r" "t" "y" "u" "i" "o" "p" "s" "d" "f" "g" "h" "j" "k" "l" ]
    (builtins.substring 0 10 (builtins.hashString "sha256" "${username}-session-test"));
  rogue = "hyprixe-socket-test";
  sddm = import ../packages/sddm.nix { inherit pkgs; };
  wallpapers = pkgs.runCommand "hyprixe-vm-wallpaper-fixtures" {
    nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pillow ])) ];
  } ''
    python3 ${../../../tests/fixtures/wallpapers/generate.py} "$out"
  '';
  desktop = {
    programs.hyprixe.enable = true;
    programs.hyprixe.sddm.enable = true;
    home-manager.users.${username}.programs.hyprixe.enable = true;
    home-manager.users.${peer}.programs.hyprixe.enable = true;
  };
in
{
  name = "hyprixe-uwsm-session";
  extraPythonPackages = ps: [ ps.pillow ];

  nodes.machine = { pkgs, lib, ... }: {
    imports = [ host ];
    # The VM recreates its writable Nix store overlay at boot. Keep the user's
    # package environment in the system closure across both boot cycles.
    home-manager.useUserPackages = true;
    virtualisation.graphics = true;
    virtualisation.cores = 4;
    virtualisation.memorySize = 3072;
    hardware.graphics.enable = true;
    environment.sessionVariables.LIBGL_ALWAYS_SOFTWARE = "1";
    environment.systemPackages = [
      pkgs.jq pkgs.fontconfig pkgs.polkit pkgs.xdg-utils rofi sddm.client
      (pkgs.writeShellScriptBin "probe-brightness" ''
        exec ${lib.getExe gtkPython} ${./brightness-session.py} \
          ${../../../common/local/bin/hyprixe-brightness-popup}
      '')
    ];
    environment.etc."hyprixe-test/photo-a.jpg".source = "${wallpapers}/photo-a.jpg";
    environment.etc."hyprixe-test/photo-b.png".source = "${wallpapers}/photo-b.png";
    users.users.${username} = {
      uid = 1000;
      linger = true;
      hashedPasswordFile = toString (pkgs.runCommand "hyprixe-vm-test-password-hash" { } ''
        printf '%s\n' ${lib.escapeShellArg passwordKeys} |
          ${lib.getExe pkgs.openssl} passwd -6 -salt hyprixe-vm -stdin > "$out"
      '');
    };
    security.polkit.adminIdentities = lib.mkForce [ "unix-user:${username}" ];
    users.users.${peer}.isNormalUser = true;
    users.users.${rogue}.isNormalUser = true;
    home-manager.users.${username}.home.file.".pre-hyprixe".text = "Existing Home Manager file\n";
    specialisation.hyprixe-installed.configuration = {
      imports = [ desktop ];
      programs.hyprixe.sddm.sync = {
        enable = true;
        users = [ username peer ];
      };
      # Fixture-only membership separates the protocol's UID check from DAC.
      users.users.${rogue}.extraGroups = [ "hyprixe-sddm-sync" ];
    };
    specialisation.sddm-static.configuration = desktop;

    # The original host runs stock SDDM and already owns its UWSM session.
    programs.hyprland.enable = true;
    programs.hyprland.withUWSM = true;
    services.xserver.enable = true;
    services.displayManager = {
      sddm.enable = true;
      defaultSession = "hyprland-uwsm";
      hiddenUsers = [ peer rogue ];
    };
  };

  testScript = (builtins.readFile ../../../common/theme/hyprland_errors.py) + ''
    from pathlib import Path
    from shlex import quote
    from time import sleep
    from PIL import Image, ImageChops, ImageOps

    def user(command):
        return (
            "runuser -u ${username} -- env XDG_RUNTIME_DIR=/run/user/1000 "
            "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus " + command
        )

    def session_command(command):
        return user("systemd-run --user --quiet --wait --pipe --collect /bin/sh -ec " + quote(command))

    def in_session(command):
        return machine.succeed(session_command(command))

    def start_in_session(command):
        machine.succeed(user("systemd-run --user --quiet --collect /bin/sh -ec " + quote(command)))

    def wait_session(command):
        machine.wait_until_succeeds(session_command(command), timeout=65)

    def layer(namespace, count=1):
        return "hyprctl layers -j | jq -e " + quote(
            f'[.. | objects | select(.namespace? == "{namespace}")] | length == {count}'
        )

    def dispatch(expression):
        assert in_session("hyprctl dispatch " + quote(expression)).strip() == "ok"

    def click(x, y):
        dispatch(f"hl.dsp.cursor.move({{ x = {x}, y = {y} }})")
        machine.send_monitor_command("mouse_button 1")
        sleep(0.15)
        machine.send_monitor_command("mouse_button 0")

    def workspace(number):
        wait_session(f"hyprctl activeworkspace -j | jq -e '.id == {number}'")

    def active_window(address):
        wait_session("hyprctl activewindow -j | jq -e " + quote(f'.address == "{address}"'))

    def open_launcher():
        machine.send_key("meta_l-spc")
        wait_session(layer("rofi"))
        sleep(2)

    def screenshot(name):
        machine.screenshot(name)
        with Image.open(Path(machine.out_dir) / (name + ".png")) as image:
            return image.convert("RGB")

    def desktop_ready(wallpaper="min_forest.jpg"):
        for unit in desktop_units:
            machine.wait_until_succeeds(user(f"systemctl --user is-active {unit}"), timeout=90)
        wait_session("awww query | grep -F " + quote(wallpaper))
        wait_session(layer("waybar"))
        pid = machine.succeed(user("systemctl --user show -P MainPID hyprixe-awww.service")).strip()
        assert machine.succeed(daemon_pid).strip() == pid

    desktop_units = [
        "hyprixe-session.target", "hyprixe-awww.service", "hyprixe-wallpaper.service",
        "waybar.service", "hypridle.service", "swaync.service",
        "hyprixe-polkit.service", "hyprixe-clipboard.service",
    ]
    daemon_pid = "pgrep -u 1000 -f '^/nix/store/[^/]+/bin/awww-daemon( |$)'"
    greeter_process = "pgrep -u sddm -f 'sddm-greeter.*--socket'"
    server = "hyprixe-sddm-sync"
    state_dir = "/var/lib/hyprixe/theme"
    current = state_dir + "/current"
    policy = "/etc/hyprixe/sddm-sync-users.json"
    official = "${../../../common/wallpapers/min_forest.jpg}"
    photo_a = "${wallpapers}/photo-a.jpg"
    photo_b = "${wallpapers}/photo-b.png"
    roles = {"background", "surface", "foreground", "accent", "accent_alt", "border", "error"}

    def greeter(label, wallpaper, palette=None):
        machine.wait_until_succeeds(greeter_process, timeout=90)
        colours = palette or {"background": "#122434", "foreground": "#e6f1f4"}
        tint = tuple(bytes.fromhex(colours["background"][1:]))
        foreground = tuple(bytes.fromhex(colours["foreground"][1:]))
        with Image.open(wallpaper) as source:
            for _ in range(12):
                frame = screenshot(label)
                expected = ImageOps.fit(source.convert("RGB"), frame.size, Image.Resampling.BILINEAR)
                # Top strip is clear of the login controls. Account for the
                # gradient tint that overlays the centre-cropped wallpaper.
                y = frame.height // 18
                opacity = 0.0824 + 0.3568 * y / frame.height
                matches = 0
                for i in range(1, 9):
                    point = (i * frame.width // 9, y)
                    pixel = expected.getpixel(point)
                    actual = frame.getpixel(point)
                    assert isinstance(pixel, tuple) and isinstance(actual, tuple)
                    blended = [component * (1 - opacity) + shade * opacity
                               for component, shade in zip(pixel, tint)]
                    if max(abs(a - b) for a, b in zip(actual, blended)) <= 18:
                        matches += 1
                if matches >= 7 and foreground in frame.crop((0, 75, frame.width, frame.height - 50)).getdata():
                    return
                sleep(1)
        raise AssertionError(f"{label}: greeter did not render the expected wallpaper and palette")

    def login():
        machine.wait_until_succeeds(greeter_process, timeout=90)
        sleep(2)
        for key in "${passwordKeys}":
            machine.send_key(key, delay=0.12, log=False)
        machine.send_key("ret")
        machine.wait_until_succeeds(user("systemctl --user is-active hyprixe-session.target"), timeout=90)

    def logged_out():
        for target in desktop_units + ["graphical-session.target"]:
            machine.wait_until_succeeds(user(f"systemctl --user show -P ActiveState {target}") + " | grep -x inactive")
        machine.fail(daemon_pid)
        machine.fail("pgrep -u 1000 -x hypridle")
        machine.wait_until_succeeds(greeter_process, timeout=90)

    start_all()
    def activate(generation):
        machine.succeed(f"{generation}/bin/switch-to-configuration test")
        assert machine.succeed("readlink -f /run/current-system").strip() == generation
        # The fixture keeps a lingering user manager for logout assertions.
        # Renew its supplementary groups after changing socket enrollment.
        machine.succeed("systemctl restart user@1000.service")

    with subtest("install from an external configuration on an existing host"):
        machine.wait_for_unit("display-manager.service")
        base = machine.succeed("readlink -f /run/current-system").strip()
        generation_a = machine.succeed(f"readlink -f {base}/specialisation/hyprixe-installed").strip()
        static = machine.succeed(f"readlink -f {base}/specialisation/sddm-static").strip()
        host_file = "grep -Fqx 'Existing Home Manager file' ${homeDirectory}/.pre-hyprixe"
        machine.succeed(host_file)
        machine.fail(f"test -S /run/{server}.sock")
        machine.fail(f"test -e {current}")
        machine.fail("test -L ${homeDirectory}/${configDirectory}/hypr/hyprland.lua")
        machine.fail("test -x /etc/profiles/per-user/${username}/bin/hyprixe-theme")
        activate(generation_a)
        machine.succeed(host_file, "test -L /home/${peer}/.config/hypr/hyprland.lua")
        machine.wait_for_unit(server + ".socket")
        machine.succeed("systemctl restart display-manager.service")
    machine.fail(f"systemctl is-active {server}.service")
    assert machine.succeed(f"stat -c '%a %U %G' /run/{server}.sock").strip() == "660 root hyprixe-sddm-sync"
    machine.succeed(f"test -f {policy} && test ! -L {policy} && test \"$(stat -c '%a %u' {policy})\" = '444 0'")
    greeter("sddm-first-boot", official)
    login()

    def snapshot(wallpaper, palette):
        published = json.loads(machine.succeed(f"cat {current}/palette.json"))
        assert published == {role: palette[role] for role in roles}
        digest = machine.succeed("sha256sum /etc/hyprixe-test/" + wallpaper).split()[0]
        assert json.loads(machine.succeed(f"cat {current}/manifest.json"))["source_hash"] == digest
        machine.succeed(f"runuser -u sddm -- test -r {current}/wallpaper.png")
        return published

    with subtest("socket activation, isolated receiver and multiple local users"):
        desktop_ready()
        machine.wait_until_succeeds(f"test -s {current}/manifest.json")
        assert machine.succeed(f"stat -c '%a %U' {state_dir}").strip() == "755 hyprixe-theme"
        assert machine.succeed(f"stat -Lc '%a %U' {current}/Palette.qml").strip() == "644 hyprixe-theme"
        machine.fail(user(f"test -w {state_dir}"))
        machine.fail(f"runuser -u sddm -- test -w {state_dir}")
        # Both attempts have the right DAC group. Only one has a UID in the policy.
        machine.succeed(f"runuser -u ${rogue} -- id -Gn | grep -w {server}")
        package = "${lib.getExe sddm.client}"
        machine.succeed(
            "install -d -m755 /run/hyprixe-protocol",
            "install -m600 -o ${username} /etc/hyprixe-test/photo-a.jpg /run/hyprixe-protocol/a.jpg",
            "install -m600 -o ${peer} /etc/hyprixe-test/photo-b.png /run/hyprixe-protocol/b.png",
            "install -m600 -o ${rogue} /etc/hyprixe-test/photo-b.png /run/hyprixe-protocol/rogue.png",
            f"cp {current}/palette.json /run/hyprixe-protocol/palette.json",
        )
        database = "/run/hyprixe-protocol/palette.json"
        rejected = machine.fail(f"runuser -u ${rogue} -- {package} /run/hyprixe-protocol/rogue.png {database} 2>&1")
        assert "not enrolled" in rejected, rejected
        machine.fail(f"runuser -u ${peer} -- {package} /etc/hyprixe-test/photo-a.jpg {database}")
        machine.succeed(f"systemctl stop {server}.service")
        machine.wait_for_unit(server + ".socket")
        machine.succeed(
            f"runuser -u ${username} -- {package} /run/hyprixe-protocol/a.jpg {database} & a=$!; "
            f"runuser -u ${peer} -- {package} /run/hyprixe-protocol/b.png {database} & b=$!; "
            "wait $a; first=$?; wait $b; second=$?; test $first = 0 && test $second = 0"
        )
        peer_uid = int(machine.succeed("id -u ${peer}").strip())
        current_uid = json.loads(machine.succeed(f"cat {current}/manifest.json"))["uid"]
        assert current_uid in {1000, peer_uid}
        history = json.loads(machine.succeed(f"jq -s 'map(.uid)' {state_dir}/generations/*/manifest.json"))
        assert {1000, peer_uid} <= set(history)
        assert machine.succeed(f"find {state_dir}/generations -mindepth 1 -maxdepth 1 -type d | wc -l").strip() == "3"
        machine.wait_for_unit(server + ".service")
        machine.succeed(f"test \"$(ps -o user:32= -p $(systemctl show -P MainPID {server}.service) | xargs)\" = hyprixe-theme")

    with subtest("real SDDM rendering and last valid snapshot"):
        pictures = '"$XDG_DATA_HOME/hyprixe/personal"'
        live_palette = '"$XDG_CACHE_HOME/hyprixe/theme/current/palette.json"'
        for label, filename, image in [("a", "photo-a.jpg", photo_a), ("b", "photo-b.png", photo_b)]:
            in_session(f"install -Dm600 /etc/hyprixe-test/{filename} {pictures}/{filename}")
            in_session(f"hyprixe-theme apply {pictures}/{filename}")
            colours = json.loads(in_session(f"cat {live_palette}"))
            greeter_palette = snapshot(filename, colours)
            if label == "b":
                previous = machine.succeed(f"readlink {current}")
                machine.succeed(f"chmod 0666 {policy}")
                try:
                    result = in_session(f"hyprixe-theme apply {pictures}/photo-a.jpg 2>&1")
                    assert "Missing or invalid system synchronization policy" in result, result
                    wait_session("awww query | grep -F photo-a.jpg")
                    assert not parse_config_errors(in_session("hyprctl configerrors -j"))
                    assert machine.succeed(f"readlink {current}") == previous
                finally:
                    machine.succeed(f"chmod 0444 {policy}")
            machine.succeed(user("uwsm stop"))
            logged_out()
            greeter("sddm-wallpaper-" + label, image, greeter_palette)
            if label == "b":
                machine.wait_until_fails(f"systemctl is-active {server}.service", timeout=45)
                boot = machine.succeed("cat /proc/sys/kernel/random/boot_id")
                machine.shutdown()
                machine.start()
                assert machine.succeed("cat /proc/sys/kernel/random/boot_id") != boot
                assert machine.succeed(f"readlink {current}") == previous
                activate(generation_a)
                machine.wait_for_unit(server + ".socket")
                machine.fail(f"systemctl is-active {server}.service")
                machine.succeed("systemctl restart display-manager.service")
                greeter("sddm-after-reboot", image, greeter_palette)
            login()
            desktop_ready("photo-a.jpg" if label == "b" else filename)
        in_session("hyprixe-theme default")
        official_hash = machine.succeed("sha256sum ${../../../common/wallpapers/min_forest.jpg}").split()[0]
        assert json.loads(machine.succeed(f"cat {current}/manifest.json"))["source_hash"] == official_hash
        greeter_palette = json.loads(machine.succeed(f"cat {current}/palette.json"))
        machine.succeed(user("uwsm stop"))
        logged_out()
        greeter("sddm-return-to-default", official, greeter_palette)
        login()

    machine.succeed(
        "test -L ${homeDirectory}/${configDirectory}/hypr/hyprland.lua",
        user("systemctl --user is-active graphical-session.target"),
        user("uwsm check is-active compositor-only"),
    )
    environment = dict(
        line.split("=", 1) for line in in_session("env").splitlines()
    )
    assert environment["WAYLAND_DISPLAY"]
    assert environment["HYPRLAND_INSTANCE_SIGNATURE"]
    assert environment["XDG_RUNTIME_DIR"] == "/run/user/1000"
    assert environment["XDG_CONFIG_HOME"] == "${homeDirectory}/${configDirectory}"
    assert environment["XDG_DATA_HOME"] == "${homeDirectory}/.data-fixture"
    assert environment["XDG_CACHE_HOME"] == "${homeDirectory}/.cache-fixture"
    assert environment["XDG_STATE_HOME"] == "${homeDirectory}/.state-fixture"
    assert environment["XDG_CURRENT_DESKTOP"] == "Hyprland"
    assert environment["XDG_SESSION_TYPE"] == "wayland"
    assert environment["PATH"]
    assert environment["QT_QPA_PLATFORM"] == "wayland;xcb"
    machine.succeed("grep -Eq '^XDG_SESSION_ID=.+$' /run/user/1000/uwsm/env_session.conf")
    errors = parse_config_errors(in_session("hyprctl configerrors -j"))
    assert not errors, errors
    assert any(bind["description"].startswith("Hyprixe | ") for bind in json.loads(in_session("hyprctl binds -j")))
    workspaces = json.loads(in_session("hyprctl workspaces -j"))
    assert {1, 2, 3, 4} <= {workspace["id"] for workspace in workspaces}, workspaces

    desktop_ready()
    desktop = screenshot("hyprixe-desktop")
    machine.succeed(
        "test -s ${homeDirectory}/.state-fixture/hyprixe/session.log",
        "test -z \"$(ls -A /sys/class/backlight)\"",
    )
    bar_log = machine.succeed(user("journalctl --user -b -u waybar.service --no-pager"))
    assert "Using CSS file ${homeDirectory}/${configDirectory}/hypr/waybar/style.css" in bar_log, bar_log
    assert "Using configuration file ${homeDirectory}/${configDirectory}/hypr/waybar/configs/Frosted-Glass-no-backlight" in bar_log, bar_log
    assert "No backlight found" not in bar_log and "Theme parsing error" not in bar_log, bar_log
    for font in ["JetBrains Mono", "Symbols Nerd Font Mono", "FontAwesome"]:
        assert font in in_session(f"fc-match '{font}'"), font

    with subtest("one instance per session and authenticated Polkit"):
        for process in [
            "hypridle", ".swaync-wrapped", "wl-paste",
        ]:
            assert machine.succeed("pgrep -c -u 1000 -x " + quote(process)).strip() == "1"
        agent = r"pgrep -c -u 1000 -f '^/nix/store/[^/]+/libexec/\.?polkit-kde-authentication-agent-1(-wrapped)?( |$)'"
        assert machine.succeed(agent).strip() == "1"
        start_in_session("/run/wrappers/bin/pkexec ${pkgs.coreutils}/bin/true && touch \"$XDG_RUNTIME_DIR/polkit-authenticated\"")
        wait_session("hyprctl clients -j | jq -e '.[] | select(.class | test(\"polkit\"; \"i\"))'")
        machine.screenshot("hyprixe-polkit")
        for key in "${passwordKeys}":
            machine.send_key(key, delay=0.12, log=False)
        machine.send_key("ret")
        wait_session('test -f "$XDG_RUNTIME_DIR/polkit-authenticated"')

    locked = "hyprctl locked -j | jq -e '.locked'"

    def unlock():
        wait_session(locked)
        sleep(1.5)  # Allow the lock surface to take keyboard focus.
        machine.send_key("esc")
        for key in "${passwordKeys}":
            machine.send_key(key, delay=0.12, log=False)
        machine.send_key("ret")
        wait_session("hyprctl locked -j | jq -e '.locked == false'")

    with subtest("PAM lock denies input and invalid credentials"):
        machine.send_key("meta_l-l")
        wait_session(locked)
        sleep(3)
        machine.screenshot("hyprixe-hyprlock-default")
        machine.send_key("meta_l-spc")
        in_session(layer("rofi", 0))
        machine.send_key("x", log=False)
        machine.send_key("ret")
        sleep(3)
        in_session(locked)
        machine.screenshot("hyprixe-hyprlock-refused")
        unlock()

    with subtest("notification delivery and control center"):
        start_in_session("notify-send -t 0 Hyprixe 'VM notification' --action=default=Inspect --wait >\"$XDG_RUNTIME_DIR/notification-action\"")
        wait_session(layer("swaync-notification-window"))
        machine.screenshot("hyprixe-notification")
        notification_box = json.loads(in_session(
            "hyprctl layers -j | jq -c '.. | objects | select(.namespace? == \"swaync-notification-window\")'"
        ))
        click(notification_box["x"] + notification_box["w"] // 2, notification_box["y"] + 35)
        wait_session('grep -Fx default "$XDG_RUNTIME_DIR/notification-action"')
        in_session("notify-send Hyprixe 'VM notification center'")
        in_session("swaync-client -t")
        wait_session(layer("swaync-control-center"))
        machine.screenshot("hyprixe-notification-center")
        in_session("swaync-client -C; swaync-client -t")
        wait_session(layer("swaync-control-center", 0))

    with subtest("Hypridle lock via logind and DPMS at fixture timeouts"):
        runtime = "/run/user/1000"
        dropin = runtime + "/systemd/user/hypridle.service.d/90-fixture.conf"
        in_session('sed -e "s/timeout = 600/timeout = 3/" -e "s/timeout = 720/timeout = 7/" '
                   '"$XDG_CONFIG_HOME/hypr/hypridle.conf" > "$XDG_RUNTIME_DIR/idle-fixture.conf"')
        in_session(f"mkdir -p {quote(str(Path(dropin).parent))}; "
                   "printf '[Service]\nExecStart=\nExecStart=%s -c %s\n' \"$(command -v hypridle)\" "
                   f"{runtime}/idle-fixture.conf > {dropin}; systemctl --user daemon-reload; systemctl --user restart hypridle")
        wait_session(locked)
        wait_session("hyprctl monitors -j | jq -e '.[0].dpmsStatus == false'")
        machine.send_key("esc")
        wait_session("hyprctl monitors -j | jq -e '.[0].dpmsStatus'")
        in_session(f"rm {dropin}; systemctl --user daemon-reload; systemctl --user restart hypridle")
        unlock()

    menu = "logout_dialog"
    with subtest("Wlogout opens, toggles, and protects session actions"):
        click(1254, 20)  # Waybar power button uses the same session helper.
        wait_session(layer(menu))
        sleep(1)
        menu_image = screenshot("hyprixe-wlogout")
        for center in (304, 528, 752, 976):
            icon = menu_image.crop((center - 40, 337, center + 40, 421))
            assert (230, 241, 244) in icon.getdata(), f"Wlogout icon missing at x={center}"
        machine.send_key("esc")
        wait_session(layer(menu, 0))
        machine.send_key("meta_l-backspace")
        wait_session(layer(menu))
        machine.send_key("meta_l-backspace")
        wait_session(layer(menu, 0))
        for key in ["s", "r", "e"]:
            machine.send_key("meta_l-backspace")
            wait_session(layer(menu))
            machine.send_key(key)
            wait_session(layer("rofi"))
            machine.send_key("ret")  # The first, selected action is Cancel.
            wait_session(layer("rofi", 0))
            in_session("uwsm check is-active compositor-only")
        machine.send_key("meta_l-backspace")
        wait_session(layer(menu))
        machine.send_key("l")
        wait_session(locked)
        unlock()

    with subtest("clipboard history restores text and images"):
        start_in_session("printf %s original | wl-copy --foreground")
        wait_session("cliphist list | grep -F original")
        start_in_session("printf %s replacement | wl-copy --foreground")
        wait_session("cliphist list | grep -F replacement")
        machine.send_key("meta_l-ctrl-v")
        wait_session(layer("rofi"))
        machine.send_chars("origin")
        machine.send_key("ret")
        wait_session("test \"$(wl-paste -n)\" = original")
        wait_session(layer("rofi", 0))
        start_in_session("wl-copy --foreground --type image/png </etc/hyprixe-test/photo-b.png")
        wait_session("cliphist list | grep -F 'binary data'")
        start_in_session("printf %s replacement | wl-copy --foreground")
        machine.send_key("meta_l-ctrl-v")
        wait_session(layer("rofi"))
        machine.send_chars("png")
        machine.send_key("ret")
        wait_session("wl-paste --type image/png | cmp - /etc/hyprixe-test/photo-b.png")
        wait_session(layer("rofi", 0))
        machine.send_key("meta_l-ctrl-v")
        wait_session(layer("rofi"))
        machine.send_chars("origin")
        machine.send_key("ctrl-delete")
        wait_session("! cliphist list | grep -F original")
        wait_session(layer("rofi"))
        machine.send_key("alt-delete")
        wait_session('test -z "$(cliphist list)"')
        # Rofi -no-custom exits as soon as the wiped history has no entries.
        wait_session(layer("rofi", 0))

    # These positions refer to the rendered bar on the fixture's 1280x800 output.
    dispatch('hl.dsp.focus({ workspace = "3" })')
    workspace(3)
    click(62, 20)
    workspace(1)
    click(102, 20)
    workspace(2)
    bar_log = machine.succeed(user("journalctl --user -b -u waybar.service --no-pager"))
    assert "detected Lua-based dispatch protocol" in bar_log, bar_log

    kitty = "hyprctl clients -j | jq -e '[.[] | select(.class == \"kitty\")]"
    machine.send_key("meta_l-ret")
    wait_session(kitty + " | length == 1'")
    window = json.loads(in_session(kitty + " | .[0].address'"))
    sleep(2)
    click(62, 20)
    workspace(1)
    click(195, 20)
    workspace(2)
    active_window(window)
    kitty_screen = screenshot("hyprixe-kitty")
    taskbar = (183, 9, 217, 31)
    assert ImageChops.difference(kitty_screen.crop(taskbar), desktop.crop(taskbar)).getbbox()
    with subtest("Kitty launches Zsh with the canonical Powerlevel10k prompt"):
        in_session('git init -q "$HOME/repo"')
        machine.send_chars("cd repo\n")
        wait_session("pgrep -u 1000 -x zsh; pgrep -u 1000 -x gitstatusd")
        machine.send_chars("id\n")
        wait_session('grep -q ";id$" "$XDG_STATE_HOME/hyprixe/zsh/history"')
        functions = '(( $+functions[_zsh_autosuggest_start] && $+functions[_zsh_highlight] && $+functions[p10k] )); [[ $GITSTATUS_AUTO_INSTALL == 0 ]]'
        command = "zsh -ic " + quote(functions)
        output = in_session("${pkgs.util-linux}/bin/script -qec " + quote(command) + " /dev/null")
        assert "gitstatus failed to initialize" not in output
        machine.screenshot("hyprixe-powerlevel10k")
    click(26, 20)
    sleep(1)
    drawer = screenshot("hyprixe-drawer")
    left = (46, 11, 175, 30)
    assert ImageChops.difference(drawer.crop(left), kitty_screen.crop(left)).getbbox()
    click(26, 20)

    try:
        open_launcher()
    finally:
        preview = screenshot("hyprixe-rofi")
    # The sky and forest samples verify that the asynchronous preview painted.
    sky = preview.getpixel((400, 250))
    forest = preview.getpixel((400, 570))
    assert isinstance(sky, tuple) and isinstance(forest, tuple) and sky[0] - forest[0] > 90
    machine.send_key("esc")
    wait_session(layer("rofi", 0))
    open_launcher()
    machine.send_chars("kitty")
    machine.send_key("ret")
    wait_session(kitty + " | length == 2'")

    first_window = json.loads(in_session(kitty + " | .[0].address'"))
    open_launcher()
    click(255, 452)
    wait_session("pgrep -u 1000 -f '^[^ ]*/bin/rofi .*config-windows\\.rasi '")
    wait_session(layer("rofi"))
    machine.screenshot("hyprixe-window-switcher")
    sleep(2)
    machine.send_key("ret")
    wait_session(layer("rofi", 0))
    active_window(first_window)

    open_launcher()
    click(255, 522)
    wait_session(kitty + " | length == 3'")
    wait_session(layer("rofi", 0))

    for remaining in [2, 1, 0]:
        address = json.loads(in_session(kitty + " | .[0].address'"))
        dispatch(f'hl.dsp.focus({{ window = "address:{address}" }})')
        active_window(address)
        machine.send_chars("exit\n")
        try:
            wait_session(kitty + f" | length == {remaining}'")
        except Exception:
            machine.screenshot("hyprixe-close-failure")
            raise
    sleep(1)
    closed = screenshot("hyprixe-taskbar-empty")
    difference = ImageChops.difference(closed.crop(taskbar), desktop.crop(taskbar)).convert("L")
    assert not difference.point(lambda value: 255 if value > 5 else 0).getbbox()

    with subtest("Dolphin shortcut, Qt style, and writable preferences"):
        machine.send_key("meta_l-e")
        dolphin = "hyprctl clients -j | jq -e '.[] | select(.class | endswith(\"dolphin\"))'"
        wait_session(dolphin)
        dolphin_pid = json.loads(in_session(dolphin))["pid"]
        wait_session(f"grep -F libkvantum.so /proc/{dolphin_pid}/maps")
        machine.screenshot("hyprixe-dolphin")
        in_session('test -w "$XDG_CONFIG_HOME/dolphinrc"; test ! -L "$XDG_CONFIG_HOME/dolphinrc"')
        in_session('test -w "$XDG_CONFIG_HOME/kdeglobals"; test -w "$XDG_CONFIG_HOME/Kvantum/kvantum.kvconfig"')
        in_session('test -w "$XDG_DATA_HOME/kxmlgui5/dolphin/dolphinui.rc"')
        in_session('xdg-mime query default inode/directory | grep -Fx org.kde.dolphin.desktop')
        in_session('xdg-mime query filetype "$HOME/repo" | grep -Fx inode/directory')
        in_session('kwriteconfig6 --file dolphinrc --group HyprixeFixture --key Saved preserve')
        machine.send_key("meta_l-a")  # Physical QEMU A is logical Q on AZERTY.
        wait_session("! " + dolphin)
        machine.succeed('systemctl restart "home-manager-$(systemd-escape ${username}).service"')
        assert in_session("kreadconfig6 --file dolphinrc --group HyprixeFixture --key Saved").strip() == "preserve"
        open_launcher()
        click(255, 381)
        wait_session(dolphin)
        wait_session(layer("rofi", 0))
        machine.send_key("meta_l-a")
        wait_session("! " + dolphin)

    theme = '"$XDG_CACHE_HOME/hyprixe/theme/current"'
    state = '"$XDG_STATE_HOME/hyprixe/theme.json"'
    data = '"$XDG_DATA_HOME/hyprixe"'
    kitty_query = 'kitten @ --to "unix:$XDG_RUNTIME_DIR/hyprixe-kitty-test" get-colors'
    gradient = "hyprctl -j getoption general:col.active_border | jq -er .gradient"
    bar_unit = user("systemctl --user show -P MainPID waybar.service")
    swaync_unit = user("systemctl --user show -P MainPID swaync.service")
    journal = user("journalctl --user -b -u waybar.service --no-pager")
    compositor = in_session("printenv HYPRLAND_INSTANCE_SIGNATURE")
    bar_pid = machine.succeed(bar_unit)
    swaync_pid = machine.succeed(swaync_unit)

    assert in_session("wallust --version").strip() == "wallust 3.5.1"
    in_session(f"jq -e .enabled {state}")
    in_session(f'test "$(jq -r .wallpaper {state})" = "$XDG_DATA_HOME/hyprixe/wallpapers/min_forest.jpg"')
    original = json.loads(in_session(f"cat {theme}/palette.json"))
    base_gradient = in_session(gradient)
    start_in_session('uwsm app -- kitty --listen-on "unix:$XDG_RUNTIME_DIR/hyprixe-kitty-test" -o allow_remote_control=socket-only')
    wait_session(kitty_query + " | grep -i " + quote(original["background"]))
    in_session(f'install -Dm644 /etc/hyprixe-test/photo-a.jpg {data}/personal/photo-a.jpg')
    in_session(f'install -Dm644 /etc/hyprixe-test/photo-b.png {data}/personal/photo-b.png')

    def apply_wallpaper(filename):
        before = machine.succeed(journal).count("Reloading...")
        in_session(f"hyprixe-theme apply {data}/personal/{filename}")
        wait_session("awww query | grep -F " + quote("personal/" + filename))
        wait_session(f"jq -e '.source == \"wallust\"' {theme}/metadata.json")
        machine.wait_until_succeeds(journal + f" | awk '/Reloading/ {{ n++ }} END {{ exit !(n>{before}) }}'")
        wait_session(layer("waybar"))
        assert machine.succeed(bar_unit) == bar_pid
        assert machine.succeed(swaync_unit) == swaync_pid
        assert in_session("printenv HYPRLAND_INSTANCE_SIGNATURE") == compositor
        assert not parse_config_errors(in_session("hyprctl configerrors -j"))
        palette = json.loads(in_session(f"cat {theme}/palette.json"))
        wait_session(kitty_query + " | grep -i " + quote(palette["background"]))
        expected = tuple(bytes.fromhex(palette["workspace"][1:]))
        for _ in range(10):
            bar = screenshot("waybar-" + Path(filename).stem).crop((46, 8, 178, 34))
            colours = bar.getcolors(4000)
            if colours and any(rgb == expected and count > 15 for count, rgb in colours):
                return palette
            sleep(1)
        raise AssertionError(f"Waybar did not paint its active workspace {palette['workspace']}")

    def rofi_theme():
        return in_session('rofi -config "$XDG_CONFIG_HOME/hypr/rofi/config-launcher.rasi" -dump-theme')

    def expect_colour(name, bounds, colour):
        target = tuple(bytes.fromhex(colour[1:]))
        for _ in range(6):
            region = screenshot(name).crop(bounds)
            if target in region.getdata():
                return
            sleep(1)
        raise AssertionError(f"{name} did not paint {colour}")

    def themed_consumers(label, palette):
        in_session("notify-send Hyprixe 'Frosted Glass palette'")
        in_session("swaync-client -t")
        wait_session(layer("swaync-control-center"))
        expect_colour("swaync-" + label, (850, 35, 1280, 800), palette["foreground"])
        in_session("swaync-client -C; swaync-client -t")
        wait_session(layer("swaync-control-center", 0))
        machine.send_key("meta_l-backspace")
        wait_session(layer(menu))
        expect_colour("wlogout-" + label, (180, 280, 1100, 520), palette["foreground"])
        machine.send_key("esc")
        wait_session(layer(menu, 0))
        machine.send_key("meta_l-l")
        wait_session(locked)
        expect_colour("hyprlock-" + label, (320, 270, 960, 470), palette["accent"])
        unlock()

    palette_a = apply_wallpaper("photo-a.jpg")
    gradient_a = in_session(gradient)
    assert palette_a != original and gradient_a != base_gradient
    machine.screenshot("hyprixe-desktop-a")
    rofi_a = rofi_theme()
    open_launcher()
    machine.screenshot("hyprixe-theme-a")
    machine.send_key("esc")
    wait_session(layer("rofi", 0))
    themed_consumers("a", palette_a)
    palette_b = apply_wallpaper("photo-b.png")
    assert palette_b != palette_a and in_session(gradient) != gradient_a
    assert rofi_theme() != rofi_a
    machine.screenshot("hyprixe-desktop-b")
    start_in_session('uwsm app -- kitty --listen-on "unix:$XDG_RUNTIME_DIR/hyprixe-kitty-next" -o allow_remote_control=socket-only')
    wait_session(kitty_query.replace("kitty-test", "kitty-next") + " | grep -i " + quote(palette_b["background"]))
    open_launcher()
    machine.screenshot("hyprixe-theme-b")
    machine.send_key("esc")
    wait_session(layer("rofi", 0))
    themed_consumers("b", palette_b)
    in_session("hyprixe-theme refresh")
    assert json.loads(in_session(f"cat {theme}/palette.json")) == palette_b
    published = in_session(f"readlink {theme}")
    in_session(f"printf corrupt > {data}/personal/bad.jpg; ! hyprixe-theme apply {data}/personal/bad.jpg")
    assert in_session(f"readlink {theme}") == published
    desktop_ready("photo-b.png")
    with subtest("awww crash reapplies the wallpaper without a monitor event"):
        start_time = "systemctl --user show -P ExecMainStartTimestampMonotonic hyprixe-wallpaper.service"
        old_start = in_session(start_time).strip()
        old_pid = machine.succeed(daemon_pid).strip()
        in_session("systemctl --user kill --kill-whom=main --signal=KILL hyprixe-awww.service")
        machine.wait_until_succeeds(f"{daemon_pid} | grep -vx {old_pid}", timeout=30)
        wait_session(f"{start_time} | grep -vx {old_start}")
        desktop_ready("photo-b.png")
    assert in_session("hyprctl output create headless Hyprixe-Test").strip() == "ok"
    wait_session("awww query | grep -F 'Hyprixe-Test:' | grep -F photo-b.png")
    assert in_session("hyprctl output remove Hyprixe-Test").strip() == "ok"

    # The VM has no real backlight. Run the packaged GTK interpreter with the
    # Core helper, a private fixture sysfs, and simulated SetBrightness calls.
    popup_namespace = "hyprixe-brightness-popup"

    def launch_popup():
        start_in_session("probe-brightness")
        wait_session(layer(popup_namespace))

    launch_popup()
    machine.screenshot("hyprixe-brightness")
    popup_layer = json.loads(in_session(
        "hyprctl layers -j | jq -c '.. | objects | select(.namespace? == \"hyprixe-brightness-popup\")'"
    ))
    x, y, width, height = (popup_layer[key] for key in ("x", "y", "w", "h"))
    click(x + width - 35, y + height - 18)
    wait_session('test "$(cat "$XDG_RUNTIME_DIR/hyprixe-backlight-test/panel/brightness")" -ne 171')
    machine.send_key("home")
    wait_session('test "$(cat "$XDG_RUNTIME_DIR/hyprixe-backlight-test/panel/brightness")" -eq 13')
    machine.send_key("esc")
    wait_session(layer(popup_namespace, 0))
    launch_popup()
    in_session("probe-brightness")
    wait_session(layer(popup_namespace, 0))
    launch_popup()
    dispatch(f"hl.dsp.cursor.move({{ x = {x + width // 2}, y = {y + height // 2} }})")
    dispatch("hl.dsp.cursor.move({ x = 700, y = 200 })")
    in_session(layer(popup_namespace))
    dispatch(f"hl.dsp.cursor.move({{ x = {x + width // 2}, y = {y + height // 2} }})")
    sleep(3.2)
    in_session(layer(popup_namespace))
    dispatch("hl.dsp.cursor.move({ x = 700, y = 200 })")
    wait_session(layer(popup_namespace, 0))

    def reconnect(filename):
        machine.succeed(user("uwsm stop"))
        logged_out()
        machine.fail(agent)
        machine.fail("pgrep -u 1000 -f '^/nix/store/[^/]+/bin/wl-paste --watch cliphist store( |$)'")
        machine.fail(user("busctl --user --timeout=3s call org.freedesktop.Notifications "
                          "/org/freedesktop/Notifications org.freedesktop.Notifications GetServerInformation"))
        login()
        desktop_ready(filename)

    reconnect("photo-b.png")
    assert "dynamic theming: enabled" in in_session("hyprixe-theme status")
    assert json.loads(in_session(f"cat {theme}/palette.json")) == palette_b
    in_session('rm -rf "$XDG_CACHE_HOME/hyprixe/theme"')
    open_launcher()
    machine.send_key("esc")
    wait_session(layer("rofi", 0))
    reconnect("photo-b.png")
    assert json.loads(in_session(f"cat {theme}/palette.json")) == palette_b
    in_session("hyprixe-theme disable")
    assert json.loads(in_session(f"cat {theme}/palette.json")) == original
    reconnect("photo-b.png")
    assert "dynamic theming: disabled" in in_session("hyprixe-theme status")
    in_session("hyprixe-theme default")
    desktop_ready()
    reconnect("min_forest.jpg")
    in_session("hyprixe-theme enable")
    assert "dynamic theming: enabled" in in_session("hyprixe-theme status")

    in_session(f"hyprixe-theme apply {data}/personal/photo-b.png")
    with subtest("confirmed logout shuts down the UWSM session"):
        machine.send_key("meta_l-backspace")
        wait_session(layer(menu))
        machine.send_key("e")
        wait_session(layer("rofi"))
        machine.send_key("down")
        machine.send_key("ret")
        logged_out()
    machine.fail("journalctl -k -b --no-pager | grep -E 'segfault .* in rofi\\['")

    with subtest("static generation keeps a valid snapshot without displaying or serving it"):
        state_hash = "sha256sum ${homeDirectory}/.state-fixture/hyprixe/theme.json"
        saved_state = machine.succeed(state_hash)
        preserved = machine.succeed(f"readlink {current}")
        published_colours = json.loads(machine.succeed(f"cat {current}/palette.json"))
        manager = machine.succeed("systemctl show -P MainPID display-manager.service")
        activate(static)
        assert machine.succeed("systemctl show -P MainPID display-manager.service") == manager
        machine.fail(f"test -S /run/{server}.sock")
        machine.fail(f"systemctl is-active {server}.service")
        assert machine.succeed(f"readlink {current}") == preserved
        # Deliberately refresh the test greeter with nobody logged in.
        machine.succeed("systemctl restart display-manager.service")
        greeter("sddm-static-sync-disabled", official)
        login()
        desktop_ready("photo-b.png")
        assert machine.succeed(state_hash) == saved_state
        assert machine.succeed(f"readlink {current}") == preserved
        peer_theme = "runuser -u ${peer} -- /etc/profiles/per-user/${peer}/bin/hyprixe-theme"
        peer_status = machine.succeed(f"{peer_theme} status")
        assert "dynamic theming: enabled" in peer_status and "min_forest.jpg" in peer_status
        machine.succeed(f"{peer_theme} disable")
        assert "dynamic theming: disabled" in machine.succeed(f"{peer_theme} status")
        assert machine.succeed(state_hash) == saved_state
        desktop_ready("photo-b.png")
        machine.fail("runuser -u ${peer} -- test -r ${homeDirectory}/.state-fixture/hyprixe/theme.json")
        machine.fail(
            "journalctl -b -u display-manager.service --no-pager | "
            "grep -Ei 'module .+ is not installed|failed to load component|is not a type|qtvirtualkeyboard'"
        )

    with subtest("rollback restores publication, then disabling Hyprixe preserves user data"):
        machine.succeed(user("uwsm stop"))
        logged_out()
        activate(generation_a)
        assert machine.succeed(f"readlink {current}") == preserved
        assert machine.succeed(state_hash) == saved_state
        machine.wait_for_unit(server + ".socket")
        machine.succeed("systemctl restart display-manager.service")
        greeter("sddm-after-rollback", photo_b, published_colours)
        login()
        desktop_ready("photo-b.png")
        assert machine.succeed(state_hash) == saved_state
        assert in_session("kreadconfig6 --file dolphinrc --group HyprixeFixture --key Saved").strip() == "preserve"
        machine.succeed(user("uwsm stop"))
        logged_out()
        preserved = machine.succeed(f"readlink {current}")
        activate(base)
        machine.succeed(
            "systemctl is-active display-manager.service",
            "test -r ${homeDirectory}/${configDirectory}/dolphinrc",
            "test -s ${homeDirectory}/.cache-fixture/hyprixe/theme/current/palette.json",
            host_file,
        )
        machine.fail("test -S /run/hyprixe-sddm-sync.sock")
        machine.fail("test -L ${homeDirectory}/${configDirectory}/hypr/hyprland.lua")
        machine.fail("test -x /etc/profiles/per-user/${username}/bin/hyprixe-theme")
        assert machine.succeed(state_hash) == saved_state
        assert machine.succeed(f"readlink {current}") == preserved

    with subtest("activation refuses an unmanaged shell configuration"):
        existing = "${homeDirectory}/.zshrc"
        machine.succeed("runuser -u ${username} -- sh -c " + quote(f"printf '%s\\n' 'Personal shell file' > {existing}"))
        machine.execute(f"{generation_a}/bin/switch-to-configuration test")
        machine.wait_until_succeeds("systemctl is-failed home-manager-${username}.service")
        machine.succeed(f"test ! -L {existing} && grep -Fqx 'Personal shell file' {existing}", host_file)
        machine.succeed("journalctl -b -u home-manager-${username}.service --no-pager | grep -F '.zshrc'")
  '';
}

// Optional, complete system snapshot. Missing/invalid data always uses v1.1 paint.
import QtQuick

Item {
    id: theme
    property url paletteSource: ""
    readonly property var snapshot: paletteLoader.status === Loader.Ready ? paletteLoader.item : null
    readonly property bool coloursValid: validData(snapshot)
    readonly property bool valid: coloursValid && imageProbe.status === Image.Ready
    // Never use the fallback as a placeholder while a local snapshot settles.
    readonly property bool resolved: paletteSource.toString() === "" || paletteLoader.status === Loader.Error ||
                                     (paletteLoader.status === Loader.Ready &&
                                      (!coloursValid || imageProbe.status === Image.Ready || imageProbe.status === Image.Error))
    readonly property string wallpaper: valid ? snapshot.wallpaper : ""
    visible: false

    function validData(value) {
        if (!value || value.schema !== 1 || typeof value.wallpaper !== "string" ||
                !/^file:\/\//.test(value.wallpaper))
            return false;
        const roles = ["background", "surface", "foreground", "accent", "accent_alt", "border", "error"];
        for (let role of roles) {
            if (typeof value[role] !== "string" || !/^#[0-9a-f]{6}$/.test(value[role]))
                return false;
        }
        function luminance(colour) {
            let total = 0;
            const weights = [0.2126, 0.7152, 0.0722];
            for (let i = 0; i < 3; ++i) {
                let v = parseInt(colour.substr(1 + i * 2, 2), 16) / 255;
                total += weights[i] * (v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
            }
            return total;
        }
        for (let role of ["background", "surface"]) {
            const a = luminance(value[role]), b = luminance(value.foreground);
            if ((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) < 4.5)
                return false;
        }
        return true;
    }
    function paint(role, fallback) { return valid ? snapshot[role] : fallback; }
    function tint(role, opacity, fallback) {
        if (!valid)
            return fallback;
        const c = snapshot[role];
        return Qt.rgba(parseInt(c.substr(1, 2), 16) / 255,
                       parseInt(c.substr(3, 2), 16) / 255,
                       parseInt(c.substr(5, 2), 16) / 255, opacity);
    }
    Loader { id: paletteLoader; source: theme.paletteSource; asynchronous: false }
    Image {
        id: imageProbe
        source: theme.coloursValid ? theme.snapshot.wallpaper : ""
        // Decode once before the first frame. The full-size background shares
        // Qt's image cache, including this already validated local image.
        asynchronous: false
    }
}

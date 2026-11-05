// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic as C

C.Button {
    id: control
    property DynamicTheme theme
    property bool primary: false
    implicitHeight: 46
    implicitWidth: Math.max(100, contentItem.implicitWidth + 36)
    padding: 14
    hoverEnabled: true
    font.family: "JetBrains Mono"
    font.pixelSize: 14
    activeFocusOnTab: true
    background: Rectangle {
        radius: 12
        color: control.down ? control.theme.paint("accent", "#396e94") : (control.hovered ? control.theme.paint("surface", "#315d7a") : (control.primary ? control.theme.paint("surface", "#255d83") : control.theme.tint("surface", 0.6901960784313725, "#b01e3c51")))
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus || control.hovered ? control.theme.paint("accent_alt", "#b4f9f8") : control.theme.tint("border", 0.5019607843137255, "#807ed6ff")
        opacity: control.enabled ? 1 : 0.5
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: control.down ? control.theme.paint("background", "#e6f1f4") : control.theme.paint("foreground", "#e6f1f4")
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: control.enabled ? 1 : 0.55
    }
}

// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic as C

C.Button {
    id: control
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
        color: control.down ? "#396e94" : (control.hovered ? "#315d7a" : (control.primary ? "#255d83" : "#b01e3c51"))
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus || control.hovered ? "#b4f9f8" : "#807ed6ff"
        opacity: control.enabled ? 1 : 0.5
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: "#e6f1f4"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: control.enabled ? 1 : 0.55
    }
}

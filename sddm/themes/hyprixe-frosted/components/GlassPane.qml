// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Effects

Item {
    id: pane
    property Item wallpaper
    property rect sampleRect: Qt.rect(0, 0, width, height)
    property real cornerRadius: 24

    ShaderEffectSource {
        id: sample
        sourceItem: pane.wallpaper
        sourceRect: pane.sampleRect
        textureSize: Qt.size(Math.max(1, pane.width / 2), Math.max(1, pane.height / 2))
        live: true
        visible: false
    }
    Rectangle {
        id: mask
        anchors.fill: parent
        radius: pane.cornerRadius
        color: "white"
        layer.enabled: true
        visible: false
    }
    MultiEffect {
        anchors.fill: parent
        source: sample
        autoPaddingEnabled: false
        blurEnabled: true
        blurMax: 48
        blur: 0.8
        saturation: -0.12
        maskEnabled: true
        maskSource: mask
    }
    Rectangle {
        anchors.fill: parent
        radius: pane.cornerRadius
        color: "#b0122434"
        border.width: 1
        border.color: "#887ed6ff"
    }
}

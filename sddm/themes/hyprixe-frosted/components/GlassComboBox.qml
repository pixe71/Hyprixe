// SPDX-License-Identifier: GPL-3.0-or-later
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic as C

C.ComboBox {
    id: control
    implicitHeight: 46
    leftPadding: 14
    rightPadding: 36
    font.family: "JetBrains Mono"
    font.pixelSize: 13
    activeFocusOnTab: true
    hoverEnabled: true
    background: Rectangle {
        radius: 12
        color: "#b01a3448"
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus || control.hovered ? "#b4f9f8" : "#607ed6ff"
    }
    contentItem: Text {
        text: control.displayText
        font: control.font
        color: "#e6f1f4"
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Text {
        x: control.width - width - 14
        y: (control.height - height) / 2
        text: "⌄"
        color: "#7ed6ff"
        font.pixelSize: 19
    }
    delegate: C.ItemDelegate {
        id: entry
        required property int index
        width: control.width
        text: control.textAt(index)
        highlighted: control.highlightedIndex === index
        font: control.font
        contentItem: Text {
            text: entry.text
            color: "#e6f1f4"
            font: control.font
            wrapMode: Text.Wrap
        }
        background: Rectangle {
            radius: 8
            color: entry.highlighted ? "#315d7a" : "transparent"
        }
    }
    popup: C.Popup {
        y: control.height + 6
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 12, 240)
        padding: 6
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            C.ScrollIndicator.vertical: C.ScrollIndicator {}
        }
        background: Rectangle {
            color: "#f0122434"
            radius: 12
            border.width: 1
            border.color: "#887ed6ff"
        }
    }
    C.ToolTip {
        parent: control
        visible: control.hovered && control.displayText.length > 0
        delay: 800
        text: control.displayText
        contentItem: Text { text: control.displayText; color: "#e6f1f4"; font: control.font }
        background: Rectangle { color: "#f0122434"; radius: 8; border.color: "#887ed6ff" }
    }
}

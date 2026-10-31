// Hyprixe Frosted Glass. SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
import "components"

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#122434"
    readonly property bool wide: width >= 1100 && height >= 700
    readonly property real margin: wide ? Math.max(36, width * 0.065) : 20
    readonly property bool shortScreen: height < 850
    readonly property real verticalMargin: shortScreen ? 16 : 40
    readonly property real panePadding: shortScreen ? 20 : 28
    readonly property string themeFont: config.font || "JetBrains Mono"
    property date now: new Date()
    property bool busy: false
    property string message: ""
    readonly property string loginName: users.count > 0 ? users.currentText : manualUser.text.trim()

    function authenticate() {
        if (busy || !loginName || sessions.count === 0 || sessions.currentIndex < 0 || sessions.currentIndex >= sessions.count)
            return;
        message = "";
        busy = true;
        sddm.login(loginName, password.text, sessions.currentIndex);
    }

    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.now = new Date() }
    Connections {
        target: sddm
        ignoreUnknownSignals: true
        function onLoginFailed() {
            root.busy = false;
            root.message = qsTr("Sign-in failed. Check your password and try again.");
            password.clear();
            password.forceActiveFocus();
        }
        function onLoginSucceeded() { password.clear(); }
        function onInformationMessage(message) { root.message = message; }
    }

    Image {
        id: backgroundImage
        anchors.fill: parent
        source: Qt.resolvedUrl(config.background || "min_forest.jpg")
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        smooth: true
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#15122434" }
            GradientStop { position: 1; color: "#70122434" }
        }
    }

    Flickable {
        id: viewport
        anchors.fill: parent
        anchors.bottomMargin: 76
        contentWidth: width
        contentHeight: Math.max(height, composition.implicitHeight + 2 * root.verticalMargin)
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        C.ScrollIndicator.vertical: C.ScrollIndicator {}

        GridLayout {
            id: composition
            width: viewport.width - 2 * root.margin
            x: root.margin
            y: Math.max(root.verticalMargin, (viewport.height - implicitHeight) / 2)
            columns: root.wide ? 2 : 1
            columnSpacing: 48
            rowSpacing: 24

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: root.wide ? Qt.AlignLeft : Qt.AlignHCenter
                spacing: root.wide ? 18 : 6
                Text {
                    Layout.alignment: root.wide ? Qt.AlignLeft : Qt.AlignHCenter
                    text: "HYPRIXE"
                    color: "#b4f9f8"
                    font.family: root.themeFont
                    font.pixelSize: 14
                    font.letterSpacing: 6
                }
                Text {
                    Layout.alignment: root.wide ? Qt.AlignLeft : Qt.AlignHCenter
                    text: Qt.formatTime(root.now, "HH:mm")
                    color: "#e6f1f4"
                    font.family: root.themeFont
                    font.pixelSize: root.wide ? Math.min(112, root.height * 0.105) : 42
                    font.weight: Font.Light
                }
                Text {
                    Layout.alignment: root.wide ? Qt.AlignLeft : Qt.AlignHCenter
                    text: Qt.formatDate(root.now, Qt.locale().dateFormat(Locale.LongFormat))
                    color: "#b4f9f8"
                    font.family: root.themeFont
                    font.pixelSize: root.wide ? 19 : 13
                }
                Text {
                    visible: root.wide
                    text: "F R O S T E D   G L A S S"
                    color: "#a6c5d2"
                    font.family: root.themeFont
                    font.pixelSize: 11
                }
            }

            GlassPane {
                id: pane
                objectName: "loginPane"
                Layout.preferredWidth: Math.min(430, composition.width)
                Layout.maximumWidth: 430
                Layout.fillWidth: !root.wide
                Layout.alignment: Qt.AlignHCenter
                implicitHeight: form.implicitHeight + 2 * root.panePadding
                wallpaper: backgroundImage
                sampleRect: Qt.rect(viewport.x + composition.x + pane.x,
                                    viewport.y + composition.y + pane.y - viewport.contentY,
                                    pane.width, pane.height)

                ColumnLayout {
                    id: form
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: root.panePadding
                    spacing: root.shortScreen ? 8 : 12

                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: root.shortScreen ? 56 : 72
                        Layout.preferredHeight: root.shortScreen ? 56 : 72
                        radius: 18
                        color: "#701e4c84"
                        border.width: 1
                        border.color: "#807ed6ff"
                        Image {
                            id: avatar
                            anchors.fill: parent
                            anchors.margins: 8
                            source: users.currentValue || ""
                            visible: status === Image.Ready
                            fillMode: Image.PreserveAspectFit
                        }
                        Image {
                            anchors.fill: parent
                            anchors.margins: 12
                            source: "assets/user.svg"
                            visible: avatar.status !== Image.Ready
                        }
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: qsTr("Welcome back")
                        font.family: root.themeFont
                        font.pixelSize: root.shortScreen ? 22 : 24
                        color: "#e6f1f4"
                    }
                    Text {
                        text: qsTr("ACCOUNT")
                        color: "#a6c5d2"
                        font.family: root.themeFont
                        font.pixelSize: 11
                        font.letterSpacing: 1.5
                    }
                    GlassComboBox {
                        id: users
                        objectName: "users"
                        Layout.fillWidth: true
                        visible: count > 0
                        enabled: !root.busy
                        model: userModel
                        textRole: "name"
                        valueRole: "icon"
                        currentIndex: userModel.lastIndex >= 0 && userModel.lastIndex < count ? userModel.lastIndex : 0
                        onActivated: { password.clear(); root.message = ""; password.forceActiveFocus(); }
                    }
                    C.TextField {
                        id: manualUser
                        objectName: "manualUser"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 46
                        visible: users.count === 0
                        enabled: !root.busy
                        placeholderText: qsTr("User name")
                        color: "#e6f1f4"
                        font.family: root.themeFont
                        font.pixelSize: 14
                        leftPadding: 14
                        background: Rectangle { color: "#b01a3448"; radius: 12; border.width: 1; border.color: "#607ed6ff" }
                        onAccepted: password.forceActiveFocus()
                    }
                    C.TextField {
                        id: password
                        objectName: "password"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 50
                        enabled: !root.busy
                        focus: true
                        echoMode: TextInput.Password
                        inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                        placeholderText: qsTr("Password")
                        placeholderTextColor: "#8daebb"
                        color: "#e6f1f4"
                        selectionColor: "#2770c0"
                        selectedTextColor: "white"
                        font.family: root.themeFont
                        font.pixelSize: 15
                        leftPadding: 14
                        rightPadding: 14
                        background: Rectangle {
                            color: "#c0122434"
                            radius: 12
                            border.width: password.activeFocus ? 2 : 1
                            border.color: password.activeFocus ? "#7ed6ff" : "#607ed6ff"
                        }
                        onAccepted: root.authenticate()
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.minimumHeight: root.shortScreen ? 28 : 34
                        text: sessions.count === 0 ? qsTr("No sessions found. Check the SDDM session installation.") : root.message
                        color: "#ff9ca8"
                        wrapMode: Text.Wrap
                        font.family: root.themeFont
                        font.pixelSize: 12
                        Accessible.role: Accessible.AlertMessage
                    }
                    GlassButton {
                        objectName: "signIn"
                        Layout.fillWidth: true
                        primary: true
                        text: root.busy ? qsTr("Signing in…") : qsTr("Sign in")
                        enabled: !root.busy && root.loginName.length > 0 && sessions.count > 0 && sessions.currentIndex >= 0 && sessions.currentIndex < sessions.count
                        onClicked: root.authenticate()
                    }
                    Rectangle { Layout.fillWidth: true; Layout.topMargin: 8; Layout.bottomMargin: 4; implicitHeight: 1; color: "#307ed6ff" }
                    Text {
                        text: qsTr("SESSION")
                        color: "#a6c5d2"
                        font.family: root.themeFont
                        font.pixelSize: 11
                        font.letterSpacing: 1.5
                    }
                    GlassComboBox {
                        id: sessions
                        objectName: "sessions"
                        Layout.fillWidth: true
                        enabled: !root.busy
                        model: sessionModel
                        textRole: "name"
                        valueRole: "file"
                        currentIndex: sessionModel.lastIndex >= 0 && sessionModel.lastIndex < count ? sessionModel.lastIndex : 0
                    }
                }
            }
        }
    }

    Text {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin: root.margin
        anchors.bottomMargin: 28
        text: root.width < 480 ? "Hyprixe" : "Hyprixe · Frosted Glass"
        color: "#a6c5d2"
        font.family: root.themeFont
        font.pixelSize: 11
    }
    GlassButton {
        id: power
        objectName: "power"
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: root.margin
        anchors.bottomMargin: 18
        text: qsTr("Power")
        enabled: sddm.canReboot || sddm.canPowerOff
        onClicked: powerMenu.opened ? powerMenu.close() : powerMenu.open()
    }
    C.Popup {
        id: powerMenu
        parent: root
        focus: true
        x: root.width - width - root.margin
        y: root.height - height - 76
        width: 220
        padding: 12
        closePolicy: C.Popup.CloseOnEscape | C.Popup.CloseOnPressOutside
        background: Rectangle { color: "#f0122434"; radius: 16; border.width: 1; border.color: "#887ed6ff" }
        contentItem: ColumnLayout {
            spacing: 8
            GlassButton { objectName: "restart"; Layout.fillWidth: true; text: qsTr("Restart"); enabled: sddm.canReboot; onClicked: sddm.reboot() }
            GlassButton { objectName: "shutdown"; Layout.fillWidth: true; text: qsTr("Shut down"); enabled: sddm.canPowerOff; onClicked: sddm.powerOff() }
        }
    }
    Component.onCompleted: users.count > 0 ? password.forceActiveFocus() : manualUser.forceActiveFocus()
}

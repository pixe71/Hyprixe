"""Real Qt 6 controls/context-model test; mocked SDDM never authenticates or powers off.

Called in a child process by test_sddm.py so Qt environment stays isolated.
The software backend checks interactions/layout, not the GPU blur renderer.
"""
from pathlib import Path
import shutil
import sys
import tempfile
from PyQt6.QtCore import (QAbstractListModel, QMetaObject, QModelIndex, QObject,
                          QPointF, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot,
                          qInstallMessageHandler)
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQuick import QQuickView
from PyQt6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
warnings = []


class Model(QAbstractListModel):
    def __init__(self, rows, last=0):
        super().__init__()
        self.rows = rows
        self.last = last
        self.roles = {Qt.ItemDataRole.UserRole + i: key.encode() for i, key in enumerate(rows[0] if rows else ('name', 'icon', 'file'))}

    @pyqtProperty(int, constant=True)
    def lastIndex(self):
        return self.last

    def roleNames(self):
        return self.roles

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows) if not parent.isValid() else 0

    def data(self, index, role):
        return self.rows[index.row()].get(self.roles.get(role, b'').decode()) if index.isValid() else None


class Sddm(QObject):
    loginFailed = pyqtSignal()
    loginSucceeded = pyqtSignal()
    informationMessage = pyqtSignal(str)
    calls = []

    @pyqtProperty(bool, constant=True)
    def canReboot(self):
        return True

    @pyqtProperty(bool, constant=True)
    def canPowerOff(self):
        return True

    @pyqtSlot(str, str, int)
    def login(self, user, password, session):
        self.calls.append(('login', user, password, session))

    @pyqtSlot()
    def reboot(self):
        self.calls.append(('reboot',))

    @pyqtSlot()
    def powerOff(self):
        self.calls.append(('powerOff',))


def require(value, message):
    if not value:
        raise AssertionError(message)


def run():
    app = QGuiApplication(sys.argv)
    qInstallMessageHandler(lambda kind, context, text: warnings.append(text))
    with tempfile.TemporaryDirectory(prefix='hyprixe-qml-') as tmp:
        theme = Path(tmp) / 'theme'
        shutil.copytree(ROOT / 'sddm/themes/hyprixe-frosted', theme)
        shutil.copyfile(ROOT / 'wallpapers/min_forest.jpg', theme / 'min_forest.jpg')
        view = QQuickView()
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        context = view.rootContext()
        users = Model([{'name': 'alice', 'icon': ''}, {'name': 'bob', 'icon': ''}], last=1)
        sessions = Model([{'name': 'Hyprland', 'file': 'hyprland.desktop'},
                          {'name': 'Hyprland (uwsm-managed)', 'file': 'hyprland-uwsm.desktop'}], last=1)
        proxy = Sddm()
        context.setContextProperty('sddm', proxy)
        context.setContextProperty('userModel', users)
        context.setContextProperty('sessionModel', sessions)
        context.setContextProperty('config', {'font': 'JetBrains Mono', 'background': 'min_forest.jpg'})
        view.setSource(QUrl.fromLocalFile(str(theme / 'Main.qml')))
        require(view.status() == QQuickView.Status.Ready, '\n'.join(str(e) for e in view.errors()))
        view.resize(1920, 1080)
        view.show()
        QTest.qWait(80)
        root = view.rootObject()
        def item(name):
            result = root.findChild(QObject, name)
            require(result is not None, 'Missing control: ' + name)
            return result
        require(item('sessions').property('currentText') == 'Hyprland (uwsm-managed)', 'Last session must be retained, not forced')
        require(root.property('loginName') == 'bob', 'Last user must be retained')
        item('password').forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_A)
        require(item('password').property('text') == 'a', 'Physical keyboard input must reach the password field')
        item('password').setProperty('text', '')
        item('password').setProperty('text', 'test-only-password')
        QMetaObject.invokeMethod(root, 'authenticate')
        require(proxy.calls[-1] == ('login', 'bob', 'test-only-password', 1), 'Login must preserve selected SDDM session index')
        require(root.property('busy'), 'Busy state must prevent duplicate login')
        require(not item('signIn').property('enabled'), 'Login button must be disabled during authentication')
        proxy.loginFailed.emit()
        require(not root.property('busy') and item('password').property('text') == '', 'Failure must clear password and reenable login')
        require('failed' in root.property('message'), 'Authentication failure must be visible')
        item('sessions').setProperty('currentIndex', 0)
        item('password').setProperty('text', 'another-test')
        QMetaObject.invokeMethod(root, 'authenticate')
        require(proxy.calls[-1][-1] == 0, 'Theme must not replace a manually selected session')
        proxy.loginSucceeded.emit()
        require(item('password').property('text') == '', 'Success must clear password')
        root.setProperty('busy', False)
        # Open real Qt Quick popup/delegates with keyboard, not a ListModel.get mock.
        item('sessions').forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Space)
        QTest.qWait(50)
        QTest.keyClick(view, Qt.Key.Key_Escape)
        QMetaObject.invokeMethod(item('power'), 'clicked')
        QTest.qWait(30)
        QMetaObject.invokeMethod(item('restart'), 'clicked')
        QMetaObject.invokeMethod(item('shutdown'), 'clicked')
        require(proxy.calls[-2:] == [('reboot',), ('powerOff',)], 'Power controls must use only the SDDM proxy')
        QTest.keyClick(view, Qt.Key.Key_Escape)
        root.setProperty('message', '')
        for width, height in ((1920, 1080), (1280, 720), (1024, 768), (800, 600), (3840, 2160)):
            view.resize(width, height)
            QTest.qWait(30)
            pane = item('loginPane')
            require(pane.width() <= width - 30, f'Pane overflows at {width}x{height}')
            button = item('signIn')
            mapped = button.mapToScene(QPointF(0, 0))
            require(mapped.x() >= 0 and mapped.x() + button.width() <= width, 'Login control exceeds screen width')
            require(button.height() >= 40, 'Controls must remain usable')
        # Hidden users / empty session directory must be usable and safe.
        empty_users = Model([])
        empty_sessions = Model([])
        context.setContextProperty('userModel', empty_users)
        context.setContextProperty('sessionModel', empty_sessions)
        QTest.qWait(30)
        require(item('manualUser').property('visible'), 'Manual username entry is required when SDDM hides users')
        require(not item('signIn').property('enabled'), 'An empty session model must not allow login')
        before = len(proxy.calls)
        QMetaObject.invokeMethod(root, 'authenticate')
        require(len(proxy.calls) == before, 'No session must never submit an invalid index')
        require(not warnings, 'Qt runtime warnings: ' + '\n'.join(warnings))
        view.close()
    print('PASS: actual Qt 6 list models, preserved session index, login/error/password handling, power proxy, popups and responsive layouts')


if __name__ == '__main__':
    run()

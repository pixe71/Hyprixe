#!/usr/bin/env python3
"""Print a standard Qt 6 dock preset; optional maintainer tool, not an installer.

Requires python3-pyqt6. Run with QT_QPA_PLATFORM=offscreen to regenerate
dolphin/dock-layout.ini. Names match Dolphin 25.04's setupDockWidgets(); only
QMainWindow.saveState(0) is stored, never window/screen geometry or personal data.
"""
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDockWidget, QMainWindow, QToolBar, QWidget


def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.resize(1280, 800)  # Reference size in logical units, not saved geometry.
    window.setCentralWidget(QWidget())
    toolbar = QToolBar()
    toolbar.setObjectName('mainToolBar')
    toolbar.setFixedHeight(36)
    window.addToolBar(toolbar)
    docks = {}
    for name in ('placesDock', 'infoDock', 'foldersDock', 'terminalDock'):
        dock = QDockWidget()
        dock.setObjectName(name)
        dock.setTitleBarWidget(QWidget())  # Dolphin's locked-panel appearance.
        content = QWidget()
        content.setMinimumSize(180, 96)
        dock.setWidget(content)
        window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        docks[name] = dock
    places, info = docks['placesDock'], docks['infoDock']
    window.splitDockWidget(places, info, Qt.Orientation.Vertical)
    for name in ('foldersDock', 'terminalDock'):
        docks[name].hide()
    window.show()
    app.processEvents()
    window.resizeDocks([places], [264], Qt.Orientation.Horizontal)
    window.resizeDocks([places, info], [400, 364], Qt.Orientation.Vertical)
    app.processEvents()
    print('# Generated with tools/generate-dolphin-layout.py using Qt 6 saveState(0).')
    print('# Right column: Places/Devices above Information. No monitor or HOME data.')
    print('[State]')
    print('State=' + bytes(window.saveState().toBase64()).decode('ascii'))
    window.close()


if __name__ == '__main__':
    main()

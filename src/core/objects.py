from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
import copy

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QBrush, QIcon, QPixmap

from src.gui.utilities import giveDefaultGroupViewConfig

@dataclass(frozen=True)
class NoradObject:
    noradIndex: int
    name: str

    def toDict(self):
        return {"NORAD_INDEX": self.noradIndex, "NAME": self.name}

    @classmethod
    def fromDict(cls, data: dict):
        return cls(noradIndex=data["NORAD_INDEX"], name=data.get("NAME", ""))

    def __hash__(self):
        return hash(self.noradIndex)

    def __eq__(self, other):
        return isinstance(other, NoradObject) and self.noradIndex == other.noradIndex


@dataclass
class ObjectGroup:
    name: str
    objects: Set[NoradObject] = field(default_factory=set)
    color: str = "#1E90FF"
    visible: bool = True
    expanded: bool = True
    renderRules: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def toDict(self):
        return {
            "NAME": self.name,
            "OBJECTS": [obj.toDict() for obj in sorted(self.objects, key=lambda o: o.noradIndex)],
            "COLOR": self.color,
            "VISIBLE": self.visible,
            "EXPANDED": self.expanded,
            "RENDER_RULES": copy.deepcopy(self.renderRules)
        }

    @classmethod
    def fromDict(cls, data: dict):
        return cls(
            name=data.get("NAME", "Unnamed Group"),
            objects=set(NoradObject.fromDict(o) for o in data.get("OBJECTS", [])),
            color=data.get("COLOR", "#1E90FF"),
            visible=data.get("VISIBLE", True),
            expanded=data.get("EXPANDED", True),
            renderRules=copy.deepcopy(data.get("RENDER_RULES", {}))
        )


@dataclass
class ActiveObjectsModel:
    objectGroups: Dict[str, ObjectGroup] = field(default_factory=dict)
    ungrouped: Set[NoradObject] = field(default_factory=set)
    ungroupedExpanded: bool = True
    selectedObjects: Set[NoradObject] = field(default_factory=set)
    isGroupSelected: bool = True
    selectedGroupName: Optional[str] = None

    def allNoradIndices(self):
        noradIndices: List[int] = [obj.noradIndex for obj in self.ungrouped]
        for objectGroup in self.objectGroups.values():
            if objectGroup.visible:
                noradIndices.extend(obj.noradIndex for obj in objectGroup.objects)
        return noradIndices

    def getAllObjects(self):
        objects: Set[NoradObject] = set(self.ungrouped)
        for objectGroup in self.objectGroups.values():
            if objectGroup.visible:
                objects.update(objectGroup.objects)
        return objects

    def setSelectedObjects(self, objects: Set[NoradObject], isGroup: bool = False, groupName: Optional[str] = None):
        self.selectedObjects = set(objects)
        self.isGroupSelected = isGroup and groupName is not None
        self.selectedGroupName = groupName if self.isGroupSelected else None

    def clearSelection(self):
        self.selectedObjects.clear()
        self.isGroupSelected = False
        self.selectedGroupName = None

    def removeNoradIndexEverywhere(self, norad: int):
        self.ungrouped = {o for o in self.ungrouped if o.noradIndex != norad}
        for group in self.objectGroups.values():
            group.objects = {o for o in group.objects if o.noradIndex != norad}

    def addToUngrouped(self, obj: NoradObject):
        self.removeNoradIndexEverywhere(obj.noradIndex)
        self.ungrouped.add(obj)

    def addToGroup(self, groupName: str, obj: NoradObject):
        if groupName not in self.objectGroups:
            raise ValueError(f"Group '{groupName}' does not exist.")
        self.removeNoradIndexEverywhere(obj.noradIndex)
        self.objectGroups[groupName].objects.add(obj)

    def moveToUngrouped(self, obj: NoradObject):
        self.addToUngrouped(obj)

    def moveToGroup(self, groupName: str, obj: NoradObject):
        self.addToGroup(groupName, obj)

    def addGroup(self, groupName: str, color: Optional[str] = None):
        if groupName in self.objectGroups:
            raise ValueError(f"Group '{groupName}' already exists.")
        self.objectGroups[groupName] = ObjectGroup(name=groupName, color=color or "#1E90FF", renderRules=giveDefaultGroupViewConfig())
        return self.objectGroups[groupName]

    def removeGroup(self, groupName: str):
        if groupName in self.objectGroups:
            self.ungrouped.update(self.objectGroups[groupName].objects)
            del self.objectGroups[groupName]

    def getGroupForNoradIndex(self, noradIndex: int):
        for obj in self.ungrouped:
            if obj.noradIndex == noradIndex:
                return None
        for name, group in self.objectGroups.items():
            for obj in group.objects:
                if obj.noradIndex == noradIndex:
                    return name
        return None

    def getObjectByNoradIndex(self, noradIndex: int):
        if noradIndex is None:
            return None
        for obj in self.ungrouped:
            if obj.noradIndex == noradIndex:
                return obj
        for group in self.objectGroups.values():
            for obj in group.objects:
                if obj.noradIndex == noradIndex:
                    return obj
        return None

    def setGroupConfig(self, groupName, config):
        if groupName not in self.objectGroups:
            return
        self.objectGroups[groupName].renderRules = config

    def toDict(self):
        return {"OBJECT_GROUPS": {name: group.toDict() for name, group in self.objectGroups.items()},
                "UNGROUPED": [o.toDict() for o in self.ungrouped], "UNGROUPED_EXPANDED": self.ungroupedExpanded}

    @classmethod
    def fromDict(cls, data: dict):
        objectGroups = {name: ObjectGroup.fromDict(groupData) for name, groupData in data.get("OBJECT_GROUPS", {}).items()}
        ungrouped = set(NoradObject.fromDict(o) for o in data.get("UNGROUPED", []))
        model = cls(objectGroups=objectGroups, ungrouped=ungrouped)
        model.ungroupedExpanded = data.get("UNGROUPED_EXPANDED", True)
        return model


class ActiveObjectsEditorWidget(QDockWidget):
    activeObjectsChanged = pyqtSignal()

    def __init__(self, mainWindow, title='Active Objects'):
        super().__init__(title, mainWindow)
        self.mainWindow = mainWindow
        self.activeObjects: ActiveObjectsModel = ActiveObjectsModel()
        self.tleDatabase = None
        self._currentSearchText = ""
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QWidget())
        container = QWidget()
        self.setWidget(container)

        # TOP BAR (search + add)
        topBar = QHBoxLayout()
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search objects…")
        self.searchBar.textChanged.connect(self._filterTree)
        self.addButton = QPushButton("+")
        self.addButton.setFixedWidth(28)
        self.addButton.clicked.connect(self.openAddDialog)
        topBar.addWidget(self.searchBar)
        topBar.addWidget(self.addButton)

        # TREE WIDGET
        self.treeWidget = QTreeWidget()
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.setColumnCount(2)
        header = self.treeWidget.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        self.treeWidget.setDragEnabled(True)
        self.treeWidget.setDropIndicatorShown(True)
        self.treeWidget.setDragDropMode(QTreeWidget.InternalMove)
        self.treeWidget.setSelectionMode(QTreeWidget.SingleSelection)
        self.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeWidget.itemSelectionChanged.connect(self._onSelectionChanged)
        self.treeWidget.customContextMenuRequested.connect(self._showContextMenu)
        self.treeWidget.itemChanged.connect(self._onItemChanged)
        self.treeWidget.itemExpanded.connect(self._onItemExpanded)
        self.treeWidget.itemCollapsed.connect(self._onItemCollapsed)
        self.treeWidget.dragMoveEvent = self.dragMoveEvent
        self.treeWidget.dropEvent = self.dropEvent

        # MAIN LAYOUT
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(topBar)
        layout.addWidget(self.treeWidget)

    def populate(self, tleDatabase, modelFromSettings: dict):
        self.treeWidget.blockSignals(True)
        self.tleDatabase = tleDatabase
        self.activeObjects = ActiveObjectsModel.fromDict(modelFromSettings)
        self.treeWidget.clear()
        # UNGROUPED
        ungroupedRoot = QTreeWidgetItem(["Ungrouped", ""])
        ungroupedRoot.setData(0, Qt.UserRole, "UNGROUPED_ROOT")
        ungroupedRoot.setFlags(ungroupedRoot.flags() | Qt.ItemIsDropEnabled)
        self.treeWidget.addTopLevelItem(ungroupedRoot)
        ungroupedRoot.setExpanded(self.activeObjects.ungroupedExpanded)
        for obj in sorted(self.activeObjects.ungrouped, key=lambda o: o.noradIndex):
            self._addObjectItem(ungroupedRoot, obj)
        # GROUPED OBJECTS
        for groupName, group in self.activeObjects.objectGroups.items():
            groupItem = QTreeWidgetItem([groupName, ""])
            groupItem.setData(0, Qt.UserRole, ("GROUP", groupName))
            groupItem.setFlags(groupItem.flags() | Qt.ItemIsDropEnabled | Qt.ItemIsSelectable)
            groupItem.setTextAlignment(1, Qt.AlignRight)
            color = QColor(group.color)
            groupItem.setForeground(0, QBrush(color))
            groupItem.setIcon(0, self._createColorIcon(group.color))
            font = groupItem.font(0)
            font.setBold(True)
            groupItem.setFont(0, font)
            self.treeWidget.addTopLevelItem(groupItem)
            if group.expanded:
                groupItem.setExpanded(True)
            for obj in group.objects:
                self._addObjectItem(groupItem, obj)
        self.treeWidget.blockSignals(False)

    @staticmethod
    def _addObjectItem(parent, obj: NoradObject):
        item = QTreeWidgetItem([obj.name, str(obj.noradIndex)])
        item.setData(0, Qt.UserRole, ("OBJECT", obj))
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsSelectable)
        parent.addChild(item)

    @staticmethod
    def _createColorIcon(hexColor: str) -> QIcon:
        pixmap = QPixmap(8, 8)
        pixmap.fill(QColor(hexColor))
        return QIcon(pixmap)

    def _onSelectionChanged(self):
        items = self.treeWidget.selectedItems()
        if not items:
            self.activeObjects.clearSelection()
            self.activeObjectsChanged.emit()
            return
        selected: set[NoradObject] = set()
        data = items[0].data(0, Qt.UserRole)
        groupMode, groupName = False, None
        if isinstance(data, tuple) and data[0] == "OBJECT":
            selected.add(data[1])
        elif isinstance(data, tuple) and data[0] == "GROUP":
            group = self.activeObjects.objectGroups.get(data[1])
            if group:
                selected.update(group.objects)
            groupMode, groupName = True, group.name
        self.activeObjects.setSelectedObjects(selected, isGroup=groupMode, groupName=groupName)
        self.activeObjectsChanged.emit()

    def outsideObjectSelection(self, noradIndices):
        if isinstance(noradIndices, list):
            if not noradIndices:
                return
            noradIndices = noradIndices[0]
        if noradIndices is None:
            self.activeObjects.clearSelection()
            self.activeObjectsChanged.emit()
            return
        obj = self.activeObjects.getObjectByNoradIndex(noradIndices)
        if obj is None:
            return
        self.activeObjects.setSelectedObjects({obj}, groupName=None)
        self.treeWidget.blockSignals(True)
        self.treeWidget.clearSelection()
        found = False
        for i in range(self.treeWidget.topLevelItemCount()):
            topItem = self.treeWidget.topLevelItem(i)
            for j in range(topItem.childCount()):
                child = topItem.child(j)
                data = child.data(0, Qt.UserRole)
                if isinstance(data, tuple) and data[0] == "OBJECT" and data[1].noradIndex == noradIndices:
                    child.setSelected(True)
                    self.treeWidget.setCurrentItem(child)
                    self.treeWidget.scrollToItem(child)
                    found = True
                    break
            if found:
                break
        self.treeWidget.blockSignals(False)
        self.activeObjectsChanged.emit()

    def dragMoveEvent(self, event):
        targetItem = self.treeWidget.itemAt(event.pos())
        if not targetItem or targetItem.parent() is not None:
            event.ignore()
            return
        targetData = targetItem.data(0, Qt.UserRole)
        if targetData == "UNGROUPED_ROOT":
            event.accept()
            return
        if isinstance(targetData, tuple) and targetData[0] == "GROUP":
            event.accept()
            return
        event.ignore()

    def dropEvent(self, event):
        targetItem = self.treeWidget.itemAt(event.pos())
        if not targetItem:
            event.ignore()
            return
        draggedItems = self.treeWidget.selectedItems()
        if not draggedItems:
            event.ignore()
            return
        draggedData = draggedItems[0].data(0, Qt.UserRole)
        if not (isinstance(draggedData, tuple) and draggedData[0] == "OBJECT"):
            event.ignore()
            return
        obj = draggedData[1]
        targetData = targetItem.data(0, Qt.UserRole)
        if isinstance(targetData, tuple) and targetData[0] == "GROUP":
            self.activeObjects.moveToGroup(targetData[1], obj)
        elif targetData == "UNGROUPED_ROOT":
            self.activeObjects.moveToUngrouped(obj)
        else:
            event.ignore()
            return
        self.populate(self.tleDatabase, self.activeObjects.toDict())
        self.activeObjectsChanged.emit()
        event.acceptProposedAction()

    def _showContextMenu(self, position: QPoint):
        item = self.treeWidget.itemAt(position)
        menu = QMenu(self)
        if item is None:
            menu.addAction("Add objects...", self.openAddDialog)
            menu.addAction("Create new group...", self._createNewGroup)
        else:
            data = item.data(0, Qt.UserRole)
            if data == "UNGROUPED_ROOT":
                menu.addAction("Add objects...", self.openAddDialog)
                menu.addAction("Create new group...", self._createNewGroup)
            elif isinstance(data, tuple):
                if data[0] == "GROUP":
                    groupName = data[1]
                    menu.addAction("Rename group...", lambda: self._renameGroup(groupName))
                    menu.addAction("Change color...", lambda: self._changeGroupColor(groupName))
                    menu.addAction("Delete group...", lambda: self._deleteGroup(groupName))
                    menu.addSeparator()
                    menu.addAction("Add object to this group...", lambda: self._addObjectToSpecificGroup(groupName))
                elif data[0] == "OBJECT":
                    obj = data[1]
                    currentGroup = self.activeObjects.getGroupForNoradIndex(obj.noradIndex)
                    moveMenu = menu.addMenu("Move to...")
                    moveMenu.addAction("Ungrouped", lambda: self._moveObject(obj, None))
                    for gName in self.activeObjects.objectGroups.keys():
                        if gName != currentGroup:
                            moveMenu.addAction(f"→ {gName}", lambda gn=gName: self._moveObject(obj, gn))
                    menu.addAction("Remove object", lambda: self._removeObject(obj))
        menu.exec_(self.treeWidget.viewport().mapToGlobal(position))

    def _createNewGroup(self):
        name, ok = QInputDialog.getText(self, "New Group", "Enter group name:")
        if ok and name.strip():
            try:
                self.activeObjects.addGroup(name.strip())
                self.populate(self.tleDatabase, self.activeObjects.toDict())
                self.activeObjectsChanged.emit()
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _renameGroup(self, oldName: str):
        newName, ok = QInputDialog.getText(self, "Rename Group", "New name:", text=oldName)
        if ok and newName.strip() and newName != oldName:
            group = self.activeObjects.objectGroups.pop(oldName)
            group.name = newName.strip()  # update internal name too
            self.activeObjects.objectGroups[newName.strip()] = group
            self.populate(self.tleDatabase, self.activeObjects.toDict())
            self.activeObjectsChanged.emit()

    def _changeGroupColor(self, groupName: str):
        group = self.activeObjects.objectGroups.get(groupName)
        if not group:
            return
        color = QColorDialog.getColor(QColor(group.color), self)
        if color.isValid():
            group.color = color.name()
            self.populate(self.tleDatabase, self.activeObjects.toDict())
            self.activeObjectsChanged.emit()

    def _deleteGroup(self, groupName: str):
        reply = QMessageBox.question(self, "Delete Group", f"Delete group '{groupName}'? Objects will move to Ungrouped.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.activeObjects.removeGroup(groupName)
            self.populate(self.tleDatabase, self.activeObjects.toDict())
            self.activeObjectsChanged.emit()

    def _addObjectToSpecificGroup(self, groupName: str):
        if self.tleDatabase is None:
            return
        dialog = AddObjectDialog(self.tleDatabase, self)
        if dialog.exec_() and dialog.selectedNoradIndices:
            for noradIndex in dialog.selectedNoradIndices:
                objectName = self._getNameFromDatabase(noradIndex)
                obj = NoradObject(noradIndex, objectName)
                self.activeObjects.addToGroup(groupName, obj)
            self.populate(self.tleDatabase, self.activeObjects.toDict())
            self.activeObjectsChanged.emit()

    def _moveObject(self, obj: NoradObject, targetGroupName: str | None):
        if targetGroupName is None:
            self.activeObjects.moveToUngrouped(obj)
        else:
            self.activeObjects.moveToGroup(targetGroupName, obj)

    def _removeObject(self, obj: NoradObject):
        self.activeObjects.removeNoradIndexEverywhere(obj.noradIndex)
        self.populate(self.tleDatabase, self.activeObjects.toDict())
        self.activeObjectsChanged.emit()

    def _onItemChanged(self, item: QTreeWidgetItem, column: int):
        if column != 1:
            return
        data = item.data(0, Qt.UserRole)
        if isinstance(data, tuple) and data[0] == "GROUP":
            groupName = data[1]
            visible = item.checkState(1) == Qt.Checked
            if groupName in self.activeObjects.objectGroups:
                self.activeObjects.objectGroups[groupName].visible = visible
                self.activeObjectsChanged.emit()

    def _onItemExpanded(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.UserRole)
        if data == "UNGROUPED_ROOT":
            self.activeObjects.ungroupedExpanded = True
            return
        if isinstance(data, tuple) and data[0] == "GROUP":
            self.activeObjects.objectGroups[data[1]].expanded = True

    def _onItemCollapsed(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.UserRole)
        if data == "UNGROUPED_ROOT":
            self.activeObjects.ungroupedExpanded = False
            return
        if isinstance(data, tuple) and data[0] == "GROUP":
            self.activeObjects.objectGroups[data[1]].expanded = False

    def openAddDialog(self):
        if self.tleDatabase is None:
            return
        dialog = AddObjectDialog(self.tleDatabase, self)
        if dialog.exec_() and dialog.selectedNoradIndices:
            for norad in dialog.selectedNoradIndices:
                if norad not in self.activeObjects.allNoradIndices():
                    name = self._getNameFromDatabase(norad)
                    obj = NoradObject(norad, name)
                    self.activeObjects.addToUngrouped(obj)
            self.populate(self.tleDatabase, self.activeObjects.toDict())
            self.activeObjectsChanged.emit()

    def addItems(self, database, noradIndices: list):
        self.tleDatabase = database
        for norad in noradIndices:
            if norad not in self.activeObjects.allNoradIndices():
                name = self._getNameFromDatabase(norad)
                obj = NoradObject(norad, name)
                self.activeObjects.addToUngrouped(obj)
        self.populate(self.tleDatabase, self.activeObjects.toDict())
        self.activeObjectsChanged.emit()

    def _getNameFromDatabase(self, norad: int) -> str:
        row = self.tleDatabase.dataFrame[self.tleDatabase.dataFrame['NORAD_CAT_ID'] == norad]
        if row.empty:
            return str(norad)
        return row.iloc[0]['OBJECT_NAME']

    def getActiveObjectsModel(self):
        return self.activeObjects

    def toSettingsDict(self):
        return {'ACTIVE_OBJECTS_MODEL': self.activeObjects.toDict()}

    def _filterTree(self, text: str):
        text = text.lower().strip()
        for i in range(self.treeWidget.topLevelItemCount()):
            topItem = self.treeWidget.topLevelItem(i)
            anyChildVisible = False
            for j in range(topItem.childCount()):
                child = topItem.child(j)
                objectName = child.text(0).lower()
                noradIndex = child.text(1).lower()
                match = text in objectName or text in noradIndex
                child.setHidden(not match)
                if match:
                    anyChildVisible = True
            if topItem.data(0, Qt.UserRole) == "UNGROUPED_ROOT":
                topItem.setHidden(False)
            else:
                topItem.setHidden(not anyChildVisible)


class AddObjectDialog(QDialog):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Objects')
        self.resize(400, 500)
        self.database = database
        self.selectedNoradIndices = []

        # LIST & SEARCH BAR
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText('Search Objects…')
        self.searchBar.textChanged.connect(self.filterList)
        self.listWidget = QListWidget()
        self.listWidget.setSelectionMode(QListWidget.MultiSelection)

        # BUTTON BAR
        buttonBar = QHBoxLayout()
        addButton = QPushButton('Add')
        cancelButton = QPushButton('Cancel')
        addButton.clicked.connect(self.acceptSelection)
        cancelButton.clicked.connect(self.reject)
        buttonBar.addStretch()
        buttonBar.addWidget(addButton)
        buttonBar.addWidget(cancelButton)
        # DIALOG LAYOUT
        layout = QVBoxLayout(self)
        layout.addWidget(self.searchBar)
        layout.addWidget(self.listWidget)
        layout.addLayout(buttonBar)
        self._populate()

    def _populate(self):
        self.listWidget.clear()
        rows = self.database.dataFrame.sort_values('OBJECT_NAME')
        for _, row in rows.iterrows():
            name, noradIndex = row['OBJECT_NAME'], row['NORAD_CAT_ID']
            text = f'{name} — {noradIndex}'
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, noradIndex)
            item.setData(Qt.UserRole + 1, f'{name.lower()} {noradIndex}')
            self.listWidget.addItem(item)

    def filterList(self, text):
        text = text.lower().strip()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            item.setHidden(text not in item.text().lower())

    def acceptSelection(self):
        self.selectedNoradIndices = [item.data(Qt.UserRole) for item in self.listWidget.selectedItems()]
        self.accept()


class ObjectInfoDockWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__('Object Info', parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self._labels = {}
        self._setupUi()

    def _setupUi(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._createGroup('Identification', [('Name', 'OBJECT_NAME'), ('NORAD ID', 'NORAD_CAT_ID'), ('COSPAR ID', 'OBJECT_ID'), ]))
        layout.addWidget(self._createGroup('Status', [("Object Type", "OBJECT_TYPE"), ('Owner', 'OWNER'), ('Operational Status', 'OPS_STATUS_CODE'), ]))
        layout.addWidget(self._createGroup('Orbit (TLE)', [('Inclination (deg)', 'INCLINATION'), ('Eccentricity', 'ECCENTRICITY'), ('Mean Motion (rev/day)', 'MEAN_MOTION'), ('B*', 'BSTAR'), ]))
        layout.addStretch()
        self.setWidget(container)

    def _createGroup(self, title, fields):
        groupBox = QGroupBox(title)
        formLayout = QFormLayout()
        for labelText, fieldKey in fields:
            label = QLabel("---")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            formLayout.addRow(QLabel(labelText + ":"), label)
            self._labels[fieldKey] = label
        groupBox.setLayout(formLayout)
        return groupBox

    def clear(self):
        for label in self._labels.values():
            label.setText("---")

    def setObject(self, row):
        if row is None:
            self.clear()
            return
        for key, label in self._labels.items():
            value = row.get(key, None)
            if value is None or value == "":
                label.setText("—")
            else:
                label.setText(str(value))


class ObjectViewConfigDockWidget(QDockWidget):
    objectConfigChanged = pyqtSignal(int, dict)
    groupConfigChanged = pyqtSignal(str, dict)
    MODES = {'Always': "ALWAYS", 'When Selected': "WHEN_SELECTED", 'Never': "NEVER"}

    def __init__(self, parent=None):
        super().__init__("3D View Configuration", parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.activeObjects = ActiveObjectsModel()
        self.noradIndex = None
        self.groupName = None
        self._currentConfig = None
        self._isGroupMode = False
        self._loading = False
        self._viewMode = '2D'
        self._setupUi()

    def _setupUi(self):
        # -------- GROUP MODE HEADER
        self.shareCheckBox = QCheckBox("Share Configuration")
        self.shareCheckBox.setChecked(True)
        self.shareCheckBox.toggled.connect(self._onShareToggled)
        self.sourceCombo = QComboBox()
        self.sourceCombo.addItem("Custom shared config", "CUSTOM")
        self.sourceCombo.addItem("Copy from object", "OBJECT")
        self.sourceCombo.currentIndexChanged.connect(self._onSourceChanged)
        self.objectSourceCombo = QComboBox()
        self.objectSourceCombo.currentIndexChanged.connect(self._onEditorChanged)

        self.groupSharingHeader = QGroupBox("Group Configuration")
        self.groupSharingHeader.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        headerLayout = QFormLayout(self.groupSharingHeader)
        headerLayout.setLabelAlignment(Qt.AlignRight)
        headerLayout.addRow(self.shareCheckBox)
        headerLayout.addRow("Source:", self.sourceCombo)
        headerLayout.addRow("Object:", self.objectSourceCombo)

        # -------- CONFIGURATION WIDGET
        self.spotColorButton = self._colorButton()
        self.spotSizeSpin = QSpinBox()
        self.spotSizeSpin.setRange(4, 30)
        self.spotSizeSpin.setToolTip("Spot Size")
        self.spotGroup = self._groupBox("Spot")
        self.spotGroup.layout().addWidget(self.spotColorButton, 0, 0)
        self.spotGroup.layout().addWidget(self.spotSizeSpin, 0, 1)

        self.orbitPathGroup = self._groupBox("Orbital Path")
        self.orbitModeCombo = QComboBox()
        self.orbitModeCombo.addItems(list(self.MODES.keys()))
        self.orbitModeCombo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.orbitColorButton = self._colorButton()
        self.orbitWidthSpin = QSpinBox()
        self.orbitWidthSpin.setRange(1, 6)
        self.orbitWidthSpin.setToolTip("Line Width")
        self.orbitPathGroup.layout().addWidget(self.orbitModeCombo, 0, 0)
        self.orbitPathGroup.layout().addWidget(self.orbitColorButton, 0, 1)
        self.orbitPathGroup.layout().addWidget(self.orbitWidthSpin, 0, 2)

        self.groundTrackGroup = self._groupBox("Ground Track")
        self.groundTrackModeCombo = QComboBox()
        self.groundTrackModeCombo.addItems(self.MODES.keys())
        self.groundTrackColorButton = self._colorButton()
        self.groundTrackWidthSpin = QSpinBox()
        self.groundTrackWidthSpin.setRange(1, 5)
        self.groundTrackGroup.layout().addWidget(self.groundTrackModeCombo, 0, 0)
        self.groundTrackGroup.layout().addWidget(self.groundTrackColorButton, 0, 1)
        self.groundTrackGroup.layout().addWidget(self.groundTrackWidthSpin, 0, 2)

        self.footprintGroup = self._groupBox("Visibility Footprint")
        self.footprintModeCombo = QComboBox()
        self.footprintModeCombo.addItems(self.MODES.keys())
        self.footprintColorButton = self._colorButton()
        self.footprintWidthSpin = QSpinBox()
        self.footprintWidthSpin.setRange(1, 5)
        self.footprintGroup.layout().addWidget(self.footprintModeCombo, 0, 0)
        self.footprintGroup.layout().addWidget(self.footprintColorButton, 0, 1)
        self.footprintGroup.layout().addWidget(self.footprintWidthSpin, 0, 2)

        self.configEditorWidget = QWidget()
        self.configEditorWidget.setEnabled(False)
        configEditorLayout = QVBoxLayout(self.configEditorWidget)
        configEditorLayout.setSpacing(10)
        configEditorLayout.setContentsMargins(0, 0, 0, 0)
        configEditorLayout.addWidget(self.spotGroup)
        configEditorLayout.addWidget(self.orbitPathGroup)
        configEditorLayout.addWidget(self.groundTrackGroup)
        configEditorLayout.addWidget(self.footprintGroup)

        self.spotSizeSpin.valueChanged.connect(self._onEditorChanged)
        self.orbitModeCombo.currentIndexChanged.connect(self._onEditorChanged)
        self.orbitWidthSpin.valueChanged.connect(self._onEditorChanged)
        self.groundTrackModeCombo.currentIndexChanged.connect(self._onEditorChanged)
        self.groundTrackWidthSpin.valueChanged.connect(self._onEditorChanged)
        self.footprintModeCombo.currentIndexChanged.connect(self._onEditorChanged)
        self.footprintWidthSpin.valueChanged.connect(self._onEditorChanged)
        self.spotColorButton.clicked.connect(lambda: self._pickColor('SPOT'))
        self.groundTrackColorButton.clicked.connect(lambda: self._pickColor('GROUND_TRACK'))
        self.footprintColorButton.clicked.connect(lambda: self._pickColor('FOOTPRINT'))
        self.orbitColorButton.clicked.connect(lambda: self._pickColor('ORBIT_PATH'))

        # MAIN LAYOUT
        container = QWidget()
        mainLayout = QVBoxLayout(container)
        mainLayout.setContentsMargins(8, 8, 8, 8)
        mainLayout.addWidget(self.groupSharingHeader)
        mainLayout.addWidget(self.configEditorWidget)
        mainLayout.addStretch()
        self.setWidget(container)

    def setViewMode(self, mode: str):
        self._viewMode = mode
        is2D = mode == "2D"
        self.spotGroup.setVisible(True)
        self.groundTrackGroup.setVisible(is2D)
        self.footprintGroup.setVisible(is2D)
        self.orbitPathGroup.setVisible(not is2D)
        self._updateTitle()
        self.configEditorWidget.adjustSize()
        self.configEditorWidget.updateGeometry()

    def _updateTitle(self):
        if self.noradIndex is not None:
            self.setWindowTitle(f"{self._viewMode} View Configuration — Object {self.noradIndex}")
        elif self.groupName is not None:
            self.setWindowTitle(f"{self._viewMode} View Configuration — Group {self.groupName}")
        else:
            self.setWindowTitle(f"{self._viewMode} View Configuration — None")

    def setActiveObjects(self, activeObjects: ActiveObjectsModel):
        self.activeObjects = activeObjects

    def _onShareToggled(self, checked: bool):
        self._updateUIState()
        self._emitGroupConfig()

    def _onSourceChanged(self, index: int):
        self.objectSourceCombo.setEnabled(index == 1)
        if index == 1:
            self._refreshObjectSourceCombo()
        self._updateUIState()
        self._onEditorChanged()

    def _onObjectSourceChanged(self, index: int):
        if not self.signalsBlocked():
            self._onEditorChanged()

    def _updateUIState(self):
        if not self._isGroupMode:
            self.configEditorWidget.setVisible(True)
            self.groupSharingHeader.setVisible(False)
            enabled = self.noradIndex is not None
        else:
            self.groupSharingHeader.setVisible(True)
            shared = self.shareCheckBox.isChecked()
            sourceIsCustom = self.sourceCombo.currentData() == 'CUSTOM'
            self.sourceCombo.setEnabled(shared)
            self.objectSourceCombo.setEnabled(shared and not sourceIsCustom)
            self.configEditorWidget.setVisible(sourceIsCustom)
            enabled = shared and sourceIsCustom
        self.configEditorWidget.setEnabled(enabled)

    @staticmethod
    def _colorButton():
        colorButton = QPushButton()
        colorButton.setFixedSize(24, 24)
        colorButton.setStyleSheet("border: 1px solid #666;")
        return colorButton

    @staticmethod
    def _groupBox(title: str):
        box = QGroupBox(title)
        box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = QGridLayout(box)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        layout.setContentsMargins(8, 12, 8, 8)
        return box

    @staticmethod
    def _setButtonColor(colorButton, color):
        colorButton.setStyleSheet(f"background-color: rgb({color[0]},{color[1]},{color[2]}); border: 1px solid #666;")

    def _modeToLabel(self, mode):
        for label, value in self.MODES.items():
            if value == mode:
                return label
        return "Never"

    def setSelectedObject(self, noradIndex: int | None, config: dict):
        self._isGroupMode = False
        self.groupName = None
        self.noradIndex = noradIndex
        self._loading = True
        try:
            if noradIndex is None:
                self._clearAllUI()
                return
            self._currentConfig = copy.deepcopy(config[str(noradIndex)])
            self._normalizeConfig(self._currentConfig)
            self._updateTitle()
            self._loadConfigIntoUI(self._currentConfig)
            self._updateUIState()
        finally:
            self._loading = False

    def setSelectedGroup(self, groupName: str):
        self._isGroupMode = True
        self.groupName = groupName
        self.noradIndex = None
        group = self.activeObjects.objectGroups.get(groupName)
        if not group:
            return
        defaultConfig = giveDefaultGroupViewConfig()
        groupConfig = group.renderRules
        self._loading = True
        try:
            self._currentConfig = copy.deepcopy(groupConfig.get('CONFIG', defaultConfig))
            self._normalizeConfig(self._currentConfig)
            self._updateTitle()
            self.shareCheckBox.setChecked(groupConfig.get('SHARED', True))
            source = groupConfig.get('SOURCE', 'CUSTOM')
            idx = self.sourceCombo.findData(source)
            if idx != -1:
                self.sourceCombo.setCurrentIndex(idx)
            self._refreshObjectSourceCombo()
            sourceObject = groupConfig.get('SOURCE_OBJECT')
            if sourceObject is not None:
                idx = self.objectSourceCombo.findData(sourceObject)
                self.objectSourceCombo.setCurrentIndex(idx if idx != -1 else -1)
            if source == "CUSTOM":
                self._loadConfigIntoUI(self._currentConfig)
            self._updateUIState()
        finally:
            self._loading = False

    def _clearAllUI(self):
        self.noradIndex = None
        self.groupName = None
        self._currentConfig = None
        self.configEditorWidget.setEnabled(False)
        self._loading = True
        try:
            self.spotSizeSpin.setValue(10)
            self.groundTrackWidthSpin.setValue(1)
            self.footprintWidthSpin.setValue(1)
            self.orbitWidthSpin.setValue(1)
            gray = (100, 100, 100)
            self._setButtonColor(self.spotColorButton, gray)
            self._setButtonColor(self.groundTrackColorButton, gray)
            self._setButtonColor(self.footprintColorButton, gray)
            self._setButtonColor(self.orbitColorButton, gray)
            self.sourceCombo.setCurrentIndex(0)
            self.objectSourceCombo.clear()
            self._updateTitle()
        finally:
            self._loading = False

    def _pickColor(self, section):
        if self._currentConfig is None:
            return
        color = QColorDialog.getColor()
        if not color.isValid():
            return
        rgb = (color.red(), color.green(), color.blue())
        if section not in self._currentConfig:
            self._currentConfig[section] = {}
        self._currentConfig[section]['COLOR'] = rgb
        buttonMap = {'SPOT': self.spotColorButton, 'GROUND_TRACK': self.groundTrackColorButton,
                     'FOOTPRINT': self.footprintColorButton, 'ORBIT_PATH': self.orbitColorButton}
        self._setButtonColor(buttonMap[section], rgb)
        self._onEditorChanged()

    def _refreshObjectSourceCombo(self):
        self.objectSourceCombo.clear()
        if not self._isGroupMode or not self.groupName:
            return
        group = self.activeObjects.objectGroups.get(self.groupName)
        if not group:
            return
        for obj in sorted(group.objects, key=lambda o: o.noradIndex):
            self.objectSourceCombo.addItem(f"{obj.name} — {obj.noradIndex}", obj.noradIndex)

    def _onEditorChanged(self, *_):
        if self._loading:
            return
        if self._isGroupMode:
            self._emitGroupConfig()
        else:
            self._emitObjectConfig()

    def _emitObjectConfig(self):
        if not self._currentConfig or self.noradIndex is None:
            return
        configuration = self._currentConfig
        configuration['SPOT']['SIZE'] = self.spotSizeSpin.value()
        if self._viewMode == "2D":
            configuration['GROUND_TRACK']['MODE'] = self.MODES[self.groundTrackModeCombo.currentText()]
            configuration['GROUND_TRACK']['WIDTH'] = self.groundTrackWidthSpin.value()
            configuration['FOOTPRINT']['MODE'] = self.MODES[self.footprintModeCombo.currentText()]
            configuration['FOOTPRINT']['WIDTH'] = self.footprintWidthSpin.value()
        else:
            configuration['ORBIT_PATH']['MODE'] = self.MODES[self.orbitModeCombo.currentText()]
            configuration['ORBIT_PATH']['WIDTH'] = self.orbitWidthSpin.value()
        self.objectConfigChanged.emit(self.noradIndex, configuration)

    def _emitGroupConfig(self):
        if not self._currentConfig or not self.groupName:
            return
        shared, source = self.shareCheckBox.isChecked(), self.sourceCombo.currentData()
        sourceObject = self.objectSourceCombo.currentData() if source == "OBJECT" else None
        configuration = None
        if shared and source == "CUSTOM" and self._currentConfig:
            configuration = copy.deepcopy(self._currentConfig)
        self.groupConfigChanged.emit(self.groupName, {"SHARED": shared, "SOURCE": source, "SOURCE_OBJECT": sourceObject, "CONFIG": configuration})

    def _loadConfigIntoUI(self, config):
        if not config:
            return
        self._loading = True
        try:
            self._normalizeConfig(config)
            spot, groundTrack, footprint, orbitPath = config['SPOT'], config['GROUND_TRACK'], config['FOOTPRINT'], config['ORBIT_PATH']
            self.spotSizeSpin.setValue(spot['SIZE'])
            self._setButtonColor(self.spotColorButton, spot['COLOR'])
            self.groundTrackModeCombo.setCurrentText(self._modeToLabel(groundTrack['MODE']))
            self.groundTrackWidthSpin.setValue(groundTrack['WIDTH'])
            self._setButtonColor(self.groundTrackColorButton, groundTrack['COLOR'])
            self.footprintModeCombo.setCurrentText(self._modeToLabel(footprint['MODE']))
            self.footprintWidthSpin.setValue(footprint['WIDTH'])
            self._setButtonColor(self.footprintColorButton, footprint['COLOR'])
            self.orbitModeCombo.setCurrentText(self._modeToLabel(orbitPath['MODE']))
            self.orbitWidthSpin.setValue(orbitPath['WIDTH'])
            self._setButtonColor(self.orbitColorButton, orbitPath['COLOR'])
        finally:
            self._loading = False

    def applyGlobalVisibility(self, viewConfig: dict, currentTab: str):
        is2D = currentTab == '2D_MAP'
        showOrbitPaths, showGroundTracks, showFootprints = True, True, True
        if is2D:
            showGroundTracks = viewConfig['2D_MAP'].get('SHOW_GROUND_TRACKS', True)
            showFootprints = viewConfig['2D_MAP'].get('SHOW_FOOTPRINTS', True)
        else:
            showOrbitPaths = viewConfig['3D_VIEW'].get('SHOW_ORBIT_PATHS', True)
        self.groundTrackGroup.setEnabled(showGroundTracks and is2D)
        self.footprintGroup.setEnabled(showFootprints and is2D)
        self.orbitPathGroup.setEnabled(showOrbitPaths and not is2D)
        self.configEditorWidget.update()

    @staticmethod
    def _normalizeConfig(configuration):
        configuration.setdefault('SPOT', {})
        configuration['SPOT'].setdefault('SIZE', 10)
        configuration['SPOT'].setdefault('COLOR', (255, 255, 255))
        configuration.setdefault('GROUND_TRACK', {})
        configuration.setdefault('FOOTPRINT', {})
        configuration['GROUND_TRACK'].setdefault('MODE', "NEVER")
        configuration['GROUND_TRACK'].setdefault('WIDTH', 1)
        configuration['GROUND_TRACK'].setdefault('COLOR', (255, 255, 255))
        configuration['FOOTPRINT'].setdefault('MODE', "NEVER")
        configuration['FOOTPRINT'].setdefault('WIDTH', 1)
        configuration['FOOTPRINT'].setdefault('COLOR', (255, 255, 255))
        configuration.setdefault('ORBIT_PATH', {})
        configuration['ORBIT_PATH'].setdefault('MODE', "NEVER")
        configuration['ORBIT_PATH'].setdefault('WIDTH', 1)
        configuration['ORBIT_PATH'].setdefault('COLOR', (255, 255, 255))
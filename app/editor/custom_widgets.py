from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import QSize

# Custom Widgets
from app.data.database import DB

from app.editor.custom_gui import PropertyBox, ComboBox
from app.editor.unit_database import UnitModel
from app.editor.class_database import ClassModel
from app.editor.faction_database import FactionModel

class UnitBox(PropertyBox):
    def __init__(self, parent=None, button=False):
        super().__init__("Unit", ComboBox, parent)
        self.model = UnitModel(DB.units, parent)
        self.edit.setModel(self.model)
        self.edit.setIconSize(QSize(32, 32))
        if button:
            b = QPushButton('...')
            b.setMaximumWidth(40)
            self.add_button(b)

class ClassBox(PropertyBox):
    def __init__(self, parent=None, button=False):
        super().__init__("Class", ComboBox, parent)
        self.model = ClassModel(DB.classes, parent)
        self.edit.setModel(self.model)
        if button:
            b = QPushButton('...')
            b.setMaximumWidth(40)
            self.add_button(b)

class FactionBox(PropertyBox):
    def __init__(self, parent=None, button=False):
        super().__init__("Faction", ComboBox, parent)
        self.model = FactionModel(DB.factions, parent)
        self.edit.setModel(self.model)
        if button:
            b = QPushButton('...')
            b.setMaximumWidth(40)
            self.add_button(b)

class MovementTypeBox(PropertyBox):
    def __init__(self, parent=None, button=False):
        from app.editor.mcost_dialog import MovementTypeModel
        super().__init__("Movement Type", ComboBox, parent)
        self.model = MovementTypeModel(DB.mcost.row_headers, parent)
        self.edit.setModel(self.model)
        if button:
            b = QPushButton('...')
            b.setMaximumWidth(40)
            self.add_button(b)

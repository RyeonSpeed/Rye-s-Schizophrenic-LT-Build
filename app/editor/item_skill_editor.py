from __future__ import annotations

import json
import logging
import os
from typing import Dict, Generic, List, Optional, Type, TypeVar

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QFileDialog, QGridLayout, QVBoxLayout,
                             QHBoxLayout, QMessageBox, QPushButton, QSplitter,
                             QWidget)

import app.engine.item_component_access as ICA
import app.engine.skill_component_access as SCA
from app.data.category import Categories, CategorizedCatalog
from app.data.database.database import DB, Database
from app.data.database.items import ItemCatalog, ItemPrefab
from app.data.database.skills import SkillCatalog, SkillPrefab
from app.editor import timer
from app.editor.data_editor import SingleDatabaseEditor
from app.editor.item_skill_properties import NewComponentProperties
from app.editor.item_editor import item_import, item_model
from app.editor.lib.components.nested_list import LTNestedList
from app.editor.settings.main_settings_controller import MainSettingsController
from app.editor.skill_editor import skill_model
from app.utilities import str_utils
from app.utilities.typing import NID

T = TypeVar('T', bound=CategorizedCatalog)

class ItemSkillEditor(QWidget, Generic[T]):
    catalog_type: Type[T]

    def __init__(self, parent, database: Database) -> None:
        QWidget.__init__(self, parent)
        self._db = database
        self.categories = self.data.categories

        self.left_frame = QWidget()
        left_frame_layout = QVBoxLayout()
        self.left_frame.setLayout(left_frame_layout)
        self.tree_list = LTNestedList(self, self.data.keys(), self.categories, self.get_icon,
                                      self.on_select, self.resort_db, self.delete_from_db, self.create_new,
                                      self.duplicate)
        left_frame_layout.addWidget(self.tree_list)

        button_frame = QWidget()
        button_frame_layout = QGridLayout(button_frame)
        import_csv_button = QPushButton("Import .csv")
        import_csv_button.clicked.connect(self.import_csv)
        button_frame_layout.addWidget(import_csv_button, 0, 0, 1, 4)
        copy_to_clipboard_button = QPushButton("Copy to clipboard")
        copy_to_clipboard_button.clicked.connect(self.copy_to_clipboard)
        button_frame_layout.addWidget(copy_to_clipboard_button, 1, 0, 1, 2)
        paste_from_clipboard_button = QPushButton("Paste from clipboard")
        paste_from_clipboard_button.clicked.connect(self.paste_from_clipboard)
        button_frame_layout.addWidget(paste_from_clipboard_button, 1, 2, 1, 2)
        left_frame_layout.addWidget(button_frame)
        self.right_frame = NewItemProperties(self, None, self.attempt_change_nid, lambda: self.tree_list.regenerate_icons(True))
        self.splitter = QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.left_frame)
        self.splitter.addWidget(self.right_frame)
        self.splitter.setStyleSheet(
            "QSplitter::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eee, stop:1 #ccc); border: 1px solid #777; width: 13px; margin-top: 2px; margin-bottom: 2px; border-radius: 4px;}")

        self._layout = QHBoxLayout(self)
        self.setLayout(self._layout)

        self._layout.addWidget(self.splitter)

    @property
    def data(self) -> T:
        raise NotImplementedError("This class must be extended and this method overriden.")

    @classmethod
    def edit(cls, parent=None):
        raise NotImplementedError("This class must be extended and this method overriden.")

    def get_icon(self, nid) -> Optional[QIcon]:
        raise NotImplementedError("This class must be extended and this method overriden.")

    def import_csv(self):
        raise NotImplementedError("This class must be extended and this method overriden.")

    def reset(self):
        self.tree_list.reset(self.data.keys(), self.categories)

    def attempt_change_nid(self, old_nid: NID, new_nid: NID) -> bool:
        if old_nid == new_nid:
            return True
        if self.data.get(new_nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % new_nid)
            return False
        self.data.change_key(old_nid, new_nid)
        self.tree_list.update_nid(old_nid, new_nid)
        return True

    def on_select(self, entry_nid: Optional[NID]):
        if not entry_nid:
            self.right_frame.set_current(None)
            return
        curr_entry = self.data.get(entry_nid)
        if curr_entry:
            self.right_frame.set_current(curr_entry)

    def resort_db(self, entries: List[str], categories: Categories):
        self.data.categories = categories
        self.data.sort(lambda x: entries.index(x.nid) if x.nid in entries else -1)

    def delete_from_db(self, nid):
        self.data.remove_key(nid)
        return True

    def create_new(self, nid):
        if self.data.get(nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % nid)
            return False
        new_obj = self.catalog_type.datatype(nid, nid, '')
        self.data.append(new_obj)
        return True

    def duplicate(self, old_nid, nid):
        if self.data.get(nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % nid)
            return False
        orig_obj = self.data.get(old_nid)
        if not orig_obj:
            QMessageBox.warning(self, 'Warning', 'ID %s not found' % old_nid)
            return False
        orig_obj = self.catalog_type.datatype.restore(orig_obj.save())
        orig_obj.nid = nid
        self.data.append(orig_obj)
        return True

    def copy_to_clipboard(self):
        selected_nid = self.tree_list.get_selected_item()
        if selected_nid:
            clipboard = QApplication.clipboard()
            prefab = self.data.get(selected_nid)
            if prefab:
                json_string = json.dumps([prefab.save()])
                clipboard.setText(json_string)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        json_string = clipboard.text()
        try:
            any_nid = None
            ser_list = json.loads(json_string)
            for ser_dict in reversed(ser_list):
                prefab = self.data.datatype.restore(ser_dict)
                prefab.nid = str_utils.get_next_name(prefab.nid, self.data.keys())
                self.data.append(prefab)
                any_nid = prefab.nid
            self.reset()
            if any_nid:
                self.tree_list.select_item(any_nid)
        except Exception as e:
            logging.warning("Could not read from clipboard! %s" % e)
            QMessageBox.critical(self, "Import Error", "Could not read valid json from clipboard!")

    # @todo(mag) fix the unit tab (which is the only time this callback is used forcibly in data_editor.py) and remove this
    def on_tab_close(self):
        pass

    @classmethod
    def create(cls, parent=None, db=None):
        db = db or DB
        return cls(parent, db)

class NewItemProperties(NewComponentProperties[ItemPrefab]):
    title = "Item"
    get_components = staticmethod(ICA.get_item_components)
    get_templates = staticmethod(ICA.get_templates)
    get_tags = staticmethod(ICA.get_item_tags)

class NewSkillProperties(NewComponentProperties[SkillPrefab]):
    title = "Skill"
    get_components = staticmethod(SCA.get_skill_components)
    get_templates = staticmethod(SCA.get_templates)
    get_tags = staticmethod(SCA.get_skill_tags)

class NewItemDatabase(ItemSkillEditor):
    catalog_type = ItemCatalog

    @classmethod
    def edit(cls, parent=None):
        timer.get_timer().stop_for_editor()  # Don't need these while running game
        window = SingleDatabaseEditor(NewItemDatabase, parent)
        window.exec_()
        timer.get_timer().start_for_editor()

    @property
    def data(self):
        return self._db.items

    def get_icon(self, item_nid) -> Optional[QIcon]:
        pix = item_model.get_pixmap(self.data.get(item_nid))
        if pix:
            return QIcon(pix.scaled(32, 32))
        return None

    def import_csv(self):
        settings = MainSettingsController()
        starting_path = settings.get_last_open_path()
        fn, ok = QFileDialog.getOpenFileName(self, "Import items from csv", starting_path, "items csv (*.csv);;All Files(*)")
        if ok and fn:
            parent_dir = os.path.split(fn)[0]
            settings.set_last_open_path(parent_dir)
            item_import.update_db_from_csv(self._db, fn)
            self.reset()

class NewSkillDatabase(ItemSkillEditor):
    catalog_type = SkillCatalog

    @classmethod
    def edit(cls, parent=None):
        timer.get_timer().stop_for_editor()  # Don't need these while running game
        window = SingleDatabaseEditor(NewSkillDatabase, parent)
        window.exec_()
        timer.get_timer().start_for_editor()

    @property
    def data(self):
        return self._db.skills

    def get_icon(self, skill_nid) -> Optional[QIcon]:
        pix = skill_model.get_pixmap(self.data.get(skill_nid))
        if pix:
            return QIcon(pix.scaled(32, 32))
        return None

    def import_csv(self):
        return

# Testing
# Run "python -m app.editor.item_editor.new_item_tab" from main directory
if __name__ == '__main__':
    import sys

    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from app.data.resources.resources import RESOURCES
    DB.load('default.ltproj')
    RESOURCES.load('default.ltproj')
    window = NewItemDatabase(None, DB)
    window.show()
    app.exec_()

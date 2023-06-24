from PyQt5.QtWidgets import QWidget, QLineEdit, QMessageBox, QHBoxLayout, QVBoxLayout, \
    QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt

from app.data.resources.resources import RESOURCES
from app.data.database.database import DB

from app.editor.combat_animation_editor.palette_model import PaletteModel
from app.editor.icon_editor.icon_view import IconView
from app.editor.lib.components.validated_line_edit import NidLineEdit
from app.editor.map_sprite_editor import map_sprite_model
from app.extensions.custom_gui import ComboBox, PropertyBox

from app.utilities import str_utils

class TeamProperties(QWidget):
    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.window = parent
        self._data = self.window._data

        self.current = current

        top_section = QHBoxLayout()

        self.frame_view = IconView(self)
        top_section.addWidget(self.icon_edit)

        horiz_spacer = QSpacerItem(40, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        top_section.addSpacerItem(horiz_spacer)

        top_right_section = QVBoxLayout()

        self.nid_box = PropertyBox("Unique ID", NidLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        top_right_section.addWidget(self.nid_box)

        self.palette_box = PropertyBox("Map Sprite Palette", ComboBox, self)
        model = PaletteModel(RESOURCES.combat_palettes, self)
        self.palette_box.edit.setModel(model)
        self.palette_box.edit.view().setUniformItemSizes(True)
        self.palette_box.edit.activated.connect(self.palette_changed)
        top_right_section.addWidget(self.palette_box)

        top_section.addLayout(top_right_section)

        mid_section = QHBoxLayout()

        self.combat_palette_box = PropertyBox("Combat Palette Default", QLineEdit, self)
        self.combat_palette_box.edit.editingFinished.connect(self.combat_palette_changed)
        mid_section.addWidget(self.combat_palette_box)

        self.color_box = PropertyBox("Combat UI Color", QLineEdit, self)
        self.color_box.edit.editingFinished.connect(self.color_changed)
        mid_section.addWidget(self.color_box)

        self.allies_box = PropertyBox("Allies", MultiSelectComboBox, self)
        self.allies_box.edit.addItems(DB.teams.keys())
        self.allies_box.edit.updated.connect(self.allies_changed)

        total_section = QVBoxLayout()
        self.setLayout(total_section)
        total_section.addLayout(top_section)
        total_section.addLayout(mid_section)
        total_section.addWidget(self.allies_box)

        total_section.setAlignment(Qt.AlignTop)

    def nid_changed(self, text):
        self.current.nid = text
        self.window.update_list()

    def nid_done_editing(self):
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'Team ID %s already in use' % self.current.nid)
            self.current.nid = str_utils.get_next_name(self.current.nid, other_nids)
        self.window.left_frame.model.on_nid_changed(self._data.find_key(self.current), self.current.nid)
        self._data.update_nid(self.current, self.current.nid)
        self.draw_frame()
        self.window.update_list()

    def palette_changed(self):
        self.current.palette = self.palette_box.edit.currentText()
        self.draw_frame()
        self.window.update_list()

    def combat_palette_changed(self, text):
        self.current.combat_palette = text

    def color_changed(self, text):
        self.current.combat_color = text

    def allies_changed(self):
        self.current.set_allies(self.allies_box.edit.currentText())

    def set_current(self, current):
        self.current = current
        self.nid_box.edit.setText(current.nid)
        self.palette_box.edit.setValue(current.palette)
        self.combat_palette_box.edit.setText(current.combat_palette)
        self.color_box.edit.setText(current.combat_color)

        allies = current.allies[:] # Must make a copy
        self.allies_box.edit.clear()
        self.allies_box.edit.addItems(DB.teams.keys())
        self.allies_box.edit.setCurrentTexts(allies)

        if self.current:
            self.draw_frame()

    def draw_frame(self):
        pixmap = RESOURCES.map_sprites[0].standing_pixmap
        pix = map_sprite_model.get_basic_icon(pixmap, 0, team=self.current.nid)
        self.frame_view.set_image(pix)
        self.frame_view.show_image()

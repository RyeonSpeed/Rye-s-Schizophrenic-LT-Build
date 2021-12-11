from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, \
    QWidget, QPushButton, QMessageBox, QLabel, QComboBox, QHBoxLayout, QDialog, QCheckBox
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QPixmap

from app.data.database import DB
from app.resources.resources import RESOURCES

from app.editor.icons import MapIconButton

from app.extensions.custom_gui import ComboBox, SimpleDialog, PropertyBox, PropertyCheckBox, QHLine, RightClickListView
from app.utilities import str_utils
from app.editor.sound_editor import sound_tab
from app.editor.tile_editor import tile_tab
from app.events import node_events
from app.editor.base_database_gui import DragDropCollectionModel
from app.utilities.data import Data

class NodePropertiesMenu(QWidget):
    def __init__(self, state_manager):
        super().__init__()
        self.state_manager = state_manager

        self._initialize_components()

        # widget state
        self.current_node = None
        self.select_node(self.state_manager.state.selected_node)

        # subscriptions
        self.state_manager.subscribe_to_key(NodePropertiesMenu.__name__, 'selected_node', self.select_node)

    def select_node(self, node_nid):
        current_overworld = DB.overworlds.get(self.state_manager.state.selected_overworld)
        if(current_overworld):
            self.current_node = current_overworld.overworld_nodes.get(node_nid)
        else:
            self.current_node = None
        if(self.current_node):
            #The biggest problem with this GUI stuff currently is that the event-specific stuff doesn't go blank on node switch. This has no harmful effect in terms of engine or data, just looks bad visually
            self._data = self.current_node.menu_options
            self.model._data = self._data
            self.model.update()
            self.modify_option_widget._data = self._data
            
            self.set_components_active(True)

            self.nid_box.edit.setText(self.current_node.nid)
            self.title_box.edit.setText(self.current_node.name)
            self.map_icon_selector.set_map_icon_object(RESOURCES.map_icons.get(self.current_node.icon))
            self._populate_level_combo_box(self.level_box.edit)
            self.level_box.edit.setCurrentIndex(self.level_box.edit.findData(self.current_node.level))
        else:
            self._data = Data()
            self.set_components_active(False)

    def set_components_active(self, is_active):
        is_inactive = not is_active
        self.nid_box.setDisabled(is_inactive)
        self.title_box.setDisabled(is_inactive)
        self.level_box.setDisabled(is_inactive)
        self.map_icon_selector.setDisabled(is_inactive)
        self.view.setDisabled(is_inactive)
        self.create_button.setDisabled(is_inactive)
        self.modify_option_widget.setDisabled(is_inactive)

    def node_icon_changed(self, icon_nid):
        if(self.current_node):
            self.current_node.icon = icon_nid
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def title_changed(self, text):
        if(self.current_node):
            self.current_node.name = text
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def nid_changed(self, text):
        if(self.current_node):
            self.current_node.nid = text
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def nid_done_editing(self):
        other_nids = []
        for overworld in DB.overworlds:
            for node in overworld.overworld_nodes:
                if node is not self.current_node:
                    other_nids.append(node.nid)
        if self.current_node.nid in other_nids:
            QMessageBox.warning(
                self, 'Warning', 'Node ID %s already in use' % self.current_node.nid)
            self.current_node.nid = str_utils.get_next_int(
                self.current_node.nid, other_nids)
        for overworld in DB.overworlds:
            overworld.overworld_nodes.update_nid(self.current_node, self.current_node.nid)
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)


    def level_changed(self, index):
        if(self.current_node):
            self.current_node.level = self.level_box.edit.itemData(index)

    def _initialize_components(self):
        self.setStyleSheet("font: 10pt;")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        self.nid_box = PropertyBox("Node ID", QLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        self.layout.addWidget(self.nid_box)

        self.title_box = PropertyBox("Location Name", QLineEdit, self)
        self.title_box.edit.textChanged.connect(self.title_changed)
        self.layout.addWidget(self.title_box)

        self.level_box = PropertyBox("Level", QComboBox, self)
        self.layout.addWidget(self.level_box)

        self.map_icon_selector = NodeIconSelector(self.node_icon_changed)
        self.layout.addWidget(self.map_icon_selector)
        
        self.view = RightClickListView(
            (None, None, None), parent=self)
        self.view.currentChanged = self.on_item_changed

        self._data = Data()
        self.model = OptionModel(self._data, self)
        self.view.setModel(self.model)

        self.layout.addWidget(self.view)

        self.create_button = QPushButton("Create Event...")
        self.create_button.clicked.connect(self.create_event)
        self.layout.addWidget(self.create_button)

        self.modify_option_widget = ModifyOptionsWidget(self._data, self)
        self.layout.addWidget(self.modify_option_widget)

        self.modify_option_widget.setEnabled(False)
            
        self.state_manager.subscribe_to_key(
            NodePropertiesMenu.__name__, 'ui_refresh_signal', self._refresh_view)

    def _refresh_view(self, _=None):
        self.model.layoutChanged.emit()

    def update_list(self):
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)
    
    def select(self, idx):
        index = self.model.index(idx)
        self.view.setCurrentIndex(index)

    def deselect(self):
        self.view.clearSelection()

    def on_item_changed(self, curr, prev):
        if self._data:
            reg = self._data[curr.row()]
            self.modify_option_widget.set_current(reg)

    def get_current(self):
        for index in self.view.selectionModel().selectedIndexes():
            idx = index.row()
            if len(self._data) > 0 and idx < len(self._data):
                return self._data[idx]
        return None
    
    def _populate_level_combo_box(self, level_combo_box):
        level_combo_box.clear()
        for level in DB.levels.values():
            level_combo_box.addItem(level.name, level.nid)
        level_combo_box.activated.connect(self.level_changed)
        return level_combo_box
        
    def create_event(self, example=None):
        nid = str_utils.get_next_name('New Event', self._data.keys())
        created_event = node_events.NodeEvent(nid)
        self._data.append(created_event)
        self.modify_option_widget.setEnabled(True)
        self.model.update()
        # Select the event
        idx = self._data.index(created_event.nid)
        index = self.model.index(idx)
        self.view.setCurrentIndex(index)
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)
        return created_event

class NodeIconSelector(QWidget):
    def __init__(self, on_icon_change):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)
        self.on_icon_change = on_icon_change
        self.map_icon_clickable_image_button = MapIconButton(self)
        self.map_icon_clickable_image_button.sourceChanged.connect(self.on_node_icon_changed)
        self.map_icon_name = QLabel("no_icon_selected", self)
        self.layout.addWidget(self.map_icon_clickable_image_button)
        self.layout.addWidget(self.map_icon_name)

    def set_map_icon_object(self, map_icon_object):
        self.map_icon_name.setText(map_icon_object.nid)
        self.map_icon_clickable_image_button.set_current(map_icon_object.nid)

    def on_node_icon_changed(self, nid):
        self.on_icon_change(nid)

class OptionModel(DragDropCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            opt = self._data[index.row()]
            text = opt.nid + ': ' + opt.event
            return text
        return None

    def new(self, idx):
        ok = self.window.create_event()
        if ok:
            self._data.move_index(len(self._data) - 1, idx + 1)
            self.layoutChanged.emit()

    def duplicate(self, idx):
        view = self.window.view
        obj = self._data[idx]
        new_nid = str_utils.get_next_name(obj.nid, self._data.keys())
        serialized_obj = obj.save()
        new_obj = node_events.NodeEvent.restore(serialized_obj)
        new_obj.nid = new_nid
        self._data.insert(idx + 1, new_obj)
        self.layoutChanged.emit()
        new_index = self.index(idx + 1)
        view.setCurrentIndex(new_index)
        return new_index

class ModifyOptionsWidget(QWidget):
    def __init__(self, data, parent=None, current=None):
        super().__init__(parent)
        self.window = parent
        self._data = data

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.current = current

        self.opt_nid_box = PropertyBox("Unique ID", QLineEdit, self)
        self.opt_nid_box.edit.textChanged.connect(self.option_nid_changed)
        self.opt_nid_box.edit.editingFinished.connect(self.option_nid_done_editing)
        layout.addWidget(self.opt_nid_box)

        self.sub_nid_box = PropertyBox("Event Name", QLineEdit, self)
        self.sub_nid_box.edit.textChanged.connect(self.sub_nid_changed)
        layout.addWidget(self.sub_nid_box)

        self.visible_box = PropertyCheckBox("Visible in menu?", QCheckBox, self)
        self.visible_box.edit.stateChanged.connect(self.visibility_changed)
        layout.addWidget(self.visible_box)
        
        self.enabled_box = PropertyCheckBox("Can be selected?", QCheckBox, self)
        self.enabled_box.edit.stateChanged.connect(self.selectable_changed)
        layout.addWidget(self.enabled_box)

    def option_nid_changed(self, text):
        if self.current:
            self.current.nid = text
            self.window.update_list()

    def option_nid_done_editing(self):
        if not self.current:
            return
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values()
                      if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning',
                                'Option ID %s already in use' % self.current.nid)
            self.current.nid = str_utils.get_next_name(
                self.current.nid, other_nids)
        self._data.update_nid(self.current, self.current.nid)
        self.window.update_list()

    def sub_nid_changed(self, text):
        self.current.event = text
        self.window.update_list()

    def visibility_changed(self, state):
        self.current.visible = bool(state)

    def selectable_changed(self, state):
        self.current.enabled = bool(state)

    def set_current(self, current):
        self.current = current
        self.opt_nid_box.edit.setText(current.nid)
        self.sub_nid_box.edit.setText(current.event)
        self.visible_box.edit.setChecked(bool(current.visible))
        self.enabled_box.edit.setChecked(bool(current.enabled))

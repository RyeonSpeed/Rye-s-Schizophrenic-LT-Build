import os

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon

from app.data.resources.map_animations import MapAnimation
from app.data.resources.resources import RESOURCES

from app.utilities.data import Data
from app.data.database.database import DB
from app.data.database import item_components, components

from app.extensions.custom_gui import DeletionTab, DeletionDialog

from app.editor.settings import MainSettingsController
from app.editor.base_database_gui import ResourceCollectionModel

from app.utilities import str_utils

class MapAnimationModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            animation = self._data[index.row()]
            text = animation.nid
            return text
        elif role == Qt.DecorationRole:
            animation = self._data[index.row()]
            pixmap = animation.pixmap
            if not pixmap:
                return None
            width = pixmap.width() // animation.frame_x
            height = pixmap.height() // animation.frame_y
            median_frame = animation.num_frames // 2
            left = (median_frame % animation.frame_x) * width
            top = (median_frame // animation.frame_x) * height

            middle_frame = pixmap.copy(left, top, width, height)
            return QIcon(middle_frame)
        return None

    def create_new(self):
        settings = MainSettingsController()
        starting_path = settings.get_last_open_path()
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select Animation PNG", starting_path, "PNG Files (*.png);;All Files(*)")
        new_animation = None
        if ok:
            for fn in fns:
                if fn.endswith('.png'):
                    nid = os.path.split(fn)[-1][:-4]
                    pix = QPixmap(fn)
                    nid = str_utils.get_next_name(nid, [d.nid for d in RESOURCES.animations])
                    new_animation = MapAnimation(nid, fn, pix)
                    RESOURCES.animations.append(new_animation)
                else:
                    QMessageBox.critical(self.window, "File Type Error!", "Map Animation must be PNG format!")
            parent_dir = os.path.split(fns[-1])[0]
            settings.set_last_open_path(parent_dir)
        return new_animation

    def delete(self, idx):
        # Check to see what is using me?
        res = self._data[idx]
        nid = res.nid
        affected_items = item_components.get_items_using(item_components.ComponentType.MapAnimation, nid, DB)
        if affected_items:
            from app.editor.item_editor.item_model import ItemModel
            model = ItemModel
            msg = "Deleting Map Animation <b>%s</b> would affect these items."
            deletion_tab = DeletionTab(affected_items, model, msg, "Items")
            ok = DeletionDialog.inform([deletion_tab], self.window)
            if ok:
                pass
            else:
                return
        super().delete(idx)

    def on_nid_changed(self, old_nid, new_nid):
        # What uses Animations
        # Certain item components
        components.swap_values(DB.items.values(), item_components.ComponentType.MapAnimation, old_nid, new_nid)

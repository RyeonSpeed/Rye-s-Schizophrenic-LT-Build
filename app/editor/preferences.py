from PyQt5.QtWidgets import QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt

from app import dark_theme
from app.extensions.custom_gui import ComboBox, PropertyBox, Dialog

from app.editor.settings import MainSettingsController

name_to_button = {'L-click': Qt.LeftButton,
                  'R-click': Qt.RightButton}
button_to_name = {v: k for k, v in name_to_button.items()}

class PreferencesDialog(Dialog):
    theme_options = ['Light', 'Dark', 'Discord', 'Sidereal', 'Mist']

    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.settings = MainSettingsController()

        self.saved_preferences = {}
        self.saved_preferences['select_button'] = self.settings.get_select_button(Qt.LeftButton)
        self.saved_preferences['place_button'] = self.settings.get_place_button(Qt.RightButton)
        self.saved_preferences['theme'] = self.settings.get_theme(0)

        self.available_options = name_to_button.keys()

        label = QLabel("Modify mouse preferences for Unit and Tile Painter Menus")

        self.select = PropertyBox('Select', ComboBox, self)
        for option in self.available_options:
            self.select.edit.addItem(option)
        self.place = PropertyBox('Place', ComboBox, self)
        for option in self.available_options:
            self.place.edit.addItem(option)
        self.select.edit.setValue(button_to_name[self.saved_preferences['select_button']])
        self.place.edit.setValue(button_to_name[self.saved_preferences['place_button']])
        self.select.edit.currentIndexChanged.connect(self.select_changed)
        self.place.edit.currentIndexChanged.connect(self.place_changed)

        self.theme = PropertyBox('Theme', ComboBox, self)
        for option in self.theme_options:
            self.theme.edit.addItem(option)
        self.theme.edit.setValue(self.theme_options[self.saved_preferences['theme']])
        self.theme.edit.currentIndexChanged.connect(self.theme_changed)

        self.layout.addWidget(label)
        self.layout.addWidget(self.select)
        self.layout.addWidget(self.place)
        self.layout.addWidget(self.theme)
        self.layout.addWidget(self.buttonbox)

    def select_changed(self, idx):
        choice = self.select.edit.currentText()
        if choice == 'L-click':
            self.place.edit.setValue('R-click')
        else:
            self.place.edit.setValue('L-click')

    def place_changed(self, idx):
        choice = self.place.edit.currentText()
        if choice == 'L-click':
            self.select.edit.setValue('R-click')
        else:
            self.select.edit.setValue('L-click')

    def theme_changed(self, idx):
        choice = self.theme.edit.currentText()
        ap = QApplication.instance()
        dark_theme.set(ap, idx)
        self.window.set_icons(idx)  # Change icons of main editor

    def accept(self):
        self.settings.set_select_button(name_to_button[self.select.edit.currentText()])
        self.settings.set_place_button(name_to_button[self.place.edit.currentText()])
        self.settings.set_theme(self.theme.edit.currentIndex())
        super().accept()

    def reject(self):
        super().reject()

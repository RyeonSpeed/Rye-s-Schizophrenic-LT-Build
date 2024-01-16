import os
import importlib

for module_name in os.listdir(os.path.dirname(__file__)):
    if module_name == '__init__.py' or module_name == '__init__.pyc':
        continue
    if module_name[-3:] == '.py':
        print("Importing Custom Components in %s..." % module_name)
        module = importlib.import_module('custom_components.' + module_name[:-3])
        importlib.reload(module)
    if module_name[-4:] == '.pyc':
        print("Importing Custom Components in %s..." % module_name)
        module = importlib.import_module('custom_components.' + module_name[:-4])
        importlib.reload(module)
del module_name
from typing import Tuple

try:
    from typing_extensions import Protocol
except ModuleNotFoundError:
    Protocol = object
    print("You are missing the `typing-extensions` module.\nTry running `pip install -r requirements_editor.txt`")

Point = Tuple[int, int]
Segment = Tuple[Point, Point]

NID = str
UID = int
Color3 = Tuple[int, int, int]
Color4 = Tuple[int, int, int, int]
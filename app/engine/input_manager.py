from app.engine import engine
from app.engine import config as cf
from app.constants import WINWIDTH, WINHEIGHT

class InputManager():
    def __init__(self):
        self.init_joystick()

        self.buttons = ('UP', 'DOWN', 'LEFT', 'RIGHT', 'SELECT', 'BACK', 'INFO', 'AUX', 'START')
        self.toggle_buttons = self.buttons[4:]  # These buttons cause state to change

        self.update_key_map()

        # Build and down button checker
        self.keys_pressed = {}
        self.joys_pressed = {}
        for button in self.buttons:
            self.keys_pressed[button] = False
            self.joys_pressed[button] = False

        #self.update_joystick_control()

        self.key_up_events = []
        self.key_down_events = []
        self.change_keymap_mode = False
        self.current_mouse_position = None
        self.finger_down_time = 0
        self.finger_down_position = (1,1)
        self.unavailable_button = None

    # The joystick needs be plugged in before this method is called
    def init_joystick(self):
        self.joystick = None
        self.joystick_name = None

    def get_joystick_init(self) -> bool:
        return self.joystick and self.joystick.get_init()

    def set_change_keymap(self, val):
        self.change_keymap_mode = val

    def is_pressed(self, button):
        return self.keys_pressed[button] or self.joys_pressed[button]

    def just_pressed(self, button):
        return button in self.key_down_events

    def get_mouse_position(self):
        if self.current_mouse_position:
            return (self.current_mouse_position[0] / engine.DISPLAYSURF.get_size()[0] * WINWIDTH,
                    self.current_mouse_position[1] / engine.DISPLAYSURF.get_size()[1] * WINHEIGHT)
        else:
            return None

    def get_real_mouse_position(self):
        """
        # Works whether or not mouse has been moved recently
        """
        if not cf.SETTINGS['mouse']:
            return None
        mouse_pos = engine.get_mouse_pos()
        mouse_pos = (mouse_pos[0] / engine.DISPLAYSURF.get_size()[0] * WINWIDTH,
                     mouse_pos[1] / engine.DISPLAYSURF.get_size()[1] * WINHEIGHT)
        if engine.get_mouse_focus():
            return mouse_pos
        else:  # Returns None if mouse is not in screen
            return None

    def update(self):
        self.update_key_map()
        self.update_joystick_control()

    def update_key_map(self):
        self.key_map = {}
        self.key_map['UP'] = cf.SETTINGS['key_UP']
        self.key_map['LEFT'] = cf.SETTINGS['key_LEFT']
        self.key_map['RIGHT'] = cf.SETTINGS['key_RIGHT']
        self.key_map['DOWN'] = cf.SETTINGS['key_DOWN']
        self.key_map['SELECT'] = cf.SETTINGS['key_SELECT']
        self.key_map['START'] = cf.SETTINGS['key_START']
        self.key_map['BACK'] = cf.SETTINGS['key_BACK']
        self.key_map['AUX'] = cf.SETTINGS['key_AUX']
        self.key_map['INFO'] = cf.SETTINGS['key_INFO']

        self.map_keys = {v: k for k, v in self.key_map.items()}

    def update_joystick_control(self):
        self.joystick_control = {}

        self.joystick_control['SELECT'] = [('is_button', 0)]  # A
        self.joystick_control['BACK'] = [('is_button', 1)]  # B
        self.joystick_control['START'] = [('is_button', 3), ('is_button', 6), ('is_button', 7)]  # Y, Select, Start
        self.joystick_control['INFO'] = [('is_button', 2), ('is_button', 5), ('is_axis', 2, -0.5, 4)] # X, RB, R2
        self.joystick_control['AUX'] = [('is_button', 4), ('is_axis', 2, 0.5, 5)] # LB, L2
        # hat
        self.joystick_control['LEFT'] = [('is_hat', 0, 'x', -1, 0), ('is_axis', 0, -0.5, 0)]
        self.joystick_control['RIGHT'] = [('is_hat', 0, 'x', 1, 1), ('is_axis', 0, 0.5, 1)]
        self.joystick_control['UP'] = [('is_hat', 0, 'y', 1, 2), ('is_axis', 1, -0.5, 2)]
        self.joystick_control['DOWN'] = [('is_hat', 0, 'y', -1, 3), ('is_axis', 1, 0.5, 3)]

        # handle buttons that need to know when they were last pressed
        self.button_state = {k: False for k in range(10)}
        self.hat_state = {k: False for k in range(4)}
        self.axis_state = {k: False for k in range(6)}

    def process_input(self, events):
        self.key_up_events.clear()
        self.key_down_events.clear()
        # Check fingers
        for event in events:
            if event.type == engine.FINGERUP or event.type == engine.FINGERDOWN or event.type == engine.FINGERMOTION:
                #button = self.map_keys.get(event.key)
                if 0.04 <= event.x <= 0.095 and 0.78 <= event.y <= 0.85:
                    button = 'UP'
                elif 0.04 < event.x <= 0.095 and 0.92 < event.y <= 0.99:
                    button = 'DOWN'
                elif 0.095 < event.x <= 0.15 and 0.85 < event.y <= 0.92:
                    button = 'RIGHT'
                elif 0.00 <= event.x < 0.04 and 0.85 < event.y <= 0.92:
                    button = 'LEFT'
                elif 0.91 <= event.x <= 0.97 and 0.81 <= event.y <= 0.89:
                    button = 'SELECT'
                elif 0.79 <= event.x <= 0.86 and 0.81 <= event.y <= 0.89:
                    button = 'AUX'
                elif 0.86 < event.x <= 0.92 and 0.72 <= event.y <= 0.80:
                    button = 'INFO'
                elif 0.86 <= event.x <= 0.92 and 0.91 <= event.y <= 0.97:
                    button = 'BACK'
                elif 0.82 <= event.x <= 1 and 0.06 <= event.y <= 0.12:
                    button = 'START'
                else:
                    button = 'NA'
                key_up = event.type == engine.FINGERUP
                key_down = event.type == engine.FINGERDOWN
                key_move = event.type == engine.FINGERMOTION
                if button:
                    # Update keys pressed
                    if key_up:
                        if button != 'NA':
                            self.key_up_events.append(button)
                        for b in self.buttons:
                            self.keys_pressed[button] = False
                    elif key_down and button != 'NA':
                        self.keys_pressed[button] = True
                        self.key_down_events.append(button)
                    elif key_move:
                        for b in self.buttons:
                            if b == button:
                                self.keys_pressed[b] = True
                                self.key_down_events.append(b)
                            elif self.keys_pressed[b]:
                                self.keys_pressed[b] = False

        # Return the correct event for this frame
        # Gives priority to later inputs
        # Remove reversed to give priority to earlier inputs
        for button in reversed(self.key_down_events):
            if button in self.toggle_buttons:
                return button
        # If only arrow keys pressed, return last one pressed
        if self.key_down_events:
            return self.key_down_events[-1]

    def handle_joystick(self):
        def update_state(pushed, state, button_id, button):
            # If state change
            if pushed != state[button_id]:
                self.joys_pressed[button] = pushed
                state[button_id] = pushed
                if pushed:
                    self.key_down_events.append(button)
                else:
                    self.key_up_events.append(button)
                return True
            return False

        for button in self.buttons:
            controls = self.joystick_control.get(button)
            for control in reversed(controls):
                # If the button behaves like a normal button
                if control[0] == 'is_button' and self.joystick.get_numbuttons() > control[1]:
                    pushed = self.joystick.get_button(control[1])
                    update_state(pushed, self.button_state, control[1], button)

                # If the button is controlured to a hat direction
                elif control[0] == 'is_hat' and self.joystick.get_numhats() > control[1]:
                    status = self.joystick.get_hat(control[1])
                    if control[2] == 'x':  # Which axis
                        amount = status[0]
                    else:  # 'y'
                        amount = status[1]
                    pushed = amount == control[3]  # Binary amounts
                    update_state(pushed, self.hat_state, control[4], button)

                # If the button is controlured to a joystick
                elif control[0] == 'is_axis' and self.joystick.get_numaxes() > control[1]:
                    amount = self.joystick.get_axis(control[1])
                    if control[2] < 0:
                        pushed = amount < control[2]
                    elif control[2] > 0:
                        pushed = amount > control[2]
                    update_state(pushed, self.axis_state, control[3], button)

INPUT: InputManager = None
def get_input_manager() -> InputManager:
    global INPUT
    if not INPUT:
        INPUT = InputManager()
    return INPUT


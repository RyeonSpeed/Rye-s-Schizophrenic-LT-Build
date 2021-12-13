from app.utilities.data import Prefab

class NodeMenuEvent(Prefab):
    def __init__(self, nid):
        self.nid = nid          #Should be the same as the event name in the event editor. i.e., this is the exact name of the event to call.
        self.event_name = ''    #Display name of the event. This is what's shown in the menu, but the above is the event's actual id.   
        self.visible = False    #Whether the option will appear in the list
        self.enabled = False    #Whether the option can be selected (i.e., if visible but not enabled, will be greyed out)
        
    @classmethod
    def default(cls):
        return cls('0')


from app.utilities.data import Prefab

class NodeEvent(Prefab):
    def __init__(self, nid):
        self.nid = nid
        self.event = 'None'     #Name of the event   
        self.visible = False    #Whether the option will appear in the list
        self.enabled = False    #Whether the option can be selected (i.e., if visible but not enabled, will be greyed out)
        
    @classmethod
    def default(cls):
        return cls('None')

from dataclasses import dataclass, asdict, fields

def dataclass_from_dict(klass, d):
    try:
        fieldtypes = {f.name:f.type for f in fields(klass)}
        return klass(**{f:dataclass_from_dict(fieldtypes[f],d[f]) for f in d if f in fieldtypes})
    except:
        return d # Not a dataclass field

@dataclass
class GameFlags():
    has_fatal_errors: bool = True

    def save(self):
        return asdict(self)
    
    def restore(self, d):
        restored = dataclass_from_dict(self.__class__, d)
        self.__dict__ = restored.__dict__
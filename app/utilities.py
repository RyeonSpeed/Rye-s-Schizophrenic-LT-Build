def get_next_name(name, names):
    if name not in names:
        return name
    else:
        counter = 1
        while True:
            test_name = name + (' (%s)' % counter)
            if test_name not in names:
                return test_name
            counter += 1

def get_next_int(name, names):
    if name not in names:
        return name
    else:
        counter = 1
        while True:
            test_name = str(counter)
            if test_name not in names:
                return test_name
            counter += 1

def intify(s: str) -> list:
    vals = s.split(',')
    return [int(i) for i in vals]

def skill_parser(s: str) -> list:
    if s is not None:
        each_skill = [each.split(',') for each in s.split(';')]
        split_line = [(int(s_l[0]), s_l[1]) for s_l in each_skill]
        return split_line
    else:
        return []

def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False

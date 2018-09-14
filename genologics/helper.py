from collections import defaultdict

class RandomDepthDotStyleDict(defaultdict):

    """Radome depth defaultdict, access attribute with dot e.g. mydict.attr.attri.attrib"""

    def __init__(self):

        super(RandomDepthDotStyleDict, self).__init__(RandomDepthDotStyleDict)

    def __getattr__(self, key):

        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):

        self[key] = value

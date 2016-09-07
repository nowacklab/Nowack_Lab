from jsonpickle.ext import numpy
import json
import jsonpickle as jsp
numpy.register_handlers()

class Measurement:
    
    @staticmethod
    def tojson(obj, filename):
        obj_string = jsp.encode(obj)
        obj_dict = json.loads(obj_string)
        with open(filename, 'w') as f:
            json.dump(obj_dict, f, sort_keys=True, indent=4)

    @staticmethod
    def fromjson(json_file):
        with open(json_file) as f:
            obj_dict = json.load(f)
        obj_string = json.dumps(obj_dict)
        obj = jsp.decode(obj_string)
        return obj

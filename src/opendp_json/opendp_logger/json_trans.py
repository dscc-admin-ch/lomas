import opendp.trans as trans 
from opendp_json.opendp_logger import JTransformation, wrapper

for f in dir(trans):
    if f[:5] == "make_":
        locals()[f] = wrapper(f, getattr(trans, f), 'trans')


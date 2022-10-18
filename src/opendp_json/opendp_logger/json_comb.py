import opendp.comb as comb 
from opendp_json.opendp_logger import wrapper

for f in dir(comb):
    if f[:5] == "make_":
        locals()[f] = wrapper(f, getattr(comb, f), 'comb')
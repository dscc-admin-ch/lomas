import opendp.meas as meas 
from opendp_json.opendp_logger import JMeasurement, wrapper

for f in dir(meas):
    if f[:5] == "make_":
        locals()[f] = wrapper(f, getattr(meas, f), 'meas')
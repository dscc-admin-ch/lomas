from .models.mwem import MWEM
# from .models.dpctgan import DPCTGAN
from .models.mst import MST
# from .models.patectgan import PATECTGAN

import globals  

from typing import Dict
import pandas as pd

synth_map = {
    "MWEM": MWEM,
    # "dpctgan": DPCTGAN,
    "MST": MST,
    # "patectgan": PATECTGAN
}
# synth_map = {
#     'mwem': {
#         'class': 'snsynth.mwem.MWEMSynthesizer'
#     },
#     'dpctgan': {
#         'class': 'snsynth.pytorch.nn.dpctgan.DPCTGAN'
#     },
#     'patectgan': {
#         'class': 'snsynth.pytorch.nn.patectgan.PATECTGAN'
#     },
#     'mst': {
#         'class': 'snsynth.mst.mst.MSTSynthesizer'
#     },
#     'pacsynth': {
#         'class': 'snsynth.aggregate_seeded.AggregateSeededSynthesizer'
#     },
#     'dpgan': {
#         'class': 'snsynth.pytorch.nn.dpgan.DPGAN'
#     },
#     'pategan': {
#         'class': 'snsynth.pytorch.nn.pategan.PATEGAN'
#     }
# }
def synth(synth_type:str, eps:float, params: Dict[str, int] = {}):
    sd = synth_map[synth_type](globals.TRAIN, eps)
    return sd.export()

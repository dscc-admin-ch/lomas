from .status import PartyStatus

def acc_m_eps(acc, eps):
    # accuracy minus epsilon (divided by 100 to normalize) capped at 0
    return max([0, acc-(eps/300)])

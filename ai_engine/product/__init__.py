"""DENTAI Product Intelligence Layer V1."""
from .models import *

def analyze_case(*args,**kwargs):
    """Lazy import keeps CLI module execution warning-free."""
    from .analyze_case import analyze_case as _analyze_case
    return _analyze_case(*args,**kwargs)

__all__=["analyze_case"]

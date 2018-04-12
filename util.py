from decorator import decorator
from time import time
import json

def memoize(expiry_time=0, _cache=None, num_args=None):
  def _memoize(func, *args, **kw):
    if _cache is None and not hasattr(func, '_cache'):
      func._cache = {}
    cache = _cache or func._cache
    
    mem_args = args[:num_args]
    if kw: 
      key = mem_args, frozenset(kw.iteritems())
    else:
      key = mem_args
    if key in cache:
      result, timestamp = cache[key]
      age = time() - timestamp
      if not expiry_time or age < expiry_time:
          return result
    result = func(*args, **kw)
    cache[key] = (result, time())
    return result
  return decorator(_memoize)

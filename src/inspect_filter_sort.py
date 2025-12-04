
from pytubefix.contrib.search import Filter

print("Filter attributes:")
for attr in dir(Filter):
    if not attr.startswith("_"):
        val = getattr(Filter, attr)
        print(f"{attr}: {val}")
        if isinstance(val, type):
             print(f"  Attributes of {attr}:")
             for sub_attr in dir(val):
                 if not sub_attr.startswith("_"):
                     print(f"    {sub_attr}")

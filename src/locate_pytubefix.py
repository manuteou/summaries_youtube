
import sys
import os

try:
    import pytubefix
    print(f"pytubefix file: {pytubefix.__file__}")
    from pytubefix.contrib.search import Search, Filter
    print("Imported Search and Filter")
    print(f"Filter dir: {dir(Filter)}")
    
    # Check for sort options
    if hasattr(Filter, 'get_sort_by'):
        print(f"Filter.get_sort_by: {Filter.get_sort_by}")
        print(dir(Filter.get_sort_by))
    
    if hasattr(Filter, 'sort_by'):
         print(f"Filter.sort_by: {Filter.sort_by}")

except ImportError as e:
    print(f"Error: {e}")
    print(f"sys.path: {sys.path}")

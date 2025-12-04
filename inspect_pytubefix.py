
from pytubefix.contrib.search import Search, Filter

print("Filter attributes/methods:")
print(dir(Filter))
print("\nFilter.get_sort_by attributes/methods (if exists):")
try:
    print(dir(Filter.get_sort_by))
except:
    print("No get_sort_by")

print("\nFilter.sort_by attributes/methods (if exists):")
try:
    print(dir(Filter.sort_by))
except:
    print("No sort_by")

print("\nFilter.create() attributes/methods:")
f = Filter.create()
print(dir(f))

print("\nSearch attributes/methods:")
print(dir(Search))

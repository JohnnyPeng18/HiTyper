
#The builtin types are collected from https://docs.python.org/zh-cn/3/library/stdtypes.html
builtins = [
"int", "float", "complex", "bool", "list", "tuple", "range", "str", "bytes", "bytearray", "memoryview", "set", "frozenset", "dict", "dict_keys", "dict_values", "dict_items", "None"
]


#The following functions will not be automatcally inferred using the type templates in builtin_method, HiTyper has explicit rules to handle them in typerule.py
builtin_method_properties = {
    #The following methods change the types of caller instead of return some new types
    "self-changable": {
        "list": ["append", "clear", "extend", "insert", "pop", "remove"],
        "set": ["update", "intersection_update", "difference_update", "symmetric_difference_update", "add", "remove", "discard", "pop", "clear"],
        "dict": ["clear", "pop", "popitem", "setdefault", "update"],
        "overall": ["append", "clear", "extend", "insert", "pop", "remove", "update", "intersection_update", "difference_update", "symmetric_difference_update", "add", "discard", "pop", "popitem", "setdefault"]
    },
    #The following methods generate return values according to the arguments
    "special-return": {
        "standalone": ["abs", "divmod", "enumerate", "frozenset", "list", "next", "round", "set", "sorted", "sum", "tuple", "type", "max", "min"],
        "list": ["copy"],
        "set": ["pop"],
        "dict": ["items", "keys", "values", "pop", "popitem", "get"],
        "overall": ["abs", "divmod", "enumerate", "frozenset", "list", "next", "round", "set", "sorted", "sum", "tuple", "type", "max", "min", "copy", "items", "keys", "values", "pop", "popitem", "get"]
    }
}

special_types = {
    "@iterable@": ["list", "tuple", "range", "str", "bytes", "bytearray", "set", "frozenset", "dict"],
    "@byte-like@": ["bytes", "bytearray"],
    "@set-like@": ["set", "frozenset"],
    "@subscriptable@": ["list", "tuple", "str", "bytes", "bytearray"],
    "@number@": ["bool", "int", "float", "complex"],
    "@hashable@": [],
    "@sequence@": ["str", "bytes", "bytearray", "tuple", "list", "range"],
    "@collection@": ["set", "frozenset", "dict"],
    "@path-like@": ["str", "bytes"]
}

#For the simplicity, HiTyper treats some types as their commonly-used alternatives, although this is not always correct
simplified_types = {
    #builtins
    "dict_keys": "set",
    "dict_values": "set",
    "dict_items": "set",
    #typing module
    "typing.NoReturn": "None",
    "typing.AnyStr": "str",
    "typing.ByteString": "str",
    "typing.TypedDict": "Dict",
    "typing.FrozenSet": "frozenset",
    "typing.DeafultDict": "Dict",
    "typing.OrderedDict": "Dict",
    "typing.ItemsView": "Set",
    "typing.KeysView": "Set",
    "typing.Mapping": "Dict",
    "typing.MappingView": "Dict",
    "typing.MutableMapping": "Dict",
    "typing.MutableSequence": "List",
    "typing.MutableSet": "Set",
    "typing.Sequence": "List",
    "typing.ValuesView": "List",
    "typing.AbstractSet": "Set",
    "typing.Text": "str",
    #collections module
    "collections.ChainMap": "Dict",
    "collections.Counter": "Dict",
    "collections.OrderedDict": "Dict",
    "collections.defaultdict": "Dict",
    "collections.UserDict": "Dict",
    "collections.UserList": "List",
    "collections.UserString": "str",
    "collections.abc.Iterable": "List",
    "collections.abc.Generator": "Generator",
    "collections.abc.Callable": "Callable",
    "collections.abc.MutableSequence": "List",
    "collections.abc.ByteString": "str",
    "collections.abc.Set": "Set",
    "collections.abc.MutableSet": "Set",
    "collections.abc.Mapping": "Dict",
    "collections.abc.MutableMapping": "Dict",
    "collections.abc.MappingView": "Dict",
    "collections.abc.ItemsView": "Set",
    "collections.abc.KeysView": "Set",
    "collections.abc.ValuesView": "Set",
    "collections.abc.AsyncIterable": "List",
    "collections.abc.AsyncGenerator": "Generator"
}

builtin4user_method = {
    "abs": "__abs__",
    "hash": "__hash__",
    "next": "__next__",
    "repr": "__repr__",
    "str": "__str__"
}

#functions with dynamic features are not included
builtin_method = {
    "standalone": {
        "abs": [[("x", "@number@")], "@originaltype@"],
        "all": [[("iterable", "@iterable@")], "bool"],
        "any": [[("iterable", "@iterable@")], "bool"],
        "ascii": [[("object", "Any")], "str"],
        "bin": [[("x", "int")], "str"],
        "bool": [[("x", "Any")], "bool"],
        "bytearray": [[("source", "str"), ("encoding", "str"), ["errors", "str"]], [("source", "int")], [("source", "@iterable@")], "bytearray"],
        "bytes": [[("source", "str"), ("encoding", "str"), ["errors", "str"]], [("source", "int")], [("source", "@iterable@")], "bytes"],
        "callable": [[("object", "Any")], "bool"],
        "chr": [[("i", "int")], "str"],
        "complex": [[("real", "str")], [("real", "int"), ["imag", "int"]], [], "complex"],
        "dict": [[], "dict"],   #dict is currently not supported
        "dir": [[["object", "Any"]], "List[str]"],
        "divmod": [[("a", "int"), ("b", "int")], [("a", "int"), ("b", "float")], [("a", "float"), ("b", "int")], [("a", "float"), ("b", "float")], "@originaltype@"],
        "enumerate": [[("iterable", "@iterable@"), ["start", "int"]], "Generator[Tuple[int, @elementtype@]]"],
        "float": [[["x", "str"]], [["x", "@number@"]], "float"],
        "frozenset": [["iterable", "@iterable@"], "fronzenset[@elementtype@]"],
        "globals": [[], "dict"],
        "hasattr": [[("object", "Any"), ("name", "str")], "bool"],
        "hash": [[("object", "@hashable@")], "int"],
        "hex": [[("x", "int")], "str"],
        "id": [[("object", "Any")], "int"],
        "int": [[("x", "@number@"), ["base", "int"]], [("x", "str"), ["base", "int"]], "int"],
        "isinstance": [[("object", "Any"), ("classinfo", "Any")], "bool"],
        "issubclass": [[("object", "Any"), ("classinfo", "Any")], "bool"],
        "len": [[("s", "@sequence@")], [("s", "@collection@")], "int"],
        "list": [[["iterable", "@iterable@"]], "List[@elementtype@]"],
        "locals": [[], "dict"],
        "max": [[], "@originaltype@"],
        "memoryview": [[("object", "Any")], "memoryview"],
        "min": [[], "@originaltype@"],
        "next": [[("iterator", "Generator")], "@elementtype@"],
        "oct": [[("x", "int")], "str"],
        "open": [[("file", "@path-like@"), ["mode", "str"], ["buffering", "int"], ["encoding", "str"], ["errors", "str"], ["newline", "Optional[str]"], ["closefd", "bool"], ["opener", "Callable"]], "IO"],
        "ord": [[("c", "str")], "int"],
        "range": [[["start", "int"], ("stop", "int"), ["step", "int"]], "range"],
        "repr": [[("object", "Any")], "str"],
        "round": [[("number", "@number@"), ["ndigits", "int"]], "@originaltype@"],
        "set": [[["iterable", "@iterable@"]], "set[@elementtype@]"],
        "slice": [[["start", "int"], ("stop", "int"), ["step", "int"]], "range"],
        "sorted": [[("iterable", "@iterable@"), ["key", "Callable"], ["reverse", "bool"]], "List[@elementtype@]"],
        "str": [[("object", "Any"), ["encoding", "str"], ["errors", "str"]], "str"],
        "sum": [[("iterable", "@iterable@&@number@")], "@elementtype@"],
        "tuple": [[("iterable", "@iterable@")], "Tuple[@elementtype@]"],
        "type": [[("object", "Any")], "@originaltype@"]
    },
    "int": {
        "bit_length": [[], "int"],
        "bit_count": [[], "int"],
        "to_bytes": [[("length", "int"), ("byteorder", "str"), ["signed", "bool"]], "bytes"],
        "from_bytes": [[("length", "int"), ("byteorder", "str") , ["signed", "bool"]], "int"],
        "as_integer_ratio": [[], "Tuple[int]"]
    },
    "float": {
        "as_integer_ratio": [[], "Tuple[int]"],
        "is_integer": [[], "bool"],
        "hex": [[], "str"]
    },
    "list": {
        "index": [[("x", "@elementtype@"), ["i", "int"], ["j", "int"]], "int"],
        "count": [[("x", "@elementtype@")], "int"],
        "append": [[("x", "Any")], "None"],
        "clear": [[], "None"],
        "copy": [[], "@originaltype@"],
        "extend": [[("t", "List")], "None"],
        "insert": [[("i", "int"), ("x", "Any")], "None"],
        "pop": [[["i", "int"]], "None"],
        "remove": [[("x", "@elementtype@")], "None"],
        "reverse": [[], "None"],
        "sort": [[["key", "Callable"], ["reverse", "bool"]], "None"]
    },
    "tuple": {
        "index": [[("x", "@elementtype@"), ["i", "int"], ["j", "int"]], "int"],
        "count": [[("x", "@elementtype@")], "int"]
    },
    "range": {
        "index": [[("x", "@elementtype@"), ["i", "int"], ["j", "int"]], "int"],
        "count": [[("x", "@elementtype@")], "int"]
    },
    "str": {
        "index": [[("x", "str"), ["i", "int"], ["j", "int"]], "int"],
        "count": [[("x", "str")], "int"],
        "capitalize": [[], "str"],
        "casefold": [[], "str"],
        "center": [[("width", "int"), ["fillchar", "str"]], "str"],
        "encode": [[["encoding", "str"], ["errors", "str"]], "bytes"],
        "endswith": [[("suffix", "str"), ["start", "int"], ["end", "int"]], "bool"],
        "expandtabs": [[["tabsize", "int"]], "str"],
        "find": [[("sub", "str"), ["start", "int"], ["end", "int"]], "int"],
        "format": [[], "str"],
        "format_map": [[["mapping", "dict"]], "str"],
        "isalnum": [[], "bool"],
        "isalpha": [[], "bool"],
        "isascii": [[], "bool"],
        "isdecimal": [[], "bool"],
        "isdigit": [[], "bool"],
        "isidentifier": [[], "bool"],
        "islower": [[], "bool"],
        "isnumeric": [[], "bool"],
        "isprintable": [[], "bool"],
        "isspace": [[], "bool"],
        "istitle": [[], "bool"],
        "isupper": [[], "bool"],
        "join": [[("iterable", "@iterable@")], "str"],
        "ljust": [[("width", "int"), ["fillchar", "str"]], "str"],
        "lower": [[], "str"],
        "lstrip": [[["chars", "str"]], "str"],
        "maketrans": [[("x", "dict")], [("x", "str"), ("y", "str")], [("x", "str"), ("y", "str"), ("z", "str")], "dict"],
        "partition": [[("sep", "str")], "Tuple[str]"],
        "removeprefix": [[("prefix", "str")], "str"],
        "removesuffix": [[("suffix", "str")], "str"],
        "replace": [[("old", "str"), ("new", "str"), ["count", "int"]], "str"],
        "rfind": [[("sub", "str"), ["start", "int"], ["end", "int"]], "int"],
        "rindex": [[("sub", "str"), ["start", "int"], ["end", "int"]], "int"],
        "rjust": [[("width", "int"), ["fillchar", "str"]], "str"],
        "rpartition": [[("sep", "str")], "Tuple[str]"],
        "rsplit": [[["sep", "str"], ["maxsplit", "int"]], "List[str]"],
        "rstrip": [[["chars", "str"]], "str"],
        "split": [[["sep", "str"], ["maxsplit", "int"]], "List[str]"],
        "splitlines": [[["keepends", "bool"]], "List[str]"],
        "startswith": [[("suffix", "str"), ["start", "int"], ["end", "int"]], "bool"],
        "strip": [[["chars", "str"]], "str"],
        "swapcase": [[], "str"],
        "title": [[], "str"],
        "translate": [["table", "@subscriptable@"], "str"],
        "upper": [[], "str"],
        "zfill": [[("width", "int")], "str"]
    },
    "bytes": {
        "hex": [[["sep", "str"], ["bytes_per_sep", "int"]], "str"],
        "index": [[("x", "@byte-like@"), ["i", "int"], ["j", "int"]], "int"],
        "count": [[("x", "@byte-like@")], "int"],
        "removeprefix": [[("prefix", "@byte-like@")], "bytes"],
        "removesuffix": [[("suffix", "@byte-like@")], "bytes"],
        "decode": [[["encoding", "str"], ["errors", "str"]], "str"],
        "endswith": [[("suffix", "@byte-like@"), ["start", "int"], ["end", "int"]], "bool"],
        "find": [[("sub", "@byte-like@"), ["start", "int"], ["end", "int"]], "int"],
        "join": [[("iterable", "@iterable@")], "bytes"],
        "maketrans": [[("from", "@byte-like@"), ("to", "@byte-like@")], "bytes"],
        "partition": [[("sep", "@byte-like@")], "Tuple[bytes]"],
        "replace": [[("old", "@byte-like@"), ("new", "bytes"), ["count", "int"]], "bytes"],
        "rfind": [[("sub", "@byte-like@"), ["start", "int"], ["end", "int"]], "int"],
        "rindex": [[("sub", "@byte-like@"), ["start", "int"], ["end", "int"]], "int"],
        "rpartition": [[("sep", "@byte-like@")], "Tuple[bytes]"],
        "startswith":[[("suffix", "@byte-like@"), ["start", "int"], ["end", "int"]], "bool"],
        "translate": [[("table", "bytes"), ["delete", "@byte-like@"]], "bytes"],
        "center": [[("width", "int"), ["fillbyte", "@byte-like@"]], "bytes"],
        "ljust": [[("width", "int"), ["fillbyte", "@byte-like@"]], "bytes"],
        "lstrip": [[["chars", "@byte-like@"]], "bytes"],
        "rjust": [[("width", "int"), ["fillbyte", "@byte-like@"]], "bytes"],
        "rsplit": [[["sep", "@byte-like@"], ["maxsplit", "int"]], "List[bytes]"],
        "rstrip": [[["chars", "@byte-like@"]], "bytes"],
        "split": [[["sep", "@byte-like@"], ["maxsplit", "int"]], "List[bytes]"],
        "rstrip": [[["chars", "@byte-like@"]], "bytes"],
        "capitalize": [[], "bytes"],
        "expandtabs": [[["tabsize", "int"]], "bytes"],
        "isalnum": [[], "bool"],
        "isalpha": [[], "bool"],
        "isascii": [[], "bool"],
        "isdigit": [[], "bool"],
        "islower": [[], "bool"],
        "isspace": [[], "bool"],
        "istitle": [[], "bool"],
        "isupper": [[], "bool"],
        "lower": [[], "bytes"],
        "splitlines": [[["keepends", "bool"]], "List[bytes]"],
        "swapcase": [[], "bytes"],
        "title": [[], "bytes"],
        "upper": [[], "bytes"],
        "zfill": [[("width", "int")], "bytes"]
    },
    "bytearray": {
        "hex": [[["sep", "str"], ["bytes_per_sep", "int"]], "str"],
        "index": [[("x", "@byte-like@"), ["i", "int"], ["j", "int"]], "int"],
        "count": [[("x", "@byte-like@")], "int"],
        "removeprefix": [[("prefix", "@byte-like@")], "bytes"],
        "removesuffix": [[("suffix", "@byte-like@")], "bytes"],
        "decode": [[["encoding", "str"], ["errors", "str"]], "str"],
        "endswith": [[("suffix", "@byte-like@"), ["start", "int"], ["end", "int"]], "bool"],
        "find": [[("sub", "bytes"), ["start", "int"], ["end", "int"]], "int"],
        "join": [[("iterable", "@iterable@")], "bytearray"],
        "maketrans": [[("from", "@byte-like@"), ("to", "@byte-like@")], "bytes"],
        "partition": [[("sep", "@byte-like@")], "Tuple[bytearray]"],
        "replace": [[("old", "@byte-like@"), ("new", "@byte-like@"), ["count", "int"]], "bytearray"],
        "rfind": [[("sub", "@byte-like@"), ["start", "int"], ["end", "int"]], "int"],
        "rindex": [[("sub", "@byte-like@"), ["start", "int"], ["end", "int"]], "int"],
        "rpartition": [[("sep", "@byte-like@")], "Tuple[bytearray]"],
        "startswith":[[("suffix", "@byte-like@"), ["start", "int"], ["end", "int"]], "bool"],
        "translate": [[("table", "bytes"), ["delete", "@byte-like@"]], "bytearray"],
        "center": [[("width", "int"), ["fillbyte", "@byte-like@"]], "bytearray"],
        "ljust": [[("width", "int"), ["fillbyte", "@byte-like@"]], "bytearray"],
        "lstrip": [[["chars", "@byte-like@"]], "bytearray"],
        "rjust": [[("width", "int"), ["fillbyte", "@byte-like@"]], "bytearray"],
        "rsplit": [[["sep", "@byte-like@"], ["maxsplit", "int"]], "List[bytearray]"],
        "rstrip": [[["chars", "@byte-like@"]], "bytearray"],
        "split": [[["sep", "@byte-like@"], ["maxsplit", "int"]], "List[bytearray]"],
        "rstrip": [[["chars", "@byte-like@"]], "bytearray"],
        "capitalize": [[], "bytearray"],
        "expandtabs": [[["tabsize", "int"]], "bytearray"],
        "isalnum": [[], "bool"],
        "isalpha": [[], "bool"],
        "isascii": [[], "bool"],
        "isdigit": [[], "bool"],
        "islower": [[], "bool"],
        "isspace": [[], "bool"],
        "istitle": [[], "bool"],
        "isupper": [[], "bool"],
        "lower": [[], "bytearray"],
        "splitlines": [[["keepends", "bool"]], "List[bytearray]"],
        "swapcase": [[], "bytearray"],
        "title": [[], "bytearray"],
        "upper": [[], "bytearray"],
        "zfill": [[("width", "int")], "bytearray"]
    },
    "memoryview": {
        "tobytes": [[["order", "str"]], "bytes"],
        "hex": [[["sep", "str"], ["bytes_per_sep", "int"]], "str"],
        "tolist": [[], "List"],
        "toreadonly": [[], "memoryview"],
        "release": [[], "None"],
        "cast": [[("format", "str"), ["shape", "List[int]"]], [("format", "str"), ["shape", "Tuple[int]"]], "memoryview"]
    },
    "set": {
        "isdisjoint": [[("other", "@set-like@")], "bool"],
        "issubset": [[("other", "@iterable@")], "bool"],
        "issuperset": [[("other", "@iterable@")], "bool"],
        "union": [[("other", "@iterable@")], "set"],
        "intersection": [[("other", "@iterable@")], "set"],
        "difference": [[("other", "@iterable@")], "set"],
        "symmetric_difference": [[("other", "@iterable@")], "set"],
        "copy": [[], "set"],
        "update": [[("others", "@iterable@")], "set"],
        "intersection_update": [[("others", "@iterable@")], "set"],
        "difference_update": [[("others", "@iterable@")], "set"],
        "symmetric_difference_update": [[("other", "@iterable@")], "set"],
        "add": [[("elem", "Any")], "set"],
        "remove": [[("elem", "@elementtype@")], [("elem", "set")], "set"],
        "discard": [[("elem", "@elementtype@")], [("elem", "set")], "set"],
        "pop": [[("elem", "@elementtype@")], "@elementtype@"],
        "clear": [[], "set"]
    },
    "frozenset": {
        "isdisjoint": [["other", "@set-like@"], "bool"],
        "issubset": [["other", "@iterable@"], "bool"],
        "issuperset": [["other", "@iterable@"], "bool"],
        "union": [["other", "@iterable@"], "frozenset"],
        "intersection": [["other", "@iterable@"], "frozenset"],
        "difference": [["other", "@iterable@"], "frozenset"],
        "symmetric_difference": [["other", "@iterable@"], "frozenset"],
        "copy": [[], "frozenset"]
    },
    "dict": {
        "clear": [[], "dict"],
        "copy": [[], "dict"],
        "get": ([[("key", "@keytype@")], "@valuetype@"], [[("key", "Any")], "None"]),
        "items": [[], "dict_items[List[Tuple[@keytype@, @valuetype@]]]"],
        "keys": [[], "dict_keys[List[@keytype@]]"],
        "pop": [[("key", "@keytype@")], "@valuetype@"],
        "popitem": [[], "Tuple[@keytype@, @valuetype@]"],
        "setdefault": [[("key", "Any")], "dict"],
        "update": [[("other", "dict")], [("other", "@iterable@")], "dict"],
        "values": [[], "dict_values[List[@valuetype@]]"]
    }

}





#The types in typing module are extracted from https://docs.python.org/zh-cn/3/library/typing.html
#Type annotations that are removed after 3.9 are not included into this list
typing_module = [
#The following types are supported by the typing rules defined inside HiTyper
"Tuple", "Union", "Optional", "Type", "Dict", "List", "Set", "Pattern", "Match", "Text", "Generator", "Callable",

#The following types are simplified to other types
"NoReturn", "AnyStr", "TypedDict", "FrozenSet", "DefaultDict", "OrderedDict", "ByteString", "ItemsView", "KeysView", "Mapping", 
"MappingView", "MutableMapping", "MutableSequence", "MutableSet", "Sequence", "ValuesView", "Iterable", "AbstractSet",

#The following types are too detailed and rarely used. HiTyper can only recognize them but will not infer them
"NewType", "Generic", "Any", "TypeAlias", "Concatenate", "Literal", "ClassVar", "Final", "Annotated", "TypeGuard",
"ParamSpec", "ParamSpecArgs", "ParamSpecKwargs", "Protocol", "NamedTuple",  "ChainMap", "Counter", "Deque", "IO", 
"TextIO", "BinaryIO", "Hashable", "Sized", "Collection", "Container",  "Iterator", "Reversible"
]

#The types in collections module are extracted from https://docs.python.org/zh-cn/3/library/collections.html
collections_module = [
"ChainMap", "Counter", "deque", "defaultdict", "namedtuple", "OrderedDict", "UserDict", "UserList", "UserString",
]


#The types in collections module are extracted from https://docs.python.org/zh-cn/3/library/collections.abc.html
collections_abc_module = [
"Container", "Hashable", "Iterable", "Iterator", "Reversible", "Generator", "Sized", "Callable", "Collection", "Sequence", "MutableSequence",
"ByteString", "Set", "MutableSet", "Mapping", "MutableMapping", "MappingView", "ItemsView", "KeysView", "ValuesView", "Awaitable", "Coroutine",
"AsyncIterable", "AsyncIterator", "AsyncGenerator"
]

#The standard errors are extracted from https://docs.python.org/zh-cn/3/library/exceptions.html
errors = [
"BaseException", "Exception", "ArithmeticError", "BufferError", "LookupError", "AssertionError", "AttributeError", "EOFError", "GeneratorExit", "ImportError",
"ModuleNotFoundError", "IndexError", "KeyError", "KeyboardInterrupt", "MemoryError", "NameError", "NotImplementedError", "OSError", "OverflowError", "RecursionError",
"ReferenceError", "RuntimeError", "StopIteration", "StopAsyncIteration", "SyntaxError", "IndentationError", "TabError", "SystemError", "SystemExit", "TypeError",
"UnboundLocalError", "UnicodeError", "UnicodeEncodeError", "UnicodeTranslateError", "ValueError", "ZeroDivisionError", "EnvironmentError", "IOError", "WindowsError",
"BlockingIOError", "ChildProcessError", "ConnectionError", "BrokenPipeError", "ConnectionAbortedError", "ConnectionRefusedError", "ConnectionResetError", 
"FileExistsError", "FileNotFoundError", "InterruptedError", "IsADirectoryError", "NotADirectoryError", "PermissionError", "ProcessLookupError", "TimeoutError"
]

#The standard errors are extracted from https://docs.python.org/zh-cn/3/library/exceptions.html
warnings = [
"Warning", "DeprecationWarning", "PendingDeprecationWarning", "RuntimeWarning", "SyntaxWarning", "UserWarning", "FutureWarning", "ImportWarning", "UnicodeWarning",
"BytesWarning", "EncodingWarning", "ResourceWarning"
]


stdtypes = {
    "typing": typing_module,
    "collections": collections_module,
    "collections_abc": collections_abc_module,
    "builtins": builtins,
    "errors": errors,
    "warnings": warnings,
    "overall": typing_module + builtins + collections_module + collections_abc_module + errors + warnings
}


#This map converts the types stored in TypeObject to commonly used type names in source code
exporttypemap = {}
for i in stdtypes["builtins"]:
    exporttypemap[i.lower()] = i
for i in stdtypes["errors"]:
    exporttypemap[i.lower()] = i
for i in stdtypes["warnings"]:
    exporttypemap[i.lower()] = i
for i in stdtypes["typing"]:
    if i.lower() not in exporttypemap:
        exporttypemap[i.lower()] = "typing." + i
for i in stdtypes["collections"]:
    if i.lower() not in exporttypemap:
        exporttypemap[i.lower()] = "collections." + i
for i in stdtypes["collections_abc"]:
    if i.lower() not in exporttypemap:
        exporttypemap[i.lower()] = "collections.abc." + i



#This map converts commonly used type names in source code to TypeObject
inputtypemap = {}
for i in exporttypemap:
    if exporttypemap[i] in simplified_types:
        inputtypemap[exporttypemap[i].lower()] = simplified_types[exporttypemap[i]]
    else:
        for j in stdtypes["builtins"]:
            typestr = j
            if typestr.lower() not in inputtypemap:
                inputtypemap[typestr.lower()] = j 
        for j in stdtypes["errors"]:
            typestr = j
            if typestr.lower() not in inputtypemap:
                inputtypemap[typestr.lower()] = j 
        for j in stdtypes["warnings"]:
            typestr = j
            if typestr.lower() not in inputtypemap:
                inputtypemap[typestr.lower()] = j 
        for j in stdtypes["typing"]:
            typestr = "typing." + j
            if typestr.lower() not in inputtypemap:
                inputtypemap[typestr.lower()] = j 
        for j in stdtypes["collections"]:
            typestr = "collections." + j
            if typestr.lower() not in inputtypemap:
                inputtypemap[typestr.lower()] = j 
        for j in stdtypes["collections_abc"]:
            typestr = "collections_abc." + j
            if typestr.lower() not in inputtypemap:
                inputtypemap[typestr.lower()] = j 





#This map provide the comparison between standard types as there may exist mutiple types name actually pointing one type.
typeequalmap = {
    "text": 0,
    "str": 0,
    "bool": 1,
    "int": 1,
    "float": 2,
    "complex": 3,
    "generator": 11,
    "iterator": 11,
    "list": 12,
    "tuple": 13,
    "range": 14,
    "set": 15,
    "frozenset": 16,
    "dict": 17

}

startnum = 1000
for i in stdtypes["builtins"]:
    if i.lower() not in typeequalmap:
        typeequalmap[i.lower()] = startnum
        startnum += 1

for i in stdtypes["errors"]:
    if i.lower() not in typeequalmap:
        typeequalmap[i.lower()] = startnum
        startnum += 1

for i in stdtypes["warnings"]:
    if i.lower() not in typeequalmap:
        typeequalmap[i.lower()] = startnum
        startnum += 1

for i in stdtypes["typing"]:
    if i.lower() not in typeequalmap:
        typeequalmap[i.lower()] = startnum
        startnum += 1

for i in stdtypes["collections"]:
    if i.lower() not in typeequalmap:
        typeequalmap[i.lower()] = startnum
        startnum += 1

for i in stdtypes["collections_abc"]:
    if i.lower() not in typeequalmap:
        typeequalmap[i.lower()] = startnum
        startnum += 1





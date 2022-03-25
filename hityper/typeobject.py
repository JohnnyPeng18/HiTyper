import re
from hityper.stdtypes import stdtypes, exporttypemap, inputtypemap, typeequalmap
from hityper import logger

logger.name = __name__

class TypeObject(object):
    def __init__(self, t, category, added = False):
        self.type = t

        #categories: 0 - builtins
        #1 - standard libraries
        #2 - user defined 
        self.category = category
        self.compatibletypes = [t]

        self.startnodename = None
        self.startnodeorder = None

        self.added = added

        if t in ["bool", "int", "float", "complex"]:
            self.compatibletypes = ["int", "float", "complex", "bool"]

        self.elementtype = []
        self.keytype = []
        self.valuetype = []

    def buildTuple(self, t):
        self.type = "Tuple"
        self.elementtype = t

    def buildDict(self, key, value):
        self.type = "Dict"
        self.elementtype = key
        self.keytype = key
        self.valuetype = value
    
    def buildList(self, t):
        self.type = "List"
        self.elementtype = t

    def buildSet(self, t):
        self.type = "Set"
        self.elementtype = t

    @property
    def getBuiltinTypes(self):
        #ref: https://docs.python.org/zh-cn/3/library/typing.html
        #ref: https://docs.python.org/3/library/stdtypes.html
        self.builintypes = {}
        self.builintypes["element"] = ["bool", "int", "float", "None", "Any", "Text", "type", "bytes"]
        self.builintypes["generic"] = [ "List", "Tuple", "Set", "Dict", "Union", "Optional", "Callable", "Iterable", "Sequence", "Generator"]
        self.builintypes["rare"] = ["complex", "bytearray", "Frozenset", "memoryview", "range"]
        return self.builintypes

    @staticmethod
    def isCompatible(l, r):
        for t in l.compatibletypes:
            if t == r.type:
                return True
        return False

    @staticmethod
    def existCompatible(l, listr):
        for r in listr:
            if TypeObject.isCompatible(l, r):
                return True
        if TypeObject.existSame(l, listr):
            return True
        return False

    @staticmethod
    def existNumbers(l, listr, exact = False):
        #now we conduct exact match
        if not exact:
            return False
        if l.type in ["int", "float"]:
            for r in listr:
                if r.type in ["int", "float"]:
                    return True
        return False


    #l is x and optional[x] in listr will return true
    @staticmethod
    def existOptional(l, listr):
        for t in listr:
            if t.type.lower() == "optional" and len(t.elementtype) == 1 and typeequalmap[t.elementtype[0].type.lower()] == typeequalmap[l.type.lower()]:
                return True
        return False


    @staticmethod
    def existSame( l, listr):
        for r in listr:
            if TypeObject.isIdentical(l,r):
                return True
        return False

    @staticmethod
    def existSimilar(l, listr):
        for r in listr:
            if TypeObject.isSimilar(l,r):
                return True
        return False

    @staticmethod
    def findSame(l, listr):
        for r in listr:
            if TypeObject.isIdentical(l,r):
                return r
        return None

    @staticmethod
    def isIdentical( l, r):

        if l.category != 0 and r.category != 0:
            if l.type == r.type:
                return True
            elif l.category == r.category and l.category == 2 and (l.type.split(".")[-1] == r.type.split(".")[-1]):
                return True
            else:
                return False
        if  l.category == 0 and r.category == 0:
            if typeequalmap[l.type.lower()] == typeequalmap[r.type.lower()]:
                if l.type.lower() not in ["list", "tuple", "set", "iterable", "optional", "union", "sequence", "generator", "dict"]:
                    return True
                else:
                    if l.type.lower() == "dict" and TypeObject.isIdenticalSet(l.keytype, r.keytype) and TypeObject.isIdenticalSet(l.valuetype, r.valuetype):
                        return True
                    elif l.type.lower() in ["list", "tuple", "set", "iterable", "optional", "union", "sequence", "generator"] and TypeObject.isIdenticalSet(l.elementtype, r.elementtype):
                        return True
            elif (l.type.lower() == "literal" and typeequalmap[r.type.lower()] <= 3) or (r.type.lower() == "literal" and typeequalmap[l.type.lower()] <= 3):
                return True
            elif (l.type.lower() == "iterable" and typeequalmap[r.type.lower()] <= 17 and typeequalmap[r.type.lower()] >= 11) or (r.type.lower() == "iterable" and typeequalmap[l.type.lower()] <= 17 and typeequalmap[l.type.lower()] >= 11):
                return True
        if l.category == 0 and r.category == 2 and l.type.lower() == "type" and len(l.elementtype) == 1:
            return TypeObject.isIdentical(l.elementtype[0], r)
        if r.category == 0 and l.category == 2 and r.type.lower() == "type" and len(r.elementtype) == 1:
            return TypeObject.isIdentical(r.elementtype[0], l)
        return False
    
    @staticmethod
    def isSimilar(l,r):
        if l.category == 0 and r.category == 0 and typeequalmap[l.type.lower()] == typeequalmap[r.type.lower()]:
            return True
        elif l.type.lower() == r.type.lower():
            return True
        else:
            return False
    
    @staticmethod
    def isIdenticalSet( llist, rlist):
        for l in llist:
            if l.type.lower() == "any":
                return True
            if not TypeObject.existSame(l, rlist) and l.type.lower() != "any":
                return False
        for r in rlist:
            if r.type.lower() == "any":
                return True
            if not TypeObject.existSame(r, llist) and r.type.lower() != "any":
                return False
        return True

    @staticmethod
    def existType(t, listr):
        for r in listr:
            if isinstance(t, str):
                if (r.category == 0 and typeequalmap[t.lower()] == typeequalmap[r.type.lower()]) or (r.category == 2 and r.type == t):
                    return True
            elif isinstance(t, TypeObject):
                if (r.category == 0 and t.category == 0 and typeequalmap[t.type.lower()] == typeequalmap[r.type.lower()]) or (t.type == r.type):
                    return True
        return False

    @staticmethod
    def equal2type(t, typestr):
        if typeequalmap[t.type.lower()] == typeequalmap[typestr.lower()]:
            return True
        return False

    @staticmethod
    def equal2onetype(t, typestrs):
        for s in typestrs:
            if typeequalmap[t.type.lower()] == typeequalmap[s.lower()]:
                return True
        return False


    @staticmethod
    def combineTypes(listt):
        if len(listt) > 1:
            typeobject = TypeObject("Union", 0)
            typeobject.elementtype = listt
            return typeobject
        elif len(listt) == 1:
            return listt[0]
        else:
            return None

    @staticmethod
    def usertypeCompare(l, rlist):
        for r in rlist:
            if l.category == r.category and l.category == 2 and ((l.type.split(".")[-1] == r.type.split(".")[-1])):
                return True
        return False

    @staticmethod
    def existIncluded(l, rlist):
        for r in rlist:
            if TypeObject.isIncluded(l,r):
                return True
        return False
        

    #if l is included in r, for generic types, list[a] is included in list[a,b]
    @staticmethod
    def isIncluded(l, r):
        if r.type == "Optional" and len(r.elementtype) == 1 and l.type == r.elementtype[0].type:
            return True
        elif l.type != r.type:
            return False
        elif l.type == r.type and l.type in ["List", "Tuple", "Dict", "Set", "Iterable", "Optional", "Union", "Sequence", "Generator"]:
            if l.type == "Dict":
                for t in l.keytype:
                    if not TypeObject.existSame(t, r.keytype) and not TypeObject.existOptional(t, r.keytype) and not TypeObject.existIncluded(t, r.keytype):
                        return False
                for t in l.valuetype:
                    if not TypeObject.existSame(t, r.valuetype) and not TypeObject.existOptional(t, r.valuetype) and not TypeObject.existIncluded(t, r.valuetype):
                        return False
                return True
            else:
                for t in l.elementtype:
                    if not TypeObject.existSame(t, r.elementtype) and not TypeObject.existOptional(t, r.elementtype) and not TypeObject.existIncluded(t, r.elementtype):
                        return False
                return True

    @staticmethod
    def isSetIncluded(llist, rlist):
        for r in rlist:
            if TypeObject.existSame(r, llist) or TypeObject.existNumbers(r, llist) or TypeObject.usertypeCompare(r, llist):
                continue
            else:
                included = False
                for l in llist:
                    if TypeObject.isIncluded(r, l):
                        included = True
                        break
                if included:
                    continue
            return False
        return True

    @staticmethod
    def isSetIncluded2(llist, rlist):
        for r in rlist:
            if TypeObject.existSimilar(r, llist) or TypeObject.existNumbers(r, llist, exact = True) or TypeObject.usertypeCompare(r, llist):
                continue
            else:
                included = False
                for l in llist:
                    if TypeObject.isIncluded(r, l):
                        included = True
                        break
                if included:
                    continue
            return False
        return True



    @staticmethod
    def simplifyGenericType(t):
        if not isinstance(t, TypeObject):
            return t
        if t.type in ["Set", "Tuple", "List", "Awaitable", "Iterable", "Union"]:
            t.elementtype = TypeObject.removeInclusiveTypes(t.elementtype)
        elif t.type == "Dict":
            t.keytype = TypeObject.removeInclusiveTypes(t.keytype)
            t.valuetype = TypeObject.removeInclusiveTypes(t.valuetype)
        elif t.type == "Optional":
            t.elementtype = TypeObject.removeRedundantTypes(t.elementtype)
            rm = None
            for et in t.elementtype:
                if et.type == "None":
                    rm = et
                    break
            if rm != None and rm in t.elementtype:
                t.elementtype.remove(rm)

        return t


    @staticmethod
    def removeRedundantTypes(listt):
        outs = []
        for t in listt:
            typeobj = TypeObject.simplifyGenericType(t)
            if not TypeObject.existSame(typeobj, outs):
                outs.append(typeobj)
        return outs

    #Example: if list[] and list[a] exists at the same time, then list[] is removed
    @staticmethod
    def removeInclusiveTypes(listt):
        outs = TypeObject.removeRedundantTypes(listt)
        removed = True
        
        while removed:
            removed = False
            for i in range(0, len(outs)):
                for j in range(0, len(outs)):
                    if i != j and TypeObject.isIncluded(outs[i], outs[j]):
                        removed = True
                        target = outs[i]
                        break
            if removed and target in outs:
                outs.remove(target)
        return outs


    def __str__(self):
        return TypeObject.resolveTypeName(self)
            

    @staticmethod
    def resolveTypeName(t):
        if isinstance(t, TypeObject):
            if t.category != 0:
                return t.type
            elif t.type.lower() not in exporttypemap:
                raise TypeError("Unknown type: " + t.type)
            typestr = exporttypemap[t.type.lower()]
            if t.type in ["Dict", "Callable"]:
                typestr = typestr + "["
                if len(t.keytype) == 0:
                    typestr += ", "
                elif len(t.keytype) == 1:
                    typestr = typestr + TypeObject.resolveTypeName(t.keytype[0]) + ", "
                else:
                    typestr += "typing.Union["
                    for n in t.keytype:
                        typestr = typestr + TypeObject.resolveTypeName(n) + ","
                    typestr = typestr[:-1]
                    typestr += "], "
                if len(t.valuetype) == 0:
                    pass
                elif len(t.valuetype) == 1:
                    typestr = typestr + TypeObject.resolveTypeName(t.valuetype[0])
                else:
                    typestr += "typing.Union["
                    for n in t.valuetype:
                        typestr = typestr + TypeObject.resolveTypeName(n) + ","
                    typestr = typestr[:-1]
                    typestr += "]"
                typestr += "]"
            elif t.type in ["Set", "Tuple", "List", "Awaitable", "Iterable", "Sequence", "Generator"]:
                typestr = typestr + "["
                if len(t.elementtype) == 1:
                    typestr = typestr + TypeObject.resolveTypeName(t.elementtype[0])
                elif len(t.elementtype) == 2 and (t.elementtype[0].type == "None" or t.elementtype[1].type == "None"):
                    typestr += "typing.Optional["
                    for i in t.elementtype:
                        if i.type != "None":
                            typestr = typestr + TypeObject.resolveTypeName(i) 
                    typestr += "]"
                elif len(t.elementtype) >= 2:
                    typestr += "typing.Union["
                    for n in t.elementtype:
                        typestr = typestr + TypeObject.resolveTypeName(n) + ","
                    typestr = typestr[:-1]
                    typestr += "]"
                typestr += "]"
            elif t.type == "Optional":
                typestr += "["
                if len(t.elementtype) > 1:
                    typestr += "typing.Union["
                    for n in t.elementtype:
                        typestr = typestr + TypeObject.resolveTypeName(n) + ","
                    typestr = typestr[:-1]
                    typestr += "]"
                elif len(t.elementtype) == 1:
                    typestr = typestr + TypeObject.resolveTypeName(t.elementtype[0]) + "]"
                else:
                    typestr += "]"
            elif t.type == "Union":
                typestr += "["
                if len(t.elementtype) == 0:
                    typestr += "]"
                if len(t.elementtype) == 1:
                    typestr = typestr + TypeObject.resolveTypeName(t.elementtype[0]) + "]"
                elif len(t.elementtype) > 1:
                    for n in t.elementtype:
                        typestr = typestr + TypeObject.resolveTypeName(n) + ","
                    typestr = typestr[:-1]
                    typestr += "]"
            return typestr
        else:
            raise TypeError("t should be a TypeObject.")
    
    @staticmethod
    def resolveTypeNames(tlist):
        typestr = "Possible Types {"
        if isinstance(tlist, list):
            for i, t in enumerate(tlist):
                typestr = typestr + " " + str(i+1) + "." + str(t.category) + "- " + TypeObject.resolveTypeName(t)
        else:
            raise TypeError("tlist must be a list of TypeObject.")
        return typestr + " }"

    @staticmethod
    def resolveTypeNames2(tlist):
        typestr = "Union["
        if isinstance(tlist, list):
            for i, t in enumerate(tlist):
                typestr = typestr + TypeObject.resolveTypeName(t) + ","
            if typestr[-1] == ",":
                typestr = typestr[:len(typestr)-1]
        else:
            raise TypeError("tlist must be a list of TypeObject.")
        return typestr + "]"

    @staticmethod
    def checkType(typestr):
        typeobjs = TypeObject.Str2Obj(typestr)
        if len(typeobjs) == 0:
            return None
        elif typeobjs[0].category == 0 and len(typeobjs[0].elementtype) == 0 and len(typeobjs[0].keytype) == 0 and len(typeobjs[0].valuetype) == 0:
            return "simple"
        elif typeobjs[0].category == 0:
            return "generic"
        elif typeobjs[0].category == 2:
            return "user-defined"
        else:
            return None


    @staticmethod
    def Str2Obj(typestr):
        strobjs = []
        typestr = typestr.replace(" ", "")
        typestr = typestr.replace("builtins.", "")
        typestr = typestr.replace("typing_extensions.", "typing.")
        if len(typestr) > 2 and typestr[0] == "[" and typestr[-1] == "]":
            typestr = typestr[1:len(typestr) - 1]
        if typestr == None or typestr == "":
            return strobjs
        if len(typestr) > 500:
            #logger.warning("Type name is too long.")
            return strobjs
        if typestr in ["Union", "typing.Union"] and "[" not in typestr:
            return strobjs
        elif typestr.lower() in inputtypemap:
            strobjs.append(TypeObject(inputtypemap[typestr.lower()], 0))
            return strobjs
        elif "[" in typestr and "]" in typestr:
            typestr = typestr.replace("t.", "typing.")
            index1 = typestr.index("[")
            index2 = typestr.rfind("]")
            innerstr = typestr[index1 + 1:index2]
            if "Union" in typestr[:index1]:
                strs = innerstr.split(",")
                leftnum = 0
                rightnum = 0
                cur_str = ""
                for s in strs:
                        cur_str += s
                        leftnum += s.count("[")
                        rightnum += s.count("]")
                        if leftnum == rightnum:
                            strobjs += TypeObject.Str2Obj(cur_str)
                            cur_str = ""
                        else:
                            cur_str += ","
                return strobjs
            elif "Optional" in typestr[:index1] or "typing.Optional" in typestr[:index1]:
                strobjs += TypeObject.Str2Obj(innerstr)
                strobjs.append(TypeObject("None", 0))
                return strobjs
            if typestr[:index1].lower() in inputtypemap:
                typeobj = TypeObject(inputtypemap[typestr[:index1].lower()], 0)
                if "Dict" in typestr[:index1] or "Mapping" in typestr[:index1] or "Callable" in typestr[:index1]:
                    if "," in innerstr:
                        commaindex = innerstr.split(",")
                        leftnum = 0
                        rightnum = 0
                        cur_str = ""
                        count = 0
                        for s in commaindex:
                            cur_str += s
                            leftnum += s.count("[")
                            rightnum += s.count("]")
                            if leftnum == rightnum:
                                if count == 0:
                                    typeobj.keytype += TypeObject.Str2Obj(cur_str)
                                else:
                                    typeobj.valuetype += TypeObject.Str2Obj(cur_str)
                                count += 1
                                cur_str = ""
                            else:
                                cur_str += ","
                        strobjs.append(typeobj)
                        return strobjs
                    else:
                        return strobjs
                else:
                    strs = innerstr.split(",")
                    leftnum = 0
                    rightnum = 0
                    cur_str = ""
                    for s in strs:
                        cur_str += s
                        leftnum += s.count("[")
                        rightnum += s.count("]")
                        if leftnum == rightnum:
                            typeobj.elementtype += TypeObject.Str2Obj(cur_str)
                            cur_str = ""
                        else:
                            cur_str += ","
                    
                    '''
                    if "[" in innerstr and "]" in innerstr:
                        typeobj.elementtype = TypeObject.Str2Obj(innerstr)
                    else:
                        strs = innerstr.split(",")
                        for s in strs:
                            typeobj.elementtype += TypeObject.Str2Obj(s)
                    '''
                    strobjs.append(typeobj)
                    return strobjs
            else:
                typeobj = TypeObject(typestr.replace("[typing.Any]", ""), 2)
                strobjs.append(typeobj)
                return strobjs
        elif typestr.startswith("typing") and "[" not in typestr and typestr.lower() in inputtypemap:
            typeobj = TypeObject(inputtypemap[typestr.lower()], 0)
            strobjs.append(typeobj)
            return strobjs
        else:
            typeobj = TypeObject(typestr, 2)
            strobjs.append(typeobj)
            return strobjs

    @staticmethod
    def DumpObject(typeobj):
        print("Type: " + typeobj.type)
        print("Element Type:" + TypeObject.resolveTypeNames(typeobj.elementtype))
        print("Key Type:" + TypeObject.resolveTypeNames(typeobj.keytype))
        print("Value Type:" + TypeObject.resolveTypeNames(typeobj.valuetype))

    @staticmethod
    def DumpOriObject(typeobj):
        elementtypestr = ""
        for t in typeobj.elementtype:
            elementtypestr += TypeObject.DumpOriObject(t) + " [SEP] "
        keytypestr = ""
        for t in typeobj.keytype:
            keytypestr += TypeObject.DumpOriObject(t) + " [SEP] "
        valuetypestr = ""
        for t in typeobj.valuetype:
            valuetypestr += TypeObject.DumpOriObject(t) + " [SEP] "
        return "@Type: {}, Element Type: [{}], Key Type: [{}], Value Type: [{}]@".format(typeobj.type, elementtypestr, keytypestr, valuetypestr)
    
    @staticmethod
    def DumpOriObjects(typeobjs):
        typestr = ""
        for i, obj in enumerate(typeobjs):
            typestr += "{} - {} \n".format(i, TypeObject.DumpOriObject(obj))
        return typestr


    def dump(self):
        obj = {"type": self.type, "category": self.category, "added": self.added, "compatibletypes": self.compatibletypes, "startnodename": self.startnodename, "startnodeorder": self.startnodeorder}
        elementtype = []
        for i in self.elementtype:
            elementtype.append(i.dump())
        obj["elementtype"] = elementtype
        keytype = []
        for i in self.keytype:
            keytype.append(i.dump())
        obj["keytype"] = keytype
        valuetype = []
        for i in self.valuetype:
            valuetype.append(i.dump())
        obj["valuetype"] = valuetype

        return obj

    @staticmethod
    def load(dictobj):
        obj = TypeObject(dictobj["type"], dictobj["category"], added = dictobj["added"])
        obj.compatibletypes = dictobj["compatibletypes"]
        obj.startnodename = dictobj["startnodename"]
        obj.startnodeorder = dictobj["startnodeorder"]
        for i in dictobj["elementtype"]:
            obj.elementtype.append(TypeObject.load(i))
        for i in dictobj["keytype"]:
            obj.keytype.append(TypeObject.load(i))
        for i in dictobj["valuetype"]:
            obj.valuetype.append(TypeObject.load(i))
        return obj


        

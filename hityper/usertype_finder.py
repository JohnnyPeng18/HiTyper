import ast
import sys, getopt
import os
import glob
from hityper.typeobject import TypeObject
from hityper import logger
from func_timeout import func_set_timeout, FunctionTimedOut
from hityper.stdtypes import stdtypes


logger.name = __name__

scaned_files = []

def transformConstant(node):
    if not isinstance(node, ast.Constant):
        raise ValueError("Only Support Constant AST node.")
    if isinstance(node.value, str):
        return TypeObject("Text", 0)
    elif isinstance(node.value, bytes):
        return TypeObject("bytes", 0)
    elif isinstance(node.value, bool):
        return TypeObject("bool", 0)
    elif isinstance(node.value, float):
        return TypeObject("float", 0)
    elif isinstance(node.value, int):
        return TypeObject("int", 0)
    elif node.value == None:
        return TypeObject("None", 0)
    elif type(node.value) == type(Ellipsis):
        return None
    else:
        raise TypeError("Currently we do not suupport constant of type: " + str(type(node.value)))

def Attribute2Str(node):
    if isinstance(node, ast.Attribute):
        return Attribute2Str(node.value) + "_@_" + node.attr
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return transformConstant(node).type
    elif isinstance(node,ast.Call):
        return Attribute2Str(node.func) + "()"
    else:
        return "<Other>"


class ASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.classes = []
        self.classattributes = {}
        self.classstack = []
        self.curclass = -1
        self.types = []                     #raw types directly imported
        self.files = []                     #imported packages
        self.modules = []                   #imported modules
        self.mode = 0
        self.funcstack = []
        self.curfunc = -1
        self.parentclasses = {}
        self.onlyimportedmodules = []         #For those only imported but do not know what imported from this module
        self.modulealiases = {}


    def visit_ClassDef(self, node):
        if node.name not in self.classes:
            self.classes.append(node.name)
        if node.name not in self.parentclasses:
            self.parentclasses[node.name] = []
        if len(node.bases) > 0:
            for i in node.bases:
                if hasattr(i, "id") and i.id != "object" and i.id not in self.parentclasses[node.name]:
                    self.parentclasses[node.name].append(i.id)
        self.classstack.append(node.name)
        self.curclass += 1
        if self.curclass == 0 and node.name not in self.classattributes:
            self.classattributes[node.name] = {}
        self.generic_visit(node)
        self.classstack.pop(self.curclass)
        self.curclass -= 1

    def extract_argument(self, node):
        if type(node) != ast.arguments:
            raise ValueError("Only arguments node is acceptable.")
        else:
            arglist = []
            if hasattr(node, "posonlyargs"):
                for a in node.posonlyargs:
                    arglist.append(a.arg)
            for a in node.args:
                arglist.append(a.arg)
            if node.vararg != None:
                arglist.append(node.vararg.arg)
            for a in node.kwonlyargs:
                arglist.append(a.arg)
            if node.kwarg != None:
                arglist.append(node.kwarg.arg)
            return arglist



    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_FunctionDef(self, node):
        self.funcstack.append(node.name)
        self.curfunc += 1
        if self.curclass == 0:
            self.classattributes[self.classstack[self.curclass]][node.name] = self.extract_argument(node.args)

        self.generic_visit(node)
        self.funcstack.pop(self.curfunc)
        self.curfunc -= 1
        
    def visit_Attribute(self, node):
        if self.curclass == 0:
            attr = Attribute2Str(node)
            if attr.startswith("self") and "_@_" in attr:
                items = attr.split("_@_")
                self.classattributes[self.classstack[self.curclass]][items[1]] = None




    # AST Node related to import
    def visit_Import(self, node):
        if self.mode == 1:
            for name in node.names:
                if name.name not in self.modules:
                    self.modules.append(name.name)
                    self.onlyimportedmodules.append(name.name)
                    if hasattr(name, "asname"):
                        self.modulealiases[name.asname] = name.name
        
            self.generic_visit(node)

    # AST Node related to import
    def visit_ImportFrom(self, node):
        if self.mode == 1:
            if(len(node.names) > 0):
                for name in node.names:
                    if name.name == "*":
                        if node.module != None:
                            self.files.append([node.module, node.level])
                        else:
                            self.files.append(["<Cur_Repo>", node.level])
                    elif name.name.islower():
                        if node.module != None:
                            self.files.append([node.module + "." + name.name, node.level])
                        else:
                            self.files.append(["<Cur_Repo>" + "." + name.name, node.level])
                    else:
                        if node.module != None:
                            self.types.append([node.module, name.name, node.level])
                        else:
                            self.types.append(["<Cur_Repo>", name.name, node.level])
                    if node.level == 0 and node.module != None and node.module.split(".")[0] not in self.modules:
                        self.modules.append(node.module.split(".")[0])

            self.generic_visit(node)

    def visit_Assign(self, node):
        if self.curfunc == -1 and type(node.value) == ast.Call and \
        (type(node.value.func) == ast.Name and node.value.func.id in stdtypes["overall"] or\
        type(node.value.func) == ast.Attribute and node.value.func.attr in  stdtypes["overall"] ):
            for n in node.targets:
                if type(n) == ast.Name and len(n.id) >= 1 and n.id[0].isupper():
                    self.classes.append(n.id)

        if self.curfunc == -1:
            if type(node.value) == ast.Name:
                right = node.value.id
                for t in self.types:
                    if t[1] == right:
                        for n in node.targets:
                            if type(n) == ast.Name and len(n.id) >= 1 and n.id[0].isupper():
                                self.classes.append(n.id)
                        break
            elif type(node.value) == ast.Subscript and type(node.value.value) == ast.Name:
                right = node.value.value.id
                for t in self.types:
                    if t[1] == right:
                        for n in node.targets:
                            if type(n) == ast.Name and len(n.id) >= 1 and n.id[0].isupper():
                                self.classes.append(n.id)
                        break
            elif type(node.value) == ast.Subscript and type(node.value.value) == ast.Attribute and type(node.value.value.value) == ast.Name and node.value.value.value.id == "typing":
                for n in node.targets:
                    if type(n) == ast.Name and len(n.id) >= 1 and n.id[0].isupper():
                        self.classes.append(n.id)



    def run(self, node, mode):
        self.mode = mode
        self.visit(node)
        return self.classes

class UsertypeFinder(object):
    def __init__(self, path, repo, validate):
        self.types = []                     #raw types directly imported
        self.files = []                     #imported packages
        self.finaltypes = {}                #final/validated user defined types
        self.finaltypes["direct"] = []       
        self.finaltypes["indirect"] = []
        self.finaltypes["init"] = []
        self.finaltypes["num"] = 0
        self.finaltypes["module"] = []
        self.finaltypes["unrecognized"] = []
        self.finaltypes["unrecognized_modules"] = []
        self.modules = []                   #imported modules
        self.userdefinedmodules = {}        #all user defined modules in this project
        self.path  = path                   #original path
        self.platform = sys.platform                   # default linux
        self.validate = validate
        self.parentclasses = {}

        if self.platform =="win32":
            self.paths = path.split("\\")
        else:
            self.paths = path.split("/")        #path of source file
        if repo != None:
            if self.platform == "win32":
                self.repopaths = repo.split("\\")
            else:
                self.repopaths = repo.split("/")    #path of root repo
        else:
            self.repopaths = []

        
        for i in range(0,len(self.paths)):
            if i < len(self.repopaths) and self.paths[i] != self.repopaths[i]:
                raise ValueError("Repository path should be the preffix of source file path.")
        self.paths = self.paths[len(self.repopaths):]


    def mergesubtype(self, parentclass):
        for key in parentclass:
            if key in self.parentclasses:
                for t in parentclass[key]:
                    if t not in self.parentclasses[key]:
                        self.parentclasses[key].append(t)
            else:
                self.parentclasses[key] = []
                for t in parentclass[key]:
                    self.parentclasses[key].append(t)


    # build the path of imported modules
    def buildpath(self, level, name):
        if level == 0:
            return "/".join(self.repopaths) + "/" + name.replace(".", "/")
        elif level == 1:
            if not name.startswith("<Cur_Repo>"):
                return "/".join(self.repopaths) + "/" + "/".join(self.paths[:-1]) + "/" + name.replace(".", "/")
            else:
                names = name.split(".")
                del names[0]
                if len(names) > 0:
                    return "/".join(self.repopaths) + "/" + "/".join(self.paths[:-1]) + "/" + "/".join(names)
                else:
                    return "/".join(self.repopaths) + "/" + "/".join(self.paths[:-1])
        else:
            paths = self.repopaths + self.paths
            return "/".join(paths[:-level]) + "/" + name.replace(".", "/")

    # tranform "a.b.c" to "a/b/c"
    def transformpath(self, name, repopaths):
        if self.platform == "win32":
            paths = name.split("\\")
        else:
            paths = name.split("/")
        paths = paths[len(repopaths):]
        return ".".join(paths)

    def scan_module(self):
        for i in os.walk("/".join(self.repopaths)):
            if "__init__.py" in i[2]:
                if self.platform == "win32" and i[0].split("\\")[-1] not in self.userdefinedmodules:
                    self.userdefinedmodules[i[0].split("\\")[-1]] = i[0]
                elif i[0].split("\\")[-1] not in self.userdefinedmodules:
                    self.userdefinedmodules[i[0].split("/")[-1]] = i[0]

    
    def find_file(self, path):
        '''
        paths = path.split(".")
        finalpath = None
        if paths[0] in self.userdefinedmodules:
            filepath = self.userdefinedmodules[paths[0]]
            for i in range(1, len(paths)):
                filepath = filepath + "/" + paths[i]
            return filepath
        else:
            return None
        '''
        filepath = path.replace(".", "/") + ".py"
        filepath2 = path.replace(".", "/") + "/__init__.py"
        files = glob.glob("/".join(self.repopaths) + "/**/" + filepath, recursive = True)
        if len(files) >= 1:
            return files
        else:
            files = glob.glob("/".join(self.repopaths) + "/**/" + filepath2, recursive = True)
            if len(files) >= 1:
                return files
            else:
                return None




    def parse_initfiles(self, path, repopaths):
        if not os.path.isfile(path):
            return None
        else:
            source = open(path, "r").read()
            root = ast.parse(source)
            a = analyzer(path, "/".join(repopaths), self.validate)
            types, _ = a.run(root)
            return types
            
    def scan_file(self, filepath, name, repopaths):
        if filepath.endswith(".py"):
            filepath = filepath.replace(".py", "")
        if(os.path.isdir(filepath) and filepath not in scaned_files):
            scaned_files.append(filepath)
            types = self.parse_initfiles(filepath + "/__init__.py", repopaths)
            for t in types["indirect"]:
                finalt = [t[0], name, t[2], t[3]]
                if finalt not in self.finaltypes["indirect"]:
                    self.finaltypes["indirect"].append(finalt)
            for t in types["direct"]:
                finalt = [t[0], name, t[2], t[3]]
                if finalt not in self.finaltypes["indirect"]:
                    self.finaltypes["indirect"].append(finalt)
            for t in types["init"]:
                finalt = [filepath + "/__init__.py", name, t[0], t[1]]
                if finalt not in self.finaltypes["indirect"]:
                    self.finaltypes["indirect"].append(finalt)
            for m in types["module"]:
                if m not in self.modules:
                    self.modules.append(m)
            return 1
                    
        elif(os.path.isfile(filepath + ".py") and filepath not in scaned_files):
            scaned_files.append(filepath)
            finalpath = filepath + ".py"
            source = open(finalpath, "r").read()
            root = ast.parse(source)
            a = ASTVisitor()
            classes = a.run(root, 1)
            classattributes = a.classattributes
            self.mergesubtype(a.parentclasses)
            for c in classes:
                self.finaltypes["indirect"].append([finalpath, self.transformpath(filepath, self.repopaths), c, self.getclassattr(classattributes, c)])
            return 1
        elif filepath in scaned_files:
            return 2
        else:
            return 0


    # extract indirectly imported types
    def extract_class(self, targetfiles):
        for e in targetfiles:
            filepath = self.buildpath(e[1], e[0])
            
            if(self.scan_file(filepath, e[0], self.repopaths) == 0):
                filepaths = self.find_file(e[0])
                if filepaths != None:
                    for filepath in filepaths:
                        self.scan_file(filepath, e[0], self.repopaths)
                else:
                    self.finaltypes["unrecognized_modules"].append(e[0].split(".")[0])

        for m in self.onlyimportedmodules:
            files = glob.glob("/".join(self.repopaths) + "/**/" + m + "/__init__.py", recursive = True)
            if len(files) == 0 and "." in m:
                files = glob.glob("/".join(self.repopaths) + "/**/" + m.replace(".", "/") + ".py", recursive = True)
            for f in files:
                finaltypes = self.parse_initfiles(f, self.repopaths)
                for t in finaltypes["direct"]:
                    self.finaltypes["indirect"].append(t)
                for t in finaltypes["indirect"]:
                    self.finaltypes["indirect"].append(t)
                for t in finaltypes["init"]:
                    self.finaltypes["indirect"].append([f, m, t[0], t[1]])
            if len(files) == 0:
                self.finaltypes["unrecognized_modules"].append(m)

            
    def getclassattr(self, classattr, c):
        if c in classattr:
            return classattr[c]
        else:
            return None

    # validate directly imported types
    def validate_type(self, types):
        for t in types:
            filepath = self.buildpath(t[2], t[0])
            if os.path.isfile(filepath + ".py"):
                finalpath = filepath + ".py"
                source = open(finalpath, "r").read()
                root = ast.parse(source)
                a = ASTVisitor()
                classes = a.run(root, 1)
                classattributes = a.classattributes
                self.mergesubtype(a.parentclasses)
                if(t[1] in classes):
                    self.finaltypes["direct"].append([finalpath, self.transformpath(filepath, self.repopaths), t[1], self.getclassattr(classattributes, t[1])])
            elif os.path.isfile(filepath + "/__init__.py"):
                types = self.parse_initfiles(filepath + "/__init__.py", self.repopaths)
                finalt = None
                for tt in types["indirect"]:
                    if t[1] == tt[2]:
                        finalt = [tt[0], self.transformpath(tt[0].replace(".py", ""), self.repopaths), t[1], tt[3]]
                for tt in types["init"]:
                    if t[1] == tt[0]:
                        finalt = [filepath + "/__init__.py", self.transformpath(filepath, self.repopaths), t[1], tt[1]]
                for tt in types["direct"]:
                    if t[1] == tt[2]:
                        finalt = [tt[0], self.transformpath(tt[0].replace(".py", ""), self.repopaths), t[1], tt[3]]
                if finalt != None:
                    self.finaltypes["direct"].append(finalt)
            else:
                finalpaths = self.find_file(t[0])
                if finalpaths != None:
                    for finalpath in finalpaths:
                        if finalpath != None and os.path.isfile(finalpath) and finalpath.endswith("__init__.py"):
                            finaltypes = self.parse_initfiles(finalpath, self.repopaths)
                            for f in finaltypes["direct"]:
                                if t[1] == f[2]:
                                    self.finaltypes["direct"].append([f[0], f[1], t[1], f[3]])

                        if finalpath != None and os.path.isfile(finalpath):
                            source = open(finalpath, "r").read()
                            root = ast.parse(source)
                            a = ASTVisitor()
                            classes = a.run(root, 1)
                            classattributes = a.classattributes
                            self.mergesubtype(a.parentclasses)
                            if(t[1] in classes):
                                self.finaltypes["direct"].append([finalpath, self.transformpath(filepath, self.repopaths), t[1], self.getclassattr(classattributes, t[1])])
                else:
                    self.finaltypes["unrecognized"].append(["", t[0], t[1]])

    # remove redundant indirectly imported types which occur as directly imported
    def remove_redundant_types(self):
        removed = []
        for ind in self.finaltypes["indirect"]:
            for d in self.finaltypes["direct"]:
                if ind[0] == d[0] and ind[2] == d[2]:
                    removed.append(ind)
        for r in removed:
            for ind in range(0, len(self.finaltypes["indirect"])):
                if self.finaltypes["indirect"][ind] == r:
                    del self.finaltypes["indirect"][ind]
                    break

        #replace <Cur_Repo> with . in the result
        for ind in self.finaltypes["indirect"]:
            if ind[1] == "<Cur_Repo>":
                ind[1] = "."
            elif "<Cur_Repo>" in ind[1]:
                ind[1] = ind[1].replace("<Cur_Repo>", "")
        for d in self.finaltypes["direct"]:
            if d[1] == "<Cur_Repo>":
                d[1] = "."
            elif "<Cur_Repo>" in d[1]:
                d[1] = d[1].replace("<Cur_Repo>", "")

        #remove types begin with lower case
        removed = []
        for t in self.finaltypes["direct"]:
            if t[2][0].islower():
                removed.append(t)
        for t in removed:
            if t in self.finaltypes["direct"]:
                self.finaltypes["direct"].remove(t)

        removed = []
        for t in self.finaltypes["indirect"]:
            if t[2][0].islower():
                removed.append(t)
        for t in removed:
            if t in self.finaltypes["indirect"]:
                self.finaltypes["indirect"].remove(t)


    def run(self, node):
        logger.info("Start finding user-defined types...")
        visitor = ASTVisitor()
        visitor.run(node, 1)
        self.types = visitor.types
        self.files = visitor.files
        self.modules = visitor.modules
        for c in visitor.classes:
            if c in visitor.classattributes:
                self.finaltypes["init"].append([c, visitor.classattributes[c]])
            else:
                self.finaltypes["init"].append([c, None])
        self.parentclasses = visitor.parentclasses
        self.onlyimportedmodules = visitor.onlyimportedmodules
        #print(self.files)
        #print(self.paths[:])
        self.scan_module()
        self.extract_class(self.files)
        if self.validate:
            self.validate_type(self.types)
        else:
            for t in self.types:
                self.finaltypes["direct"].append(["", t[0], t[1], None])
        self.remove_redundant_types()
        self.finaltypes["num"] = len(self.finaltypes["direct"]) + len(self.finaltypes["indirect"]) + len(self.finaltypes["init"]) + len(self.finaltypes["unrecognized"])
        self.finaltypes["module"] = self.modules
        logger.info("Finished finding user-defined types...")
        return self.finaltypes, self.parentclasses

    @func_set_timeout(300)
    def invoke(self, node):
        return self.run(node)

    def print_as_csv(self, verbose):
        for d in self.finaltypes["direct"]:
            print(d[0] + "," + d[1] + "," + d[2])
        for d in self.finaltypes["indirect"]:
            print(d[0] + "," + d[1] + "," + d[2])
        if verbose:
            for d in self.finaltypes["init"]:
                print(self.path + "," + self.transformpath(self.path.replace(".py", ""), self.repopaths) + "," + d[0])

        
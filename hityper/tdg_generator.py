from hityper.tdg import *
from hityper.typeobject import *
from hityper import logger
from hityper.stdtypes import builtin_method_properties, stdtypes, inputtypemap

import ast
from copy import deepcopy, copy
import sys, getopt
from pycg.pycg import CallGraphGenerator
from pycg import formats
from pycg.utils.constants import CALL_GRAPH_OP
import json

logger.name = __name__


# A map from ast nodes to op strings
AST2Op = {}
AST2Op[ast.Add] = "+"
AST2Op[ast.Sub] = "-"
AST2Op[ast.Mult] = "*"
AST2Op[ast.Div] = "/"
AST2Op[ast.FloorDiv] = "//"
AST2Op[ast.Mod] = "%"
AST2Op[ast.Pow] = "%"
AST2Op[ast.LShift] = "<<"
AST2Op[ast.RShift] = ">>"
AST2Op[ast.BitOr] = "|"
AST2Op[ast.BitXor] = "^"
AST2Op[ast.BitAnd] = "&"
AST2Op[ast.MatMult] = "@"
AST2Op[ast.UAdd] = "+"
AST2Op[ast.USub] = "-"
AST2Op[ast.Not] = "not"
AST2Op[ast.Invert] = "~"
AST2Op[ast.And] = "and"
AST2Op[ast.Or] = "or"
AST2Op[ast.Eq] = "=="
AST2Op[ast.NotEq] = "!="
AST2Op[ast.Lt] = "<"
AST2Op[ast.LtE] = "<="
AST2Op[ast.Gt] = ">"
AST2Op[ast.GtE] = ">="
AST2Op[ast.Is] = "is"
AST2Op[ast.IsNot] = "isnot"
AST2Op[ast.In] = "in"
AST2Op[ast.NotIn] = "not in"





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


def Attribute2Str_Call(node):
    temp1 = ''
    temp1 += Attribute2Str(node.func) + "("
    for argsnode in node.args:
        temp1 += (Attribute2Str(argsnode)+"_&")
    temp1 += ")"
    return temp1


class AliasAnalyzer(ast.NodeVisitor):
    def __init__(self, aliasgraph):
        self.aliasgraph = aliasgraph
        self.curfunc = None
        self.curclass = None
    
    def visit_ClassDef(self, node):
        if self.curclass == None:
            self.curclass = node.name
            self.generic_visit(node)
            self.curclass = None

    
    def visit_FunctionDef(self, node):
        if self.curfunc == None:
            self.curfunc = node.name
            self.generic_visit(node)
            self.curfunc = None

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)
    

    #check the assignment like self.xxx = xxx or cls.xxx = xxx, which may create alias
    def visit_Assign(self, node):
        if self.curclass == None:
            classstr = "global"
        else:
            classstr = self.curclass
        if self.curfunc == None:
            funcstr = "global"
        else:
            funcstr = self.curfunc
        if type(node.value) == ast.Attribute:
            attrstr = Attribute2Str(node.value)
            if "<Other>" in attrstr:
                logger.warning("Failed to initialize attribute " + attrstr)
            else:
                p = self.aliasgraph.addAttribute(attrstr, classstr + "@" + funcstr)
                if "()" not in attrstr:
                    for t in node.targets:
                        targetstr = Attribute2Str(t)
                        if "<Other>" not in targetstr:
                            q = self.aliasgraph.addAttribute(targetstr, classstr + "@" + funcstr)
                            q.alias.append(p)
                            p.alias.append(q)
        elif type(node.value) == ast.Name:
            attrtargets = []
            for t in node.targets:
                if type(t) == ast.Attribute or type(t) == ast.Name:
                    attrtargets.append(t)
            attrstr = Attribute2Str(node.value)
            p = self.aliasgraph.addAttribute(attrstr, classstr + "@" + funcstr)
            if "()" not in attrstr:
                for t in attrtargets:
                    targetstr = Attribute2Str(t)
                    if "<Other>" not in targetstr:
                        q = self.aliasgraph.addAttribute(targetstr, classstr + "@" + funcstr)
                        q.alias.append(p)
                        p.alias.append(q)


        self.generic_visit(node)


    def visit_AnnAssign(self, node):
        if node.value != None:
            if self.curclass == None:
                classstr = "global"
            else:
                classstr = self.curclass
            if self.curfunc == None:
                funcstr = "global"
            else:
                funcstr = self.curfunc
            if type(node.value) == ast.Attribute:
                attrstr = Attribute2Str(node.value)
                if "<Other>" in attrstr:
                    logger.warning("Failed to initialize attribute " + attrstr)
                else:
                    p = self.aliasgraph.addAttribute(attrstr, classstr + "@" + funcstr)
                    if "()" not in attrstr:
                        targetstr = Attribute2Str(node.target)
                        if "<Other>" not in targetstr:
                            q = self.aliasgraph.addAttribute(targetstr, classstr + "@" + funcstr)
                            q.alias.append(p)
                            p.alias.append(q)
            elif type(node.value) == ast.Name:
                attrstr = Attribute2Str(node.value)
                p = self.aliasgraph.addAttribute(attrstr, classstr + "@" + funcstr)
                if "()" not in attrstr:
                    targetstr = Attribute2Str(node.target)
                    if "<Other>" not in targetstr:
                        q = self.aliasgraph.addAttribute(targetstr, classstr + "@" + funcstr)
                        q.alias.append(p)
                        p.alias.append(q)
        
        self.generic_visit(node)



    def visit_Attribute(self, node):
        attrstr = Attribute2Str(node)
        if "<Other>" in attrstr:
            logger.warning("Unsupported attribute: " + attrstr)
        if self.curclass == None:
            classstr = "global"
        else:
            classstr = self.curclass
        if self.curfunc == None:
            funcstr = "global"
        else:
            funcstr = self.curfunc
        p = self.aliasgraph.addAttribute(attrstr, classstr + "@" + funcstr)
        if p == None:
            logger.warning("Failed to initialize attribute ", attrstr)



    def run(self, node):
        self.visit(node)
        return self.aliasgraph



class TDGGenerator(ast.NodeVisitor):
    def __init__(self, filename, optimize, locations, usertypes, alias = 0, repo = None):

        #usertypes
        self.usertypes = self.processUserTypes(usertypes)
        
        #type graph
        self.GlobalTG = GlobalTypeGraph(filename, self.usertypes)
        self.filename = filename
        self.tgstack = []

        #stacks and corresponding cusors
        self.curfunc = -1
        self.funcstack = []
        self.curclass = -1
        self.classstack = []
        self.curop = -1
        self.opstack = []

        #variable maps
        self.localvar2id = []
        self.lastlocalvar = []
        self.globalvar2id = {}
        self.lastglobalvar = {}
        self.attribute2id = []
        self.lastattribute = []
        
        #other info
        self.modules = []
        self.classnames = []

        if isinstance(locations, list):
            self.locations = locations
        elif locations == None:
            self.locations = locations
        else:
            logger.error("Invalid locations for generating TDGs.")
            raise ValueError("Invalid locations for generating TDGs.")
        self.visitedfuncs = []
        self.withitemnames = []
        self.withpos = []

        #flags
        self.asifcond = False
        self.subscriptwrite =  False
        self.augassignread = False
        self.forin = False
        self.optimized = optimize
        self.alias = alias
        self.repo = repo


        logger.info("Handling file #"+ filename)



    def processUserTypes(self, usertype):
        usertypes = []
        for t in usertype["direct"]:
            if t[2] not in usertypes:
                usertypes.append(t[2])
        for t in usertype["indirect"]:
            if t[2] not in usertypes:
                usertypes.append(t[2])
        for t in usertype["unrecognized"]:
            if t[2] not in usertypes:
                usertypes.append(t[2])
        for t in usertype["init"]:
            if t not in usertypes:
                usertypes.append(t[0])
        return usertypes


    def addNode(self, node):
        if self.curclass == -1 and self.curfunc == -1:
            self.GlobalTG.addNode(node)
        elif self.curfunc != -1:
            self.tgstack[self.curfunc].addNode(node)

    def searchNode(self, nodetype, nodename, nodepos):
        if self.curclass == -1 and self.curfunc == -1:
            for node in self.GlobalTG.globalnodes:
                if node.nodetype == nodetype and node.lineno == nodepos[0] and node.columnno == nodepos[1] and node.columnend == nodepos[2]:
                    if nodetype == "TypeGen" and node.op == nodename:
                        return node
                    elif nodetype == "Symbol" and node.symbol == nodename:
                        return node
        elif self.curfunc != -1:
            for node in self.tgstack[self.curfunc].nodes:
                if node.nodetype == nodetype and node.lineno == nodepos[0] and node.columnno == nodepos[1] and node.columnend == nodepos[2]:
                    if nodetype == "TypeGen" and node.op == nodename:
                        return node
                    elif nodetype == "Symbol" and node.symbol == nodename:
                        return node



    def extractTypeCondition(self, node, inverse = 1):
        '''
        if type(node) == ast.BoolOp and type(node.op) == ast.And:
            return self.extractTypeCondition(node.values[0], inverse) + self.extractTypeCondition(node.values[1], inverse)
        elif type(node) == ast.UnaryOp and type(node.op) == ast.Not:
            return self.extractTypeCondition(node.operand, inverse * -1)
        '''
        # type(x) == y
        if (type(node) == ast.Compare and type(node.left) == ast.Call and type(node.left.func) == ast.Name 
            and node.left.func.id == "type" and len(node.left.args) == 1 and len(node.ops) == 1 and type(node.ops[0]) in [ast.Eq, ast.NotEq]
            and len(node.comparators) == 1 and type(node.comparators[0]) in [ast.Name, ast.Attribute]):
            branchnode = BranchNode([], [], None)
            self.opstack.append(branchnode)
            self.curop += 1
            self.visit(node.left.args[0])
            typestr = Attribute2Str(node.comparators[0])
            if typestr in stdtypes["overall"]:
                typeobject = TypeObject(inputtypemap[typestr], 0)
            else:
                typeobject = TypeObject(typestr, 2)
            if type(node.ops[0]) == ast.NotEq:
                inverse = inverse * -1
            if inverse == 1:
                branchnode.addTypes([typeobject, None])
            else:
                branchnode.addTypes([None, typeobject])
            self.opstack.pop(self.curop)
            self.curop -= 1
            self.addNode(branchnode)
            return [branchnode]
        # x is y
        elif (type(node) == ast.Compare and (type(node.left) == ast.Name or type(node.left) == ast.Attribute) and len(node.ops) == 1
            and type(node.ops[0]) in [ast.Is, ast.IsNot] and len(node.comparators) == 1 and type(node.comparators[0]) in [ast.Name, ast.Attribute, ast.Constant]):
            branchnode = BranchNode([], [], None)
            self.opstack.append(branchnode)
            self.curop += 1
            self.visit(node.left)
            if type(node.comparators[0]) == ast.Constant:
                typeobject = transformConstant(node.comparators[0])
            else:
                typestr = Attribute2Str(node.comparators[0])
                if typestr in stdtypes["overall"]:
                    typeobject = TypeObject(inputtypemap[typestr], 0)
                else:
                    typeobject = TypeObject(typestr, 2)
            if type(node.ops[0]) == ast.IsNot:
                inverse = inverse * -1
            if inverse == 1:
                branchnode.addTypes([typeobject, None])
            else:
                branchnode.addTypes([None, typeobject])
            self.opstack.pop(self.curop)
            self.curop -= 1
            self.addNode(branchnode)
            return [branchnode]
        # isinstance(x,y)
        elif (type(node) == ast.Call and type(node.func) == ast.Name and node.func.id == "isinstance"
            and len(node.args) == 2 and type(node.args[1]) in [ast.Name, ast.Attribute]):
            branchnode = BranchNode([], [], None)
            self.opstack.append(branchnode)
            self.curop += 1
            self.visit(node.args[0])
            typestr = Attribute2Str(node.args[1])
            if typestr in stdtypes["overall"]:
                typeobject = TypeObject(inputtypemap[typestr], 0)
            else:
                typeobject = TypeObject(typestr, 2)
            if inverse == 1:
                branchnode.addTypes([typeobject, None])
            else:
                branchnode.addTypes([None, typeobject])
            self.opstack.pop(self.curop)
            self.curop -= 1
            self.addNode(branchnode)
            return [branchnode]
        else:
            if type(node) != ast.Constant:
                self.asifcond = True
                self.visit(node)
                self.asifcond = False
            return []

    def visitfield(self, field):
        for node in field:
            if node != None:
                self.visit(node)
    
    def buildmergename(self, nodes):
        namestr = ""
        for n in nodes:
            if isinstance(n, SymbolNode):
                if n.scope == "local":
                    namestr = namestr + str(n.symbol) + str(n.order)
                elif n.scope == "attribute":
                    namestr = namestr + str(n.classname) + "." + str(n.symbol) + str(n.order)
            elif isinstance(n, MergeNode):
                namestr = namestr + "(" + str(n.mergevar) + ")"
            elif isinstance(n, BranchNode):
                namestr = namestr + "(" + "branch " +str(n.branchvar) + " )"
            else:
                namestr += n.name
            namestr += ", "
        namestr = namestr[: len(namestr) - 2]
        return namestr

    def clearlast(self):
        if self.curclass != -1:
            for key in self.lastattribute[self.curclass]:
                self.lastattribute[self.curclass][key] = None
        for key in self.lastglobalvar:
            self.lastglobalvar[key] = None


    def addMergeNodes(self):
        varusemap = {}
        if self.curfunc != -1 and len(self.tgstack[self.curfunc].loopbuffer) >= self.tgstack[self.curfunc].inloop:
            loopbuffer = self.tgstack[self.curfunc].loopbuffer[self.tgstack[self.curfunc].inloop - 1]
        elif self.curfunc != -1 and len(self.tgstack[self.curfunc].loopbuffer) < self.tgstack[self.curfunc].inloop:
            return
        elif len(self.GlobalTG.loopbuffer) >= self.GlobalTG.inloop:
            loopbuffer = self.GlobalTG.loopbuffer[self.GlobalTG.inloop - 1]
        else:
            return

        for n in loopbuffer:
            if isinstance(n, SymbolNode):
                if n.symbol not in varusemap:
                    varusemap[n.symbol] = n
                elif n.order < varusemap[n.symbol].order:
                    varusemap[n.symbol] = n

        #if first use is write, then do not add merge
        changed = True
        while(changed):
            changed = False
            for key in varusemap:
                if len(varusemap[key].ins) > 1:
                    raise ValueError("Symbol nodes should not have more than 1 input nodes.")
                elif varusemap[key].ctx != "Load":
                    del varusemap[key]
                    changed = True
                    break

                
        #add merge nodes for the first use
        for key in varusemap:
            if key in self.lastglobalvar:
                mergenode = MergeNode([varusemap[key].ins[0], self.lastglobalvar[key]], [varusemap[key]], self.buildmergename([varusemap[key].ins[0], self.lastglobalvar[key]]))
                varusemap[key].ins[0].addOuts(mergenode)
                varusemap[key].ins[0].outs.remove(varusemap[key])
                self.lastglobalvar[key].addOuts(mergenode)
            elif self.curclass != -1 and key in self.lastattribute[self.curclass]:
                mergenode = MergeNode([varusemap[key].ins[0], self.lastattribute[self.curclass][key]], [varusemap[key]], self.buildmergename([varusemap[key].ins[0], self.lastattribute[self.curclass][key]]))
                varusemap[key].ins[0].addOuts(mergenode)
                varusemap[key].ins[0].outs.remove(varusemap[key])
                self.lastattribute[self.curclass][key].addOuts(mergenode)
            elif self.curfunc != -1 and key in self.lastlocalvar[self.curfunc]:
                mergenode = MergeNode([varusemap[key].ins[0], self.lastlocalvar[self.curfunc][key]], [varusemap[key]], self.buildmergename([varusemap[key].ins[0], self.lastlocalvar[self.curfunc][key]]))
                varusemap[key].ins[0].addOuts(mergenode)
                varusemap[key].ins[0].outs.remove(varusemap[key])
                self.lastlocalvar[self.curfunc][key].addOuts(mergenode)
            varusemap[key].ins = [mergenode]
            self.addNode(mergenode)


    def addMerge4Except(self):
        if self.curfunc != -1 and len(self.tgstack[self.curfunc].trybuffer) >= self.tgstack[self.curfunc].intry:
            trybuffer = self.tgstack[self.curfunc].trybuffer[self.tgstack[self.curfunc].intry - 1]
        elif self.curfunc != -1 and len(self.tgstack[self.curfunc].trybuffer) < self.tgstack[self.curfunc].intry:
            #self.tgstack[self.curfunc].trybuffer.append({})
            return 
        elif len(self.GlobalTG.trybuffer) >= self.GlobalTG.intry:
            trybuffer = self.GlobalTG.trybuffer[self.GlobalTG.intry - 1]
        elif len(self.GlobalTG.trybuffer) < self.GlobalTG.intry :
            #self.GlobalTG.trybuffer.append({})
            return

        for key in trybuffer:
            nodes = trybuffer[key]
            if key in self.lastglobalvar and self.lastglobalvar[key] != None:
                nodes = [self.lastglobalvar[key]] + nodes
                mergenode = MergeNode(nodes, [], self.buildmergename(nodes))
                self.lastglobalvar[key] = mergenode
                for n in nodes:
                    n.addOuts(mergenode)
            elif self.curclass != -1 and key in self.lastattribute[self.curclass] and self.lastattribute[self.curclass][key] != None:
                nodes = [self.lastattribute[self.curclass][key]] + nodes
                mergenode = MergeNode(nodes, [], self.buildmergename(nodes))
                self.lastattribute[self.curclass][key] = mergenode
                for n in nodes:
                    n.addOuts(mergenode)
            elif self.curfunc != -1 and key in self.lastlocalvar[self.curfunc]:
                nodes = [self.lastlocalvar[self.curfunc][key]] + nodes
                mergenode = MergeNode(nodes, [], self.buildmergename(nodes))
                self.lastlocalvar[self.curfunc][key] = mergenode
                for n in nodes:
                    n.addOuts(mergenode)
            else:
                mergenode = MergeNode(nodes, [], self.buildmergename(nodes))
                if self.curfunc != -1:
                    self.lastlocalvar[self.curfunc][key] = mergenode
                elif self.curclass != -1:
                    self.lastattribute[self.curclass][key] = mergenode
                else:
                    self.lastglobalvar[key] = mergenode
                for n in nodes:
                    n.addOuts(mergenode)
            self.addNode(mergenode)


    def addMerge4Finally(self):
        if self.curfunc != -1:
            exceptbuffer = self.tgstack[self.curfunc].exceptbuffer
        else:
            exceptbuffer = self.GlobalTG.exceptbuffer
        keys = []
        for b in exceptbuffer:
            keys += b.keys()
        for key in keys:
            nodes = []
            if key in self.lastglobalvar and self.lastglobalvar[key] != None:
                nodes.append(self.lastglobalvar[key])
            elif self.curfunc != -1 and key in self.lastlocalvar[self.curfunc] and self.lastlocalvar[self.curfunc][key] != None:
                nodes.append(self.lastlocalvar[self.curfunc][key])
            elif self.curclass != -1 and key in self.lastattribute[self.curclass] and self.lastattribute[self.curclass][key] != None:
                nodes.append(self.lastattribute[self.curclass][key])
            for b in exceptbuffer:
                if key in b:
                    nodes.append(b[key])
            if len(nodes) == 1:
                if nodes[0].scope == "local":
                    self.lastlocalvar[self.curfunc][key] = nodes[0]
                elif nodes[0].scope == "global":
                    self.lastglobalvar[key] = nodes[0]
                elif nodes[0].scope == "attribute":
                    self.lastattribute[self.curclass][key] = nodes[0]
            else:
                
                mergenode = MergeNode(nodes, [], self.buildmergename(nodes))
                if self.curfunc != -1:
                    self.lastlocalvar[self.curfunc][key] = mergenode
                elif self.curclass != -1:
                    self.lastattribute[self.curclass][key] = mergenode
                else:
                    self.lastglobalvar[key] = mergenode
                for n in nodes:
                    n.addOuts(mergenode)
                self.addNode(mergenode)
            



            

    def visit_Import(self, node):
        for i in node.names:
            if i.asname != None:
                self.modules.append(i.asname)
            else:
                self.modules.append(i.name)

    def visit_ImportFrom(self, node):
        for i in node.names:
            if i.asname != None:
                self.modules.append(i.asname)
            else:
                self.modules.append(i.name)
        


    def visit_ClassDef(self, node):
        self.classstack.append(node.name)
        self.curclass += 1
        self.attribute2id.append({})
        self.lastattribute.append({})

        #add classname as a type
        if len(self.classstack) == 1:
            self.classnames.append(node.name)


        self.visitfield(node.body)

        self.classstack.pop(self.curclass)
        self.attribute2id.pop(self.curclass)
        self.lastattribute.pop(self.curclass)
        self.curclass -= 1

    def visit_FunctionDef(self, node):
        if len(self.classstack) != 0:
            funcname = node.name + "@"
            for c in self.classstack:
                funcname = funcname + c + ","
            funcname = funcname[: len(funcname) -1]
        else:
            funcname = node.name + "@global"
        if ((self.locations != None and funcname in self.locations) or self.locations == None) and funcname not in self.visitedfuncs:
            self.visitedfuncs.append(funcname)
            logger.debug("[3rd Pass: TDG Generation] Visiting Function #" + funcname + "# at Line: " + str(node.lineno))
            self.funcstack.append(node.name)
            self.curfunc += 1
            if self.curclass != -1:
                classname = self.classstack[self.curclass]
            else:
                classname = None
            tg = TypeGraph(funcname, self.usertypes, self.filename, classname, self.GlobalTG)
            tg.startlineno = node.lineno
            self.tgstack.append(tg)
            self.localvar2id.append({})
            self.lastlocalvar.append({})




        
            self.clearlast()
            self.visit(node.args)
            self.visitfield(node.body)
            self.clearlast()

            self.finalize(tg)
            self.GlobalTG.addTG(tg)
            self.funcstack.pop(self.curfunc)
            self.tgstack.pop(self.curfunc)
            self.localvar2id.pop(self.curfunc)
            self.lastlocalvar.pop(self.curfunc)
            self.curfunc -= 1
        else:
            pass

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)


    def visit_arguments(self, node):
        self.visitfield(node.args)
        self.visitfield(node.kwonlyargs)
        if node.kwarg != None:
            self.visit(node.kwarg)
        if node.vararg != None:
            self.visit(node.vararg)


        if len(node.defaults) != 0:
            index_offset = len(node.args) - len(node.defaults)
            for i in range(0, len(node.args)):
                if i - index_offset >= 0:
                    index = i-index_offset
                    if type(node.defaults[index]) == ast.Constant and transformConstant(node.defaults[index]) != None:
                        typenode = TypeNode([self.lastlocalvar[self.curfunc][node.args[i].arg]], transformConstant(node.defaults[index]))
                        typenode.setNodePos(node.defaults[index].lineno, node.defaults[index].col_offset, node.defaults[index].end_col_offset)
                        self.lastlocalvar[self.curfunc][node.args[i].arg].addIns(typenode)
                        self.addNode(typenode)
                    elif type(node.defaults[index]) == ast.Name:
                        typegen = TypeGenNode("=", [], [self.lastlocalvar[self.curfunc][node.args[i].arg]])
                        typegen.setNodePos(node.defaults[index].lineno, node.defaults[index].col_offset, node.defaults[index].end_col_offset)
                        self.opstack.append(typegen)
                        self.curop += 1
                        self.visit(node.defaults[index])
                        self.opstack.pop(self.curop)
                        self.curop -= 1
                        self.lastlocalvar[self.curfunc][node.args[i].arg].addIns(typegen)
                        self.addNode(typegen)
                    #we are not sure what initial value developers will give, it's rediculous
                    elif type(node.defaults[index]) != ast.Constant:
                        typegen = TypeGenNode("=", [], [self.lastlocalvar[self.curfunc][node.args[i].arg]])
                        typegen.setNodePos(node.defaults[index].lineno, node.defaults[index].col_offset, node.defaults[index].end_col_offset)
                        self.opstack.append(typegen)
                        self.curop += 1
                        self.visit(node.defaults[index])
                        self.opstack.pop(self.curop)
                        self.curop -= 1
                        self.lastlocalvar[self.curfunc][node.args[i].arg].addIns(typegen)
                        self.addNode(typegen)

        if len(node.kw_defaults) != 0:
            for i in range(0, len(node.kw_defaults)):
                if node.kw_defaults[i] != None:
                    if type(node.kw_defaults[i]) == ast.Constant and transformConstant(node.kw_defaults[i]) != None:
                        typenode = TypeNode([self.lastlocalvar[self.curfunc][node.kwonlyargs[i].arg]], transformConstant(node.kw_defaults[i]))
                        typenode.setNodePos(node.kw_defaults[i].lineno, node.kw_defaults[i].col_offset, node.kw_defaults[i].end_col_offset)
                        self.lastlocalvar[self.curclass][node.kwonlyargs[i].arg].addIns(typenode)
                        self.addNode(typenode)
                    elif type(node.kw_defaults[i]) == ast.Name:
                        typegen = TypeGenNode("=", [], [self.lastlocalvar[self.curfunc][node.kwonlyargs[i].arg]])
                        typegen.setNodePos(node.kw_defaults[i].lineno, node.kw_defaults[i].col_offset, node.kw_defaults[i].end_col_offset)
                        self.opstack.append(typegen)
                        self.curop += 1
                        self.visit(node.kw_defaults[i])
                        self.opstack.pop(self.curop)
                        self.curop -= 1
                        self.lastlocalvar[self.curfunc][node.kwonlyargs[i].arg].addIns(typegen)
                        self.addNode(typegen)
                    #we are not sure what initial value developers will give, it's rediculous
                    elif type(node.kw_defaults[i]) != ast.Constant:
                        typegen = TypeGenNode("=", [], [self.lastlocalvar[self.curfunc][node.kwonlyargs[i].arg]])
                        typegen.setNodePos(node.kw_defaults[i].lineno, node.kw_defaults[i].col_offset, node.kw_defaults[i].end_col_offset)
                        self.opstack.append(typegen)
                        self.curop += 1
                        self.visit(node.kw_defaults[i])
                        self.opstack.pop(self.curop)
                        self.curop -= 1
                        self.lastlocalvar[self.curfunc][node.kwonlyargs[i].arg].addIns(typegen)
                        self.addNode(typegen)





    def visit_arg(self, node):
        if node.arg != "self":
            self.localvar2id[self.curfunc][node.arg] = 0
            symbol = SymbolNode([], [], node.arg + "(arg)", 0, ctx = "Arg")
            symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
            self.lastlocalvar[self.curfunc][node.arg] = symbol
            self.tgstack[self.curfunc].addNode(symbol)

    def visit_keyword(self, node):
        self.visit(node.value)



    def visit_Assign(self, node):

        #TypeGenNode
        typegen = TypeGenNode("=", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)


        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.value)
        self.visitfield(node.targets)

        self.opstack.pop(self.curop)
        self.curop -= 1
        if self.curop != -1:
            typegen.addOuts(self.opstack[self.curop])
            self.opstack[self.curop].addIns(typegen)
        self.addNode(typegen)


    def visit_AugAssign(self, node):
        typegen = TypeGenNode(AST2Op[type(node.op)], [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1

        self.augassignread = True
        self.visit(node.target)
        self.visit(node.value)
        self.augassignread = False

        self.opstack.pop(self.curop)
        self.curop -= 1

        typegen2 = TypeGenNode("=", [typegen], [])
        typegen2.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen2)
        self.curop += 1

        self.visit(node.target)

        self.opstack.pop(self.curop)
        self.curop -= 1
        typegen.addOuts(typegen2)
        if self.curop != -1 and not self.asifcond:
            typegen2.addOuts(self.opstack[self.curop])
            self.opstack[self.curop].addIns(typegen2)
        self.addNode(typegen)
        self.addNode(typegen2)

    def visit_AnnAssign(self, node):
        if node.value != None:
            typegen = TypeGenNode("=", [], [])
            typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)


            self.opstack.append(typegen)
            self.curop += 1

            if node.value != None:
                self.visit(node.value)
            if node.target != None:
                self.visit(node.target)

            self.opstack.pop(self.curop)
            self.curop -= 1
            if self.curop != -1:
                typegen.addOuts(self.opstack[self.curop])
                self.opstack[self.curop].addIns(typegen)
            self.addNode(typegen)

    def visit_Call(self, node):
        asifcond = self.asifcond
        if self.asifcond:
            self.asifcond = False

        #Type Gen Node
        typegen = TypeGenNode("call", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1

        #case 1: independent functions, such as func()
        if isinstance(node.func, ast.Name):
            typegen.setFunc(node.func.id)
            self.visitfield(node.args)
            self.visitfield(node.keywords)



        #case 2: property functions, such as a.append()
        elif isinstance(node.func, ast.Attribute):
            attrstr = Attribute2Str(node.func)
            if attrstr.count("_@_") > 1:
                typegen.setFunc(attrstr)
                self.visitfield(node.args)
                self.visitfield(node.keywords)
            else:
                typegen.setFunc(node.func.attr)
                if type(node.func.value) == ast.Name and node.func.value.id == "self":
                    self.visit(node.func.value)
                    typegen.attr = "self"
                else:
                    self.visit(node.func.value)
                    typegen.attr = Attribute2Str(node.func.value)
                self.visitfield(node.args)
                self.visitfield(node.keywords)

                if node.func.attr in builtin_method_properties["self-changable"]["overall"]:
                    if isinstance(typegen.ins[0], SymbolNode):
                        symbol = SymbolNode([typegen], [], typegen.ins[0].symbol, 0, classname=typegen.ins[0].classname, scope=typegen.ins[0].scope)
                        symbol.setNodePos(typegen.ins[0].lineno, typegen.ins[0].columnno, typegen.ins[0].columnend)
                        symbol.ctx = "Write"
                        if self.curfunc != -1:
                            if symbol.symbol in self.localvar2id[self.curfunc]:
                                self.localvar2id[self.curfunc][symbol.symbol] += 1
                            else:
                                self.localvar2id[self.curfunc][symbol.symbol] = 0
                            self.lastlocalvar[self.curfunc][symbol.symbol] = symbol
                            symbol.order = self.localvar2id[self.curfunc][symbol.symbol]
                        elif symbol.symbol in self.globalvar2id:
                            self.globalvar2id[symbol.symbol] += 1
                            symbol.order = self.globalvar2id[symbol.symbol]
                            self.lastglobalvar[symbol.symbol] = symbol
                        self.addNode(symbol)
                        typegen.addOuts(symbol)
        

        self.opstack.pop(self.curop)
        self.curop -= 1
        if self.curop != -1 and not asifcond:
            typegen.addOuts(self.opstack[self.curop])
            self.opstack[self.curop].addIns(typegen)

        self.addNode(typegen)

    def visit_Subscript(self, node):
        asifcond = self.asifcond
        if self.asifcond:
            self.asifcond = False
        subscriptwrite = self.subscriptwrite
        if self.subscriptwrite:
            self.subscriptwrite = False
        if (type(node.ctx) == ast.Store or subscriptwrite) and not self.augassignread:
            typegen = TypeGenNode("Subscript_Write", [], [])
            typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
            self.opstack.append(typegen)
            self.curop += 1

            if not subscriptwrite:
                self.visit(node.value)
            elif type(node.value) == ast.Subscript:
                pre_node = self.searchNode("TypeGen", "Subscript_Read", [node.value.lineno, node.value.col_offset, node.value.end_col_offset])
                if pre_node != None:
                    typegen.addIns(pre_node)
                    pre_node.addOuts(typegen)
            else:
                self.visit(node.value)
            self.visit(node.slice)

            self.opstack.pop(self.curop)
            self.curop -= 1

            if isinstance(typegen.ins[0], SymbolNode):
                symbol = SymbolNode([typegen], [], typegen.ins[0].symbol, 0, classname=typegen.ins[0].classname, scope=typegen.ins[0].scope)
                symbol.setNodePos(typegen.ins[0].lineno, typegen.ins[0].columnno, typegen.ins[0].columnend)
                symbol.ctx = "Write"
                if symbol.symbol in self.globalvar2id:
                    self.globalvar2id[symbol.symbol] += 1
                    symbol.order = self.globalvar2id[symbol.symbol]
                    self.lastglobalvar[symbol.symbol] = symbol
                elif self.curfunc != -1 and symbol.symbol in self.localvar2id[self.curfunc]:
                    self.localvar2id[self.curfunc][symbol.symbol] += 1
                    symbol.order = self.localvar2id[self.curfunc][symbol.symbol]
                    self.lastlocalvar[self.curfunc][symbol.symbol] = symbol
                elif self.curclass != -1 and symbol.symbol in self.attribute2id[self.curclass]:
                    self.attribute2id[self.curclass][symbol.symbol] += 1
                    symbol.order = self.attribute2id[self.curclass][symbol.symbol]
                    self.lastattribute[self.curclass][symbol.symbol] = symbol
                self.addNode(symbol)

                typegen.addOuts(symbol)
            elif isinstance(node.value, ast.Name) and node.value.id == "self":
                symbol = SymbolNode([typegen], [], "self", 0, classname=self.classstack[self.curclass], scope=self.funcstack[self.curfunc])
                symbol.setNodePos(typegen.ins[0].lineno, typegen.ins[0].columnno, typegen.ins[0].columnend)
                symbol.ctx = "Write"
                if self.curclass != -1:
                    if symbol.symbol in self.attribute2id[self.curclass]:
                        self.attribute2id[self.curclass][symbol.symbol] += 1
                        symbol.order = self.attribute2id[self.curclass][symbol.symbol]
                        self.lastattribute[self.curclass][symbol.symbol] = symbol
                    else:
                        self.attribute2id[self.curclass][symbol.symbol] = 0
                        symbol.order = 0
                        self.lastattribute[self.curclass][symbol.symbol] = symbol
                self.addNode(symbol)

                typegen.addOuts(symbol)
            else:
                self.opstack.append(typegen)
                self.curop += 1
                self.subscriptwrite = True
                self.visit(node.value)
                self.opstack.pop(self.curop)
                self.curop -= 1
                self.subscriptwrite = False
            
            if not asifcond and self.curop != -1:
                typegen.addIns(self.opstack[self.curop])
                self.opstack[self.curop].addOuts(typegen)
            self.addNode(typegen)

        elif type(node.ctx) == ast.Load or self.augassignread:
            typegen = TypeGenNode("Subscript_Read", [], [])
            typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
            self.opstack.append(typegen)
            self.curop += 1

            self.visit(node.value)
            self.visit(node.slice)

            self.opstack.pop(self.curop)
            self.curop -= 1
            if not asifcond and self.curop != -1:
                typegen.addOuts(self.opstack[self.curop])
                self.opstack[self.curop].addIns(typegen)
            self.addNode(typegen)



    def visit_Slice(self, node):
        self.generic_visit(node)

    def visit_Index(self, node):
        self.visit(node.value)

    def visit_BinOp(self, node):

        asifcond = self.asifcond
        if self.asifcond == True:
            self.asifcond = False

        #Type Gen Node
        typegen = TypeGenNode(AST2Op[type(node.op)], [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.left)

        self.visit(node.right)


        self.opstack.pop(self.curop)
        self.curop -= 1
        if not asifcond and self.curop != -1:
            typegen.addOuts(self.opstack[self.curop])
            self.opstack[self.curop].addIns(typegen)

        #typegen.performTypingRules()
        self.addNode(typegen)


    def visit_UnaryOp(self, node):
        asifcond = self.asifcond
        if self.asifcond:
            self.asifcond = False

        typegen = TypeGenNode(AST2Op[type(node.op)], [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.operand)

        self.opstack.pop(self.curop)
        self.curop -= 1

        if not asifcond and self.curop != -1:
            typegen.addOuts(self.opstack[self.curop])
            self.opstack[self.curop].addIns(typegen)
        #typegen.performTypingRules()
        self.addNode(typegen)


    def visit_Constant(self, node):
        if self.curop != -1:
            typeobject = transformConstant(node)
            if typeobject != None:
                typenode = TypeNode([self.opstack[self.curop]], typeobject)
                typenode.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                self.opstack[self.curop].addIns(typenode)
                self.addNode(typenode)


    def visit_Name(self, node):
        if (node.id in stdtypes["overall"] or node.id in self.classnames or node.id in self.classstack) and type(node.ctx) == ast.Load:
            if self.curop != -1:
                if node.id in stdtypes["overall"]:
                    #typeobject = TypeObject(inputtypemap[node.id], 0)
                    typeobject = TypeObject(node.id, 0)
                else:
                    typeobject = TypeObject(node.id, 2)
                typenode = TypeNode([self.opstack[self.curop]], typeobject)
                typenode.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                self.opstack[self.curop].addIns(typenode)
                self.addNode(typenode)

        elif node.id in stdtypes["errors"] or node.id in stdtypes["warnings"]:
            if self.curop != -1:
                typeobject = TypeObject(node.id, 0)
                typenode = TypeNode([self.opstack[self.curop]], typeobject)
                typenode.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                self.opstack[self.curop].addIns(typenode)
                self.addNode(typenode)

        elif node.id == "self" and type(node.ctx) == ast.Load and not self.subscriptwrite:
            if self.curclass == -1:
                raise ValueError("self should be used within class.")
            typeobject = TypeObject(self.classstack[self.curclass], 2)
            typenode = TypeNode([self.opstack[self.curop]], typeobject)
            typenode.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
            if self.curop != -1 and not self.asifcond:
                self.opstack[self.curop].addIns(typenode)
            self.addNode(typenode)

        elif type(node.ctx) == ast.Load or (self.augassignread and not self.forin):
            #case 1: global variable
            if (self.curclass == -1 and self.curfunc == -1) or node.id in self.globalvar2id:
                if node.id not in self.globalvar2id:
                    if node.id in self.modules:
                        if self.curop != -1 and not self.asifcond:
                            symbol = SymbolNode([], [self.opstack[self.curop]], node.id, 0, scope = "module")
                        else:
                            symbol = SymbolNode([], [], node.id, 0, scope = "module")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        if self.curop != -1 and not self.asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.addNode(symbol)
                    else:
                        if node.id.startswith("__") and node.id.endswith("__"):
                            self.globalvar2id[node.id] = 0
                            if self.curop != -1 and not self.asifcond:
                                symbol = SymbolNode([], [self.opstack[self.curop]], node.id, self.globalvar2id[node.id], scope = "global")
                            else:
                                symbol = SymbolNode([], [], node.id, self.globalvar2id[node.id], scope = "global")
                            symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                            self.lastglobalvar[node.id] = symbol
                            if self.curop != -1 and not self.asifcond:
                                self.opstack[self.curop].addIns(symbol)
                            self.addNode(symbol)
                        else:
                            self.globalvar2id[node.id] = 0
                            if self.curop != -1 and not self.asifcond:
                                symbol = SymbolNode([], [self.opstack[self.curop]], node.id, self.globalvar2id[node.id], scope = "global")
                            else:
                                symbol = SymbolNode([], [], node.id, self.globalvar2id[node.id], scope = "global")
                            symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                            self.lastglobalvar[node.id] = symbol
                            if self.curop != -1 and not self.asifcond:
                                self.opstack[self.curop].addIns(symbol)
                            self.addNode(symbol)
                            logger.warning(node.id + " variable is read but it is not previously defined!")
                else:
                    self.globalvar2id[node.id] += 1
                    if self.curop != -1 and not self.asifcond:
                        #the first time being read in a function
                        if node.id not in self.lastglobalvar or self.lastglobalvar[node.id] == None:
                            symbol = SymbolNode([], [self.opstack[self.curop]], node.id, self.globalvar2id[node.id], scope = "global")
                            if self.curfunc != -1:
                                self.GlobalTG.addNode(symbol)
                        else:
                            symbol = SymbolNode([self.lastglobalvar[node.id]], [self.opstack[self.curop]], node.id, self.globalvar2id[node.id], scope = "global")
                            self.lastglobalvar[node.id].addOuts(symbol)
                    else:
                        #the first time being read in a function
                        if node.id not in self.lastglobalvar or self.lastglobalvar[node.id] == None:
                            symbol = SymbolNode([], [], node.id, self.globalvar2id[node.id], scope = "global")
                            if self.curfunc != -1:
                                self.GlobalTG.addNode(symbol)
                        else:
                            symbol = SymbolNode([self.lastglobalvar[node.id]], [], node.id, self.globalvar2id[node.id], scope = "global")
                            self.lastglobalvar[node.id].addOuts(symbol)
                    symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                    self.lastglobalvar[node.id] = symbol
                    if self.curop != -1 and not self.asifcond:
                        self.opstack[self.curop].addIns(symbol)
                    self.addNode(symbol)
            #case 2: local variable
            elif self.curfunc != -1:
                if node.id not in self.localvar2id[self.curfunc] or node.id not in self.lastlocalvar[self.curfunc]:
                    if node.id in self.modules:
                        if self.curop != -1 and not self.asifcond:
                            symbol = SymbolNode([], [self.opstack[self.curop]], node.id, 0, scope = "module")
                        else:
                            symbol = SymbolNode([], [], node.id, 0, scope = "module")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        if self.curop != -1 and not self.asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.addNode(symbol)
                    elif node.id.startswith("__") and node.id.endswith("__"):
                        self.localvar2id[self.curfunc][node.id] = 0
                        if self.curop != -1 and not self.asifcond:
                            symbol = SymbolNode([], [self.opstack[self.curop]], node.id, self.localvar2id[self.curfunc][node.id])
                        else:
                            symbol = SymbolNode([], [], node.id, self.localvar2id[self.curfunc][node.id])
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastlocalvar[self.curfunc][node.id] = symbol
                        if self.curop != -1 and not self.asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.tgstack[self.curfunc].addNode(symbol)
                    else:
                        self.localvar2id[self.curfunc][node.id] = 0
                        if self.curop != -1 and not self.asifcond:
                            symbol = SymbolNode([], [self.opstack[self.curop]], node.id, self.localvar2id[self.curfunc][node.id])
                        else:
                            symbol = SymbolNode([], [], node.id, self.localvar2id[self.curfunc][node.id])
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastlocalvar[self.curfunc][node.id] = symbol
                        if self.curop != -1 and not self.asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.tgstack[self.curfunc].addNode(symbol)
                        logger.warning(node.id + " variable is read but it is not previously defined! Line: " + str(node.lineno))
                else:
                    self.localvar2id[self.curfunc][node.id] += 1
                    if self.curop != -1 and not self.asifcond:
                        symbol = SymbolNode([self.lastlocalvar[self.curfunc][node.id]], [self.opstack[self.curop]], node.id, self.localvar2id[self.curfunc][node.id])
                    else:
                        symbol = SymbolNode([self.lastlocalvar[self.curfunc][node.id]], [], node.id, self.localvar2id[self.curfunc][node.id])
                    symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                    self.lastlocalvar[self.curfunc][node.id].addOuts(symbol)
                    self.lastlocalvar[self.curfunc][node.id] = symbol
                    if self.curop != -1 and not self.asifcond:
                        self.opstack[self.curop].addIns(symbol)
                    self.tgstack[self.curfunc].addNode(symbol)
        elif type(node.ctx) == ast.Del:
            #case 1: global variable
            if (self.curclass == -1 and self.curfunc == -1) or node.id in self.globalvar2id:
                if node.id not in self.globalvar2id:
                    pass
                    #raise ValueError( node.id + "does not exist.")
                else:
                    del self.globalvar2id[node.id]
                    del self.lastglobalvar[node.id]
            #case 2: local variable
            if self.curfunc != -1:
                if node.id not in self.localvar2id[self.curfunc]:
                    raise ValueError( node.id + "does not exist.")
                else:
                    del self.localvar2id[self.curfunc][node.id]
                    del self.lastlocalvar[self.curfunc][node.id]
        elif type(node.ctx) == ast.Store:
            #case 1: global variable
            if (self.curclass == -1 and self.curfunc == -1) or node.id in self.globalvar2id:
                if node.id not in self.globalvar2id:
                    self.globalvar2id[node.id] = 0
                else:
                    self.globalvar2id[node.id] += 1
                symbol = SymbolNode([self.opstack[self.curop]], [], node.id, self.globalvar2id[node.id], scope = "global", ctx = "Write")
                symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                self.opstack[self.curop].addOuts(symbol)
                self.lastglobalvar[node.id] = symbol
                self.addNode(symbol)
            #case 2: local variables
            elif self.curfunc != -1:
                if node.id not in self.localvar2id[self.curfunc]:
                    self.localvar2id[self.curfunc][node.id] = 0
                else:
                    self.localvar2id[self.curfunc][node.id] += 1
                symbol = SymbolNode([self.opstack[self.curop]], [], node.id,  self.localvar2id[self.curfunc][node.id], ctx = "Write")
                symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                self.lastlocalvar[self.curfunc][node.id] = symbol
                self.opstack[self.curop].addOuts(symbol)
                self.tgstack[self.curfunc].addNode(symbol)

        else:
            raise ValueError("Do not support such Name node.")


    def visit_Attribute(self, node):

        attrstr = Attribute2Str(node)

        asifcond = self.asifcond
        if self.asifcond == True:
            self.asifcond = False

        if "<Other>" in attrstr:
            typegen = TypeGenNode(".", [], [], attr = node.attr)
            typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

            self.opstack.append(typegen)
            self.curop += 1

            self.visit(node.value)

            self.opstack.pop(self.curop)
            self.curop -= 1

            self.addNode(typegen)
            if not asifcond  and self.curop != -1:
                typegen.addOuts(self.opstack[self.curop])
                self.opstack[self.curop].addIns(typegen)

        #case 1: depth = 2
        elif attrstr.count("_@_") == 1:

            if type(node.value) == ast.Constant:
                typegen = TypeGenNode(".", [], [], attr = node.attr)
                typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

                self.opstack.append(typegen)
                self.curop += 1

                self.visit(node.value)

                self.opstack.pop(self.curop)
                self.curop -= 1

                self.addNode(typegen)
                if not asifcond  and self.curop != -1:
                    typegen.addOuts(self.opstack[self.curop])
                    self.opstack[self.curop].addIns(typegen)


            elif type(node.value) == ast.Name and node.value.id == "self":
                if type(node.ctx) == ast.Load or self.augassignread:
                    if self.curclass == -1:
                        raise ValueError("self should be used within a class.")
                    if node.attr not in self.attribute2id[self.curclass]:
                        self.attribute2id[self.curclass][node.attr] = 0
                        if self.curop != -1 and not asifcond:
                            symbol = SymbolNode([], [self.opstack[self.curop]], node.attr, self.attribute2id[self.curclass][node.attr], classname = self.classstack[self.curclass], scope = "attribute")
                        else:
                            symbol = SymbolNode([], [], node.attr, self.attribute2id[self.curclass][node.attr], classname = self.classstack[self.curclass], scope = "attribute")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastattribute[self.curclass][node.attr] = symbol
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.GlobalTG.addNode(symbol)
                        if self.curfunc != -1:
                            self.tgstack[self.curfunc].addNode(symbol)
                    else:
                        self.attribute2id[self.curclass][node.attr] += 1
                        if self.curop != -1 and not asifcond:
                            #occur first time in else branch of if statement
                            if node.attr not in self.lastattribute[self.curclass] or self.lastattribute[self.curclass][node.attr] == None:
                                symbol = SymbolNode([], [self.opstack[self.curop]], node.attr, self.attribute2id[self.curclass][node.attr], classname = self.classstack[self.curclass], scope = "attribute")
                                if self.curfunc != -1:
                                    self.GlobalTG.addNode(symbol)
                            else:
                                symbol = SymbolNode([self.lastattribute[self.curclass][node.attr]], [self.opstack[self.curop]], node.attr, self.attribute2id[self.curclass][node.attr], classname = self.classstack[self.curclass], scope = "attribute")
                                self.lastattribute[self.curclass][node.attr].addOuts(symbol)
                        else:
                            if node.attr not in self.lastattribute[self.curclass] or self.lastattribute[self.curclass][node.attr] == None:
                                symbol = SymbolNode([], [], node.attr, self.attribute2id[self.curclass][node.attr], classname = self.classstack[self.curclass], scope = "attribute")
                                if self.curfunc != -1:
                                    self.GlobalTG.addNode(symbol)
                            else:
                                symbol = SymbolNode([self.lastattribute[self.curclass][node.attr]], [], node.attr, self.attribute2id[self.curclass][node.attr], classname = self.classstack[self.curclass], scope = "attribute")
                                self.lastattribute[self.curclass][node.attr].addOuts(symbol)
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastattribute[self.curclass][node.attr] = symbol
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.addNode(symbol)
                elif type(node.ctx) == ast.Del:
                    if node.attr not in self.attribute2id[self.curclass]:
                        pass
                        #raise ValueError(node.attr + "does not exist.")
                    else:
                        del self.attribute2id[self.curclass][node.attr]
                        del self.lastattribute[self.curclass][node.attr]
                elif type(node.ctx) == ast.Store:
                    if node.attr not in self.attribute2id[self.curclass]:
                        self.attribute2id[self.curclass][node.attr] = 0
                    else:
                        self.attribute2id[self.curclass][node.attr] += 1
                    symbol = SymbolNode([self.opstack[self.curop]], [], node.attr, self.attribute2id[self.curclass][node.attr], classname = self.classstack[self.curclass], scope = "attribute", ctx = "Write")
                    symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                    self.lastattribute[self.curclass][node.attr] = symbol
                    self.opstack[self.curop].addOuts(symbol)
                    self.GlobalTG.addNode(symbol)
                    if self.curfunc != -1:
                        self.tgstack[self.curfunc].addNode(symbol)

            else:
                if ((type(node.ctx) == ast.Load or self.augassignread) and
                    (attrstr not in self.globalvar2id or (attrstr in self.globalvar2id and attrstr not in self.lastglobalvar)) and
                    (self.curfunc == -1 or (attrstr not in self.localvar2id[self.curfunc] or (attrstr in self.localvar2id[self.curfunc] and attrstr not in self.lastlocalvar[self.curfunc])))):
                    typegen = TypeGenNode(".", [], [], attr = node.attr)
                    typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

                    self.opstack.append(typegen)
                    self.curop += 1

                    self.visit(node.value)

                    self.opstack.pop(self.curop)
                    self.curop -= 1

                    self.addNode(typegen)

                    if self.curfunc == -1:
                        self.globalvar2id[attrstr] = 0
                        if self.curop != -1 and not asifcond:
                            symbol = SymbolNode([typegen], [self.opstack[self.curop]], attrstr, 0, scope = "global")
                        else:
                            symbol = SymbolNode([typegen], [], attrstr, 0, scope = "global")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastglobalvar[attrstr] = symbol
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.GlobalTG.addNode(symbol)
                    elif self.curfunc != -1:
                        self.localvar2id[self.curfunc][attrstr] = 0
                        if self.curop != -1 and not asifcond:
                            symbol = SymbolNode([typegen], [self.opstack[self.curop]], attrstr, 0)
                        else:
                            symbol = SymbolNode([typegen], [], attrstr, 0)
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastlocalvar[self.curfunc][attrstr] = symbol
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.tgstack[self.curfunc].addNode(symbol)
                    typegen.addOuts(symbol)
                elif type(node.ctx) == ast.Store and attrstr not in self.globalvar2id and (self.curfunc == -1 or attrstr not in self.localvar2id[self.curfunc]):
                    if self.curclass == -1 and self.curfunc == -1:
                        self.globalvar2id[attrstr] = 0
                        symbol = SymbolNode([self.opstack[self.curop]], [], attrstr, 0, scope = "global", ctx = "Write")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastglobalvar[attrstr] = symbol
                        self.opstack[self.curop].addOuts(symbol)
                        self.GlobalTG.addNode(symbol)
                    elif self.curfunc != -1:
                        self.localvar2id[self.curfunc][attrstr] = 0
                        symbol = SymbolNode([self.opstack[self.curop]], [], attrstr, 0, ctx = "Write")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastlocalvar[self.curfunc][attrstr] = symbol
                        self.opstack[self.curop].addOuts(symbol)
                        self.tgstack[self.curfunc].addNode(symbol)
                elif attrstr in self.globalvar2id or self.curfunc == -1:
                    if type(node.ctx) == ast.Load or self.augassignread:
                        self.globalvar2id[attrstr] += 1
                        if self.curop != -1 and not asifcond:
                            if self.lastglobalvar[attrstr] == None:
                                symbol = SymbolNode([], [self.opstack[self.curop]], attrstr, self.globalvar2id[attrstr], scope = "global")
                                if self.curfunc != -1:
                                    self.GlobalTG.addNode(symbol)
                            else:
                                symbol = SymbolNode([self.lastglobalvar[attrstr]], [self.opstack[self.curop]], attrstr, self.globalvar2id[attrstr], scope = "global")
                                self.lastglobalvar[attrstr].addOuts(symbol)
                        else:
                            if self.lastglobalvar[attrstr] == None:
                                symbol = SymbolNode([self.lastglobalvar[attrstr]], [], attrstr, self.globalvar2id[attrstr], scope = "global")
                                if self.curfunc != -1:
                                    self.GlobalTG.addNode(symbol)
                            else:
                                symbol = SymbolNode([self.lastglobalvar[attrstr]], [], attrstr, self.globalvar2id[attrstr], scope = "global")
                                self.lastglobalvar[attrstr].addOuts(symbol)
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastglobalvar[attrstr] = symbol
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.addNode(symbol)
                    elif type(node.ctx) == ast.Del:
                        del self.globalvar2id[attrstr]
                        del self.lastglobalvar[attrstr]
                    elif type(node.ctx) == ast.Store:
                        self.globalvar2id[attrstr] += 1
                        symbol = SymbolNode([self.opstack[self.curop]], [], attrstr, self.globalvar2id[attrstr], scope = "global", ctx = "Write")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastglobalvar[attrstr] = symbol
                        self.opstack[self.curop].addOuts(symbol)
                        self.GlobalTG.addNode(symbol)
                elif attrstr in self.localvar2id[self.curfunc]:
                    if type(node.ctx) == ast.Load or self.augassignread:
                        self.localvar2id[self.curfunc][attrstr] += 1
                        if self.curop != -1 and not asifcond:
                            symbol = SymbolNode([self.lastlocalvar[self.curfunc][attrstr]], [self.opstack[self.curop]], attrstr, self.localvar2id[self.curfunc][attrstr])
                        else:
                            symbol = SymbolNode([self.lastlocalvar[self.curfunc][attrstr]], [], attrstr, self.localvar2id[self.curfunc][attrstr])
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastlocalvar[self.curfunc][attrstr].addOuts(symbol)
                        self.lastlocalvar[self.curfunc][attrstr] = symbol
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.tgstack[self.curfunc].addNode(symbol)
                    elif type(node.ctx) == ast.Del:
                        del self.localvar2id[self.curfunc][attrstr]
                        del self.lastlocalvar[self.curfunc][attrstr]
                    elif type(node.ctx) == ast.Store:
                        self.localvar2id[self.curfunc][attrstr] += 1
                        symbol = SymbolNode([self.opstack[self.curop]], [], attrstr, self.localvar2id[self.curfunc][attrstr], ctx = "Write")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastlocalvar[self.curfunc][attrstr] = symbol
                        self.opstack[self.curop].addOuts(symbol)
                        self.tgstack[self.curfunc].addNode(symbol)

                    
                    

        #case 2: depth > 2
        else:
            if type(node.ctx) == ast.Load or self.augassignread:
                #case 1: global variables
                if (self.curclass == -1 and self.curfunc == -1) or attrstr in self.globalvar2id:
                    if attrstr not in self.globalvar2id:
                        self.globalvar2id[attrstr] = 0
                        if self.curop != -1 and not asifcond:
                            symbol = SymbolNode([], [self.opstack[self.curop]], attrstr, self.globalvar2id[attrstr], scope = "global")
                        else:
                            symbol = SymbolNode([], [], attrstr, self.globalvar2id[attrstr], scope = "global")
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.lastglobalvar[attrstr] = symbol
                        self.GlobalTG.addNode(symbol)
                    else:
                        self.globalvar2id[attrstr] += 1
                        if self.curop != -1 and not asifcond:
                            if self.lastglobalvar[attrstr] == None:
                                symbol = SymbolNode([], [self.opstack[self.curop]], attrstr, self.globalvar2id[attrstr], scope = "global")
                                if self.curfunc != -1:
                                    self.GlobalTG.addNode(symbol)
                            else:
                                symbol = SymbolNode([self.lastglobalvar[attrstr]], [self.opstack[self.curop]], attrstr, self.globalvar2id[attrstr], scope = "global")
                                self.lastglobalvar[attrstr].addOuts(symbol)
                        else:
                            if self.lastglobalvar[attrstr] == None:
                                symbol = SymbolNode([], [], attrstr, self.globalvar2id[attrstr], scope = "global")
                                if self.curfunc != -1:
                                    self.GlobalTG.addNode(symbol)
                            else:
                                symbol = SymbolNode([self.lastglobalvar[attrstr]], [], attrstr, self.globalvar2id[attrstr], scope = "global")
                                self.lastglobalvar[attrstr].addOuts(symbol)
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.lastglobalvar[attrstr] = symbol
                        self.addNode(symbol)
                #case 2: local variables
                elif self.curfunc != -1:
                    if attrstr not in self.localvar2id[self.curfunc] or attrstr not in self.lastlocalvar[self.curfunc]:
                        if attrstr not in self.localvar2id[self.curfunc]:
                            self.localvar2id[self.curfunc][attrstr] = 0
                        else:
                            self.localvar2id[self.curfunc][attrstr] += 1
                        if self.curop != -1 and not asifcond:
                            symbol = SymbolNode([], [self.opstack[self.curop]], attrstr, self.localvar2id[self.curfunc][attrstr])
                        else:
                            symbol = SymbolNode([], [], attrstr, self.localvar2id[self.curfunc][attrstr])
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.lastlocalvar[self.curfunc][attrstr] = symbol
                        self.tgstack[self.curfunc].addNode(symbol)
                    else:
                        self.localvar2id[self.curfunc][attrstr] += 1
                        if self.curop != -1 and not asifcond:
                            symbol = SymbolNode([self.lastlocalvar[self.curfunc][attrstr]], [self.opstack[self.curop]], attrstr, self.localvar2id[self.curfunc][attrstr])
                        else:
                            symbol = SymbolNode([self.lastlocalvar[self.curfunc][attrstr]], [], attrstr, self.localvar2id[self.curfunc][attrstr])
                        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                        self.lastlocalvar[self.curfunc][attrstr].addOuts(symbol)
                        if self.curop != -1 and not asifcond:
                            self.opstack[self.curop].addIns(symbol)
                        self.lastlocalvar[self.curfunc][attrstr] = symbol
                        self.tgstack[self.curfunc].addNode(symbol)
            elif type(node.ctx) == ast.Del:
                #case 1: global variables
                if (self.curclass == -1 and self.curfunc == -1) or attrstr in self.globalvar2id:
                    del self.lastglobalvar[attrstr]
                    del self.globalvar2id[attrstr]
                #case 2: local variables
                elif self.curfunc != -1:
                    del self.lastlocalvar[self.curfunc][attrstr]
                    del self.localvar2id[self.curfunc][attrstr]
            elif type(node.ctx) == ast.Store:
                #case 1: global variables
                if (self.curclass == -1 and self.curfunc == -1) or attrstr in self.globalvar2id:
                    if attrstr not in self.globalvar2id:
                        self.globalvar2id[attrstr] = 0
                    else:
                        self.globalvar2id[attrstr] += 1
                    symbol = SymbolNode([self.opstack[self.curop]], [], attrstr, self.globalvar2id[attrstr], scope = "global", ctx = "Write")
                    symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                    self.lastglobalvar[attrstr] = symbol
                    self.opstack[self.curop].addOuts(symbol)
                    self.GlobalTG.addNode(symbol)
                #case 2: local variables
                if self.curfunc != -1:
                    if attrstr not in self.localvar2id[self.curfunc]:
                        self.localvar2id[self.curfunc][attrstr] = 0
                    else:
                        self.localvar2id[self.curfunc][attrstr] += 1
                    symbol = SymbolNode([self.opstack[self.curop]], [], attrstr, self.localvar2id[self.curfunc][attrstr], ctx = "Write")
                    symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                    self.lastlocalvar[self.curfunc][attrstr] = symbol
                    self.opstack[self.curop].addOuts(symbol)
                    self.tgstack[self.curfunc].addNode(symbol)
        

        
    def visit_IfExp(self, node):
        typegen = TypeGenNode("IfExp", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1
        
        self.visit_If(node)

        self.opstack.pop(self.curop)
        self.curop -= 1
        if self.curop != -1:
            typegen.addOuts(self.opstack[self.curop])
            self.opstack[self.curop].addIns(typegen)
        self.addNode(typegen)

    def visit_JoinedStr(self, node):
        typegen = TypeGenNode("JoinedStr", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
        
        self.opstack.append(typegen)
        self.curop += 1

        self.generic_visit(node)

        self.opstack.pop(self.curop)
        self.curop -= 1
        if self.curop != -1:
            typegen.addOuts(self.opstack[self.curop])
            self.opstack[self.curop].addIns(typegen)
        self.addNode(typegen)





    def visit_If(self, node):
        ###extract type conditions
        branchnodes = self.extractTypeCondition(node.test)
        

        attribute2id_ori = deepcopy(self.attribute2id)
        globalvar2id_ori = deepcopy(self.globalvar2id)
        localvar2id_ori = deepcopy(self.localvar2id)

        removed = []
        for n in branchnodes:
            var = n.ins[0]
            if isinstance(var, SymbolNode):
                if var.scope == "global":
                    self.lastglobalvar[var.name] = n
                    n.brachvar = var.name + str(self.globalvar2id[var.name])
                elif var.scope == "local":
                    self.lastlocalvar[self.curfunc][var.name] = n
                    n.branchvar = var.name + str(self.localvar2id[self.curfunc][var.name])
                elif var.scope == "attribute":
                    self.lastattribute[self.curclass][var.name] = n
                    n.branchvar = var.name + str(self.attribute2id[self.curclass][var.name])
            else:
                removed.append(n)
        for n in removed:
            if n in branchnodes:
                branchnodes.remove(n)

        if self.curfunc != -1:
            lastlocalvar_backup = copy(self.lastlocalvar[self.curfunc])
        if self.curclass != -1:
            lastattribute_backup = copy(self.lastattribute[self.curclass])
        lastglobalvar_backup = copy(self.lastglobalvar)

        for n in branchnodes:
            var = n.ins[0]
            if var.scope == "global":
                self.globalvar2id[var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.globalvar2id[var.name], scope = "global", extra = True)
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastglobalvar[var.name] = symbol
                self.addNode(symbol)
            elif var.scope == "local":
                self.localvar2id[self.curfunc][var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.localvar2id[self.curfunc][var.name], extra = True)
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastlocalvar[self.curfunc][var.name] = symbol
                self.addNode(symbol)
            elif var.scope == "attribute":
                self.attribute2id[self.curclass][var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.attribute2id[self.curclass][var.name], classname = var.classname, scope = "attribute", extra = True)
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastattribute[self.curclass][var.name] = symbol
                self.addNode(symbol)


        if isinstance(node.body, list):
            #for node: If
            self.visitfield(node.body)
        else:
            #for node: IfExp
            self.visit(node.body)

        if self.curfunc != -1:
            lastlocalvar_true = copy(self.lastlocalvar[self.curfunc])
        if self.curclass != -1:
            lastattribute_true = copy(self.lastattribute[self.curclass])
        lastglobalvar_true = copy(self.lastglobalvar)
        

        attribute2id_true = deepcopy(self.attribute2id)
        globalvar2id_true = deepcopy(self.globalvar2id)
        localvar2id_true = deepcopy(self.localvar2id)

        
        if self.curclass != -1:
            self.lastattribute[self.curclass] = copy(lastattribute_backup)
        if self.curfunc != -1:
            self.lastlocalvar[self.curfunc] = copy(lastlocalvar_backup)
        self.lastglobalvar = copy(lastglobalvar_backup) 

        for n in branchnodes:
            var = n.ins[0]
            if var.scope == "global":
                self.globalvar2id[var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.globalvar2id[var.name], scope = "global", extra = True)
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastglobalvar[var.name] = symbol
                self.addNode(symbol)
            elif var.scope == "local":
                self.localvar2id[self.curfunc][var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.localvar2id[self.curfunc][var.name], extra = True)
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastlocalvar[self.curfunc][var.name] = symbol
                self.addNode(symbol)
            elif var.scope == "attribute":
                self.attribute2id[self.curclass][var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.attribute2id[self.curclass][var.name], classname = var.classname, scope = "attribute", extra = True)
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastattribute[self.curclass][var.name] = symbol
                self.addNode(symbol)

        if isinstance(node.orelse, list):
            #for node: If
            self.visitfield(node.orelse)
        else:
            #for node: IfExp
            self.visit(node.orelse)

        #TODO branch and merge cases

        for key in self.globalvar2id:
            #variable created in true body and used in false body
            if key not in lastglobalvar_backup and key in lastglobalvar_true and key in self.lastglobalvar:
                mergenode = MergeNode([self.lastglobalvar[key], lastglobalvar_true[key]], [], self.buildmergename([self.lastglobalvar[key], lastglobalvar_true[key]]))
                self.lastglobalvar[key].addOuts(mergenode)
                lastglobalvar_true[key].addOuts(mergenode)
                self.lastglobalvar[key] = mergenode
                self.GlobalTG.addNode(mergenode)
                if self.curfunc != -1:
                    self.tgstack[self.curfunc].addNode(mergenode)
            #variable created in true body and not used in false body
            elif key not in lastglobalvar_backup and key in lastglobalvar_true and key not in self.lastglobalvar:
                self.lastglobalvar[key] = lastglobalvar_true[key]
            #variable created in false body
            elif key not in lastglobalvar_backup and key not in lastglobalvar_true:
                pass
            #variable created before if and used in both true and false body or used only in false body
            elif key in globalvar2id_true and globalvar2id_true[key] != self.globalvar2id[key] and self.lastglobalvar[key] != None and lastglobalvar_true[key] != None:
                mergenode = MergeNode([self.lastglobalvar[key], lastglobalvar_true[key]], [], self.buildmergename([self.lastglobalvar[key], lastglobalvar_true[key]]))
                self.lastglobalvar[key].addOuts(mergenode)
                lastglobalvar_true[key].addOuts(mergenode)
                self.lastglobalvar[key] = mergenode
                self.GlobalTG.addNode(mergenode)
                if self.curfunc != -1:
                    self.tgstack[self.curfunc].addNode(mergenode)
            #varaible created before if and used only in true body
            elif key in globalvar2id_true and globalvar2id_true[key] == self.globalvar2id[key] and self.globalvar2id[key] > globalvar2id_ori[key] and key in lastglobalvar_backup and lastglobalvar_backup[key] != None and lastglobalvar_true[key] != None:
                mergenode = MergeNode([lastglobalvar_backup[key], lastglobalvar_true[key]], [], self.buildmergename([lastglobalvar_backup[key], lastglobalvar_true[key]]))
                lastglobalvar_backup[key].addOuts(mergenode)
                lastglobalvar_true[key].addOuts(mergenode)
                self.lastglobalvar[key] = mergenode
                self.GlobalTG.addNode(mergenode)
                if self.curfunc != -1:
                    self.tgstack[self.curfunc].addNode(mergenode)

        if self.curfunc != -1:
            for key in self.localvar2id[self.curfunc]:
                #variable created in true body and used in false body
                if key not in lastlocalvar_backup and key in lastlocalvar_true and key in self.lastlocalvar[self.curfunc]:
                    mergenode = MergeNode([self.lastlocalvar[self.curfunc][key], lastlocalvar_true[key]], [], self.buildmergename([self.lastlocalvar[self.curfunc][key], lastlocalvar_true[key]]))
                    self.lastlocalvar[self.curfunc][key].addOuts(mergenode)
                    lastlocalvar_true[key].addOuts(mergenode)
                    self.lastlocalvar[self.curfunc][key] = mergenode
                    self.tgstack[self.curfunc].addNode(mergenode)
                #variable created in true body and not used in false body
                elif key not in lastlocalvar_backup and key in lastlocalvar_true and key not in self.lastlocalvar[self.curfunc]:
                    self.lastlocalvar[self.curfunc][key] = lastlocalvar_true[key]
                #variable created in false body
                elif key not in lastlocalvar_backup and key not in lastlocalvar_true:
                    pass
                #variable created before if and used in both true and false body or used only in false body
                elif key in localvar2id_true[self.curfunc] and localvar2id_true[self.curfunc][key] != self.localvar2id[self.curfunc][key] and lastlocalvar_true[key] != None and self.lastlocalvar[self.curfunc][key] != None:
                    mergenode = MergeNode([self.lastlocalvar[self.curfunc][key], lastlocalvar_true[key]], [], self.buildmergename([self.lastlocalvar[self.curfunc][key], lastlocalvar_true[key]]))
                    self.lastlocalvar[self.curfunc][key].addOuts(mergenode)
                    lastlocalvar_true[key].addOuts(mergenode)
                    self.lastlocalvar[self.curfunc][key] = mergenode
                    self.tgstack[self.curfunc].addNode(mergenode)
                #varaible created before if and used only in true body
                elif key in localvar2id_true[self.curfunc] and localvar2id_true[self.curfunc][key] == self.localvar2id[self.curfunc][key] and key in lastlocalvar_backup and self.localvar2id[self.curfunc][key] > localvar2id_ori[self.curfunc][key] and lastlocalvar_backup[key] != None and lastlocalvar_true[key] != None:
                    mergenode = MergeNode([lastlocalvar_backup[key], lastlocalvar_true[key]], [], self.buildmergename([lastlocalvar_backup[key], lastlocalvar_true[key]]))
                    lastlocalvar_backup[key].addOuts(mergenode)
                    lastlocalvar_true[key].addOuts(mergenode)
                    self.lastlocalvar[self.curfunc][key] = mergenode
                    self.tgstack[self.curfunc].addNode(mergenode)
        if self.curclass != -1:
            for key in self.attribute2id[self.curclass]:
                #variable created in true body and used in false body
                if key not in lastattribute_backup and key in lastattribute_true and key in self.lastattribute[self.curclass]:
                    mergenode = MergeNode([self.lastattribute[self.curclass][key], lastattribute_true[key]], [], self.buildmergename([self.lastattribute[self.curclass][key], lastattribute_true[key]]))
                    self.lastattribute[self.curclass][key].addOuts(mergenode)
                    lastattribute_true[key].addOuts(mergenode)
                    self.lastattribute[self.curclass][key] = mergenode
                    self.addNode(mergenode)
                #variable created in true body and not used in false body
                elif key not in lastattribute_backup and key in lastattribute_true and key not in self.lastattribute[self.curclass]:
                    self.lastattribute[self.curclass][key] = lastattribute_true[key]
                #variable created in false body
                elif key not in lastattribute_backup and key not in lastattribute_true:
                    pass
                #variable created before if and used in both true and false body or used only in false body
                elif key in attribute2id_true[self.curclass] and attribute2id_true[self.curclass][key] != self.attribute2id[self.curclass][key] and self.lastattribute[self.curclass][key] != None and lastattribute_true[key] != None:
                    mergenode = MergeNode([self.lastattribute[self.curclass][key], lastattribute_true[key]], [], self.buildmergename([self.lastattribute[self.curclass][key], lastattribute_true[key]]))
                    self.lastattribute[self.curclass][key].addOuts(mergenode)
                    lastattribute_true[key].addOuts(mergenode)
                    self.lastattribute[self.curclass][key] = mergenode
                    self.addNode(mergenode)
                elif key in attribute2id_true[self.curclass] and attribute2id_true[self.curclass][key] == self.attribute2id[self.curclass][key] and key in lastattribute_backup and self.attribute2id[self.curclass][key] > attribute2id_ori[self.curclass][key] and lastattribute_backup[key] != None and lastattribute_true[key] != None:
                    mergenode = MergeNode([lastattribute_backup[key], lastattribute_true[key]], [], self.buildmergename([lastattribute_backup[key], lastattribute_true[key]]))
                    lastattribute_backup[key].addOuts(mergenode)
                    lastattribute_true[key].addOuts(mergenode)
                    self.lastattribute[self.curclass][key] = mergenode
                    self.addNode(mergenode)


        #branch nodes should not exist in lastvar map
        for n in branchnodes:
            var = n.ins[0]
            if var.scope == "global" and self.lastglobalvar[var.name] == n:
                self.globalvar2id[var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.globalvar2id[var.name], scope = "global")
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastglobalvar[var.name] = symbol
                self.addNode(symbol)
            elif var.scope == "local" and self.lastlocalvar[self.curfunc][var.name] == n:
                self.localvar2id[self.curfunc][var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.localvar2id[self.curfunc][var.name])
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastlocalvar[self.curfunc][var.name] = symbol
                self.addNode(symbol)
            elif var.scope == "attribute" and self.lastattribute[self.curclass][var.name] == n:
                self.attribute2id[self.curclass][var.name] += 1
                symbol = SymbolNode([n], [], var.symbol, self.attribute2id[self.curclass][var.name])
                symbol.setNodePos(var.lineno, var.columnno, var.columnend)
                n.addOuts(symbol)
                self.lastattribute[self.curclass][var.name] = symbol
                self.addNode(symbol)





    def visit_Try(self, node):

        if self.curfunc != -1:
            lastlocalvar_ori = copy(self.lastlocalvar[self.curfunc])
        if self.curclass != -1:
            lastattribute_ori = copy(self.lastattribute[self.curclass])
        lastglobalvar_ori = copy(self.lastglobalvar)

        if self.curfunc != -1:
            self.tgstack[self.curfunc].intry += 1
        else:
            self.GlobalTG.intry += 1

        self.visitfield(node.body)
        
        if self.curfunc != -1:
            lastlocalvar_try = copy(self.lastlocalvar[self.curfunc])
        if self.curclass != -1:
            lastattribute_try = copy(self.lastattribute[self.curclass])
        lastglobalvar_try = copy(self.lastglobalvar)

        if self.curfunc != -1:
            self.lastlocalvar[self.curfunc] = copy(lastlocalvar_ori)
        if self.curclass != -1:
            self.lastattribute[self.curclass] = copy(lastattribute_ori)
        self.lastglobalvar = copy(lastglobalvar_ori)

        self.addMerge4Except()

        if self.curfunc != -1:
            self.tgstack[self.curfunc].intry -= 1
            if len(self.tgstack[self.curfunc].trybuffer) > self.tgstack[self.curfunc].intry:
                self.tgstack[self.curfunc].trybuffer.pop(self.tgstack[self.curfunc].intry)
        else:
            self.GlobalTG.intry -= 1
            if len(self.GlobalTG.trybuffer) > self.GlobalTG.intry:
                self.GlobalTG.trybuffer.pop(self.GlobalTG.intry)

        self.visitfield(node.handlers)

        if self.curfunc != -1:
            self.lastlocalvar[self.curfunc] = copy(lastlocalvar_try)
        if self.curclass != -1:
            self.lastattribute[self.curclass] = copy(lastattribute_try)
        self.lastglobalvar = copy(lastglobalvar_try)

        self.visitfield(node.orelse)

        self.addMerge4Finally()

        self.visitfield(node.finalbody)

        if self.curfunc != -1:
            self.tgstack[self.curfunc].inexcept = 0
            self.tgstack[self.curfunc].exceptbuffer.clear()
        else:
            self.GlobalTG.inexcept = 0
            self.GlobalTG.exceptbuffer.clear()

        






    def visit_ExceptHandler(self, node):
        if self.curfunc != -1:
            lastlocalvar_ori = copy(self.lastlocalvar[self.curfunc])
        if self.curclass != -1:
            lastattribute_ori = copy(self.lastattribute[self.curclass])
        lastglobalvar_ori = copy(self.lastglobalvar)

        if node.name != None:
            symbol = SymbolNode([], [], node.name, 0)
            symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
            typeobject = TypeObject("Exception", 0)
            symbol.types.append(typeobject)
            if self.curfunc != -1:
                self.localvar2id[self.curfunc][node.name] = 1
                self.lastlocalvar[self.curfunc][node.name] = symbol
            else:
                self.globalvar2id[node.name] = 1
                self.lastglobalvar[node.name] = symbol
            self.addNode(symbol)

        if self.curfunc != -1:
            self.tgstack[self.curfunc].inexcept += 1
        else:
            self.GlobalTG.inexcept += 1

        self.visitfield(node.body)

        if self.curfunc != -1:
            self.lastlocalvar[self.curfunc] = copy(lastlocalvar_ori)
            if node.name != None and node.name in self.localvar2id[self.curfunc]:
                del self.localvar2id[self.curfunc][node.name]
                deletekeys = []
                for key in self.localvar2id[self.curfunc]:
                    if key.startswith(node.name + "_@_"):
                        deletekeys.append(key)
                for key in deletekeys:
                    del self.localvar2id[self.curfunc][key]
        if self.curclass != -1:
            self.lastattribute[self.curclass] = copy(lastattribute_ori)
        self.lastglobalvar = copy(lastglobalvar_ori)
        if node.name != None and node.name in self.globalvar2id:
            del self.globalvar2id[node.name]
            deletekeys = []
            for key in self.globalvar2id:
                if key.startswith(node.name + "_@_"):
                        deletekeys.append(key)
            for key in deletekeys:
                del self.globalvar2id[key]

        
    def visit_AsyncFor(self, node):
        self.visit_For(node)

        

    def visit_For(self, node):
        if len(node.orelse) != 0:
            raise ValueError("Currently we do not support for loops with else statements.")

        typegen = TypeGenNode("forin", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        

        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.target)

        self.visit(node.iter)

        self.opstack.pop(self.curop)
        self.curop -= 1

        attribute2id_ori = deepcopy(self.attribute2id)
        globalvar2id_ori = deepcopy(self.globalvar2id)
        localvar2id_ori = deepcopy(self.localvar2id)


        if self.curfunc != -1:
            lastlocalvar_ori = copy(self.lastlocalvar[self.curfunc])
        if self.curclass != -1:
            lastattribute_ori = copy(self.lastattribute[self.curclass])
        lastglobalvar_ori = copy(self.lastglobalvar)

        
        if self.curfunc != -1:
            self.tgstack[self.curfunc].inloop += 1
        else:
            self.GlobalTG.inloop += 1


        self.visitfield(node.body)


        #add merge nodes for vars after this loop
        if self.curfunc != -1:
            for key in self.localvar2id[self.curfunc]:
                if key in localvar2id_ori[self.curfunc] and key in lastlocalvar_ori and self.localvar2id[self.curfunc][key] > localvar2id_ori[self.curfunc][key]:
                    mergenode = MergeNode([self.lastlocalvar[self.curfunc][key], lastlocalvar_ori[key]], [], self.buildmergename([self.lastlocalvar[self.curfunc][key], lastlocalvar_ori[key]]))
                    self.lastlocalvar[self.curfunc][key].addOuts(mergenode)
                    lastlocalvar_ori[key].addOuts(mergenode)
                    self.lastlocalvar[self.curfunc][key] = mergenode
                    self.addNode(mergenode)
        elif self.curclass != -1:
            for key in self.attribute2id[self.curclass]:
                if key in attribute2id_ori[self.curclass] and key in lastattribute_ori and self.attribute2id[self.curclass][key] > attribute2id_ori[self.curclass][key] and self.lastattribute[self.curclass][key] != None and lastattribute_ori[key] != None:
                    mergenode = MergeNode([self.lastattribute[self.curclass][key], lastattribute_ori[key]], [], self.buildmergename([self.lastattribute[self.curclass][key], lastattribute_ori[key]]))
                    self.lastattribute[self.curclass][key].addOuts(mergenode)
                    lastattribute_ori[key].addOuts(mergenode)
                    self.lastattribute[self.curclass][key] = mergenode
                    self.addNode(mergenode)
        
        for key in self.globalvar2id:
            if key in globalvar2id_ori and key in lastglobalvar_ori and self.globalvar2id[key] > globalvar2id_ori[key] and self.lastglobalvar[key] != None and lastglobalvar_ori[key] != None:
                mergenode = MergeNode([self.lastglobalvar[key], lastglobalvar_ori[key]], [], self.buildmergename([self.lastglobalvar[key], lastglobalvar_ori[key]]))
                self.lastglobalvar[key].addOuts(mergenode)
                lastglobalvar_ori[key].addOuts(mergenode)
                self.lastglobalvar[key] = mergenode
                self.addNode(mergenode)



        
        #add merges for the first use of variables in this loop
        self.addMergeNodes()

        if self.curfunc != -1:
            self.tgstack[self.curfunc].inloop -= 1
            if len(self.tgstack[self.curfunc].loopbuffer) > self.tgstack[self.curfunc].inloop:
                self.tgstack[self.curfunc].loopbuffer.pop(self.tgstack[self.curfunc].inloop)
        else:
            self.GlobalTG.inloop -= 1
            if len(self.GlobalTG.loopbuffer) > self.GlobalTG.inloop:
                self.GlobalTG.loopbuffer.pop(self.GlobalTG.inloop)

        self.addNode(typegen)
        


    def visit_While(self, node):
        if len(node.orelse) != 0:
            raise ValueError("Currently we do not support for loops with else statements.")

        self.asifcond = True
        self.visit(node.test)
        self.asifcond = False

        attribute2id_ori = deepcopy(self.attribute2id)
        globalvar2id_ori = deepcopy(self.globalvar2id)
        localvar2id_ori = deepcopy(self.localvar2id)

        if self.curfunc != -1:
            lastlocalvar_ori = copy(self.lastlocalvar[self.curfunc])
        if self.curclass != -1:
            lastattribute_ori = copy(self.lastattribute[self.curclass])
        lastglobalvar_ori = copy(self.lastglobalvar)

        if self.curfunc != -1:
            self.tgstack[self.curfunc].inloop += 1
        else:
            self.GlobalTG.inloop += 1

        self.visitfield(node.body)

        #add merges for the first use of variables in this loop
        self.addMergeNodes()

        #add merge nodes for vars after this loop
        if self.curfunc != -1:
            for key in self.localvar2id[self.curfunc]:
                if key in localvar2id_ori[self.curfunc] and self.localvar2id[self.curfunc][key] > localvar2id_ori[self.curfunc][key]:
                    mergenode = MergeNode([self.lastlocalvar[self.curfunc][key], lastlocalvar_ori[key]], [], self.buildmergename([self.lastlocalvar[self.curfunc][key], lastlocalvar_ori[key]]))
                    self.lastlocalvar[self.curfunc][key].addOuts(mergenode)
                    lastlocalvar_ori[key].addOuts(mergenode)
                    self.lastlocalvar[self.curfunc][key] = mergenode
                    self.addNode(mergenode)
        elif self.curclass != -1:
            for key in self.attribute2id[self.curclass]:
                if key in attribute2id_ori[self.curclass] and self.attribute2id[self.curclass][key] > attribute2id_ori[self.curclass][key] and self.lastattribute[self.curclass][key] != None and lastattribute_ori[key] != None:
                    mergenode = MergeNode([self.lastattribute[self.curclass][key], lastattribute_ori[key]], [], self.buildmergename([self.lastattribute[self.curclass][key], lastattribute_ori[key]]))
                    self.lastattribute[self.curclass][key].addOuts(mergenode)
                    lastattribute_ori[key].addOuts(mergenode)
                    self.lastattribute[self.curclass][key] = mergenode
                    self.addNode(mergenode)
        
        for key in self.globalvar2id:
            if key in globalvar2id_ori and self.globalvar2id[key] > globalvar2id_ori[key] and lastglobalvar_ori[key] != None and self.lastglobalvar[key] != None:
                mergenode = MergeNode([self.lastglobalvar[key], lastglobalvar_ori[key]], [], self.buildmergename([self.lastglobalvar[key], lastglobalvar_ori[key]]))
                self.lastglobalvar[key].addOuts(mergenode)
                lastglobalvar_ori[key].addOuts(mergenode)
                self.lastglobalvar[key] = mergenode
                self.addNode(mergenode)


        if self.curfunc != -1:
            self.tgstack[self.curfunc].loopbuffer.pop(self.tgstack[self.curfunc].inloop - 1)
            self.tgstack[self.curfunc].inloop -= 1
        else:
            self.GlobalTG.loopbuffer.pop(self.GlobalTG.inloop - 1)
            self.GlobalTG.inloop -= 1


    def visit_Break(self, node):
        logger.warning("Break statement at line {} visited, it may change the data flow but currently HiTyper does not handle it.".format(node.lineno))

    def visit_Continue(self, node):
        logger.warning("Continue statement at line {} visited, it may change the data flow but currently HiTyper does not handle it.".format(node.lineno))



    def visit_With(self, node):
        
        self.withpos.append([node.lineno, node.col_offset, node.end_col_offset])

        self.visitfield(node.items)

        self.visitfield(node.body)

        for item in self.withitemnames[len(self.withitemnames) - 1]:
            if self.curfunc != -1 and item in self.localvar2id[self.curfunc]:
                del self.localvar2id[self.curfunc][item]
                del self.lastlocalvar[self.curfunc][item]
                deletekeys = []
                for key in self.localvar2id[self.curfunc]:
                    if key.startswith(item +"_@_"):
                        deletekeys.append(key)
                for key in deletekeys:
                    del self.localvar2id[self.curfunc][key]
                    if key in self.lastlocalvar[self.curfunc]:
                        del self.lastlocalvar[self.curfunc][key]
            elif item in self.globalvar2id:
                del self.globalvar2id[item]
                del self.lastglobalvar[item]
                deletekeys = []
                for key in self.globalvar2id:
                    if key.startswith(item + "_@_"):
                        deletekeys.append(key)
                for key in deletekeys:
                    del self.globalvar2id[key]
                    if key in self.lastglobalvar:
                        del self.lastglobalvar[key]
        self.withitemnames.pop(len(self.withitemnames) - 1)
        self.withpos.pop(len(self.withpos) - 1)

    def visit_AsyncWith(self, node):
        self.visit_With(node)

    def visit_withitem(self, node):
        if node.optional_vars != None:
            typegen = TypeGenNode("=", [], [])
            index = len(self.withpos) - 1
            typegen.setNodePos(self.withpos[index][0], self.withpos[index][1], self.withpos[index][2])

            self.opstack.append(typegen)
            self.curop += 1

            self.visit(node.context_expr)

            self.visit(node.optional_vars)

            self.withitemnames.append([Attribute2Str(node.optional_vars)])

            self.opstack.pop(self.curop)
            self.curop -= 1


            self.addNode(typegen)
        else:
            self.asifcond = True
            self.visit(node.context_expr)
            self.asifcond = False
            self.withitemnames.append([])


    def visit_BoolOp(self, node):
        asifcond = self.asifcond
        if self.asifcond:
            self.asifcond = False
        typegen = TypeGenNode(AST2Op[type(node.op)], [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1

        if len(node.values) > 2:
            self.visit(node.values[0])
            self.visit(node.values[1])
        else:
            self.visitfield(node.values)

        self.opstack.pop(self.curop)
        self.curop -= 1

        if len(node.values) > 2:
            prev_typegen = typegen
            for i in range(2, len(node.values)):
                curnode = node.values[i]
                more_typegen = TypeGenNode(AST2Op[type(node.op)], [prev_typegen], [])
                prev_typegen.addOuts(more_typegen)
                more_typegen.setNodePos(curnode.lineno, curnode.col_offset, curnode.end_col_offset)
                self.opstack.append(more_typegen)
                self.curop += 1
                self.visit(curnode)
                self.opstack.pop(self.curop)
                self.curop -= 1
                self.addNode(more_typegen)
                prev_typegen = more_typegen
        else:
            prev_typegen = typegen


        if self.curop != -1 and not asifcond:
            self.opstack[self.curop].addIns(prev_typegen)
            prev_typegen.addOuts(self.opstack[self.curop])
        #typegen.performTypingRules()
        self.addNode(typegen)

    def visit_Compare(self, node):
        lastcompare = None
        i = -1
        asifcond = self.asifcond
        if self.asifcond == True:
            self.asifcond = False
        for op in node.ops:
            i += 1
            if lastcompare == None:
                typegen = TypeGenNode(AST2Op[type(op)], [], [])
                typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
                self.addNode(typegen)
                self.opstack.append(typegen)
                self.curop += 1
                self.visit(node.left)
                self.visit(node.comparators[0])
                self.opstack.pop(self.curop)
                self.curop -= 1
                # typegen.performTypingRules()
                lastcompare = typegen
            else:
                typegen = TypeGenNode(AST2Op[type(op)], [], [])
                typegen.setNodePos(node.comparators[i-1].lineno, node.comparators[i-1].col_offset, node.comparators[i-1].end_col_offset)
                self.addNode(typegen)
                self.opstack.append(typegen)
                self.curop += 1
                self.visit(node.comparators[i-1])
                self.visit(node.comparators[i])
                self.opstack.pop(self.curop)
                self.curop -= 1
                typegen2 = TypeGenNode("and", [lastcompare, typegen], [])
                lastcompare.addOuts(typegen2)
                typegen.addOuts(typegen2)
                typegen2.setNodePos(node.comparators[i].lineno, node.comparators[i].col_offset, node.comparators[i].end_col_offset)
                lastcompare = typegen2
                # typegen2.performTypingRules()
                self.addNode(typegen2)

        if self.curop != -1 and not asifcond:
            lastcompare.addOuts(self.opstack[self.curop])
            self.opstack[self.curop].addIns(lastcompare)





    def visit_List(self, node):
        if type(node.ctx) == ast.Store:
            typegen = TypeGenNode("List_Write", [self.opstack[self.curop]], [])
            self.opstack[self.curop].addOuts(typegen)
        else:
            typegen = TypeGenNode("List_Read", [], [self.opstack[self.curop]])
            self.opstack[self.curop].addIns(typegen)
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1
        self.generic_visit(node)
        self.opstack.pop(self.curop)
        self.curop -= 1
        #typegen.performTypingRules(iterable=True)
        self.addNode(typegen)


    def visit_Tuple(self, node):
        if type(node.ctx) == ast.Store:
            typegen = TypeGenNode("Tuple_Write", [self.opstack[self.curop]], [])
            self.opstack[self.curop].addOuts(typegen)

        else:
            typegen = TypeGenNode("Tuple_Read", [], [self.opstack[self.curop]])
            self.opstack[self.curop].addIns(typegen)
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1
        self.generic_visit(node)
        self.opstack.pop(self.curop)
        self.curop -= 1
        #typegen.performTypingRules(iterable=True)
        self.addNode(typegen)


    def visit_Set(self, node):
        typegen = TypeGenNode("Set_Read", [], [self.opstack[self.curop]])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
        self.opstack[self.curop].addIns(typegen)

        self.opstack.append(typegen)
        self.curop += 1
        self.generic_visit(node)
        self.opstack.pop(self.curop)
        self.curop -= 1
        #typegen.performTypingRules(iterable=True)
        self.addNode(typegen)


    def visit_Dict(self, node):
        typegen = TypeGenNode("Dict_Read", [], [self.opstack[self.curop]], splitindex = len(node.keys))
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
        self.opstack[self.curop].addIns(typegen)
        self.opstack.append(typegen)
        self.curop += 1
        self.visitfield(node.keys)
        self.visitfield(node.values)
        self.opstack.pop(self.curop)
        self.curop -= 1
        #typegen.performTypingRules(iterable=True)
        self.addNode(typegen)

    def visit_Return(self, node):
        name = "Return_Value@" + self.funcstack[self.curfunc]
        if self.curclass != -1:
            name = name + "@" + self.classstack[self.curclass]
        symbol = SymbolNode([], [], name, 0, ctx = "Return")
        symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.opstack.append(symbol)
        self.curop += 1
        self.generic_visit(node)

        self.opstack.pop(self.curop)
        self.curop -= 1
        self.addNode(symbol)

    def visit_Lambda(self, node):
        logger.warning("Lambda function at line {} visited, currently HiTyper does not support Lambda function, it may result in incorrect inference.".format(node.lineno))
        typenode = TypeNode([self.opstack[self.curop]], TypeObject("Callable", 0))
        typenode.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
        self.opstack[self.curop].addIns(typenode)
        self.addNode(typenode)

    def visit_Expr(self, node):
        if type(node.value) != ast.Constant:
            self.visit(node.value)

    def visit_Await(self, node):
        self.visit(node.value)

    def visit_comprehension(self, node):
        typegen = TypeGenNode("forin", [], [])
        typegen.setNodePos(node.iter.lineno, node.iter.col_offset, node.iter.end_col_offset)

        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.iter)
        
        self.forin = True
        self.visit(node.target)
        self.forin = False

        self.opstack.pop(self.curop)
        self.curop -= 1

        self.asifcond = True
        self.visitfield(node.ifs)
        self.asifcond = False

        self.addNode(typegen)


    def visit_DictComp(self, node):
        asifcond = self.asifcond
        if self.asifcond:
            self.asifcond = False
        typegen = TypeGenNode("DictComp", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.visitfield(node.generators)

        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.key)

        self.visit(node.value)

        self.opstack.pop(self.curop)
        self.curop -= 1

        if not asifcond and self.curop != -1:
            self.opstack[self.curop].addIns(typegen)
            typegen.addOuts(self.opstack[self.curop])

        self.addNode(typegen)

    def visit_ListComp(self, node):
        asifcond = self.asifcond
        if self.asifcond:
            self.asifcond = False
        typegen = TypeGenNode("ListComp", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.visitfield(node.generators)

        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.elt)

        self.opstack.pop(self.curop)
        self.curop -= 1

        if not asifcond and self.curop != -1:
            self.opstack[self.curop].addIns(typegen)
            typegen.addOuts(self.opstack[self.curop])

        self.addNode(typegen)

    def visit_SetComp(self, node):
        asifcond = self.asifcond
        if self.asifcond:
            self.asifcond = False
        typegen = TypeGenNode("SetComp", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.visitfield(node.generators)

        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.elt)

        self.opstack.pop(self.curop)
        self.curop -= 1

        if not asifcond and self.curop != -1:
            self.opstack[self.curop].addIns(typegen)
            typegen.addOuts(self.opstack[self.curop])

        self.addNode(typegen)


    def visit_GeneratorExp(self, node):
        asifcond = self.asifcond
        if self.asifcond:
            self.asifcond = False
        typegen = TypeGenNode("GeneratorExp", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

        self.visitfield(node.generators)

        self.opstack.append(typegen)
        self.curop += 1

        self.visit(node.elt)

        self.opstack.pop(self.curop)
        self.curop -= 1

        if not asifcond and self.curop != -1:
            self.opstack[self.curop].addIns(typegen)
            typegen.addOuts(self.opstack[self.curop])

        self.addNode(typegen)

    def visit_Yield(self, node):
        typegen = TypeGenNode("yield", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
        
        self.opstack.append(typegen)
        self.curop += 1

        if node.value != None:
            self.visit(node.value)

        self.opstack.pop(self.curop)
        self.curop -= 1

        if len(self.opstack) == 0:
            name = "Return_Value@" + self.funcstack[self.curfunc]
            if self.curclass != -1:
                name = name + "@" + self.classstack[self.curclass]
            symbol = SymbolNode([typegen], [], name, 0, ctx = "Return")
            symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

            typegen.addOuts(symbol)
            self.addNode(symbol)
        else:
            self.opstack[self.curop].addIns(typegen)
            typegen.addOuts(self.opstack[self.curop])
    
        self.addNode(typegen)


    def visit_YieldFrom(self, node):
        typegen = TypeGenNode("yield", [], [])
        typegen.setNodePos(node.lineno, node.col_offset, node.end_col_offset)
        
        self.opstack.append(typegen)
        self.curop += 1

        if node.value != None:
            self.visit(node.value)

        self.opstack.pop(self.curop)
        self.curop -= 1

        if len(self.opstack) == 0:
            name = "Return_Value@" + self.funcstack[self.curfunc]
            if self.curclass != -1:
                name = name + "@" + self.classstack[self.curclass]
            symbol = SymbolNode([typegen], [], name, 0, ctx = "Return")
            symbol.setNodePos(node.lineno, node.col_offset, node.end_col_offset)

            typegen.addOuts(symbol)
            self.addNode(symbol)
        else:
            self.opstack[self.curop].addIns(typegen)
            typegen.addOuts(self.opstack[self.curop])
    
        self.addNode(typegen)
        

    def visit_Assert(self, node):
        logger.warning("Assert statement visited at Line {}, it may change the data flow of program, but HiTyper currently ignores it.".format(node.lineno))


    def finalize(self, tg):
        if isinstance(tg, TypeGraph):
            for key in tg.symbolnodes:
                for n in tg.symbolnodes[key]:
                    if len(n.ins) > 1:
                        mergenode = MergeNode(n.ins, [n], self.buildmergename(n.ins))
                        for innode in n.ins:
                            innode.outs[innode.outs.index(n)] = mergenode
                        n.ins = [mergenode]
                        self.addNode(mergenode)
            for n in tg.returnvaluenodes:
                if len(n.ins) > 1:
                    mergenode = MergeNode(n.ins, [n], self.buildmergename(n.ins))
                    for innode in n.ins:
                        innode.outs[innode.outs.index(n)] = mergenode
                    n.ins = [mergenode]
                    self.addNode(mergenode)
        else:
            for key in tg.globalsymbolnodes:
                for n in tg.globalsymbolnodes[key]:
                    if len(n.ins) > 1:
                        mergenode = MergeNode(n.ins, [n], self.buildmergename(n.ins))
                        for innode in n.ins:
                            innode.outs[innode.outs.index(n)] = mergenode
                        n.ins = [mergenode]
                        self.addNode(mergenode)


    def canRemove(self, node):
        for i in node.ins:
            if isinstance(i, BranchNode):
                return False
        return True


    def optimize(self, tg):
        #remove redundant merge nodes (for which do not have output nodes)
        if isinstance(tg, TypeGraph):
            changed = True
            while(changed):
                removenodes = []
                for n in tg.mergenodes:
                    if len(n.outs) == 0 and self.canRemove(n):
                        removenodes.append(n)
                changed = False
                for n in removenodes:
                    for innode in n.ins:
                        if n in innode.outs:
                            innode.outs.remove(n)
                    tg.mergenodes.remove(n)
                    tg.nodes.remove(n)
                    changed = True
        else:
            changed = True
            while(changed):
                removenodes = []
                for n in tg.globalmergenodes:
                    if len(n.outs) == 0 and self.canRemove(n):
                        removenodes.append(n)
                changed = False
                for n in removenodes:
                    for innode in n.ins:
                        if n in innode.outs:
                            innode.outs.remove(n)
                    tg.globalmergenodes.remove(n)
                    tg.globalnodes.remove(n)
                    changed = True

        #remove redundant branch nodes (for which do not have output nodes)
        if isinstance(tg, TypeGraph):
            changed = True
            while(changed):
                removenodes = []
                for n in tg.branchnodes:
                    if (len(n.outs) == 0 and self.canRemove(n)) or (len(n.outs) == 1 and n.outs[0] == "PlaceHolder"):
                        removenodes.append(n)
                changed = False
                for n in removenodes:
                    for innode in n.ins:
                        if n in innode.outs:
                            innode.outs.remove(n)
                    tg.branchnodes.remove(n)
                    tg.nodes.remove(n)
                    changed = True
        else:
            changed = True
            while(changed):
                removenodes = []
                for n in tg.globalbranchnodes:
                    if (len(n.outs) == 0 and self.canRemove(n)) or (len(n.outs) == 1 and n.outs[0] == "PlaceHolder"):
                        removenodes.append(n)
                changed = False
                for n in removenodes:
                    for innode in n.ins:
                        if n in innode.outs:
                            innode.outs.remove(n)
                    tg.globalbranchnodes.remove(n)
                    tg.globalnodes.remove(n)
                    changed = True

        #refine branch nodes
        if isinstance(tg, TypeGraph):
            for n in tg.branchnodes:
                if len(n.outs) == 3 and n.outs[0] == "PlaceHolder":
                    outs = [n.outs[2], n.outs[1]]
                    n.outs = outs
        else:
            for n in tg.globalbranchnodes:
                if len(n.outs) == 3 and n.outs[0] == "PlaceHolder":
                    outs = [n.outs[2], n.outs[1]]
                    n.outs = outs
                    
            

    def run(self, root):
        if self.alias > 0:
            logger.info("[1st Pass: Alias Analysis] Started...")
            a = AliasAnalyzer(self.GlobalTG.aliasgraph)
            self.GlobalTG.aliasgraph = a.run(root)
            logger.info("[1st Pass: Alias Analysis] Generated {0} attribute nodes, captured {1} aliases.".format(len(self.GlobalTG.aliasgraph.nodes), self.GlobalTG.aliasgraph.getAliasNum()))
            logger.info("[1st Pass: Alias Analysis] Finished!")
        else:
            logger.info("[1st Pass: Alias Analysis] Skipped...")

        if self.repo != None:
            logger.info("[2nd Pass: Call Analysis] Started...")
            cg = CallGraphGenerator([self.filename], self.repo, -1, CALL_GRAPH_OP)
            cg.analyze()
            formatter = formats.Simple(cg)
            output = formatter.generate()
            self.GlobalTG.callgraph = output
            num = 0
            for key in output:
                num += len(output[key])
            logger.info("[2nd Pass: Call Analysis] Captured {0} call relationships.".format(num))
            logger.info("[2nd Pass: Call Analysis] Finished!")
        else:
            logger.info("[2nd Pass: Call Analysis] Skipped...")
        
        if self.alias <= 1:
            logger.info("[3rd Pass: TDG Generation] Started...")
            self.visit(root)
            self.GlobalTG.addClassname(self.classnames)
            if self.optimized:
                self.optimize(self.GlobalTG)
                for tg in self.GlobalTG.tgs:
                    self.optimize(tg)
            logger.info("[3rd Pass: TDG Generation] Finished!")
        else:
            logger.info("[3rd Pass: TDG Generation] Skipped...")
        return self.GlobalTG

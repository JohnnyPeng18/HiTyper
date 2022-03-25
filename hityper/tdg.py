from graphviz import Digraph
from hityper import logger
from hityper.typeobject import TypeObject
from hityper.typerule import TypingRule
from hityper.rej_typerule import Rej_TypingRule
from hityper.config import config
from copy import copy, deepcopy
import Levenshtein



logger.name = __name__



def checkAttribute(dictobj, attrs):
    for a in attrs:
        if a not in dictobj:
            return False
    return True

class GraphBaseNode(object):
    def __init__(self, ins, outs, name):
        #Node Type: Symbol, TypeGen, Type, Base
        self.nodetype = "Base"
        self.ins = ins
        self.outs = outs
        self.name = name
        self.lineno = 0
        self.columnno = 0
        self.columnend = 0
        self.tg = None
        self.rejtypes = []
        self.nodeid = "Not Assigned"

        #visitlabel: 0 - this node is never visited
        #1 - state of input node of this node is not determined, move to queue and wait
        #2 - this node is finalized and can pass message to neighbors
        self.visitlabel = 0

    def setNodePos(self, lineno, columnno, columnend):
        self.lineno = lineno
        self.columnno = columnno
        self.columnend = columnend

    def addIns(self, ins):
        if isinstance(ins, list):
            for i in ins:
                if i not in self.ins:
                    self.ins.append(i)
                else:
                    logger.warning("Input node " + i.name + " already exists in input list of " + self.name)
        else:
            if ins in self.ins:
                logger.warning("Input node " + ins.name + " already exists in input list of " + self.name)
            else:
                self.ins.append(ins)

    def addOuts(self, outs):
        if isinstance(outs, list):
            for o in outs:
                if o not in self.outs:
                    self.outs.append(o)
                else:
                    logger.warning("Ouput node " + o.name + " already exists in ouput list of " + self.name)
        else:
            if outs in self.outs:
                logger.warning("Ouput node " + outs.name + " already exists in ouput list of " + self.name)
            else:
                self.outs.append(outs)

    def _dump(self):
        node = {}
        node["ins"] = []
        for n in self.ins:
            node["ins"].append(n.nodeid)
        node["outs"] = []
        for n in self.outs:
            node["outs"].append(n.nodeid)
        node["name"] = self.name
        node["lineno"] = self.lineno
        node["columnno"] = self.columnno
        node["columnend"] = self.columnend
        if self.tg != None:
            if isinstance(self.tg, TypeGraph):
                node["tg"] = [self.tg.name, len(self.tg.symbolnodes), len(self.tg.typegennodes), len(self.tg.typenodes)]
            else:
                node["tg"] = [self.tg.name, len(self.tg.globalsymbols), len(self.tg.globaltypegennodes), len(self.tg.globaltypenodes)]
        else:
            node["tg"] = None
        node["rejtypes"] = []
        for t in self.rejtypes:
            if isinstance(t, TypeObject):
                node["rejtypes"].append(t.dump())
            else:
                node["rejtypes"].append(t)
        node["nodeid"] = self.nodeid
        node["visitlabel"] = self.visitlabel
        return node


    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an GraphBaseNode object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["nodetype", "ins", "outs", "name", "lineno", "columnno", "columnend", "tg", "rejtypes", "visitlabel", "types", "nodeid"]):
            logger.error("Missing important information when resuming the GraphBaseNode object!")
            return None
        else:
            try:
                node = GraphBaseNode([], [], dictobj["name"])
                node.nodetype = dictobj["nodetype"]
                node.name = dictobj["name"]
                node.lineno = dictobj["lineno"]
                node.columnno = dictobj["columnno"]
                node.columnend = dictobj["columnend"]
                node.visitlabel = dictobj["visitlabel"]
                node.nodeid = dictobj["nodeid"]
                return node
            except Exception as e:
                logger.error("Cannot resume GraphBaseNode object, reason: " + str(e))
                return None



    

class SymbolNode(GraphBaseNode):
    def __init__(self, ins, outs, symbol, order, classname = None, scope = "local", ctx = "Read", extra = False):
        super(SymbolNode, self).__init__(ins, outs, symbol)
        self.nodetype = "Symbol"

        #extra: add for branch nodes
        self.extra = extra

        #scope: local - for local variables
        #global - for global variables
        #attribute - for class attributes
        #module - for imported modules
        self.scope = scope
        self.symbol = symbol
        self.classname = classname
        self.order = order
        self.types = []
        #context: Read - this symbol is read
        #Write - this symbol is written
        #Arg - this symbol is argument
        #Return - this symbol is return value
        self.ctx = ctx

        #tags: 0 - initial, 
        #1 - statically added, should not change
        #2 - add user defined type
        #3 - dynamically change types using flow algorithm
        #4 - add from DL model
        self.tag = 0

        #indicate whether the type set changes or not during last operation
        self.change = False

    def addTypes(self, t, tag, independent_op = True):
        if independent_op:
            self.change = False
        if(type(t) == type([])):
            for i in t:
                if (isinstance(i, TypeObject) and i not in self.types):
                    self.change = True
                    self.types.append(i)
                else:
                    raise TypeError("t contains elements which are not TypeObjects.")
        elif(isinstance(t, TypeObject)):
            self.change = True
            self.types.append(t)
        else:
            raise TypeError("t should be either a List[TypeObject] or a TypeObject.")
            return -1
        self.tag = tag

    def mergeTypes(self):
        self.change = False
        if(self.tag == 1):
            return 0
        else:
            for innode in self.ins:
                self.addTypes(innode.types, 3)
            return 0

    def removeType(self, t):
        self.change = False
        if(self.tag == 1):
            return 0
        else:
            if(isinstance(t, TypeObject) and t in self.types):
                self.change = True
                self.remove(t)


    def dump(self):
        node = self._dump()
        node["nodetype"] = self.nodetype
        node["extra"] = self.extra
        node["scope"] = self.scope
        node["symbol"] = self.symbol
        node["classname"] = self.classname
        node["order"] = self.order
        node["types"] = []
        for t in self.types:
            if isinstance(t, TypeObject):
                node["types"].append(t.dump())
            else:
                node["types"].append(t)
        node["ctx"] = self.ctx
        node["tag"] = self.tag
        node["change"] = self.change
        return node


    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an SymbolNode object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["nodetype", "ins", "outs", "name", "lineno", "columnno", "columnend", "tg", "rejtypes", "visitlabel", "types", "extra", "scope", "symbol", "classname", "order", "ctx", "tag", "change"]):
            logger.error("Missing important information when resuming the SymbolNode object!")
            return None
        else:
            try:
                node = SymbolNode([], [], dictobj["symbol"], dictobj["order"], classname = dictobj["classname"], scope = dictobj["scope"], ctx = dictobj["ctx"], extra = dictobj["extra"])
                node.nodetype = dictobj["nodetype"]
                node.name = dictobj["name"]
                node.lineno = dictobj["lineno"]
                node.columnno = dictobj["columnno"]
                node.columnend = dictobj["columnend"]
                node.visitlabel = dictobj["visitlabel"]
                node.nodeid = dictobj["nodeid"]
                node.types = []
                for t in dictobj["types"]:
                    node.types.append(TypeObject.load(t))
                node.tag = dictobj["tag"]
                node.change = dictobj["change"]
                return node
            except Exception as e:
                logger.error("Cannot resume SymbolNode object, reason: " + str(e))
                return None




class TypeGenNode(GraphBaseNode):
    def __init__(self, operation, ins, outs, func = None, attr = None, splitindex = 0):
        super(TypeGenNode, self).__init__(ins, outs, operation)
        self.nodetype = "TypeGen"
        self.op = operation
        #for Call AST nodes
        self.func = func
        #for Attribute AST nodes
        self.attr = attr
        self.types = []
        self.splitindex = 0
        self.rejinputtypes = []

    def setFunc(self, func):
        self.func = func

    def checktypes(self):
        for n in self.ins:
            if len(n.types) == 0:
                return False
        return True

    def performTypingRules(self, usertype = None, iterable=False):
        # if it's not about ierable or it's call -> format(which may cause more than 3 input nodes)
        #if not iterable and not(self.op == "call" and (self.func in call_overargu_funcs)):
        if not iterable and self.op != "call":
        # if not iterable and not (self.op=="call" and self.func=="format") and not (self.op=="call" and (self.func=="count" or self.func=="index" or self.func=="endswith")):
            # since it's possible that the length of ins is more than 3 when x if xx else xx is concerned, we don't check the len of ins
            # e.g state = (IOLoop.READ if readable else 0) | (IOLoop.WRITE if writable else 0)
            # if self.op !='Subscript_Write':
            #     if len(self.ins) > 3:
            #         raise ValueError("TypeGenNode should not have more than 3 input nodes.(Not include List)")
            if self.op=='Subscript_Write':
                if len(self.ins) > 4:
                    raise ValueError("TypeGenNode with Subscript_Write should not have more than 4 input nodes")

        norej = True
        typerule = TypingRule()
        outputs = typerule.act(self.ins, self.op, self.func, self.attr, usertype, iterable=iterable, curnode = self)
        if self.op not in ["List_Write", "Tuple_Write"]:
            if len(outputs) == 2:
                self.rejinputtypes = outputs[0]
                if not isinstance(outputs[1], list):
                    self.types = [outputs[1]]
                else:
                    self.types = outputs[1]
                if len(self.rejinputtypes) < len(self.ins):
                    if self.op == "call":
                        logger.error("[Static Inference]Incorrect number of rejected types in {} {} at line {}. Expected number of rejected types are {} but get {}".format(self.op, self.func, self.lineno, len(self.ins), len(self.rejinputtypes)))
                        raise ValueError("Incorrect number of rejected types " + "in " + self.op + self.func + " at Line: " + str(self.lineno) )
                    else:
                        logger.error("[Static Inference]Incorrect number of rejected types in {} at line {}. Expected number of rejected types are {} but get {}".format(self.op, self.lineno, len(self.ins), len(self.rejinputtypes)))
                        raise ValueError("Incorrect number of rejected types " + "in " + self.op + " at Line: " + str(self.lineno) )
                elif self.checktypes():
                    for i,n in enumerate(self.rejinputtypes):
                        if len(n) != 0:
                            norej = False
                        if i < len(self.ins):
                            for t in n:
                                if t.added and t not in self.ins[i].rejtypes:
                                    self.ins[i].rejtypes.append(t)
            else:
                raise ValueError("outputs should have at least 3 elements.")
        # if it's list_write or tuple_write
        else:
            if len(outputs) == 2:
                self.rejinputtypes = outputs[0]
                if not isinstance(outputs[1], list):
                    self.types = [outputs[1]]
                else:
                    self.types = outputs[1]
                if len(self.rejinputtypes) < len(self.ins):
                    raise ValueError("Incorrect number of rejected types.")
                else:
                    for i,n in enumerate(self.rejinputtypes):
                        if len(n) != 0:
                            norej = False
                        if i < len(self.ins):
                            for t in n:
                                if t.added and t not in self.ins[i].rejtypes:
                                    self.ins[i].rejtypes.append(t)
        return norej

    def performRejTypingRule(self, usertype = None, iterable = False):
        rejtyperule = Rej_TypingRule()
        rejtypes = rejtyperule.act(self, self.ins, self.op, self.func, self.attr, usertype, iterable = iterable)
        if len(rejtypes) != len(self.ins):
            if self.op == "call":
                logger.error("[Static Inference]Incorrect number of rejected types in {} {} at line {}. Expected number of rejected types are {} but get {}".format(self.op, self.func, self.lineno, len(self.ins), len(rejtypes)))
                raise ValueError("Incorrect number of rejected types " + "in " + self.op +  " " + self.func + " at Line: " + str(self.lineno) )
            else:
                logger.error("[Static Inference]Incorrect number of rejected types in {} at line {}. Expected number of rejected types are {} but get {}".format(self.op, self.lineno, len(self.ins), len(rejtypes)))
                raise ValueError("Incorrect number of rejected types " + "in " + self.op + " at Line: " + str(self.lineno) )
        else:
            for i,n in enumerate(rejtypes):
                self.ins[i].rejtypes += n
        
    def dump(self):
        node = self._dump()
        node["nodetype"] = self.nodetype
        node["op"] = self.op
        node["func"] = self.func
        node["attr"] = self.attr
        node["types"] = []
        for t in self.types:
            if isinstance(t, TypeObject):
                node["types"].append(t.dump())
            else:
                node["types"].append(t)
        node["splitindex"] = self.splitindex
        node["rejinputtypes"] = []
        for t in self.rejinputtypes:
            if isinstance(t, TypeObject):
                node["rejinputtypes"].append(t.dump())
            else:
                node["rejinputtypes"].append(t)
        return node


    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an TypeGenNode object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["nodetype", "ins", "outs", "name", "lineno", "columnno", "columnend", "tg", "rejtypes", "visitlabel", "types", "op", "func", "attr", "splitindex", "rejinputtypes"]):
            logger.error("Missing important information when resuming the TypeGenNode object!")
            return None
        else:
            try:
                node = TypeGenNode(dictobj["op"], [], [], func = dictobj["func"], attr = dictobj["attr"], splitindex = dictobj["splitindex"])
                node.nodetype = dictobj["nodetype"]
                node.name = dictobj["name"]
                node.lineno = dictobj["lineno"]
                node.columnno = dictobj["columnno"]
                node.columnend = dictobj["columnend"]
                node.visitlabel = dictobj["visitlabel"]
                node.nodeid = dictobj["nodeid"]
                node.types = []
                for t in dictobj["types"]:
                    node.types.append(TypeObject.load(t))
                node.rejtypes = []
                for t in dictobj["rejtypes"]:
                    node.rejtypes.append(TypeObject.load(t))
                node.rejinputtypes = []
                for t in dictobj["rejinputtypes"]:
                    node.rejinputtypes.append(TypeObject.load(t))
                return node
            except Exception as e:
                logger.error("Cannot resume TypeGenNode object, reason: " + str(e))
                return None
        


class TypeNode(GraphBaseNode):
    def __init__(self, outs, t):
        if(not isinstance(t, TypeObject)):
            raise ValueError("t must be a TypeObject object.")
        super(TypeNode, self).__init__({}, outs, t.type)
        self.nodetype = "Type"
        self.type = t
        self.types = [t]

    def dump(self):
        node = self._dump()
        node["nodetype"] = self.nodetype
        node["type"] = self.type.dump()
        node["types"] = []
        for t in self.types:
            node["types"].append(t.dump())
        node["rejtypes"] = []
        for t in self.rejtypes:
            node["rejtypes"].append(t.dump())
        return node


    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an TypeNode object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["nodetype", "ins", "outs", "name", "lineno", "columnno", "columnend", "tg", "rejtypes", "visitlabel", "types", "type"]):
            logger.error("Missing important information when resuming the TypeNode object!")
            return None
        else:
            try:
                node = TypeNode([], TypeObject.load(dictobj["type"]))
                node.nodetype = dictobj["nodetype"]
                node.name = dictobj["name"]
                node.lineno = dictobj["lineno"]
                node.columnno = dictobj["columnno"]
                node.columnend = dictobj["columnend"]
                node.visitlabel = dictobj["visitlabel"]
                node.nodeid = dictobj["nodeid"]
                node.types = []
                for t in dictobj["types"]:
                    node.types.append(TypeObject.load(t))
                node.rejtypes = []
                for t in dictobj["rejtypes"]:
                    node.rejtypes.append(TypeObject.load(t))
                return node
            except Exception as e:
                logger.error("Cannot resume TypeNode object, reason: " + str(e))
                return None



class BranchNode(GraphBaseNode):
    def __init__(self, ins, outs, var):
        super(BranchNode, self).__init__(ins, outs, "branch")
        self.nodetype = "Branch"
        self.branchvar = var
        self.outtypes = []
        self.types = [[], []]
        self.rejtypes = [[], []]
    
    def addTypes(self, types):
        self.outtypes = types

    def splitTypes(self):
        if len(self.ins) != 1:
            logger.error("Branch node must have exactly one input node.")
            raise ValueError("Branch node must have exactly one input node.")
        elif len(self.outs) != 2:
            logger.error("Branch node must have exactly two output nodes.")
            raise ValueError("Branch node must have exactly two output nodes.")
        else:
            types = copy(self.ins[0].types)
            for t in self.outtypes:
                if t != None:
                    removetype = TypeObject.findSame(t, types)
                    if removetype != None:
                        types.remove(removetype)
            self.types = []
            for t in self.outtypes:
                if t != None:
                    self.types.append([t])
                else:
                    self.types.append(TypeObject.removeInclusiveTypes(types))
    
    def dump(self):
        node = self._dump()
        node["nodetype"] = self.nodetype
        node["branchvar"] = self.branchvar
        node["outtypes"] = []
        for t in self.outtypes:
            if t != None:
                node["outtypes"].append(t.dump())
            else:
                node["outtypes"].append(t)
        node["types"] = [[], []]
        for t in self.types[0]:
            node["types"][0].append(t.dump())
        for t in self.types[1]:
            node["types"][1].append(t.dump())
        node["rejtypes"] = [[], []]
        for t in self.rejtypes[0]:
            node["rejtypes"][0].append(t.dump())
        for t in self.rejtypes[1]:
            node["rejtypes"][1].append(t.dump())
        return node


    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an BranchNode object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["nodetype", "ins", "outs", "name", "lineno", "columnno", "columnend", "tg", "rejtypes", "visitlabel", "branchvar", "types", "outtypes"]):
            logger.error("Missing important information when resuming the BranchNode object!")
            return None
        else:
            try:
                node = BranchNode([], [], dictobj["branchvar"])
                node.nodetype = dictobj["nodetype"]
                node.name = dictobj["name"]
                node.lineno = dictobj["lineno"]
                node.columnno = dictobj["columnno"]
                node.columnend = dictobj["columnend"]
                node.visitlabel = dictobj["visitlabel"]
                node.nodeid = dictobj["nodeid"]
                node.types = [[], []]
                for t in dictobj["types"][0]:
                    node.types[0].append(TypeObject.load(t))
                for t in dictobj["types"][1]:
                    node.types[1].append(TypeObject.load(t))
                node.rejtypes = [[], []]
                for t in dictobj["rejtypes"][0]:
                    node.rejtypes[0].append(TypeObject.load(t))
                for t in dictobj["rejtypes"][1]:
                    node.rejtypes[1].append(TypeObject.load(t))
                node.outtypes = []
                for t in dictobj["outtypes"]:
                    if t != None:
                        node.outtypes.append(TypeObject.load(t))
                    else:
                        node.outtypes.append(t)
                return node
            except Exception as e:
                logger.error("Cannot resume BranchNode object, reason: " + str(e))
                return None
            



            


class MergeNode(GraphBaseNode):
    def __init__(self, ins, outs, var):
        super(MergeNode, self).__init__(ins, outs, "merge")
        self.nodetype = "Merge"
        self.mergevar = var
        self.types = []

    def dump(self):
        node = self._dump()
        node["nodetype"] = self.nodetype
        node["mergevar"] = self.mergevar
        node["types"] = []
        for t in self.types:
            node["types"].append(t.dump())
        return node

    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an MergeNode object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["nodetype", "ins", "outs", "name", "lineno", "columnno", "columnend", "tg", "rejtypes", "visitlabel", "mergevar", "types"]):
            logger.error("Missing important information when resuming the MergeNode object!")
            return None
        else:
            try:
                node = MergeNode([], [], dictobj["mergevar"])
                node.nodetype = dictobj["nodetype"]
                node.name = dictobj["name"]
                node.lineno = dictobj["lineno"]
                node.columnno = dictobj["columnno"]
                node.columnend = dictobj["columnend"]
                node.visitlabel = dictobj["visitlabel"]
                node.nodeid = dictobj["nodeid"]
                node.types = []
                for t in dictobj["types"]:
                    node.types.append(TypeObject.load(t))
                node.rejtypes = []
                for t in dictobj["rejtypes"]:
                    node.rejtypes.append(TypeObject.load(t))
                return node
            except Exception as e:
                logger.error("Cannot resume MergeNode object, reason: " + str(e))
                return None

                

        
        

    
        


class TypeGraph(object):
    def __init__(self, name, usertypes, filename, classname, globaltg):
        self.name = name
        self.filename = filename
        self.nodes = []
        self.symbolnodes = {}
        self.typegennodes = {}
        self.typenodes = {}
        self.branchnodes = []
        self.mergenodes = []
        self.classname = classname
        self.globaltg = globaltg

        #for graph generation
        self.loopbuffer = []
        self.inloop = 0
        self.trybuffer = []
        self.intry = 0
        self.exceptbuffer = []
        self.inexcept = 0

        self.usertypes = usertypes
        self.argnodes = []
        self.returnvaluenodes = []
        self.startlineno = 0

        self.nodeindex = 0


    def getNode(self, lineno, name, nodetype = "Symbol"):
        if nodetype == "Symbol":
            for n in self.symbolnodes:
                if n.lineno == lineno and n.name == name:
                    return n
        elif nodetype == "TypeGen":
            for n in self.typegennodes:
                if n.lineno == lineno and n.op == name:
                    return n
        else:
            return None


    def addNode(self, node):
        if self.inloop:
            if len(self.loopbuffer) != self.inloop:
                self.loopbuffer.append([node])
            else:
                self.loopbuffer[self.inloop - 1].append(node)
        if self.intry and len(self.trybuffer) != self.intry:
            varmap = {}
            self.trybuffer.append(varmap)
        elif self.intry and isinstance(node, SymbolNode) and node.ctx == "Write":
            if node.symbol not in self.trybuffer[self.intry - 1]:
                self.trybuffer[self.intry - 1][node.symbol] = [node]
            elif node.symbol in self.trybuffer[self.intry - 1]:
                self.trybuffer[self.intry - 1][node.symbol].append(node)
        if self.inexcept and len(self.exceptbuffer) != self.inexcept:
            varmap = {}
            self.exceptbuffer.append(varmap)
        elif self.inexcept and isinstance(node, SymbolNode) and node.ctx == "Write":
            self.exceptbuffer[self.inexcept - 1][node.symbol] = node
        elif self.inexcept and isinstance(node, SymbolNode) and node.ctx == "Read":
            if len(self.exceptbuffer) == self.inexcept and node.symbol in self.exceptbuffer[self.inexcept - 1]:
                self.exceptbuffer[self.inexcept - 1][node.symbol] = node
        self.nodes.append(node)
        if not isinstance(node.tg, GlobalTypeGraph):
            node.tg = self
            node.nodeid = self.name + "@" + str(self.nodeindex)
            self.nodeindex += 1
        if (isinstance(node, SymbolNode)):
            if node.ctx == "Arg":
                self.argnodes.append(node)
            elif node.ctx == "Return":
                self.returnvaluenodes.append(node)
            if (node.symbol not in self.symbolnodes):
                self.symbolnodes[node.symbol] = [node]
            else:
                self.symbolnodes[node.symbol].append(node)
        elif (isinstance(node, TypeGenNode)):
            if (node.op not in self.typegennodes):
                self.typegennodes[node.op] = [node]
            else:
                self.typegennodes[node.op].append(node)
        elif (isinstance(node, TypeNode)):
            if (node.type not in self.typenodes):
                self.typenodes[node.type] = node
        elif (isinstance(node, BranchNode)):
            self.branchnodes.append(node)
        elif (isinstance(node, MergeNode)):
            self.mergenodes.append(node)

    def hasNode(self, node):
        if node in self.nodes:
            return True
        else:
            return False

    def getEmptySymbols(self):
        emptysymbols = []
        for key in self.symbolnodes:
            for n in self.symbolnodes[key]:
                if len(n.types) == 0:
                    emptysymbols.append(n)
        return emptysymbols

    def getFailedTypeGens(self):
        failedtypegens = []
        for key in self.typegennodes:
            for n in self.typegennodes[key]:
                if len(n.types) == 0:
                    failedtypegens.append(n)

    def getNoInputNodes(self):
        noinputnodes = []
        for n in self.nodes:
            if len(n.ins) == 0 and n not in noinputnodes:
                noinputnodes.append(n)
        return noinputnodes

    def clearVisitLabel(self):
        for n in self.nodes:
            n.visitlabel = 0

    def getNodewithRejTypes(self):
        nodes = []
        for n in self.nodes:
            if not isinstance(n, BranchNode) and len(n.rejtypes) != 0:
                nodes.append(n)
            elif isinstance(n, BranchNode) and (len(n.rejtypes[0]) != 0 or len(n.rejtypes[1]) != 0):
                nodes.append(n)
        return nodes
    
    def isDominate(self, a, b, iternum):
        if iternum > 100:
            return False
        if len(a.outs) == 0:
            return False
        elif a == b:
            return True
        else:
            bemptyins = []
            for innode in b.ins:
                if len(innode.types) == 0:
                    if isinstance(innode, TypeGenNode) and innode.op == "call" and innode.func != None and  "_@_" in innode.func:
                        return False
                    bemptyins.append(innode)
            if len(bemptyins) == 0:
                return False
            for node in bemptyins:
                if not self.isDominate(a, node, iternum+1):
                    return False

            return True

    def isSetDominate(self, seta, b, iternum):
        outs = []
        if iternum > 100:
            return False
        for n in seta:
            outs += n.outs
        if len(outs) == 0:
            return False
        elif b in seta:
            return True
        else:
            bemptyins = []
            for innode in b.ins:
                if len(innode.types) == 0:
                    if isinstance(innode, TypeGenNode) and innode.op == "call" and innode.func != None and  "_@_" in innode.func:
                        return False
                    bemptyins.append(innode)
            if len(bemptyins) == 0:
                return False
            for node in bemptyins:
                if not self.isSetDominate(seta, node, iternum +1):
                    return False
            return True

    def getReturnType(self):
        returntype = []
        if len(self.returnvaluenodes) == 0:
            return [TypeObject("None",0)]
        for r in self.returnvaluenodes:
            returntype += r.types
        return returntype



        





    def passTypes(self, debug = False):

        #print message
        logger.info("[Static Inference] Start iterating TDG " + self.name)


        changed = True
        iters = 0
        while(changed and iters < config["max_tdg_iteration"]):

            logger.debug("[Static Inference] iters: " + str(iters))


            changed = False

            #Forward Passing Types
            queue = self.getNoInputNodes()

            logger.debug("[Static Inference] Initial nodes:")
            for n in queue:
                if isinstance(n, TypeGenNode) and n.name == "call" and n.func != None:
                    logger.debug("initial node: " + n.name + n.func +  " at Line: " + str(n.lineno))
                else:
                    logger.debug("initial node: " + n.name +  " at Line: " + str(n.lineno))
                    
            


            iters += 1
            self.clearVisitLabel()
            inneriter = 0
            while(len(queue) != 0 and inneriter < 1000):
                inneriter += 1
                curnode = queue[0]
                queue.pop(0)
                curnode.visitlabel = 2

                if isinstance(curnode, TypeGenNode) and curnode.name == "call" and curnode.func != None:
                    logger.debug("[Static Inference] visit node: " + curnode.name + curnode.func + " at Line: " + str(curnode.lineno) + " (label:" + str(curnode.visitlabel) + ")")
                else:
                    logger.debug("[Static Inference] visit node: " + curnode.name + " at Line: " + str(curnode.lineno) + " (label:" + str(curnode.visitlabel) + ")")

                for n in curnode.ins:
                    if n.visitlabel < 2:
                        curnode.visitlabel = 1
                        if curnode not in queue:
                            queue.append(curnode)

                if curnode.visitlabel == 2:
                    logger.debug("[Static Inference] This node is finalized.")
                    if isinstance(curnode, SymbolNode):
                        if len(curnode.ins) > 1:
                            logger.error("[Static Inference] Symbol node should not have more than 1 input nodes.")
                            raise ValueError("Symbol node should not have more than 1 input nodes.")
                        else:
                            if curnode.scope == "global" and len(curnode.types) == 0:
                                types = []
                                for n in self.globaltg.globalsymbols[curnode.symbol]:
                                    for t in n.types:
                                        if not TypeObject.existSame(t, types):
                                            types.append(t)
                                curnode.types = types
                            for n in curnode.ins:
                                if curnode.tag != 1 and curnode.tag != 4:
                                    curnode.tag = 3
                                    if not isinstance(n, BranchNode) and not TypeObject.isIdenticalSet(n.types, curnode.types):
                                        logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "Changed.")
                                        changed = True
                                        curnode.types = copy(n.types)
                                    elif isinstance(n, BranchNode) and not TypeObject.isIdenticalSet(n.types[n.outs.index(curnode)], curnode.types):
                                        logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "Changed.")
                                        changed = True
                                        curnode.types = copy(n.types[n.outs.index(curnode)])
                                elif not isinstance(n, BranchNode) and  not TypeObject.isIdenticalSet(n.types, curnode.types):
                                    pass
                                    #logger.warning("[Static Inference] The types of " + curnode.name + " is statically added as: {" + TypeObject.resolveTypeNames(curnode.types) + "}" + "However, the types of input node are: {" +TypeObject.resolveTypeNames(n.types) + "}")
                                elif isinstance(n, BranchNode) and not TypeObject.isIdenticalSet(n.types[n.outs.index(curnode)], curnode.types):
                                    pass
                                    #logger.warning("[Static Inference] The types of " + curnode.name + " is statically added as: {" + TypeObject.resolveTypeNames(curnode.types) + "}" + "However, the types of input node are: {" +TypeObject.resolveTypeNames(n.types[n.outs.index(curnode)]) + "}")
                    elif isinstance(curnode, TypeGenNode):
                        curnode.tag = 3
                        prev_types = deepcopy(curnode.types)
                        if curnode.op == "call" and not curnode.performTypingRules(usertype = self.usertypes):
                            pass
                        elif curnode.op not in ["List_Read", "List_Write", "Set_Read", "Dict_Read", "Tuple_Read", "Tuple_Write", "JoinedStr"] and not curnode.performTypingRules(usertype = self.usertypes):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "reject some types.")
                            #TODO:changed = True
                        elif curnode.op in ["List_Read", "List_Write", "Set_Read", "Dict_Read", "Tuple_Read", "Tuple_Write", "JoinedStr"] and not curnode.performTypingRules(usertype = self.usertypes, iterable = True):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "reject some types.")
                            #TODO:changed = True
                        curnode.types = curnode.types
                        if not TypeObject.isIdenticalSet(prev_types, curnode.types):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "reject some types.")
                            changed = True
                    elif isinstance(curnode, TypeNode):
                        curnode.tag = 3
                    elif isinstance(curnode, MergeNode):
                        curnode.tag = 3
                        prev_types = deepcopy(curnode.types)
                        curnode.types = []
                        for n in curnode.ins:
                            if not isinstance(n, BranchNode):
                                for t in n.types:
                                    if not TypeObject.existSame(t, curnode.types):
                                        curnode.types.append(t)
                            else:
                                for t in n.types[n.outs.index(curnode)]:
                                    if not TypeObject.existSame(t, curnode.types):
                                        curnode.types.append(t)
                        curnode.types = curnode.types
                        if not TypeObject.isIdenticalSet(prev_types, curnode.types):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "changed.")
                            changed = True
                    elif isinstance(curnode, BranchNode):
                        curnode.tag = 3
                        prev_types = deepcopy(curnode.types)
                        curnode.splitTypes()
                        if not TypeObject.isIdenticalSet(prev_types[0], curnode.types[0]) or not TypeObject.isIdenticalSet(prev_types[1], curnode.types[1]):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "changed.")
                            changed = True

                for n in curnode.outs:
                    if n == "PlaceHolder":
                        continue
                    elif n.visitlabel == 0:
                        n.visitlabel = 1
                        queue.append(n)
                        if isinstance(n, TypeGenNode) and n.name == "call":
                            logger.debug("[Static Inference] Add node: " + n.name + n.func + " at Line: " + str(n.lineno))
                        else:
                            logger.debug("[Static Inference] Add node: " + n.name + " at Line: " + str(n.lineno))
                    #this indicate a loop occurs
                    elif n.visitlabel == 1:
                        pass
                    elif n.visitlabel == 2:
                        if isinstance(n, TypeGenNode) and n.name == "call":
                            logger.debug("[Static Inference] Node: " + n.name + n.func +  " at Line: " + str(n.lineno) +" has been finalized.")
                        else:
                            logger.debug("[Static Inference] Node: " + n.name +  " at Line: " + str(n.lineno) +" has been finalized.")
            #Backward Rejecting Types
            
            
            queue = self.getNodewithRejTypes()
            while(len(queue) != 0):
                for n in queue:
                    if isinstance(n, SymbolNode):
                        endrejtypes = []
                        for t in n.rejtypes:
                            rejt = TypeObject.findSame(t, n.types)
                            if rejt != None:
                                n.types.remove(rejt)
                                if rejt.startnodename == n.symbol and rejt.startnodeorder == n.order:
                                    endrejtypes.append(rejt)
                        if len(n.ins) == 1:
                            if isinstance(n.ins[0], BranchNode):
                                for t in n.rejtypes:
                                    if TypeObject.existSame(t, n.ins[0].types[n.ins[0].outs.index(n)]) and t not in endrejtypes:
                                        n.ins[0].rejtypes[n.ins[0].outs.index(n)].append(t)
                            else:
                                for t in n.rejtypes:
                                    if TypeObject.existSame(t, n.ins[0].types) and t not in endrejtypes:
                                        n.ins[0].rejtypes.append(t)
                        n.rejtypes = []
                    elif isinstance(n, TypeNode):
                        for t in n.rejtypes:
                            if TypeObject.findSame(t, n.types) != None:
                                logger.debug("Type node at Line: " + str(n.lineno) +  " with type " + TypeObject.resolveTypeName(t) + str(t.added) + " is rejected. ")
                                #raise ValueError("Type node at Line: " + str(n.lineno) +  " is rejected. " + TypeObject.resolveTypeName(t) + str(t.added))
                        n.rejtypes = []
                    elif isinstance(n, TypeGenNode) and len(n.rejtypes) != 0:
                        if n.op not in ["List_Read", "List_Write", "Set_Read", "Dict_Read", "Tuple_Read", "Tuple_Write", "JoinedStr"]:
                            n.performRejTypingRule(usertype = self.usertypes)
                        else:
                            n.performRejTypingRule(usertype = self.usertypes, iterable = True)
                        n.rejtypes = []
                    elif isinstance(n, BranchNode):
                        for t in n.rejtypes[0]:
                            rejt = TypeObject.findSame(t, n.types[0])
                            if rejt != None:
                                n.types[0].remove(rejt)
                        for t in n.rejtypes[1]:
                            rejt = TypeObject.findSame(t, n.types[1])
                            if rejt != None:
                                n.types[1].remove(rejt)
                        
                        for t in n.rejtypes[0]:
                            if TypeObject.existSame(t, n.ins[0].types):
                                n.ins[0].rejtypes.append(t)
                        
                        for t in n.rejtypes[1]:
                            if len(n.ins) > 1 and TypeObject.existSame(t, n.ins[1].types):
                                n.ins[1].rejtypes.append(t)

                        n.rejtypes = [[],[]]
                    elif isinstance(n, MergeNode):
                        for t in n.rejtypes:
                            rejt = TypeObject.findSame(t, n.types)
                            if rejt != None:
                                n.types.remove(rejt)
                        for innode in n.ins:
                            for t in n.rejtypes:
                                if TypeObject.existSame(t, innode.types):
                                    innode.rejtypes.append(t)
                        n.rejtypes = []
                    else:
                        raise TypeError("Unknown Node.")
                queue = self.getNodewithRejTypes()
                
                        

        #print message
        logger.info("[Static Inferece] Finished iterating TDG.")


    
    def findHotTypes(self):
        logger.info("[Hot Type Slot Finder] Start finding hot type slots in TDG:" + self.name)
        queue = self.getEmptySymbols()
        removed = []
        for i in range(0, len(queue)):
            for j in range(0, len(queue)):
                if i != j and self.isDominate(queue[i], queue[j], 0):
                    removed.append(queue[j])
        for n in removed:
            if n in queue:
                queue.remove(n)
        removed = []

        for n in queue:
            nodes = copy(queue)
            nodes.remove(n)
            if self.isSetDominate(nodes, n, 0):
                removed.append(n)
        for n in removed:
            if n in queue:
                queue.remove(n)
        
        for n in self.argnodes:
            if len(n.types) == 1 and n.types[0].type == "None" and n not in queue:
                queue.append(n)
        
        removed = []
        for n in queue:
            if n.ctx == "Return" and len(n.ins) == 0:
                removed.append(n)

        for n in removed:
            if n in queue:
                queue.remove(n)

        for n in queue:
            logger.info("Hot Type: " + n.name + " at Location: [" + str(n.lineno) + "," + str(n.columnno) + "," + str(n.columnend) + "]")

        logger.info("[Hot Type Slot Finder] Finished finding hot type slots in TDG:" + self.name)
        
        return queue


    def simplifyTypes(self):
        for n in self.nodes:
            if isinstance(n, BranchNode):
                types = []
                types.append(TypeObject.removeInclusiveTypes(n.types[0]))
                types.append(TypeObject.removeInclusiveTypes(n.types[1]))
                n.types = types
            elif n in self.returnvaluenodes and len(n.ins) == 0:
                n.types.append(TypeObject("None", 0))
            else:
                n.types = TypeObject.removeInclusiveTypes(n.types)



    #This function defines how to map the explicitly wrong recommended types to a valid type
    def replaceType(self, usertypes, tt, nodename, simmodel = None):
        if tt.category != 0 and tt.type not in usertypes and len(tt.type) != 0:
            largest_score = 0
            largest_type = None
            typestr = tt.type
            for ut in usertypes:
                if simmodel:
                    if typestr != "" and ut[0].split(".")[-1] != "":
                        score = simmodel.get_similarity(typestr, ut[0].split(".")[-1])
                    else:
                        score = 0
                else:
                    score = Levenshtein.ratio(typestr, ut[0].split(".")[-1])
                if score > largest_score:
                    largest_score = score
                    largest_type = ut[0]
            nscore = 0
            ntype = None
            for ut in usertypes:
                
                if simmodel:
                    if nodename != "" and ut[0].split(".")[-1] != "":
                        score = simmodel.get_similarity(nodename, ut[0].split(".")[-1])
                    else:
                        score = 0
                else:
                    score = Levenshtein.ratio(nodename, ut[0].split(".")[-1])
                if score > nscore:
                    nscore = score
                    ntype = ut[0]
            if not simmodel:
                if largest_type != None and largest_score + 0.1 >= nscore:
                    logger.info("[Type Correction]Recommended type {} has been corrected to {} for variable {}".format(typestr, largest_type, nodename))
                    tt.type = largest_type
                    tt.category = 2
                elif ntype != None and largest_score + 0.1 < nscore:
                    logger.info("[Type Correction]Recommended type {} has been corrected to {} for variable {}".format(typestr, ntype, nodename))
                    tt.type = ntype
                    tt.category = 2
            else:
                if largest_type != None and largest_score > nscore:
                    logger.info("[Type Correction]Recommended type {} has been corrected to {} for variable {}".format(typestr, largest_type, nodename))
                    tt.type = largest_type
                    tt.category = 2
                elif ntype != None and largest_score <= nscore:
                    logger.info("[Type Correction]Recommended type {} has been corrected to {} for variable {}".format(typestr, ntype, nodename))
                    tt.type = ntype
                    tt.category = 2
            

    def recommendType(self, typeslots, recommendations, usertypes, modules, topn, simmodel = None):
        classname = self.name.split("@")[-1]
        funcname = "{}.{}".format(classname, self.name.split("@")[0])
        if "," in classname:
            classname = classname.split(",")[-1]
        if classname not in recommendations or funcname not in recommendations[classname]:
            logger.error("[Type Recommendation]Cannot find the entry in recommendations for current TDG {}".format(self.name))
            return None
        rec = recommendations[classname][funcname]
        for t in typeslots:
            name = t.symbol
            if t.ctx == "Arg":
                name = name.replace("(arg)", "").split("@")[0]
            elif t.ctx == "Return":
                name = name.replace("Return_Value@", "").split("@")[0]
            else:
                name = name.split("@")[0] 
            rectypes = []
            for r in rec["annotations"]:
                if r["name"] == name and r["category"] == t.ctx.lower().replace("read", "local").replace("write", "local"):
                    for i in range(0, topn):
                        if i < len(r["type"]):
                            rectypes += TypeObject.Str2Obj(r["type"][i])
            if len(rectypes) == 0:
                logger.warning("[Type Recommendation]Cannot get the recommended types for varibale {} or the recommended type set is empty.".format(name))
                continue
            verifiedtypes = []
            for tt in rectypes:
                if tt.category == 0:
                    for ett in tt.elementtype:
                        if ett.category != 0 and ett.type.split(".")[0] not in modules:
                            self.replaceType(usertypes, ett, name, simmodel = simmodel)
                    for ett in tt.keytype:
                        if ett.category != 0 and ett.type.split(".")[0] not in modules:
                            self.replaceType(usertypes, ett, name, simmodel = simmodel)
                    for ett in tt.valuetype:
                        if ett.category != 0 and ett.type.split(".")[0] not in modules:
                            self.replaceType(usertypes, ett, name, simmodel = simmodel)
                    verifiedtypes.append(tt)
                elif tt.category != 0 and tt.type.split(".")[0] not in modules:
                    self.replaceType(usertypes, tt, name, simmodel = simmodel)
            logger.info("[Type Recommendation]Found recommendation for variable {}, recommended types: {}".format(name, TypeObject.DumpOriObjects(rectypes)))
            for tt in rectypes:
                tt.added = True
                tt.startnodename = t.symbol
                tt.startnodeorder = t.order
            verifiedtypes = TypeObject.removeRedundantTypes(verifiedtypes)
            t.types += verifiedtypes
            t.tag = 4

    def storeAttributeTypes(self):
        if self.name == "__init__":
            for n in self.nodes:
                if isinstance(n, SymbolNode) and n.scope == "attribute":
                    if n.classname not in self.globaltg.classtypes:
                        self.globaltg.classtypes[n.classname] = {}
                        self.globaltg.classtypes[n.classname]["@id@"] = {}
                    if n.symbol not in self.globaltg.classtypes[n.classname]:
                        self.globaltg.classtypes[n.classname][n.symbol] = []
                        self.globaltg.classtypes[n.classname]["@id@"][n.symbol] = 0
                    if len(n.types) > 0 and n.order >= self.globaltg.classtypes[n.classname]["@id@"][n.symbol]:
                        self.globaltg.classtypes[n.classname][n.symbol] = copy(n.types)
                        self.globaltg.classtypes[n.classname]["@id@"][n.symbol] = n.order

    def recommendReturnType(self, recommendations, usertypes, modules, topn, filename = None, model = None, nn = "typilus"):
        nodes = []
        for n in self.returnvaluenodes:
            if len(n.types) == 0 and len(n.ins) != 0:
                nodes.append(n)

        self.recommendType(nodes, recommendations, usertypes, modules, topn,  filename = filename, model = model, nn = nn)

                

            
            
        
    

            



    

    


            
    def resolveName(self, node):
        if (isinstance(node, SymbolNode)):
            if "Return_Value" in node.name:
                return node.name + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]" + "\n " + str(TypeObject.resolveTypeNames(node.types))
            elif node.scope == "attribute":
                return str(node.classname) + "." + str(node.name) + "," + str(node.order) + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]" + "\n " + str(TypeObject.resolveTypeNames(node.types))
            else:
                return node.name + "," + str(node.order) + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]" + "\n " + str(TypeObject.resolveTypeNames(node.types))
        elif (isinstance(node, TypeGenNode)):
            if node.name == "call":
                return str(node.name) + " " + str(node.func) + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]"
            else:
                return str(node.name) + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]"
        elif (isinstance(node, TypeNode)):
            return str(node.name) + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]"
        elif (isinstance(node, BranchNode)):
            return str(node.name) + " " + str(node.branchvar)
        elif (isinstance(node, MergeNode)):
            return str(node.name) + " " + str(node.mergevar)
        else:
            return str(node.name)


    def draw(self, filerepo = None):
        if filerepo != None:
            filename = filerepo + "/" + self.filename.replace("/", "_") + "_" + self.name
        else:
            filename = self.filename.replace("/", "_") + "_" + self.name
        f = Digraph("Type Graph", filename = filename)

        #draw symbol node
        f.attr("node", shape = "box")
        for key in self.symbolnodes:
            for n in self.symbolnodes[key]:
                f.node(self.resolveName(n))
                

        #draw typegen node
        f.attr("node", shape = "ellipse")
        for key in self.typegennodes:
            for n in self.typegennodes[key]:
                f.node(self.resolveName(n))
        
        for n in self.mergenodes:
            f.node(self.resolveName(n))
        
        for n in self.branchnodes:
            f.node(self.resolveName(n))

        #draw type node
        f.attr("node", shape = "circle")
        for key in self.typenodes:
            f.node(self.resolveName(self.typenodes[key]))

        f.attr("node", shape = "triangle")

        i = 0
        #draw arrows
        for n in self.nodes:
            for outn in n.outs:
                if self.hasNode(outn):
                    i += 1
                    f.edge(self.resolveName(n), self.resolveName(outn))
        #f.view(filename = self.name)
        f.render(filename=filename,view=False)


    def returntypes(self):
        types = []
        typemap = {}
        explicitreturn = False
        for s in self.symbolnodes:
            for n in self.symbolnodes[s]:
                if n.ctx == "Arg":
                    if "arg@" + n.symbol.replace("(arg)", "").split("@")[0] not in typemap:
                        res = {"category": "arg", "name": n.symbol.replace("(arg)", "").split("@")[0], "type": []}
                        typemap["arg@" + n.symbol.replace("(arg)", "").split("@")[0]] = res
                    else:
                        res = typemap["arg@" + n.symbol.replace("(arg)", "").split("@")[0]]
                    for t in n.types:
                        if not TypeObject.existSame(t, res["type"]):
                            res["type"].append(t)
                elif n.ctx == "Return":
                    if "return@" + n.symbol.replace("Return_Value@", "").split("@")[0] not in typemap:
                        res = {"category": "return", "name": n.symbol.replace("Return_Value@", "").split("@")[0], "type": []}
                        typemap["return@" + n.symbol.replace("Return_Value@", "").split("@")[0]] = res
                    else:
                        res = typemap["return@" + n.symbol.replace("Return_Value@", "").split("@")[0]]
                    for t in n.types:
                        if not TypeObject.existSame(t, res["type"]):
                            res["type"].append(t)
                    explicitreturn = True
                else:
                    if "local@" + n.symbol.split("@")[0] not in typemap:
                        res = {"category": "local", "name": n.symbol.split("@")[0], "type": []}
                        typemap["local@" + n.symbol.split("@")[0]] = res
                    else:
                        res = typemap["local@" + n.symbol.split("@")[0]]
                    for t in n.types:
                        if not TypeObject.existSame(t, res["type"]):
                            res["type"].append(t)

        for t in typemap:
            types.append(typemap[t])
        if explicitreturn == False:
            types.append({"category": "return", "name": self.name.split("@")[0], "type": [TypeObject("None", 0)]})

        return types
    
    def dumptypes(self):
        types = []
        typemap = {}
        explicitreturn = False
        for s in self.symbolnodes:
            for n in self.symbolnodes[s]:
                if n.ctx == "Arg":
                    if "arg@" + n.symbol.replace("(arg)", "").split("@")[0] not in typemap:
                        res = {"category": "arg", "name": n.symbol.replace("(arg)", "").split("@")[0], "type": []}
                        typemap["arg@" + n.symbol.replace("(arg)", "").split("@")[0]] = res
                    else:
                        res = typemap["arg@" + n.symbol.replace("(arg)", "").split("@")[0]]
                    for t in n.types:
                        typename = TypeObject.resolveTypeName(t)
                        if typename not in res["type"]:
                            res["type"].append(typename)
                elif n.ctx == "Return":
                    if "return@" + n.symbol.replace("Return_Value@", "").split("@")[0] not in typemap:
                        res = {"category": "return", "name": n.symbol.replace("Return_Value@", "").split("@")[0], "type": []}
                        typemap["return@" + n.symbol.replace("Return_Value@", "").split("@")[0]] = res
                    else:
                        res = typemap["return@" + n.symbol.replace("Return_Value@", "").split("@")[0]]
                    for t in n.types:
                        typename = TypeObject.resolveTypeName(t)
                        if typename not in res["type"]:
                            res["type"].append(typename)
                    explicitreturn = True
                else:
                    if "local@" + n.symbol.split("@")[0] not in typemap:
                        res = {"category": "local", "name": n.symbol.split("@")[0], "type": []}
                        typemap["local@" + n.symbol.split("@")[0]] = res
                    else:
                        res = typemap["local@" + n.symbol.split("@")[0]]
                    for t in n.types:
                        typename = TypeObject.resolveTypeName(t)
                        if typename not in res["type"]:
                            res["type"].append(typename)
        for t in typemap:
            types.append(typemap[t])
        if explicitreturn == False:
            types.append({"category": "return", "name": self.name.split("@")[0], "type": ["None"]})
        return types




    def _dump(self, item):
        if isinstance(item, list):
            d = []
            for i in item:
                d.append(self._dump(i))
            return d
        elif isinstance(item, dict):
            d = {}
            for i in item:
                if isinstance(i, TypeObject):
                    d[i.type] = self._dump(item[i])
                else:
                    d[i] = self._dump(item[i])
            return d
        elif isinstance(item, SymbolNode) or isinstance(item, TypeGenNode) or isinstance(item, TypeNode) or \
            isinstance(item, BranchNode) or isinstance(item, MergeNode):
            return item.dump()
        elif isinstance(item, TypeGraph):
            return item.dump()
        elif isinstance(item, AliasGraph):
            return item.dump()
        else:
            return item
        



    def dump(self):
        tg = {}
        tg["name"] = self.name
        tg["filename"] = self.filename
        tg["nodes"] = self._dump(self.nodes)
        tg["symbolnodes"] = self._dump(self.symbolnodes)
        tg["typegennodes"] = self._dump(self.typegennodes)
        tg["typenodes"] = self._dump(self.typenodes)
        tg["branchnodes"] = self._dump(self.branchnodes)
        tg["mergenodes"] = self._dump(self.mergenodes)
        tg["classname"] = self.classname
        tg["globaltg"] = self.globaltg.name
        tg["inloop"] = self.inloop
        tg["loopbuffer"] = self._dump(self.loopbuffer)
        tg["trybuffer"] = self._dump(self.trybuffer)
        tg["intry"] = self.intry
        tg["exceptbuffer"] = self._dump(self.exceptbuffer)
        tg["inexcept"] = self.inexcept
        tg["usertypes"] = self.usertypes
        tg["argnodes"] = self._dump(self.argnodes)
        tg["returnvaluenodes"] = self._dump(self.returnvaluenodes)
        tg["startlineno"] = self.startlineno
        tg["nodeindex"] = self.nodeindex

        return tg


    @staticmethod
    def load(dictobj, globaltg = None):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an TypeGraph object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["name", "tgs", "symbolnodes", "typegennodes", "typenodes", "nodes", "branchnodes", "mergenodes", "inloop", \
            "loopbuffer", "trybuffer", "intry", "exceptbuffer", "inexcept", "usertypes", "argnodes", "returnvaluenodes", "startlineno", "nodeindex"]):
            logger.error("Missing important information when resuming the TypeGraph object!")
            return None
        else:
            try:
                tg = TypeGraph(dictobj["name"], dictobj["usertypes"], dictobj["filename"], dictobj["classname"], None)
                nodetype2load = {"Symbol": SymbolNode.load, "TypeGen": TypeGenNode.load, "Type": TypeNode.load, "Branch": BranchNode.load, "Merge": MergeNode.load}
                idmap = {}
                tg.nodes = []
                for n in dictobj["nodes"]:
                    node = nodetype2load[n["nodetype"]](n)
                    idmap[n["nodeid"]] = node
                    tg.nodes.append(node)
                    if dictobj["tg"][0] == tg.name:
                        node.tg = tg
                    elif globaltg != None:
                        node.tg = globaltg
                for n in dictobj["nodes"]:
                    for i in n["ins"]:
                        idmap[n["nodeid"]].ins.append(idmap[i])
                    for i in n["outs"]:
                        idmap[n["nodeid"]].outs.append(idmap[i])
                tg.symbolnodes = {}
                for name in dictobj["symbolnodes"]:
                    tg.symbolnodes[name] = []
                    for n in dictobj["symbolnodes"][name]:
                        tg.symbolnodes[name].append(idmap[n["nodeid"]])
                tg.typegennodes = {}
                for name in dictobj["typegennodes"]:
                    tg.typegennodes[name] = []
                    for n in dictobj["typegennodes"][name]:
                        tg.typegennodes[name].append(idmap[n["nodeid"]])
                tg.typenodes = {}
                for name in dictobj["typenodes"]:
                    if len(dictobj["typenodes"][name]) != 0:
                        tg.typenodes[idmap[dictobj["typenodes"][name][0]]] = []
                        for n in dictobj["typenodes"][name]:
                            tg.typenodes[idmap[dictobj["typenodes"][name][0]]].append(idmap[n["nodeid"]])
                tg.branchnodes = []
                for n in dictobj["branchnodes"]:
                    tg.branchnodes.append(idmap[n["nodeid"]])
                tg.mergenodes = []
                for n in dictobj["mergenodes"]:
                    tg.mergenodes.append(idmap[n["nodeid"]])
                tg.inloop = dictobj["inloop"]
                tg.loopbuffer = []
                for k in dictobj["loopbuffer"]:
                    temp = []
                    for n in k:
                        temp.append(idmap[n["nodeid"]])
                    tg.loopbuffer.append(temp)
                tg.intry = dictobj["intry"]
                tg.trybuffer = []
                for k in dictobj["trybuffer"]:
                    temp = {}
                    for n in k:
                        temp[n] = idmap[k[n]["nodeid"]]
                    tg.trybuffer.append(temp)
                tg.inexcept = dictobj["inexcept"]
                tg.exceptbuffer = []
                for k in dictobj["exceptbuffer"]:
                    temp = {}
                    for n in k:
                        temp[n] = idmap[k[n]["nodeid"]]
                    tg.exceptbuffer.append(temp)
                tg.argnodes = []
                for n in dictobj["argnodes"]:
                    tg.argnodes.append(idmap[n["nodeid"]])
                tg.returnvaluenodes = []
                for n in dictobj["returnvaluenodes"]:
                    tg.returnvaluenodes.append(idmap[n["nodeid"]])
                tg.startlineno = dictobj["startlineno"]
                return tg
            except Exception as e:
                logger.error("Cannot resume TypeGraph object, reason: " + str(e))
                return None
            



class GlobalTypeGraph(object):
    def __init__(self, name, usertypes):
        self.name = name
        self.tgs = []
        self.classnames = []
        self.globalsymbols = {}
        self.globaltypegennodes = {}
        self.globaltypenodes = {}
        self.globalnodes = []
        self.globalbranchnodes = []
        self.globalmergenodes = []
        self.inloop = 0
        self.loopbuffer = []
        self.trybuffer = []
        self.intry = 0
        self.exceptbuffer = []
        self.inexcept = 0
        self.usertypes = usertypes
        self.aliasgraph = AliasGraph()
        self.nodeindex = 0
        self.callgraph = None

        self.classtypes = {}

    def getTG(self, lineno):
        for i,tg in enumerate(self.tgs):
            if i < len(self.tgs) and self.tgs[i].startlineno > lineno and tg.startlineno <= lineno:
                return tg
        return None

    def addTG(self, tg):
        self.tgs.append(tg)

    def addClassname(self, clsname):
        if isinstance(clsname, list):
            for i in clsname:
                if i not in self.classnames:
                    self.classnames.append(i)
        else:
            self.classnames.append(clsname)

    def addNode(self, node):
        if self.inloop:
            if len(self.loopbuffer) != self.inloop:
                self.loopbuffer.append([node])
            else:
                self.loopbuffer[self.inloop - 1].append(node)
        if self.intry and len(self.trybuffer) != self.intry:
            varmap = {}
            self.trybuffer.append(varmap)
        elif self.intry and isinstance(node, SymbolNode) and node.ctx == "Write":
            if node.symbol not in self.trybuffer[self.intry - 1]:
                self.trybuffer[self.intry - 1][node.symbol] = [node]
            elif node.symbol in self.trybuffer[self.intry - 1]:
                self.trybuffer[self.intry - 1][node.symbol].append(node)
        if self.inexcept and len(self.exceptbuffer) != self.inexcept:
            varmap = {}
            self.exceptbuffer.append(varmap)
        elif self.inexcept and isinstance(node, SymbolNode) and node.ctx == "Write":
            self.exceptbuffer[self.inexcept - 1][node.symbol] = node
        elif self.inexcept and isinstance(node, SymbolNode) and node.ctx == "Read":
            if len(self.exceptbuffer) == self.inexcept and node.symbol in self.exceptbuffer[self.inexcept - 1]:
                self.exceptbuffer[self.inexcept - 1][node.symbol] = node
        self.globalnodes.append(node)
        node.tg = self
        node.nodeid = self.name + "@" + str(self.nodeindex)
        self.nodeindex += 1
        if (isinstance(node, SymbolNode) and node.scope != "local"):
            if (node.symbol not in self.globalsymbols):
                self.globalsymbols[node.symbol] = [node]
            else:
                self.globalsymbols[node.symbol].append(node)
        elif (isinstance(node, TypeGenNode)):
            if (node.op not in self.globaltypegennodes):
                self.globaltypegennodes[node.op] = [node]
            else:
                self.globaltypegennodes[node.op].append(node)
        elif (isinstance(node, TypeNode)):
            if (node.type not in self.globaltypenodes):
                self.globaltypenodes[node.type] = node
        elif (isinstance(node, BranchNode)):
            self.globalbranchnodes.append(node)
        elif (isinstance(node, MergeNode)):
            self.globalmergenodes.append(node)
    
    def hasNode(self, node):
        if node in self.globalnodes:
            return True
        else:
            return False

    def resolveName(self, node):
        if (isinstance(node, SymbolNode)):
            if "Return_Value" in node.name:
                return node.name + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]" + "\n " + str(TypeObject.resolveTypeNames(node.types))
            elif node.scope == "attribute":
                return str(node.classname) + "." + str(node.name) + "," + str(node.order) + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]" + "\n " + str(TypeObject.resolveTypeNames(node.types))
            else:
                return node.name + "," + str(node.order) + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]" + "\n " + str(TypeObject.resolveTypeNames(node.types))
        elif (isinstance(node, TypeGenNode)):
            if node.name == "call":
                return node.name + " " + node.func + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]"
            else:
                return node.name + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]"
        elif (isinstance(node, TypeNode)):
            return node.name + "\n  [" + str(node.lineno) + ", " + str(node.columnno) + ", " + str(node.columnend) + "]"
        elif (isinstance(node, BranchNode)):
            return str(node.name) + " " + str(node.branchvar)
        elif (isinstance(node, MergeNode)):
            return str(node.name) + " " + str(node.mergevar)
        elif isinstance(node, AliasNode):
            return str(node.name) + " @" +str(node.id) + "\n(" + str(node.scope) + ")"
        else:
            return str(node.name)

    def getNoInputNodes(self):
        noinputnodes = []
        for n in self.globalnodes:
            if len(n.ins) == 0 and n not in noinputnodes:
                noinputnodes.append(n)
        return noinputnodes

    def clearVisitLabel(self):
        for n in self.globalnodes:
            n.visitlabel = 0

    def getNodewithRejTypes(self):
        nodes = []
        for n in self.globalnodes:
            if not isinstance(n, BranchNode) and len(n.rejtypes) != 0:
                nodes.append(n)
            elif isinstance(n, BranchNode) and (len(n.rejtypes[0]) != 0 or len(n.rejtypes[1]) != 0):
                nodes.append(n)
        return nodes

    def passTypes(self, debug = False):

        #print message
        logger.info("[Static Inference] Start iterating Global TDG " + self.name)


        changed = True
        iters = 0
        while(changed and iters < 100):

            logger.debug("[Static Inference] iters: " + str(iters))


            changed = False

            #Forward Passing Types
            queue = self.getNoInputNodes()

            logger.debug("[Static Inference] Initial nodes:")
            for n in queue:
                if isinstance(n, TypeGenNode) and n.name == "call" and n.func != None:
                    logger.debug("initial node: " + n.name + n.func +  " at Line: " + str(n.lineno))
                else:
                    logger.debug("initial node: " + n.name +  " at Line: " + str(n.lineno))
                    
            


            iters += 1
            self.clearVisitLabel()
            inneriter = 0
            while(len(queue) != 0 and inneriter < 1000):
                inneriter += 1
                curnode = queue[0]
                queue.pop(0)
                curnode.visitlabel = 2

                if isinstance(curnode, TypeGenNode) and curnode.name == "call" and curnode.func != None:
                    logger.debug("[Static Inference] visit node: " + curnode.name + curnode.func + " at Line: " + str(curnode.lineno) + " (label:" + str(curnode.visitlabel) + ")")
                else:
                    logger.debug("[Static Inference] visit node: " + curnode.name + " at Line: " + str(curnode.lineno) + " (label:" + str(curnode.visitlabel) + ")")

                for n in curnode.ins:
                    if n.visitlabel < 2:
                        curnode.visitlabel = 1
                        if curnode not in queue:
                            queue.append(curnode)

                if curnode.visitlabel == 2:
                    logger.debug("[Static Inference] This node is finalized.")
                    if isinstance(curnode, SymbolNode):
                        if len(curnode.ins) > 1:
                            logger.error("[Static Inference] Symbol node should not have more than 1 input nodes.")
                            raise ValueError("Symbol node should not have more than 1 input nodes.")
                        else:
                            for n in curnode.ins:
                                if curnode.tag != 1 and curnode.tag != 4:
                                    curnode.tag = 3
                                    if not isinstance(n, BranchNode) and not TypeObject.isIdenticalSet(n.types, curnode.types):
                                        logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "Changed.")
                                        changed = True
                                        curnode.types = copy(n.types)
                                    elif isinstance(n, BranchNode) and not TypeObject.isIdenticalSet(n.types[n.outs.index(curnode)], curnode.types):
                                        logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "Changed.")
                                        changed = True
                                        curnode.types = copy(n.types[n.outs.index(curnode)])
                                elif not isinstance(n, BranchNode) and  not TypeObject.isIdenticalSet(n.types, curnode.types):
                                    logger.warning("[Static Inference] The types of " + curnode.name + " is statically added as: {" + TypeObject.resolveTypeNames(curnode.types) + "}" + "However, the types of input node are: {" +TypeObject.resolveTypeNames(n.types) + "}")
                                elif isinstance(n, BranchNode) and not TypeObject.isIdenticalSet(n.types[n.outs.index(curnode)], curnode.types):
                                    logger.warning("[Static Inference] The types of " + curnode.name + " is statically added as: {" + TypeObject.resolveTypeNames(curnode.types) + "}" + "However, the types of input node are: {" +TypeObject.resolveTypeNames(n.types[n.outs.index(curnode)]) + "}")
                    elif isinstance(curnode, TypeGenNode):
                        curnode.tag = 3
                        prev_types = deepcopy(curnode.types)
                        if curnode.op == "call" and not curnode.performTypingRules(usertype = self.usertypes):
                            pass
                        elif curnode.op not in ["List_Read", "List_Write", "Set_Read", "Dict_Read", "Tuple_Read", "Tuple_Write", "JoinedStr"] and not curnode.performTypingRules(usertype = self.usertypes):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "reject some types.")
                            #TODO:changed = True
                        elif curnode.op in ["List_Read", "List_Write", "Set_Read", "Dict_Read", "Tuple_Read", "Tuple_Write", "JoinedStr"] and not curnode.performTypingRules(usertype = self.usertypes, iterable = True):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "reject some types.")
                            #TODO:changed = True
                        curnode.types = curnode.types
                        if not TypeObject.isIdenticalSet(prev_types, curnode.types):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "reject some types.")
                            changed = True
                    elif isinstance(curnode, TypeNode):
                        curnode.tag = 3
                    elif isinstance(curnode, MergeNode):
                        curnode.tag = 3
                        prev_types = deepcopy(curnode.types)
                        curnode.types = []
                        for n in curnode.ins:
                            if not isinstance(n, BranchNode):
                                for t in n.types:
                                    if not TypeObject.existSame(t, curnode.types):
                                        curnode.types.append(t)
                            else:
                                for t in n.types[n.outs.index(curnode)]:
                                    if not TypeObject.existSame(t, curnode.types):
                                        curnode.types.append(t)
                        curnode.types = curnode.types
                        if not TypeObject.isIdenticalSet(prev_types, curnode.types):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "changed.")
                            changed = True
                    elif isinstance(curnode, BranchNode):
                        curnode.tag = 3
                        prev_types = deepcopy(curnode.types)
                        curnode.splitTypes()
                        if not TypeObject.isIdenticalSet(prev_types[0], curnode.types[0]) or not TypeObject.isIdenticalSet(prev_types[1], curnode.types[1]):
                            logger.debug("[Static Inference] Node: " + curnode.name + " at Line: " + str(curnode.lineno) + "changed.")
                            changed = True

                for n in curnode.outs:
                    if n == "PlaceHolder":
                        continue
                    elif n.visitlabel == 0:
                        n.visitlabel = 1
                        queue.append(n)
                        if isinstance(n, TypeGenNode) and n.name == "call":
                            logger.debug("[Static Inference] Add node: " + n.name + n.func + " at Line: " + str(n.lineno))
                        else:
                            logger.debug("[Static Inference] Add node: " + n.name + " at Line: " + str(n.lineno))
                    #this indicate a loop occurs
                    elif n.visitlabel == 1:
                        pass
                    elif n.visitlabel == 2:
                        if isinstance(n, TypeGenNode) and n.name == "call":
                            logger.debug("[Static Inference] Node: " + n.name + n.func +  " at Line: " + str(n.lineno) +" has been finalized.")
                        else:
                            logger.debug("[Static Inference] Node: " + n.name +  " at Line: " + str(n.lineno) +" has been finalized.")
            #Backward Rejecting Types
            
            
            queue = self.getNodewithRejTypes()
            while(len(queue) != 0):
                for n in queue:
                    if isinstance(n, SymbolNode):
                        endrejtypes = []
                        for t in n.rejtypes:
                            rejt = TypeObject.findSame(t, n.types)
                            if rejt != None:
                                n.types.remove(rejt)
                                if rejt.startnodename == n.symbol and rejt.startnodeorder == n.order:
                                    endrejtypes.append(rejt)
                        if len(n.ins) == 1:
                            if isinstance(n.ins[0], BranchNode):
                                for t in n.rejtypes:
                                    if TypeObject.existSame(t, n.ins[0].types[n.ins[0].outs.index(n)]) and t not in endrejtypes:
                                        n.ins[0].rejtypes[n.ins[0].outs.index(n)].append(t)
                            else:
                                for t in n.rejtypes:
                                    if TypeObject.existSame(t, n.ins[0].types) and t not in endrejtypes:
                                        n.ins[0].rejtypes.append(t)
                        n.rejtypes = []
                    elif isinstance(n, TypeNode):
                        for t in n.rejtypes:
                            if TypeObject.findSame(t, n.types) != None:
                                logger.debug("Type node at Line: " + str(n.lineno) +  " with type " + TypeObject.resolveTypeName(t) + str(t.added) + " is rejected. ")
                                #raise ValueError("Type node at Line: " + str(n.lineno) +  " is rejected. " + TypeObject.resolveTypeName(t) + str(t.added))
                        n.rejtypes = []
                    elif isinstance(n, TypeGenNode) and len(n.rejtypes) != 0:
                        if n.op not in ["List_Read", "List_Write", "Set_Read", "Dict_Read", "Tuple_Read", "Tuple_Write", "JoinedStr"]:
                            n.performRejTypingRule(usertype = self.usertypes)
                        else:
                            n.performRejTypingRule(usertype = self.usertypes, iterable = True)
                        n.rejtypes = []
                    elif isinstance(n, BranchNode):
                        for t in n.rejtypes[0]:
                            rejt = TypeObject.findSame(t, n.types[0])
                            if rejt != None:
                                n.types[0].remove(rejt)
                        for t in n.rejtypes[1]:
                            rejt = TypeObject.findSame(t, n.types[1])
                            if rejt != None:
                                n.types[1].remove(rejt)
                        
                        for t in n.rejtypes[0]:
                            if TypeObject.existSame(t, n.ins[0].types):
                                n.ins[0].rejtypes.append(t)
                        
                        for t in n.rejtypes[1]:
                            if len(n.ins) > 1 and TypeObject.existSame(t, n.ins[1].types):
                                n.ins[1].rejtypes.append(t)

                        n.rejtypes = [[],[]]
                    elif isinstance(n, MergeNode):
                        for t in n.rejtypes:
                            rejt = TypeObject.findSame(t, n.types)
                            if rejt != None:
                                n.types.remove(rejt)
                        for innode in n.ins:
                            for t in n.rejtypes:
                                if TypeObject.existSame(t, innode.types):
                                    innode.rejtypes.append(t)
                        n.rejtypes = []
                    else:
                        raise TypeError("Unknown Node.")
                queue = self.getNodewithRejTypes()
                
                        

        #print message
        logger.info("[Static Inferece] Finished iterating TDG.")


    def returntypes(self):
        types = []
        typemap = {}
        for s in self.globalsymbols:
            for n in self.globalsymbols[s]:
                if "local@" + n.symbol.split("@")[0] not in typemap:
                    res = {"category": "local", "name": n.symbol.split("@")[0], "type": []}
                    typemap["local@" + n.symbol.split("@")[0]] = res
                else:
                    res = typemap["local@" + n.symbol.split("@")[0]]
                for t in n.types:
                    if not TypeObject.existSame(t, res["type"]):
                        res["type"].append(t)

        for t in typemap:
            types.append(typemap[t])

        return types

    def dumptypes(self):
        types = []
        typemap = {}
        for s in self.globalsymbols:
            for n in self.globalsymbols[s]:
                if "local@" + n.symbol.split("@")[0] not in typemap:
                    res = {"category": "local", "name": n.symbol.split("@")[0], "type": []}
                    typemap["local@" + n.symbol.split("@")[0]] = res
                else:
                    res = typemap["local@" + n.symbol.split("@")[0]]
                for t in n.types:
                    typename = TypeObject.resolveTypeName(t)
                    if typename not in res["type"]:
                        res["type"].append(typename)
        for t in typemap:
            types.append(typemap[t])
        return types

    def draw(self, filerepo = None):
        if filerepo != None:
            filename = filerepo + "/" + self.name.replace("/", "_")
        else:
            filename = self.name.replace("/", "_")
        f = Digraph("Type Graph", filename = filename)

        #draw symbol node
        f.attr("node", shape = "box")
        for key in self.globalsymbols:
            for n in self.globalsymbols[key]:
                f.node(self.resolveName(n))

        #draw typegen node
        f.attr("node", shape = "ellipse")
        for key in self.globaltypegennodes:
            for n in self.globaltypegennodes[key]:
                f.node(self.resolveName(n))

        for n in self.globalbranchnodes:
            f.node(self.resolveName(n))

        for n in self.globalmergenodes:
            f.node(self.resolveName(n))

        #draw type node
        f.attr("node", shape = "circle")
        for key in self.globaltypenodes:
            f.node(self.resolveName(self.globaltypenodes[key]))

        #draw arrows
        for n in self.globalnodes:
            for outn in n.outs:
                if self.hasNode(outn):
                    f.edge(self.resolveName(n), self.resolveName(outn))
        f.render(filename=filename,view=False)


    def drawAliasGraph(self):
        f = Digraph("Alias Graph", filename = "/research/dept7/ypeng/prompt/Prompt4Type/graphviz_figs/" + self.name.split("/")[-1] + "_AliasGraph", format = "png")

        f.attr("node", shape = "ellipse")
        for n in self.aliasgraph.nodes:
            f.node(self.resolveName(n))

        
        for n in self.aliasgraph.nodes:
            for outn in n.outs:
                f.edge(self.resolveName(n), self.resolveName(outn))

        f.attr("edge", color = "red", dir = "none")
        aliasedges=[]
        for n in self.aliasgraph.nodes:
            for outn in n.alias:
                if [self.resolveName(n), self.resolveName(outn)] not in aliasedges:
                    f.edge(self.resolveName(n), self.resolveName(outn))
                    aliasedges.append([self.resolveName(n), self.resolveName(outn)])

        f.render(directory='/research/dept7/ypeng/prompt/Prompt4Type/graphviz_figs/')

    
    def _dump(self, item):
        if isinstance(item, list):
            d = []
            for i in item:
                d.append(self._dump(i))
            return d
        elif isinstance(item, dict):
            d = {}
            for i in item:
                if isinstance(i, TypeObject):
                    d[i.type] = self._dump(item[i])
                else:
                    d[i] = self._dump(item[i])
            return d
        elif isinstance(item, SymbolNode) or isinstance(item, TypeGenNode) or isinstance(item, TypeNode) or \
            isinstance(item, BranchNode) or isinstance(item, MergeNode):
            return item.dump()
        elif isinstance(item, TypeGraph):
            return item.dump()
        elif isinstance(item, AliasGraph):
            return item.dump()
        else:
            return item
        



    def dump(self):
        globaltg = {}
        globaltg["name"] = self.name
        globaltg["tgs"] = self._dump(self.tgs)
        globaltg["globalsymbols"] = self._dump(self.globalsymbols)
        globaltg["globaltypegennodes"] = self._dump(self.globaltypegennodes)
        globaltg["globaltypenodes"] = self._dump(self.globaltypenodes)
        globaltg["globalnodes"] = self._dump(self.globalnodes)
        globaltg["globalbranchnodes"] = self._dump(self.globalbranchnodes)
        globaltg["globalmergenodes"] = self._dump(self.globalmergenodes)
        globaltg["inloop"] = self.inloop
        globaltg["loopbuffer"] = self._dump(self.loopbuffer)
        globaltg["trybuffer"] = self._dump(self.trybuffer)
        globaltg["intry"] = self.intry
        globaltg["exceptbuffer"] = self._dump(self.exceptbuffer)
        globaltg["inexcept"] = self.inexcept
        globaltg["usertypes"] = self.usertypes
        globaltg["aliasgraph"] = self._dump(self.aliasgraph)
        globaltg["classtypes"] = self.classtypes
        globaltg["nodeindex"] = self.nodeindex
        globaltg["callgraph"] = self.callgraph
        return globaltg



    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an GlobalTypeGraph object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["name", "tgs", "globalsymbols", "globaltypegennodes", "globaltypenodes", "globalnodes", "globalbranchnodes", "globalmergenodes", "inloop", \
            "loopbuffer", "trybuffer", "intry", "exceptbuffer", "inexcept", "usertypes", "aliasgraph", "classtypes", "nodeindex", "callgraph"]):
            logger.error("Missing important information when resuming the GlobalTypeGraph object!")
            return None
        else:
            try:
                globaltg = GlobalTypeGraph(dictobj["name"], dictobj["usertypes"])
                idmap = {}
                globaltg.globalnodes = []
                nodetype2load = {"Symbol": SymbolNode.load, "TypeGen": TypeGenNode.load, "Type": TypeNode.load, "Branch": BranchNode.load, "Merge": MergeNode.load}
                for n in dictobj["globalnodes"]:
                    node = nodetype2load[n["nodetype"]](n)
                    globaltg.globalnodes.append(node)
                    idmap[n["nodeid"]] = node
                    if n["tg"][0] == globaltg.name:
                        node.tg = globaltg
                    else:
                        logger.warning("The TypeGraph " +n["tg"][0] +  " node " + node.name +" belongs to cannot be found.")
                for n in dictobj["globalnodes"]:
                    for i in n["ins"]:
                        idmap[n["nodeid"]].ins.append(idmap[i])
                    for i in n["outs"]:
                        idmap[n["nodeid"]].outs.append(idmap[i])
                globaltg.globalsymbols = {}
                for name in dictobj["globalsymbols"]:
                    globaltg.globalsymbols[name] = []
                    for n in dictobj["globalsymbols"][name]:
                        globaltg.globalsymbols[name].append(idmap[n["nodeid"]])
                globaltg.globaltypegennodes = {}
                for name in dictobj["globaltypegennodes"]:
                    globaltg.globaltypegennodes[name] = []
                    for n in dictobj["globaltypegennodes"][name]:
                        globaltg.globaltypegennodes[name].append(idmap[n["nodeid"]])
                globaltg.globaltypenodes = {}
                for name in dictobj["globaltypenodes"]:
                    if len(dictobj["globaltypenodes"][name]) != 0:
                        globaltg.globaltypenodes[idmap[dictobj["globaltypenodes"][name][0]]] = []
                        for n in dictobj["globaltypenodes"][name]:
                            globaltg.globaltypenodes[idmap[dictobj["globaltypenodes"][name][0]]].append(idmap[n["nodeid"]])
                globaltg.globalbranchnodes = []
                for n in dictobj["globalbranchnodes"]:
                    globaltg.globalbranchnodes.append(idmap[n["nodeid"]])
                globaltg.globalmergenodes = []
                for n in dictobj["globalmergenodes"]:
                    globaltg.globalmergenodes.append(idmap[n["nodeid"]])
                globaltg.inloop = dictobj["inloop"]
                globaltg.loopbuffer = []
                for k in dictobj["loopbuffer"]:
                    temp = []
                    for n in k:
                        temp.append(idmap[n["nodeid"]])
                    globaltg.loopbuffer.append(temp)
                globaltg.intry = dictobj["intry"]
                globaltg.trybuffer = []
                for k in dictobj["trybuffer"]:
                    temp = {}
                    for n in k:
                        temp[n] = idmap[k[n]["nodeid"]]
                    globaltg.trybuffer.append(temp)
                globaltg.inexcept = dictobj["inexcept"]
                globaltg.exceptbuffer = []
                for k in dictobj["exceptbuffer"]:
                    temp = {}
                    for n in k:
                        temp[n] = idmap[k[n]["nodeid"]]
                    globaltg.exceptbuffer.append(temp)
                globaltg.classtypes = dictobj["classtypes"]
                globaltg.tgs = []
                for t in dictobj["tgs"]:
                    tg = TypeGraph.load(t, globaltg = globaltg)
                    tg.globaltg = globaltg
                    globaltg.tgs.append(tg)
                globaltg.callgraph = dictobj["callgraph"]
                return globaltg
            except Exception as e:
                logger.error("Cannot resume GlobalTypeGraph object, reason: " + str(e))
                return None


            

            



class AliasNode(object):
    def __init__(self, name, scope, nodetype, ins, outs):
        self.name = name
        #nodetype:
        #attr
        #local
        self.nodetype = nodetype
        #scope must be like: class@func, using global to replace class or func if the attribute is defined global 4
        self.scope = scope
        self.ins = ins
        self.outs = outs
        self.alias = []
        self.id = -1
        
    def dump(self):
        node = {}
        node["name"] = self.name
        node["scope"] = self.scope
        node["nodetype"] = self.nodetype
        node["ins"] = []
        for n in self.ins:
            node["ins"].append(n.id)
        node["outs"] = []
        for n in self.outs:
            node["outs"].append(n.id)
        node["alias"] = []
        for n in self.alias:
            node["alias"].append(n.id)
        node["id"] = self.id
        return node

    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an AliasNode object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["name", "scope", "nodetype", "ins", "outs", "alias", "id"]):
            logger.error("Missing important information when resuming the AliasNode object!")
            return None
        else:
            n = AliasNode(dictobj["name"], dictobj["scope"], dictobj["nodetype"], [], [])
            n.id = dictobj["id"]
            return n




'''
This graph stores the possible aliases in current code file, 
the relationship between aliases in this table is not sound.
'''
class AliasGraph(object): 
    def __init__(self):
        self.nodes = []
        self.rootnodes = []


    def addNode(self, node):
        node.id = len(self.nodes) + 1
        self.nodes.append(node)
        if len(node.ins) == 0:
            self.rootnodes.append(node)

    def searchNode(self, name, scope):
        items = name.split("_@_")
        for n in self.rootnodes:
            if n.name == items[0] and n.scope == scope:
                p = n
                index = 1
                if index >= len(items):
                    return p
                while(len(p.outs) >= 0):
                    found = False
                    for q in p.outs:
                        if q.name == items[index] and q.scope == scope:
                            p = q
                            index += 1
                            found = True
                            break
                    if index >= len(items):
                        return p
                    if not found:
                        break
        return None

    def addAttribute(self, name, scope):
        items = name.split("_@_")
        rootfound = False
        for n in self.rootnodes:
            if items[0] in ["self", "cls"] and n.name == items[0] and n.scope == scope.split("@")[0]:
                rootfound = True
                if items[0] == "cls":
                    items[0] = "self"
                p = n
                index = 1
                if index >= len(items):
                    return p
                while(len(p.outs) >= 0):
                    found = False
                    for q in p.outs:
                        if q.name == items[index] and q.scope == scope.split("@")[0]:
                            p = q
                            index += 1
                            found = True
                            break
                    if index >= len(items):
                        return p
                    if not found:
                        break
                for i in range(index, len(items)):
                    node = AliasNode(items[i], scope.split("@")[0], "attr", [p], [])
                    p.outs.append(node)
                    self.addNode(node)
                    p = node
                return p
            elif n.name == items[0] and n.scope == scope:
                rootfound = True
                p = n
                index = 1
                if index >= len(items):
                    return p
                while(len(p.outs) >= 0):
                    found = False
                    for q in p.outs:
                        if q.name == items[index] and q.scope == scope:
                            p = q
                            index += 1
                            found = True
                            break
                    if index >= len(items):
                        return p
                    if not found:
                        break
                for i in range(index, len(items)):
                    node = AliasNode(items[i], scope, "attr", [p], [])
                    p.outs.append(node)
                    self.addNode(node)
                    p = node
                return p
        if not rootfound:
            for i in range(0, len(items)):
                if i == 0:
                    if items[i] in ["self", "cls"]:
                        node = AliasNode("self", scope.split("@")[0], "attr", [], [])
                    else:
                        node = AliasNode(items[i], scope, "attr", [], [])
                else:
                    node = AliasNode(items[i], scope, "attr", [p], [])
                    p.outs.append(node)
                self.addNode(node)
                p = node
            return p

    def getAliasNum(self):
        aliases = []
        for n in self.nodes:
            for a in n.alias:
                if a not in aliases:
                    aliases.append(a)

        return len(aliases)


    def dump(self):
        aliasgraph = {}
        aliasgraph["nodes"] = []
        for n in self.nodes:
            aliasgraph["nodes"].append(n.dump())
        aliasgraph["rootnodes"] = []
        for n in self.rootnodes:
            aliasgraph["rootnodes"].append(n.dump())

        return aliasgraph

    @staticmethod
    def load(dictobj):
        if not isinstance(dictobj, dict):
            logger.error("Cannot resume an AliasGraph object from " + str(type(dictobj)))
            return None
        elif not checkAttribute(dictobj, ["nodes", "rootnodes"]):
            logger.error("Missing important information when resuming the AliasGraph!")
            return None
        else:
            a = AliasGraph()
            idmap = {}
            for n in dictobj["nodes"]:
                node = AliasNode.load(n)
                a.nodes.append(node)
                idmap[n["id"]] = node
            for n in dictobj["nodes"]:
                for i in n["ins"]:
                    idmap[n["id"]].ins.append(idmap[i])
                for i in n["outs"]:
                    idmap[n["id"]].outs.append(idmap[i])
                for i in n["alias"]:
                    idmap[n["alias"]].alias.append(idmap[i])
            for n in dictobj["rootnodes"]:
                a.rootnodes.append(idmap[n["id"]])
            return a 





                




    


        

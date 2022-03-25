from hityper.typeobject import TypeObject
import hityper.tdg
from hityper import logger
from copy import copy, deepcopy
from hityper.stdtypes import builtin_method_properties, special_types, builtin_method

logger.name == __name__

class TypingRule(object):
    def __init__(self):
        pass

    def check_failed(self, ori, rej):
        if len(ori) == len(rej):
            logger.warning("All types are rejected.")

    def sub_act(self, operands , op, func, attr, usertypes, iterable=False, curnode = None):
        if not iterable:
            if len(operands) > 0:
                left = operands[0]
            else:
                left = None
            right = None
            if(len(operands)>1):
                right = operands[1]
            else:
                right = None
            if(left != None and (not isinstance(left, hityper.tdg.GraphBaseNode)) or (right != None and not isinstance(right, hityper.tdg.GraphBaseNode))):
                raise ValueError("Operands must be a graph node")
        if (op in ["and", "or"]):
            return self.binop_and_or(left, right)
        elif (op == "not"):
            return self.unop_not(left, right)
        elif (op in ["<", "<=", ">", ">="]):
            return self.binop_compare_neq(left, right)
        elif (op in ["==", "!=", "is", "isnot"]):
            return self.binop_compare_eq(left, right)
        elif (op == "+" and right != None):
            return self.binop_add(operands)
        elif (op == "*"):
            return self.binop_mul(left, right)
        elif (op in ["-", "/", "//", "%", "**", "pow"] and right != None):
            return self.binop_num_op(left, right, op)
        elif (op in ["+", "-", "abs"] and right == None):
            return self.NumRemainSame(left, right)
        elif (op == "int" and right == None):
            return self.unop_int(left, right)
        elif (op == "float" and right == None):
            return self.unop_float(left, right)
        elif (op == "divmod"):
            return self.binop_divmod(left, right)
        elif (op in ["|", "^", "&", "<<", ">>"]):
            return self.binop_int_op(operands, func, attr, usertypes)
        elif (op == "~" and right == None):
            return self.unop_int_op(left, right)
        elif (op == "bytes" and right == None):
            return self.unop_bytes(left, right)
        elif (op == "str" and right == None):
            return self.unop_str(left, right)
        elif (op == "tuple" and right == None):
            return self.unop_tuple(left, right)
        elif (op == "list" and right == None):
            return self.unop_list(left, right)
        elif (op == "set" and right == None):
            return self.unop_set(left, right)
        elif (op == "dict" and right == None):
            return self.unop_dict(left, right)
        elif (op == "type" and right == None):
            return self.unop_type(left, right)
        elif (op in ["in", "not in"] ):
            return self.binop_in(left, right)
        elif (op == "forin" and right == None):
            return self.unop_forin(left, right)
        elif (op == "append"):
            return self.binop_append(left, right)
        elif (op == "Subscript_Write"):
            return self.triop_subscript(operands, func, attr, usertypes)
        elif (op == "Subscript_Read"):
            return self.binop_subscript(operands, func, attr, usertypes)
        elif (op == "=" and right == None):
            return self.unop_assign(left, right)
        elif (op == "call"):
            return self.call(operands, func, attr, usertypes, curnode)
        elif (op == "List_Read"):
            return self.List_Read(operands)
        elif( op == "List_Write"):
            return self.List_Write(operands)
        elif(op == "Tuple_Read"):
            return self.Tuple_Read(operands)
        elif(op == "Tuple_Write"):
            return  self.Tuple_Write(operands)
        elif(op == "Set_Read"):
            return self.Set_Read(operands)
        elif(op =="Dict_Read"):
            return  self.Dict_Read(operands)
        elif(op == "JoinedStr"):
            return self.JoinedStr(operands)
        elif(op=="."):
            return self.Attribution_Return(operands, existstype=None)
        elif(op=="ListComp"):
            return  self.listcomp_Return(operands)
        elif(op=="SetComp"):
            return self.setcomp_Return(operands)
        elif(op=="DictComp"):
            return self.dictcomp_Retrun(operands)
        elif(op=="GeneratorExp"):
            return self.GeneratorExp_Return(operands)
        elif(op=="yield"):
            return self.yieldop(operands)
        elif(op=="IfExp"):
            return self.IfExp(operands)
        else:
            return self.unknown_op(operands, op)
            #raise TypeError("Unknown Operation: " + op)

    def act(self, operands , op, func, attr, usertypes, iterable=False, curnode = None):
        #if not about iterable
        res = self.sub_act(operands , op, func, attr, usertypes, iterable=False, curnode = curnode)
        if res==None:
            print("POSIIBLE NONE RETURN op is:", op)
        return res

    def unknown_op(self, operands, op):
        logger.warning("Unknown Operation: " + op)
        rej_types = []
        outs = []
        for i in operands:
            rej_types.append([])
        return rej_types, outs




    def binop_and_or(self, left, right):
        #rule: left and right can have arbitary type
        #out: Union[left, right]
        #if one is user-defined, the return type can only be True/False
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = []
        rej_rtypes = []


        outs = TypeObject.removeRedundantTypes(ltypes + rtypes)
        return [rej_ltypes, rej_rtypes], outs

    def unop_not(self, left, right):
        #rule: left can have arbitary type
        #out: bool(including user-defined)
        rej_ltypes = []
        outs = TypeObject("bool", 0)
        return [rej_ltypes], outs

    def binop_compare_neq(self, left, right):
        #rule: left and right must have the same type, exclude user defined, type, callable
        #out: bool(including user-defined)
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = []
        rej_rtypes = []
        outs = TypeObject("bool", 0)
        for t in ltypes:
            if (not TypeObject.existCompatible(t, rtypes)) or t.category != 0 or t.type in ["type", "Callable", "Dict", "None"]:
                rej_ltypes.append(t)
        for t in rtypes:
            if (not TypeObject.existCompatible(t, ltypes)) or t.category != 0 or t.type in ["type", "Callable", "Dict", "None"]:
                rej_rtypes.append(t)
        return [rej_ltypes, rej_rtypes], outs

    def binop_compare_eq(self, left, right):
        #rule: left and right can have arbitary type
        #out: bool(including user-defined)
        rej_ltypes = []
        rej_rtypes = []
        outs = TypeObject("bool", 0)
        return [rej_ltypes, rej_rtypes], outs

    def binop_add(self, operands):
        #rule: left and right must have the same type
        #out: left/right
        left = operands[0]
        right = operands[1]
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = []
        rej_rtypes = []
        outs = []
        # if ltypes or rtypes are None, add rej
        # if len(ltypes)==0:
        #     rej_ltypes.append()
        for t in ltypes:
            if t.type in ["Tuple", "List"]:
                temp = TypeObject(t.type, 0)
                temp.elementtype += t.elementtype
                rexist = False
                for rt in rtypes:
                    if rt.type == t.type:
                        temp.elementtype += rt.elementtype
                        rexist = True
                if rexist:
                    outs.append(temp)          
            elif ((not TypeObject.existSame(t, rtypes)) and (not TypeObject.existCompatible(t, rtypes))) or t.category != 0 or t.type in ["type", "Callable", "Set", "Dict", "None"]:
                rej_ltypes.append(t)
            elif (not TypeObject.existSame(t, outs)):
                outs.append(t)
        for t in rtypes:
            if ((not TypeObject.existSame(t, ltypes)) and (not TypeObject.existCompatible(t, ltypes))) or t.category != 0 or t.type in ["type", "Callable", "Set", "Dict", "None"]:
                rej_rtypes.append(t)
            elif not TypeObject.existSame(t, outs):
                outs.append(t)
        if len(operands)==2:
            return [rej_ltypes, rej_rtypes], outs
        elif len(operands)>2:
            rej = []
            rej.append(rej_ltypes)
            rej.append(rej_rtypes)
            for i in range(2,len(operands)):
                rej.append([])
            return rej,outs

    def binop_mul(self, left, right):
        #rule: one operand must be a number, the other can not be userdefined, type, callable
        #out: left (numbers need extra consideration)
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = []
        rej_rtypes = []
        outs = []
        
        if not TypeObject.existType("int", ltypes) and not TypeObject.existType("bool", ltypes):
            for t in rtypes:
                if t.type not in ["bool", "float", "int"]:
                    rej_rtypes.append(t)
        if not TypeObject.existType("int", rtypes) and not TypeObject.existType("bool", rtypes):
            for t in ltypes:
                if t.type not in ["bool", "float", "int"]:
                    rej_ltypes.append(t)

        for t in ltypes:
            if t.type in ["type", "Callable", "None", "Set", "Dict"]:
                rej_ltypes.append(t)

        for t in rtypes:
            if t.type in ["type", "Callable", "None", "Set", "Dict"]:
                rej_rtypes.append(t)

        self.check_failed(ltypes, rej_ltypes)
        self.check_failed(rtypes, rej_rtypes)

        if TypeObject.existType("float", ltypes) or TypeObject.existType("float", rtypes):
            outs.append(TypeObject("float", 0))
        if (TypeObject.existType("int", ltypes) or TypeObject.existType("bool", ltypes)) and (TypeObject.existType("int", rtypes) or TypeObject.existType("bool", rtypes)):
            outs.append(TypeObject("int", 0))
        if TypeObject.existType("int", ltypes) or TypeObject.existType("bool", ltypes):
            for t in rtypes:
                if (t not in rej_rtypes) and (not TypeObject.existSame(t, outs)):
                    outs.append(t)
        if TypeObject.existType("int", rtypes) or TypeObject.existType("bool", rtypes):
            for t in ltypes:
                if (t not in rej_ltypes) and (not TypeObject.existSame(t, outs)):
                    outs.append(t)            
        return [rej_ltypes, rej_rtypes], outs

    def binop_num_op(self, left, right, op):
        #rule: left and right must be numbers
        #out: numbers
        #mention that False%True returns int
        #mention that % is also used in joinedstr. e.g. b = 'hello %s %s'%(a,a)
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = []
        rej_rtypes = []
        outs = []
        level = 0
        # for joinedstr
        strtemp = TypeObject("Text",0)
        if op=='%' and TypeObject.existSame(strtemp,ltypes):
            outs = [TypeObject("Text", 0)]
            # left can only be Text
            for idx in range(len(ltypes)):
                if ltypes[idx].type!="Text":
                    rej_ltypes.append(ltypes[idx])
            return [rej_ltypes, rej_rtypes], outs

        for idx in range(len(rtypes)):
            if rtypes[idx].type=="bool":
                rtypes[idx] = TypeObject("int", 0) # raise the type
            elif rtypes[idx].type not in ["bool", "int", "float", "complex"]:
                rej_rtypes.append(rtypes[idx])
            elif ["bool", "int", "float", "complex"].index(rtypes[idx].type) > level:
                level = ["bool", "int", "float", "complex"].index(rtypes[idx].type)

        for idx in range(len(ltypes)):
            if ltypes[idx].type=="bool":
                ltypes[idx] = TypeObject("int", 0) # raise the type

        for t in ltypes:
            if t.type not in ["bool", "int", "float", "complex"]:
                rej_ltypes.append(t)
            elif t.type in ["int", "float", "complex"] and TypeObject.existSame(t, rtypes) and not TypeObject.existSame(t, outs):
                outs.append(t)
            elif t.type in ["int", "float", "complex"] and not TypeObject.existSame(t, rtypes) and ["bool", "int", "float", "complex"].index(t.type) > level and not TypeObject.existSame(t, outs):
                outs.append(t)

        
        for t in rtypes:
            if t.type in ["int", "float", "complex"] and ["bool", "int", "float", "complex"].index(t.type) == level and not TypeObject.existSame(t, outs):
                outs.append(t)

        if op == "/" and len(ltypes) > len(rej_ltypes) and len(rtypes) > len(rej_rtypes):
            outs = [TypeObject("float", 0)]

        return [rej_ltypes, rej_rtypes], outs

    def NumRemainSame(self, left, right):
        #rule: accept numbers
        #out: the original number type
        #not surport user-define
        ltypes = left.types
        rej_ltypes = []
        rej_rtypes = []
        outs = []
        for t in ltypes:
            if t.type not in ["bool", "int", "float", "complex"]:
                rej_ltypes.append(t)
            elif not TypeObject.existSame(t, outs):
                outs.append(t)
        return [rej_ltypes, rej_rtypes], outs

    def unop_int(self, left, right):
        # NO MORE USED
        ltypes = left.types
        rej_ltypes = []
        outs = TypeObject("int", 0)
        for t in ltypes:
            if t.type not in ["int", "float", "complex", "bytes", "Text", "bool"]:
                rej_ltypes.append(t)
        return [rej_ltypes], outs

    def unop_float(self, left, right):
        #NO MORE USED
        ltypes = left.types
        rej_ltypes = []
        outs = TypeObject("float", 0)
        for t in ltypes:
            if t.type not in ["int", "float", "complex", "bytes", "Text", "bool"]:
                rej_ltypes.append(t)
        return [rej_ltypes], outs

    def binop_divmod(self, left, right):
        # NO MORE USED
        #rule: just the combination of / and % in numbers
        #out: numbers
        #not support user-define

        # if both left and right are int => a//b , a%b int/int
        # if one is float =>math.floor(a / b), a % b float/float
        ltypes = left.types
        rtypes = right.types
        basic_type = TypeObject("int", 0)
        llevel = rlevel = 1
        for lt in ltypes:
            if TypeObject.isCompatible(lt, basic_type):
                llevel = max(llevel, ["bool", "int", "float", "complex"].index(lt.type))
        for rt in rtypes:
            if TypeObject.isCompatible(rt,basic_type):
                rlevel = max(rlevel, ["bool", "int", "float", "complex"].index(rt.type))
        if llevel<2 and rlevel<2:
            rej_ltypes, rej_rtypes, outs = self.binop_num_op(left, right,"%")
        else:
            rej_ltypes, rej_rtypes, outs = self.binop_num_op(left, right,"/")
        finalouts = TypeObject("Tuple", 0)
        finalouts.buildTuple(outs)
        return [rej_ltypes, rej_rtypes], finalouts

    def binop_int_op(self,operands, func, attr, usertypes):
        #rule: can accept int and bool
        #out: int
        #not support user-define
        if len(operands)==2:
            left = operands[0]
            right = operands[1]
            ltypes = left.types
            rtypes = right.types
            rej_ltypes = []
            rej_rtypes = []
            outs = []
            temp1 = TypeObject("int", 0)
            temp2 = TypeObject("bool", 0)
            for t in ltypes:
                if t.type not in ["int", "bool","Any", "Set"] and t.category==0:
                    rej_ltypes.append(t)

            for t in rtypes:
                if t.type not in ["int", "bool","Any", "Set"] and t.category==0:
                    rej_rtypes.append(t)

            if TypeObject.existSame(TypeObject("Set", 0), ltypes) and TypeObject.existSame(TypeObject("Set", 0), rtypes):
                outs.append(TypeObject.findSame(TypeObject("Set", 0), ltypes))
                outs.append(TypeObject.findSame(TypeObject("Set", 0), rtypes))
        
            outs += [temp1,temp2]
            if len(ltypes) == len(rej_ltypes) or len(rtypes) == len(rej_rtypes):
                return [rej_ltypes, rej_rtypes], []
            else:
                return [rej_ltypes, rej_rtypes], outs
        elif len(operands)>2:
            temp1 = TypeObject("int", 0)
            temp2 = TypeObject("bool", 0)
            rej = []
            for inode in operands:
                itypes = inode.types
                rej_types = []
                for t in itypes:
                    if t.type not in ["int", "bool", "Any"] and t.category == 0:
                        rej_types.append(t)
                rej.append(rej_types)
            return rej,[temp1,temp2]


    def unop_int_op(self, left, right):
        #rule: can accept int and bool
        #out: int
        #not support user-define
        ltypes = left.types
        rej_ltypes = []
        outs = TypeObject("int", 0)
        for t in ltypes:
            if t.type not in ["int", "bool"]:
                rej_ltypes.append(t)
        return [rej_ltypes], outs

    def unop_bytes(self, left, right):
        # No more use here
        ltypes = left.types
        rej_ltypes = []
        outs = TypeObject("bytes", 0)
        for t in ltypes:
            if t.type in ["List", "Tuple", "Set"]:
                rej_elementtypes = []
                if isinstance(t.elementtype, list):
                    for it in t.elementtype:
                        if it.type not in ["int", "bool"]:
                            rej_elementtypes.append(it)
                elif t.elementtype.type not in ["int", "bool"]:
                    rej_elementtypes.append(t.elementtype)
                rej_type = TypeObject(t.type, 0)
                rej_type.elementtype = rej_elementtypes
                rej_ltypes.append(rej_type)
            elif t.type == "Dict":
                rej_keytypes = []
                if isinstance(t.keytype, list):
                    for it in t.keytype:
                        if it.type not in ["int", "bool"]:
                            rej_keytypes.append(it)
                elif t.keytype not in ["int", "bool"]:
                    rej_keytypes.append(t.keytype)
                rej_valuetypes = []
                rej_type = TypeObject("Dict", 0)
                rej_type.keytype = rej_keytypes
                rej_type.valuetype = rej_valuetypes
                rej_ltypes.append(rej_type)
            elif t.type not in ["int", "bool"]:
                rej_ltypes.append(t)
        return [rej_ltypes], outs

    def unop_str(self, left, right):
        #rule: can accept any type
        #out: string(including user-define)
        rej_ltypes = []
        outs = TypeObject("Text", 0)
        return [rej_ltypes], outs

    def unop_tuple(self, left, right):
        #rule: can accept iterable types
        #out: tuple
        # not support user-define
        ltypes = left.types
        rej_ltypes = []
        outs = TypeObject("Tuple", 0)
        for t in ltypes:
            if t.type not in ["Tuple", "List", "Set", "Dict", "Text"]:
                rej_ltypes.append(t)
            elif t.type == "Dict":
                if isinstance(t.keytype, list):
                    outs.elementtype += t.elementtype
                else:
                    outs.elementtype.append(t.elementtype)
            elif t.type == "Text":
                outs.elementtype.append(TypeObject("Text", 0))
            else:

                if isinstance(t.elementtype, list):
                    outs.elementtype += t.elementtype
                else:
                    outs.elementtype.append(t.elementtype)
        return [rej_ltypes], outs
    
    def unop_list(self, left, right):
        #rule: can accept iterable types
        #out: list
        # not support user-define
        ltypes = left.types
        rej_ltypes = []
        outs = TypeObject("List", 0)
        for t in ltypes:
            if t.type not in ["Tuple", "List", "Set", "Dict", "Text"]:
                rej_ltypes.append(t)
            elif t.type == "List":
                if isinstance(t.keytype, list):
                    outs.elementtype += t.elementtype
                else:
                    outs.elementtype.append(t.elementtype)
            elif t.type == "Text":
                outs.elementtype.append(TypeObject("Text", 0))
            else:

                if isinstance(t.elementtype, list):
                    outs.elementtype += t.elementtype
                else:
                    outs.elementtype.append(t.elementtype)
        return [rej_ltypes], outs
    
    def unop_set(self, left, right):
        #rule: can accept iterable types
        #out: set
        # not support user-define
        ltypes = left.types
        rej_ltypes = []
        outs = TypeObject("Set", 0)
        for t in ltypes:
            if t.type not in ["Tuple", "List", "Set", "Dict", "Text"]:
                rej_ltypes.append(t)
            elif t.type == "Set":
                if isinstance(t.keytype, list):
                    outs.elementtype += t.elementtype
                else:
                    outs.elementtype.append(t.elementtype)
            elif t.type == "Text":
                outs.elementtype.append(TypeObject("Text", 0))
            else:

                if isinstance(t.elementtype, list):
                    outs.elementtype += t.elementtype
                else:
                    outs.elementtype.append(t.elementtype)
        return [rej_ltypes], outs
    
    def unop_dict(self, left, right):
        # NOUSE
        #rule: can accept list, tuple, dict and set
        #out: tuple
        # not support user-define
        ###TODO!!!!
        ltypes = left.types
        rej_ltypes = []
        rej_rtypes = []
        outs = TypeObject("Dict", 0)
        # 1. dict() -> new empty dictionary
        if(len(ltypes)==0):
            outs = TypeObject("Dict", 0)
        # 2. dict(**kwargs)


        return [rej_ltypes, rej_rtypes], outs

    def unop_type(self, left, right):
        # NOUSE
        #rule: can accept arbitary type
        #out: type(including user-define)
        ltypes = left.types
        rej_ltypes = []
        outs = TypeObject("type", 0)
        return [rej_ltypes], outs

    def binop_in(self, left, right):
        #rule: right must be tuple, dict, list, set and string
        #out: bool
        # not support user-define
        rtypes = right.types
        rej_ltypes = []
        rej_rtypes = []
        outs = TypeObject("bool", 0)
        for t in rtypes:
            if t.type not in ["Tuple", "Dict", "List", "Set", "Text"]:
                rej_rtypes.append(t)
        return [rej_ltypes, rej_rtypes], outs

    def unop_forin(self, left, right):
        #rule: left must be tuple, dict, list, set and string
        #out: element type of left
        ltypes = left.types
        rej_ltypes = []
        outs = []
        for t in ltypes:
            if t.type not in ["Tuple", "Dict", "List", "Set", "Text"]:
                rej_ltypes.append(t)
            elif t.type == "Text":
                outs.append(TypeObject("Text", 0))
            elif t.type == "Dict":
                if isinstance(t.keytype, list):
                    outs += t.keytype
                else:
                    outs.append(t.keytype)
            else:
                if isinstance(t.elementtype, list):
                    outs += t.elementtype
                else:
                    outs.append(t.elementtype)
        return [rej_ltypes], outs    

    def binop_append(self, left, right):
        #rule: left must be list
        #out: list
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = []
        rej_rtypes = []
        outs = TypeObject("List", 0)
        for t in ltypes:
            if t.type != "List":
                rej_ltypes.append(t)
            else:
                if isinstance(t.elementtype, list):
                    outs.elementtype += t.elementtype
                else:
                    outs.elementtype.append(t.elementtype)
        
        for t in rtypes:
            outs.elementtype.append(t)

        return [rej_ltypes, rej_rtypes], outs 

    def triop_subscript(self,operands, func, attr, usertypes):
        #rule: target must be dict, list 
        #index must be int (for list, tuple, set) and arbitary (for dict)
        #value can be arbitary
        #out: updated target
        #TODO slices
        if len(operands)==2:
            # the first one is target, the second one is not used
            target = operands[0]
            index = operands[1]


            ttypes = target.types
            itypes = index.types

            rej_ttypes = []
            rej_itypes = []

            outs = []
            if TypeObject.existType("List", ttypes):
                for it in itypes:
                    if it.type not in ["int", "bool"]:
                        rej_itypes.append(it)

            for t in ttypes:
                if t.type not in ["Dict", "List"]:
                    rej_ttypes.append(t)
                elif t.type == "List":
                    otype = TypeObject("List", 0)
                    outs.append(otype)
                elif t.type == "Dict":
                    otype = TypeObject("Dict", 0)
                    outs.append(otype)

            return [rej_ttypes, rej_itypes], outs
        elif len(operands)>2:
            target = operands[0]
            index = operands[1]
            value = operands[2]

            ttypes = target.types
            itypes = index.types
            vtypes = value.types
            rej_ttypes = []
            rej_itypes = []
            rej_vtypes = []
            outs = []
            if TypeObject.existType("List", ttypes):
                for it in itypes:
                        if it.type not in ["int", "bool"]:
                            rej_itypes.append(it)

            for t in ttypes:
                if t.type not in ["Dict", "List"] and t.category != 2:
                    rej_ttypes.append(t)
                elif t.type == "List":
                    otype = TypeObject("List", 0)
                    if isinstance(t.elementtype, list):
                        otype.elementtype += t.elementtype
                    else:
                        otype.elementtype.append(t.elementtype)
                    for vt in vtypes:
                        if not TypeObject.existSame(vt, otype.elementtype):
                            otype.elementtype.append(vt)
                    outs.append(otype)
                elif t.type == "Dict":
                    otype = TypeObject("Dict", 0)
                    if isinstance(t.keytype, list):
                        otype.keytype += t.keytype
                    else:
                        otype.keytype.append(t.keytype)
                    if isinstance(t.valuetype, list):
                        otype.valuetype += t.valuetype
                    else:
                        otype.valuetype.append(t.valuetype)
                    for it in itypes:
                        if not TypeObject.existSame(it, otype.keytype):
                            otype.keytype.append(it)
                    for vt in vtypes:
                        if not TypeObject.existSame(vt, otype.valuetype):
                            otype.valuetype.append(vt)
                    outs.append(otype)
                elif t.category == 2:
                    outs.append(t)
            rej = [rej_ttypes, rej_itypes, rej_vtypes]
            for i in range(3,len(operands)):
                rej.append([])
            return rej, outs

    def binop_subscript(self, operands, func, attr, usertypes):
        #rule: target must be dict, list, tuple, text and bytes
        #index must be int (for list, tuple) and arbitary (for dict)
        #out: elementtype

        if len(operands)==1:
            target = operands[0]
            # if just the target, we won't check the rest 2
            target = operands[0]

            ttypes = target.types

            rej_ttypes = []

            outs = []

            for t in ttypes:
                if t.type not in ["Dict", "List", "Tuple", "Text", "bytes"]:
                    rej_ttypes.append(t)
                elif t.type in ["Text", "bytes"]:
                    outs.append(t)
                elif t.type == "Dict":
                    if isinstance(t.valuetype, list):
                        outs += t.valuetype
                    else:
                        outs.append(t.valuetype)
                else:
                    if isinstance(t.elementtype, list):
                        outs += t.elementtype
                    else:
                        outs.append(t.elementtype)

            # we simplify this one
            outs = TypeObject.removeRedundantTypes(outs)
            return [rej_ttypes], outs
        elif len(operands)==2:

            target = operands[0]
            index = operands[1]
            ttypes = target.types
            itypes = index.types
            rej_ttypes = []
            rej_itypes = []
            outs = []
            # if target is dict, just add [] to rej.
            if TypeObject.existType("Dict", ttypes):
                rej_itypes = []
            elif TypeObject.existType("List", ttypes) or TypeObject.existType("Tuple", ttypes) or TypeObject.existType(
                    "Text", ttypes):
                # to check the rest 1 or 2
                for it in itypes:
                    if it.type not in ["int", "bool"]:
                        rej_itypes.append(it)

            for t in ttypes:
                if t.type not in ["Dict", "List", "Tuple", "Text", "bytes"]:
                    rej_ttypes.append(t)
                elif t.type in ["Text", "bytes"]:
                    outs.append(t)
                elif t.type == "Dict":
                    if isinstance(t.valuetype, list):
                        outs += t.valuetype
                    else:
                        outs.append(t.valuetype)
                else:
                    if isinstance(t.elementtype, list):
                        outs += t.elementtype
                    else:
                        outs.append(t.elementtype)
            outs = TypeObject.removeRedundantTypes(outs)

            return [rej_ttypes, rej_itypes], outs
        elif len(operands)==3:
            target = operands[0]
            index = operands[1]
            index2 = operands[2]

            ttypes = target.types
            itypes = index.types
            itypes2 = index2.types
            rej_ttypes = []
            rej_itypes = []
            rej_itypes2 = []
            outs = []
            # if target is dict, just add [] to rej.
            if TypeObject.existType("Dict", ttypes):
                rej_itypes = []
                rej_itypes2 = []
            elif TypeObject.existType("List", ttypes) or TypeObject.existType("Tuple", ttypes) or TypeObject.existType(
                    "Text", ttypes):
                # to check the rest 1 or 2
                for it in itypes:
                    if it.type not in ["int", "bool"]:
                        rej_itypes.append(it)
                for it in itypes2:
                    if it.type not in ["int", "bool"]:
                        rej_itypes2.append(it)

            for t in ttypes:
                if t.type not in ["Dict", "List", "Tuple", "Text", "bytes"]:
                    rej_ttypes.append(t)
                elif t.type in ["Text", "bytes"]:
                    outs.append(t)
                elif t.type == "Dict":
                    if isinstance(t.valuetype, list):
                        outs += t.valuetype
                    else:
                        outs.append(t.valuetype)
                else:
                    if isinstance(t.elementtype, list):
                        outs += t.elementtype
                    else:
                        outs.append(t.elementtype)
            outs = TypeObject.removeRedundantTypes(outs)

            return [rej_ttypes, rej_itypes,rej_itypes2], outs

        elif len(operands)==4:
            target = operands[0]
            index = operands[1]
            index2 = operands[2]
            index3 = operands[3]
            ttypes = target.types
            itypes = index.types
            itypes2 = index2.types
            itypes3 = index3.types

            rej_ttypes = []
            rej_itypes = []
            rej_itypes2 = []
            rej_itypes3 = []
            outs = []
            # if target is dict, just add [] to rej.
            if TypeObject.existType("Dict", ttypes):
                rej_itypes = []
                rej_itypes2 = []
                rej_itypes3 = []
            elif TypeObject.existType("List", ttypes) or TypeObject.existType("Tuple", ttypes) or TypeObject.existType(
                    "Text", ttypes):
                # to check the rest 1 or 2
                for it in itypes:
                    if it.type not in ["int", "bool"]:
                        rej_itypes.append(it)
                for it in itypes2:
                    if it.type not in ["int", "bool"]:
                        rej_itypes2.append(it)
                for it in itypes3:
                    if it.type not in ["int", "bool"]:
                        rej_itypes3.append(it)

            for t in ttypes:
                if t.type not in ["Dict", "List", "Tuple", "Text"]:
                    rej_ttypes.append(t)
                elif t.type == "Text":
                    outs.append(TypeObject("Text", 0))
                elif t.type == "Dict":
                    if isinstance(t.valuetype, list):
                        outs += t.valuetype
                    else:
                        outs.append(t.valuetype)
                else:
                    if isinstance(t.elementtype, list):
                        outs += t.elementtype
                    else:
                        outs.append(t.elementtype)
            outs = TypeObject.removeRedundantTypes(outs)

            return [rej_ttypes, rej_itypes,rej_itypes2,rej_itypes3], outs





    def unop_assign(self, left, right):
        if left!= None:
            ltypes = left.types
            rej_ltypes = []

            return [rej_ltypes], ltypes
        else:
            logger.error("Cannot find the right value in assignment. This happens because you use a feature that is not supported by HiTyper.")
            raise ValueError("Cannot find the right value in assignment. This happens because you use a feature that is not supported by HiTyper.")


    def call(self, operands, func, attr, usertypes, curnode):
        #====================================================================
        #            case 1: Class instance and user-defined types
        #====================================================================
        if attr==None and func in usertypes:

            rej_types = []
            for i in range(0, len(operands)):
                rej_types.append([])
            typeobject = TypeObject(func, 2)
            return rej_types, [typeobject]

        else:
            
            if func in usertypes:
                rej_types = []
                for i in range(0, len(operands)):
                    rej_types.append([])
                typeobject = TypeObject(func, 2)
                return rej_types, [typeobject]


            #====================================================================
            #                  case 2: built-in function
            #====================================================================


            #====================================================================
            #                  case 2.1: regular function
            #====================================================================

            if func not in builtin_method_properties["self-changable"]["overall"] and func not in builtin_method_properties["special-return"]["overall"]:
                #member functions
                if attr != None:
                    target = operands[0]
                    rej_types = []
                    rej_target_types = []
                    rej_arg_types = []
                    outs = []
                    accpetable_targettypes = []
                    returntypes = []
                    for i in range(1, len(operands)):
                        rej_arg_types.append([])
                    for k in builtin_method:
                        if func in builtin_method[k]:
                            accpetable_targettypes.append(k)
                    for t in target.types:
                        if t.type.lower() in accpetable_targettypes:
                            rule = builtin_method[t.type.lower()][func]
                            if len(rule) == 2:
                                if len(rule[0]) < len(operands) - 1:
                                    rej_target_types.append(t)
                                    continue
                                else:
                                    for index in range(1, len(operands)):
                                        if rule[0][index - 1][1] == "Any" or isinstance(rule[0][index - 1], list):
                                            rej_types.append([])
                                            continue
                                        elif rule[0][index - 1][1].startswith("@") and rule[0][index - 1][1] in special_types:
                                            validtypes = []
                                            for i in special_types[rule[0][index - 1][1]]:
                                                validtypes += TypeObject.Str2Obj(i)
                                        elif rule[0][index - 1][1] == "@elementtype@":
                                            validtypes = t.elementtype
                                        elif rule[0][index - 1][1] == "@keytype@":
                                            validtypes = t.keytype
                                        elif rule[0][index - 1][1] == "@valuetype@":
                                            validtypes = t.valuetype
                                        else:
                                            validtypes = TypeObject.Str2Obj(rule[0][index - 1][1])
                                        for ot in operands[index].types:
                                            if not TypeObject.existType(ot, validtypes):
                                                rej_arg_types[index - 1].append(ot)
                                    if "@" not in rule[1]:
                                        returntypes = TypeObject.Str2Obj(rule[1])
                                    else:
                                        logger.warning("Unhandled return value for built-in function {}".format(func))
                            elif len(rule) > 2:
                                found = False
                                for r in rule:
                                    if isinstance(r, list) and len(r) == len(operands) - 1:
                                        found = True
                                        for index in range(1, len(operands)):
                                            if r[index - 1][1] == "Any" or isinstance(r[index - 1], list):
                                                rej_types.append([])
                                                continue
                                            elif r[index - 1][1].startswith("@") and r[index - 1][1] in special_types:
                                                validtypes = []
                                                for i in special_types[r[index - 1][1]]:
                                                    validtypes += TypeObject.Str2Obj(i)
                                            elif r[index - 1][1] == "@elementtype@":
                                                validtypes = t.elementtype
                                            elif r[index - 1][1] == "@keytype@":
                                                validtypes = t.keytype
                                            elif r[index - 1][1] == "@valuetype@":
                                                validtypes = t.valuetype
                                            else:
                                                validtypes = TypeObject.Str2Obj(r[index - 1][1])
                                            rej_optypes = []
                                            for ot in operands[index].types:
                                                if not TypeObject.existType(ot, validtypes):
                                                    rej_arg_types[index - 1].append(ot)
                                        if "@" not in rule[-1]:
                                            returntypes = TypeObject.Str2Obj(rule[-1])
                                        else:
                                            logger.warning("Unhandled return value for built-in function {}".format(func))
                                if found == False:
                                    for r in rule:
                                        if isinstance(r, list) and len(r) > len(operands) - 1:
                                            found = True
                                            for index in range(1, len(operands)):
                                                if r[index - 1][1] == "Any" or isinstance(r[index - 1], list):
                                                    rej_types.append([])
                                                    continue
                                                elif r[index - 1][1].startswith("@") and r[index - 1][1] in special_types:
                                                    validtypes = []
                                                    for i in special_types[r[index - 1][1]]:
                                                        validtypes += TypeObject.Str2Obj(i)
                                                elif r[index - 1][1] == "@elementtype@":
                                                    validtypes = t.elementtype
                                                elif r[index - 1][1] == "@keytype@":
                                                    validtypes = t.keytype
                                                elif r[index - 1][1] == "@valuetype@":
                                                    validtypes = t.valuetype
                                                else:
                                                    validtypes = TypeObject.Str2Obj(r[index - 1][1])
                                                rej_optypes = []
                                                for ot in operands[index].types:
                                                    if not TypeObject.existType(ot, validtypes):
                                                        rej_arg_types[index - 1].append(ot)
                                            if "@" not in rule[-1]:
                                                returntypes = TypeObject.Str2Obj(rule[-1])
                                            else:
                                                logger.warning("Unhandled return value for built-in function {}".format(func))

                        else:
                            rej_target_types.append(t)
                    rej_types = [rej_target_types] + rej_arg_types
                    outs = returntypes
                    return rej_types, outs
                #standalone functions
                else:
                    if func in builtin_method["standalone"]:
                        rej_types = []
                        outs = []
                        rule = builtin_method["standalone"][func]
                        for i in range(0, len(operands)):
                            rej_types.append([])
                        if len(rule) == 2:
                            if len(rule[0]) < len(operands):
                                rej_ltypes = []
                                for i in range(0, len(operands)):
                                    rej_ltypes.append([])
                                outs = []
                                return rej_ltypes, outs
                            for i in range(0, len(operands)):
                                if len(rule[0]) == 0 or rule[0][i][1] == "Any" or isinstance(rule[0][i], list):
                                    rej_types.append([])
                                    continue
                                elif rule[0][i][1].startswith("@") and rule[0][i][1] in special_types:
                                    validtypes = []
                                    for t in special_types[rule[0][i][1]]:
                                        validtypes += TypeObject.Str2Obj(t)
                                else:
                                    validtypes = TypeObject.Str2Obj(rule[0][i][1])
                                for ot in operands[i].types:
                                    if not TypeObject.existType(ot, validtypes):
                                        rej_types[i].append(ot)
                            if "@" not in rule[-1]:
                                returntypes = TypeObject.Str2Obj(rule[-1])
                            else:
                                logger.warning("Unhandled return value for built-in function {}".format(func))
                        elif len(rule) > 2:
                            found = False
                            for r in rule:
                                if isinstance(r, list) and len(r) == len(operands):
                                    found = True
                                    for i in range(0, len(operands)):
                                        if r[i][1] == "Any" or isinstance(r[i], list):
                                            rej_types.append([])
                                            continue
                                        elif r[i][1].startswith("@") and r[i][1] in special_types:
                                            validtypes = []
                                            for t in special_types[r[i][1]]:
                                                validtypes += TypeObject.Str2Obj(t)
                                        else:
                                            validtypes = TypeObject.Str2Obj(r[i][1])
                                        for ot in operands[i].types:
                                            if not TypeObject.existType(ot, validtypes):
                                                rej_types[i].append(ot)
                                if "@" not in rule[-1]:
                                    returntypes = TypeObject.Str2Obj(rule[-1])
                                else:
                                    logger.warning("Unhandled return value for built-in function {}".format(func))
                            if found == False:
                                for r in rule:
                                    if isinstance(r, list) and len(r) > len(operands) - 1:
                                        found = True
                                        for i in range(0, len(operands)):
                                            if r[i][1] == "Any" or isinstance(r[i], list):
                                                rej_types.append([])
                                                continue
                                            elif r[i][1].startswith("@") and r[i][1] in special_types:
                                                validtypes = []
                                                for t in special_types[r[i][1]]:
                                                    validtypes += TypeObject.Str2Obj(t)
                                            else:
                                                validtypes = TypeObject.Str2Obj(r[i][1])
                                            for ot in operands[i].types:
                                                if not TypeObject.existType(ot, validtypes):
                                                    rej_types[i].append(ot)
                                    if "@" not in rule[-1]:
                                        returntypes = TypeObject.Str2Obj(rule[-1])
                                    else:
                                        logger.warning("Unhandled return value for built-in function {}".format(func))
                        outs = returntypes
                        return rej_types, outs
                    else:
                        rej_ltypes = []
                        for i in range(0, len(operands)):
                            rej_ltypes.append([])
                        outs = []
                        return rej_ltypes, outs


            #====================================================================
            #                  case 2.2: self-changable function
            #====================================================================
            #list.append()
            elif func == "append":
                if attr!=None:
                    failed = False
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    temp = TypeObject("List", 0)
                    outs = []
                    for t in target.types:
                        if t.type != "List":
                            rej_target_types.append(t)
                        elif t.type == "List":
                            for types_t in t.elementtype:
                                temp.elementtype.append(types_t)
                    if len(rej_target_types) == len(target.types):
                        outs += target.types
                        failed = True
                    rej_types.append(rej_target_types)

                    rej_target_types = []
                    for i in range(1, len(operands)):
                        for t in operands[i].types:
                            if not TypeObject.existType(t, temp.elementtype):
                                temp.elementtype.append(t)
                        rej_types.append(rej_target_types)
                    if failed == False:
                        outs.append(temp)
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            #list,set,dict.clear()
            elif func=="clear":
                if attr!=None:
                    # mention that it will remove all the existing types!!!!!
                    #TODO how to deal with this situation?
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    for t in target.types:
                        if t.type not in ["List","Dict","set"]:
                            rej_target_types.append(t)
                        else:
                            temp = TypeObject(t.type, 0)
                            outs.append(temp)
                    rej_types.append(rej_target_types)
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            #list.extend()
            elif func == "extend":
                # only 2 operands
                if attr!=None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    temp = TypeObject("List", 0)
                    outs = []
                    for t in target.types:
                        if t.type != "List":
                            rej_target_types.append(t)
                        elif t.type =="List":
                            for types_t in t.elementtype:
                                temp.elementtype.append(types_t)
                    rej_types.append(rej_target_types)

                    rej_target_types = []
                    for i in range(1, len(operands)):
                        for t in operands[i].types:
                            if t.type!= "List":
                                rej_target_types.append(t)
                            for types_t in t.elementtype:
                                if not TypeObject.existType(types_t, temp.elementtype):
                                    temp.elementtype.append(types_t)
                        rej_types.append(rej_target_types)
                    outs.append(temp)
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            #list.insert()
            elif func == "insert":
                # 3 nodes here 1.list/2.int/3. obj
                if attr != None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    temp = TypeObject("List", 0)
                    outs = []
                    for t in target.types:
                        if t.type != "List":
                            rej_target_types.append(t)
                        elif t.type == "List":
                            for types_t in t.elementtype:
                                temp.elementtype.append(types_t)
                    rej_types.append(rej_target_types)

                    # second one is int
                    if len(operands) > 1:
                        rej_target_types = []
                        sub_temp = operands[1]
                        for t in sub_temp.types:
                            if t.type not in ["int","bool"]:
                                rej_target_types.append(t)
                        rej_types.append(rej_target_types)

                    rej_target_types = []
                    for i in range(1, len(operands)):
                        for t in operands[i].types:
                            if not TypeObject.existType(t, temp.elementtype):
                                temp.elementtype.append(t)
                        rej_types.append(rej_target_types)
                    outs.append(temp)
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            #list,set.dict.pop()
            elif func == "pop":
                #list1.pop(1) or just pop()
                # pop(key[,default])
                if attr!=None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    for t in target.types:
                        if t.type not in  ["List","Dict", "Set"]:
                            rej_target_types.append(t)
                        else:
                            # here we don't change the possible types in it because it's hard to say
                            outs.append(t)
                    rej_types.append(rej_target_types)
                    # the second one has to be int(for list),if there is
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            #list,set.remove()
            elif func=="remove" or func=="discard":
                if attr!=None:
                    #set.discard(value)
                    #aList.remove('xyz');
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    temp = None
                    for t in target.types:
                        if t.type not in ["List", "Set"]:
                            rej_target_types.append(t)
                        else:
                            # here we don't change the possible types in it because it's hard to say
                            temp  =deepcopy(t)
                            outs.append(temp)
                    rej_types.append(rej_target_types)
                    # the second one has to be int(for list),if there is
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    if temp!= None:
                        outs.append(temp)
                    else:
                        outs= []
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            
            elif func=="update":
                if attr!=None:
                # dict.update(dict2)
                # it is also possible that it's a user-defined function
                    if len(operands)>0:
                        rej_types = []
                        target = operands[0]
                        rej_target_types = []
                        outs = []
                        temp = TypeObject("Dict",0)
                        for t in target.types:
                            if t.type not in ["Dict"]:
                                rej_target_types.append(t)
                            else:
                                temp = deepcopy(t)

                        rej_types.append(rej_target_types)
                        # the second one has to be int(for list),if there is
                        if len(operands) > 1:
                            target = operands[1]
                            rej_target_types = []
                            for t in target.types:
                                if t.type not in ["Dict"]:
                                    rej_target_types.append(t)
                                else:
                                    temp.keytype += t.keytype
                                    temp.valuetype += t.valuetype
                                    temp.elementtype = temp.keytype

                            rej_types.append(rej_target_types)
                        if len(operands)>2:
                            for i in range(2, len(operands)):
                                rej_types.append([])

                        if temp!= None:
                            outs.append(temp)
                        else:
                            outs = []
                        return rej_types, outs
                    else:
                        rej_ltypes = []
                        for i in range(0, len(operands)):
                            rej_ltypes.append([])
                        outs = []
                        return rej_ltypes, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs


            elif func=="intersection" or func=="intersection_update" or func== "union":
                #set.intersection(set1, set2 ... etc)
                #set.union(set1, set2...)
                if attr != None:

                    rej_types = []
                    target = operands[0]
                    rej_target_types = []

                    temp = None
                    outs = []
                    for t in target.types:
                        if t.type not in ["Set"]:
                            rej_target_types.append(t)
                        elif t.type == "Set":
                            temp = deepcopy(t)
                    rej_types.append(rej_target_types)

                    if func!="union":
                        # TODO! maybe we can infer a more specific one? but too consuming now.
                        if len(operands) > 1:
                            for i in range(1, len(operands)):
                                target = operands[i]
                                rej_target_types = []
                                for t in target.types:
                                    if t.type not in ["Set"]:
                                        rej_target_types.append(t)
                                rej_types.append(rej_target_types)

                        if temp != None:
                            outs.append(temp)
                        else:
                            outs = []
                        return rej_types, outs

                    else:
                        if len(operands) > 1:
                            for i in range(1, len(operands)):
                                target = operands[i]
                                rej_target_types = []
                                for t in target.types:
                                    if t.type not in ["Set"]:
                                        rej_target_types.append(t)
                                    else:
                                        for eletype in t.elementtype:
                                            if not TypeObject.existType(eletype.type, temp.elementtype):
                                                temp.elementtype.append(eletype)

                                rej_types.append(rej_target_types)

                        if temp != None:
                            outs.append(temp)
                        else:
                            outs = []
                        return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs


            elif func=="difference" or func=="difference_update":
                # z = x.difference(y)
                # it equals to x-y
                if attr != None:

                    rej_types = []
                    target = operands[0]
                    rej_target_types = []

                    temp = None
                    outs = []
                    for t in target.types:
                        if t.type not in ["Set"]:
                            rej_target_types.append(t)
                        elif t.type == "Set":
                            temp = deepcopy(t)
                    rej_types.append(rej_target_types)

                    target = operands[1]
                    rej_target_types = []
                    for t in target.types:
                        if t.type not in ["Set"]:
                            rej_target_types.append(t)
                    rej_types.append(rej_target_types)

                    if len(operands)>2:
                        for i in range(2,len(operands)):
                            rej_types.append([])

                    if temp!= None:
                        outs.append(temp)
                    else:
                        outs= []

                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs


            elif func=="add":
                #fruits.add("orange")
                if attr != None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []

                    temp = None
                    outs = []
                    for t in target.types:
                        if t.type not in ["Set"]:
                            rej_target_types.append(t)
                        elif t.type=="Set":
                            temp = deepcopy(t)
                    rej_types.append(rej_target_types)

                    for i in range(1, len(operands)):
                        rej_types.append([])
                        target = operands[i]
                        # add the possible types in it
                        for intypes in target.types:
                            if temp!=None:
                                if not TypeObject.existType(intypes,temp.elementtype):
                                    temp.elementtype.append(intypes)
                    if temp!= None:
                        outs.append(temp)
                    else:
                        outs= []
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs


            elif func=="symmetric_difference" or func=="symmetric_difference_update":
                # set.symmetric_difference(set)
                if attr != None:

                    rej_types = []
                    target = operands[0]
                    rej_target_types = []

                    temp = None
                    outs = []
                    for t in target.types:
                        if t.type not in ["Set"]:
                            rej_target_types.append(t)
                        elif t.type == "Set":
                            temp = deepcopy(t)
                    rej_types.append(rej_target_types)

                    target = operands[1]
                    rej_target_types = []
                    for t in target.types:
                        if t.type not in ["Set"]:
                            rej_target_types.append(t)
                        else:
                            for eletype in t.elementtype:
                                if not TypeObject.existType(eletype.type,temp.elementtype):
                                    temp.elementtype.append(eletype)
                    rej_types.append(rej_target_types)

                    if len(operands) > 2:
                        for i in range(2, len(operands)):
                            rej_types.append([])

                    if temp != None:
                        outs.append(temp)
                    else:
                        outs = []
                    return rej_types, outs

                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs


            elif func=="popitem":
                # dict.popitem()
                if attr!=None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    temp = TypeObject("Tuple",0)
                    for t in target.types:
                        if t.type not in ["Dict"]:
                            rej_target_types.append(t)
                        else:
                            temp.elementtype += t.keytype
                            temp.elementtype += t.valuetype
                    rej_types.append(rej_target_types)
                    # the second one has to be int(for list),if there is
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    outs.append(temp)
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func=="setdefault":
                # setdefault is similiar as get, but slitely different
                # a.setdefault('Sex', "Never")
                if attr!=None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    for t in target.types:
                        if t.type not in ["Dict"]:
                            rej_target_types.append(t)
                        else:
                            for item in t.valuetype:
                                if item!=None:
                                    outs.append(item)
                    rej_types.append(rej_target_types)
                    # the second one has to be int(for list),if there is
                    if len(operands)==2:
                        rej_types.append([])
                    elif len(operands)==3:
                        rej_types.append([])
                        rej_types.append([])
                        for itypes in operands[2].types:
                            if not TypeObject.existSame(itypes,outs):
                                outs.append(itypes)
                    else:
                        for i in range(1, len(operands)):
                            rej_types.append([])
                    print(len(outs))
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs


            #====================================================================
            #                 case 2.3: special-return function
            #====================================================================
            elif func=="copy":
                if attr!=None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    for t in target.types:
                        if t.type not in ["List", "Dict", "set"]:
                            rej_target_types.append(t)
                        elif t.type in ["List", "Dict", "set"]:
                            outs.append(t)
                    rej_types.append(rej_target_types)
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func == "items":
                if attr != None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    for t in target.types:
                        if t.type != "Dict":
                            rej_target_types.append(t)
                        else:
                            temp = TypeObject("set", 0)
                            innerlist = TypeObject("List", 0)
                            for k in t.keytype:
                                for v in t.valuetype:
                                    innertuple = TypeObject("Tuple", 0)
                                    innertuple.elementtype.append(k)
                                    innertuple.elementtype.append(v)
                                    innerlist.elementtype.append(innertuple)
                            temp.elementtype.append(innerlist)
                            outs.append(temp)
                    rej_types.append(rej_target_types)
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    return rej_types, outs
            
            elif func == "keys":
                if attr != None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    for t in target.types:
                        if t.type != "Dict":
                            rej_target_types.append(t)
                        else:
                            temp = TypeObject("set", 0)
                            innerlist = TypeObject("List", 0)
                            for k in t.keytype:
                                innerlist.elementtype.append(k)
                            temp.elementtype.append(innerlist)
                            outs.append(temp)
                    rej_types.append(rej_target_types)
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    return rej_types, outs

            elif func == "values":
                if attr != None:
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    for t in target.types:
                        if t.type != "Dict":
                            rej_target_types.append(t)
                        else:
                            temp = TypeObject("set", 0)
                            innerlist = TypeObject("List", 0)
                            for k in t.valuetype:
                                innerlist.elementtype.append(k)
                            temp.elementtype.append(innerlist)
                            outs.append(temp)
                    rej_types.append(rej_target_types)
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    return rej_types, outs

            elif func == "abs":
                # as for NOTAttribute function, we have to make sure self.attr==None
                if attr == None:
                    ltypes = operands[0].types
                    rej_target_types = []
                    rej_ltypes = []

                    outs = []
                    for t in ltypes:
                        if t.type not in ["bool", "int", "float", "complex"]:
                            rej_target_types.append(t)
                        elif not TypeObject.existSame(t, outs):
                            if t !=None:
                                outs.append(t)
                    rej_ltypes.append(rej_target_types)
                    for i in range(1, len(operands)):
                        rej_ltypes.append([])
                    return rej_ltypes, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func == "divmod":
                # as for NOTAttribute function, we have to make sure self.attr==None
                if attr == None:
                    left = operands[0]
                    right = operands[1]
                    ltypes = left.types
                    rtypes = right.types
                    basic_type = TypeObject("int", 0)
                    llevel = rlevel = 1
                    for lt in ltypes:
                        if TypeObject.isCompatible(lt, basic_type):
                            llevel = max(llevel, ["bool", "int", "float", "complex"].index(lt.type))
                    for rt in rtypes:
                        if TypeObject.isCompatible(rt, basic_type):
                            rlevel = max(rlevel, ["bool", "int", "float", "complex"].index(rt.type))
                    if llevel < 2 and rlevel < 2:
                        [rej_ltypes, rej_rtypes], outs = self.binop_num_op(left, right, "%")
                    else:
                        [rej_ltypes, rej_rtypes], outs = self.binop_num_op(left, right, "/")
                    finalouts = TypeObject("Tuple", 0)
                    finalouts.buildTuple(outs)
                    return [rej_ltypes, rej_rtypes], finalouts
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs


            elif func == "enumerate":
                if len(operands) <= 2 and len(operands) >= 1:
                    rej_types = []
                    outs = []
                    elementtype = []
                    for i in operands:
                        rej_types.append([])
                    for t in operands[0].types:
                        if t.type not in special_types["@iterable@"]:
                            rej_types[0].append(t)
                        else:
                            elementtype += t.elementtype
                    if len(operands) == 2:
                        for t in operands[1].types:
                            if t.type != "int":
                                rej_types[1].append(t)
                    temp = TypeObject("Generator", 0)
                    for e in elementtype:
                        innertuple = TypeObject("Tuple", 0)
                        innertuple.elementtype = [TypeObject("int", 0), e]
                        temp.elementtype.append(innertuple)
                    outs.append(temp)
                    return rej_types, outs         
                else:
                    rej_types = []
                    outs = []
                    for i in range(0, len(operands)):
                        rej_types.append([])

                    return rej_types, outs

            elif func == "round":
                if attr == None:
                    # if one ,return int
                    if len(operands)==1:
                        ltypes = operands[0].types
                        rej_target_types = []
                        rej_ltypes = []
                        temp = TypeObject("int", 0)
                        outs = []
                        for t in ltypes:
                            if t.type not in ["bool", "int", "float", "complex"]:
                                rej_target_types.append(t)

                        rej_ltypes.append(rej_target_types)

                        for i in range(1, len(operands)):
                            rej_ltypes.append([])
                        outs.append(temp)
                        return rej_ltypes, outs
                    # if two ,return float (in this function naming is a problem, maybe fixed later :) )
                    elif len((operands))==2:
                        ltypes = operands[0].types
                        rtypes = operands[1].types
                        rej_target_types =  rej_rtarget_types=[]
                        rej_ltypes = []

                        temp = TypeObject("float", 0)
                        outs = []
                        for t in ltypes:
                            if t.type not in ["bool", "int", "float", "complex"]:
                                rej_target_types.append(t)
                        rej_ltypes.append(rej_target_types)

                        for t in rtypes:
                            if t.type not in ["bool", "int"]:
                                rej_rtarget_types.append(t)
                        rej_ltypes.append(rej_rtarget_types)
                        outs.append(temp)
                        return rej_ltypes, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func == "sorted":
                # the first has to be iterable
                # list debug ok , dict not debugging
                if attr == None:
                    first = operands[0].types
                    rej_target_types = []
                    rej_ltypes = []
                    temp = TypeObject("List", 0)
                    outs = []
                    for t in first:
                        if t.type not in ["List", "Tuple", "Set", "Dict", "Iterable", "Text"]:
                            rej_target_types.append(t)
                        else:
                            if isinstance(t.elementtype, list):
                                temp.elementtype += t.elementtype
                            else:
                                temp.elementtype.append(t.elementtype)

                    rej_ltypes.append(rej_target_types)

                    for i in range(1, len(operands)):
                        rej_ltypes.append([])
                    outs.append(temp)
                    return rej_ltypes, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func == "sum":
                if attr == None:

                    # the first has to be iterable
                    first = operands[0].types
                    rej_target_types = []
                    rej_ltypes = []
                    isinitial = True
                    outs = []
                    simplelevel_up = 0
                    for t in first:
                        if t.type not in ["List", "Tuple", "Set", "Dict", "Iterable", "Text"]:
                            rej_target_types.append(t)
                        for elet in t.elementtype:
                            if isinitial:
                                isinitial = False
                                if elet.type in ["bool", "int", "float", "complex"]:
                                    simplelevel_up = ["bool", "int", "float", "complex"].index(elet.type)
                                else:
                                    simplelevel_up = 0
                            else:
                                if elet.type in ["bool", "int", "float", "complex"]:

                                    simplelevel_up = max(["bool", "int", "float", "complex"].index(elet.type), simplelevel_up)
                                else:
                                    simplelevel_up = max(1,simplelevel_up)

                    temp = TypeObject(["bool", "int", "float", "complex"][simplelevel_up],"0")

                    rej_ltypes.append(rej_target_types)

                    for i in range(1, len(operands)):
                        rej_ltypes.append([])
                    outs.append(temp)
                    return rej_ltypes, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs     

            elif func == "tuple":
                # as for NOTAttribute function, we have to make sure self.attr==None
                if attr == None:
                    if len(operands)==0:
                        rej_ltypes = []
                        outs = TypeObject("Tuple", 0)
                        return [], [outs]
                    else:
                        ltypes = operands[0].types
                        rej_ltypes = []
                        outs = TypeObject("Tuple", 0)
                        for t in ltypes:
                            if t.type not in ["Tuple", "List", "Set", "Dict", "Text"]:
                                rej_ltypes.append(t)
                            elif t.type == "Dict":
                                outs.elementtype = t.keytype
                            elif t.type == "Text":
                                outs.elementtype.append(TypeObject("Text", 0))
                            else:
                                outs.elementtype = t.elementtype
                        return [rej_ltypes], outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func == "list":
                # as for NOTAttribute function, we have to make sure self.attr==None
                if attr == None:
                    if len(operands)==0:
                        rej_ltypes = []
                        outs = TypeObject("List", 0)
                        return [], [outs]
                    elif len(operands) == 1:
                        ltypes = operands[0].types
                        rej_ltypes = []
                        outs = TypeObject("List", 0)
                        for t in ltypes:
                            if t.type not in ["Tuple", "List", "Set", "Dict", "Text"]:
                                rej_ltypes.append(t)
                            elif t.type == "Dict":
                                outs.elementtype = t.keytype
                            elif t.type == "Text":
                                outs.elementtype.append(TypeObject("Text", 0))
                            else:
                                outs.elementtype = t.elementtype
                        return [rej_ltypes], outs
                    else:
                        rej_ltypes = []
                        for i in range(0, len(operands)):
                            rej_ltypes.append([])
                        outs = []
                        return rej_ltypes, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func=="set":
                # as for NOTAttribute function, we have to make sure self.attr==None
                rej_ltypes = []
                if attr == None:
                    if len(operands)==0:

                        outs = TypeObject("Set", 0)
                        return [], [outs]
                    elif len(operands)==1:
                        ltypes = operands[0].types
                        outs = TypeObject("Set", 0)
                        for t in ltypes:
                            if t.type not in ["Tuple", "List", "Set", "Dict", "Text"]:
                                rej_ltypes.append(t)
                            elif t.type == "Dict":
                                outs.elementtype = t.keytype
                            elif t.type == "Text":
                                outs.elementtype.append(TypeObject("Text", 0))
                            else:
                                outs.elementtype = t.elementtype
                        return [rej_ltypes], [outs]
                    else:
                        for i in range(0, len(operands)):
                            rej_ltypes.append([])
                        outs = []
                        return rej_ltypes, outs 
                else:
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs 

            elif func=="frozenset":
                # as for NOTAttribute function, we have to make sure self.attr==None
                rej_ltypes = []
                if attr == None:
                    if len(operands)==0:

                        outs = TypeObject("frozenset", 0)
                        return [], [outs]
                    else:
                        ltypes = operands[0].types
                        outs = TypeObject("Set", 0)
                        for t in ltypes:
                            if t.type not in ["Tuple", "List", "Set", "Dict", "Text"]:
                                rej_ltypes.append(t)
                            elif t.type == "Dict":
                                outs.elementtype = t.keytype
                            elif t.type == "Text":
                                outs.elementtype.append(TypeObject("Text", 0))
                            else:
                                outs.elementtype = t.elementtype
                        return [rej_ltypes], [outs]
                else:
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs 

            elif func == "type":
                # as for NOTAttribute function, we have to make sure self.attr==None
                if attr == None:
                    if len(operands) == 1:
                        rej_types = [[]]
                        outs = []
                        temp =TypeObject("type", 0)
                        temp.elementtype = operands[0].types
                        outs.append(temp)
                        return rej_types, outs
                    elif len(operands) == 3:
                        rej_types = [[], [], []]
                        outs = []
                        for t in operands[0].types:
                            if not TypeObject.equal2type(t, "str"):
                                rej_types[0].append(t)
                        for t in operands[1].types:
                            if not TypeObject.equal2type(t, "tuple"):
                                rej_types[1].append(t)
                        for t in operands[2].types:
                            if not TypeObject.equal2type(t, "dict"):
                                rej_types[2].append(t)
                        temp = TypeObject("type", 0)
                        outs.append(temp)
                        return rej_types, outs
                    else:
                        rej_types = []
                        outs = []
                        for i in range(0, len(operands)):
                            rej_types.append([])
                        return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func == "next":
                if attr == None:
                    if len(operands) == 1:
                        rej_types = []
                        outs = []
                        elementtype = []
                        for i in range(0, len(operands)):
                            rej_types.append([])
                        for t in operands[0].types:
                            if t.type != "Generator":
                                rej_types[0].append(t)
                            else:
                                elementtype = t.elementtype
                        outs += elementtype
                        return rej_types, outs
                    else:
                        rej_ltypes = []
                        for i in range(0, len(operands)):
                            rej_ltypes.append([])
                        outs = []
                        return rej_ltypes, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func == "max" or func=="min":
                # the input can be iterable or some argument
                # if only one iterable e.g    b = max([1,2,4]) / b = max({'a':1,'b':2})
                if attr==None:
                    ltypes = operands[0].types
                    rej_target_types = []
                    rej_ltypes = []
                    outs = []
                    if len(operands)==1:
                        temp = []
                        for t in ltypes:
                            if t.type not in ["List", "Tuple", "Set", "Dict", "Iterable", "Text"]:
                                rej_target_types.append(t)
                            elif t.type == "Dict":
                                if isinstance(t.elementtype, list):
                                    outs += t.elementtype
                                else:
                                    outs.append(t.elementtype)
                            else:
                                if t.elementtype!=[]:
                                    if t.elementtype[0]!= None:
                                        outs.append(t.elementtype[0]) # for list/dict is also okay as it returns keytype
                        rej_ltypes.append(rej_target_types)
                        for i in range(1, len(operands)):
                            rej_ltypes.append([])
                        # outs.append(temp)
                        return rej_ltypes, outs
                    # with many arguments e.g b = max(1,2,3.1)  b = max([1,2],[0,4])
                    else:
                        ifsimple = False
                        first = operands[0]
                        simplelevel_up =simplelevel_down =  0
                        isinitial = True
                        for indexop in operands:
                            for ftypes in indexop.types:
                                if ftypes.type not in ["List", "Tuple", "Set", "Dict", "Iterable", "Text"]:
                                    ifsimple = True
                                    if isinitial:
                                        isinitial = False
                                        if ftypes.type in ["bool", "int", "float", "complex"]:
                                            simplelevel_up = simplelevel_down = ["bool", "int", "float", "complex"].index(ftypes.type)
                                        else:
                                            simplelevel_up = simplelevel_down = 1
                                    else:
                                        if ftypes.type in ["bool", "int", "float", "complex"]:
                                            simplelevel_up = max(["bool", "int", "float", "complex"].index(ftypes.type),simplelevel_up)
                                            simplelevel_down = min(["bool", "int", "float", "complex"].index(ftypes.type), simplelevel_down)
                                        else:
                                            simplelevel_up = max(1,simplelevel_up)
                                            simplelevel_down = max(1,simplelevel_down)
                                # if it's like b = max([1,2],[0,4])
                                elif ftypes.type == "Dict":
                                    outs += ftypes.keytype
                                    for i in range(0, len(operands)):
                                        rej_ltypes.append([])
                                    return rej_ltypes, outs
                                else:
                                    if len(outs)==0:
                                        outs.append(ftypes)
                                    elif not TypeObject.existSame(ftypes,outs):
                                        outs.append(ftypes)
                        # add all the possible types
                        if ifsimple:
                            for i in range(simplelevel_down,simplelevel_up+1):
                                temp = TypeObject(["bool", "int", "float", "complex"][i],"0")
                                outs.append(temp)

                        for i in range(0, len(operands)):
                            rej_ltypes.append([])
                        return rej_ltypes, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            elif func == "get":
                if attr!=None:
                    # a.get('Sex', "Never")
                    rej_types = []
                    target = operands[0]
                    rej_target_types = []
                    outs = []
                    for t in target.types:
                        if t.type not in ["Dict"]:
                            rej_target_types.append(t)
                        else:
                            for item in t.valuetype:
                                if item!=None:
                                    outs.append(item)
                    rej_types.append(rej_target_types)
                    # the second one has to be int(for list),if there is
                    for i in range(1, len(operands)):
                        rej_types.append([])
                    return rej_types, outs
                else:
                    rej_ltypes = []
                    for i in range(0, len(operands)):
                        rej_ltypes.append([])
                    outs = []
                    return rej_ltypes, outs

            #====================================================================
            #              case 3: inter-procedural Analysis
            #====================================================================
            elif curnode.tg != None and curnode.tg.globaltg != None:
                rej_types = []
                for i in range(0, len(operands)):
                    rej_types.append([])
                outs = []
                for t in curnode.tg.globaltg.tgs:
                    if t.classname == curnode.tg.classname and t.name == func and func != curnode.tg.name:
                        returntype = t.getReturnType()
                        if len(returntype) == 0:
                            return rej_types, outs
                        else:
                            outs += returntype
                            return rej_types, outs
                return rej_types, outs            
            
            #====================================================================
            #              case 4: unrecognized functions
            #====================================================================
            else:
                rej_types = []
                for i in range(0, len(operands)):
                    rej_types.append([])
                outs = []
                return rej_types, outs


    def List_Read(self, operands):
        # here we do not consider about userdefine first. e.g list1 = [1,'2',user-define instance]
        # mention that the depth here is 2 e.g List = [1,1,'2',[1,2,3,4],[1,2,'hello']] then the result out will
        # only be Typeobject(list) with elementtype [int, int, text, list, list]
        # we would not merge two same types together because it could help in the List_write inference e.g a= [1,2,'3'] [x,y,z] = a
        outs = []
        temp = TypeObject("List",0)
        for i in range(len(operands)):
            # add the type not exists in the elementtype

            if isinstance(operands[i].types, list):
                temp.elementtype += operands[i].types
            else:
                temp.elementtype.append(operands[i].types)
        outs.append(temp)
        rej_types = []
        for i in range(0, len(operands)):
            rej_types.append([])
        return rej_types,outs

    def List_Write(self,operands):
        # input: operands output:[[]], [outs_types]
        # in this func, we first find the possible types from the input, then we add all the possible types into them
        # e.g. c= [1,'2',3]  [a,a1,a2]= c
        # due to the reason that type pass after this node spreads, we will infer that out = [int,text]
        rej_types = []
        outs = []
        inputtypes = []
        if len(operands) != 1:
            logger.error("The length of input nodes for ListWrite should be 1, we get {} here.".format(len(operands)))
            raise ValueError("The length of input nodes for ListWrite should be 1")
        '''
        elif len(operands[0].outs) != 1:
            logger.error("The operand's out length should be 1, we get {} here.".format(len(operands[0].outs)))
            raise ValueError("The operand's out length should be 1")
        '''

        for insnode in operands[0].ins:
            if isinstance(insnode, hityper.tdg.SymbolNode):
                if isinstance(insnode.types, list):
                    # here we add all the elementtype rather than types
                    for eacheletype in insnode.types:
                        if not isinstance(eacheletype.elementtype, list):
                            inputtypes.append(eacheletype.elementtype)
                        elif isinstance(eacheletype.elementtype, list):
                            inputtypes += eacheletype.elementtype

        outs = TypeObject.removeRedundantTypes(inputtypes)
        return [rej_types], outs



    def Tuple_Read(self,operands):
        # similiar to List Read
        outs = []
        temp = TypeObject("Tuple", 0)
        for i in range(len(operands)):
            if isinstance(operands[i].types, list):
                temp.elementtype += operands[i].types
            else:
                temp.elementtype.append(operands[i].types)
        outs.append(temp)
        rej_types = []
        for i in range(0, len(operands)):
            rej_types.append([])
        return rej_types,outs


    def Tuple_Write(self,operands):
        # input: operands output:[[]], [outs_types]
        # in this func, we first find the possible types from the input, then we add all the possible types into them
        # e.g. c= (1,'2',3)  (a,a1,a2)= c => we will infer out=[int, text].
        rej_types = []
        outs = []
        inputtypes = []
        if len(operands) != 1:
            logger.error("The length of input nodes for TupleWrite should be 1, we get {} here.".format(len(operands)))
            raise ValueError("The length of input nodes for TupleWrite should be 1")
        # here we do not constrain the out length because it can be like below:
        # for i, (setting_value, setting_type) in enumerate(zip(all_values, all_types)):
        # elif len(operands[0].outs) != 1:
        #     raise ValueError("The operand's out length should be 1")

        if operands[0].name != "forin":

            for insnode in operands[0].ins:
                if isinstance(insnode, hityper.tdg.SymbolNode):
                    if isinstance(insnode.types, list):
                        # here we add all the elementtype rather than types
                        for eacheletype in insnode.types:
                            if not isinstance(eacheletype.elementtype, list):
                                inputtypes.append(eacheletype.elementtype)
                            elif isinstance(eacheletype.elementtype, list):
                                inputtypes += eacheletype.elementtype
                elif isinstance(insnode, hityper.tdg.TypeGenNode):   # like forin node
                    if isinstance(insnode.types, list):
                        # here we add all the elementtype rather than types
                        for eacheletype in insnode.types:
                            if not isinstance(eacheletype.elementtype, list):
                                inputtypes.append(eacheletype.elementtype)
                            elif isinstance(eacheletype.elementtype, list):
                                inputtypes += eacheletype.elementtype
            outs = TypeObject.removeRedundantTypes(inputtypes)
            return [rej_types], outs
        # if it's realized by forin
        else:
            for insnode in operands[0].types:
                if isinstance(insnode, hityper.tdg.TypeObject):
                    if not isinstance(insnode.elementtype, list):
                        # here we add all the elementtype rather than types

                        inputtypes.append(insnode.elementtype)
                    elif isinstance(insnode.elementtype, list):
                        inputtypes += insnode.elementtype

            outs = TypeObject.removeRedundantTypes(inputtypes)
            return [rej_types], outs

    def Set_Read(self,operands):
        # similiar to List Read
        rej_types = []
        outs = []
        temp = TypeObject("Set", 0)
        for i in range(len(operands)):
            if isinstance(operands[i].types, list):
                temp.elementtype += operands[i].types
            else:
                temp.elementtype.append(operands[i].types)
        outs.append(temp)
        rej_types = []
        for i in range(0, len(operands)):
            rej_types.append([])
        return rej_types,outs

    def Dict_Read(self,operands):
        # similiar to List Read,but add keytype and valuetype
        rej_types = []
        outs = []
        temp = TypeObject("Dict", 0)
        # according to the rules, the first half are keytypes and the left half are valuetypes
        if(len(operands)%2!=0):
            print('len(operands) is odd. case a: lambda case b: {**kw}' )
        for i in range(int(len(operands)/2)):
            if isinstance(operands[i].types, list):
                temp.elementtype += operands[i].types
            else:
                temp.elementtype.append(operands[i].types)
        temp.keytype = temp.elementtype
        for i in range(int(len(operands)/2),len(operands)):
            if isinstance(operands[i].types, list):
                temp.valuetype += operands[i].types
            else:
                temp.valuetype.append(operands[i].types)

        outs.append(temp)
        rej_types = []
        for i in range(0, len(operands)):
            rej_types.append([])
        return rej_types,outs

    def JoinedStr(self,operands):
        rej_types = []
        outs = []
        for i in range(0, len(operands)):
            rej_types.append([])
            outs = [TypeObject("Text", 0)]
        return rej_types, outs

    def Attribution_Return(self,operands,existstype=None):
        outs = []
        '''
        if existstype==None:
            # it means no existstype here

            temp = TypeObject("Any",0)
            outs.append(temp)
        '''
        rej_types = []
        for i in range(0, len(operands)):
            rej_types.append([])
        return rej_types, outs

    def dictcomp_Retrun(self,operands):
        temp = TypeObject("Dict", 0)
        outs = []
        rej_types = []
        # there are 2 operands, one is the symbol of element, the other is the the symbol of value
        if len(operands) == 2:
            rej_target_types = []
            # element types
            ltypes = operands[0].types
            if isinstance(ltypes, list):
                temp.elementtype += ltypes
            else:
                temp.elementtype.append(ltypes)
            temp.keytype = temp.elementtype
            rej_types.append(rej_target_types)
            # value types
            rej_target_types = []
            ltypes = operands[1].types
            if isinstance(ltypes, list):
                temp.valuetype += ltypes
            else:
                temp.valuetype.append(ltypes)
            rej_types.append(rej_target_types)

            outs.append(temp)
            return rej_types, outs


    def listcomp_Return(self,operands):
        temp = TypeObject("List", 0)
        outs = []
        rej_types = []
        # there is 1 operand, one is the symbol of element,
        if len(operands) == 1:
            rej_target_types = []
            # element types
            ltypes = operands[0].types
            if isinstance(ltypes, list):
                temp.elementtype += ltypes
            else:
                temp.elementtype.append(ltypes)

            rej_types.append(rej_target_types)
            # value types

            outs.append(temp)
            return rej_types, outs

        else:
            for i in range(len(operands)):
                rej_types.append([])
            return rej_types, outs


    def setcomp_Return(self,operands):
        temp = TypeObject("Set", 0)
        outs = []
        rej_types = []
        # there is 1 operand, one is the symbol of element,
        if len(operands) == 1:
            rej_target_types = []
            # element types
            ltypes = operands[0].types
            if isinstance(ltypes, list):
                temp.elementtype += ltypes
            else:
                temp.elementtype.append(ltypes)

            rej_types.append(rej_target_types)
            # value types

            outs.append(temp)
            return rej_types, outs

        else:
            for i in range(len(operands)):
                rej_types.append([])
            return rej_types, outs

    def GeneratorExp_Return(self,operands):
        temp = TypeObject("Generator", 0)
        outs = []
        rej_types = []
        # there is 1 operand, one is the symbol of element,
        if len(operands) == 1:
            rej_target_types = []
            # element types
            ltypes = operands[0].types
            if isinstance(ltypes, list):
                temp.elementtype += ltypes
            else:
                temp.elementtype.append(ltypes)

            rej_types.append(rej_target_types)
            # value types

            outs.append(temp)
            return rej_types, outs

        else:
            for i in range(len(operands)):
                rej_types.append([])
            return rej_types, outs

    def yieldop(self, operands):
        temp = TypeObject("Generator", 0)
        outs = []
        rej_types = []
        for o in operands:
            for t in o.types:
                if not TypeObject.existSame(t, temp.elementtype):
                    temp.elementtype.append(t)
            rej_types.append([])
        outs.append(temp)
        return rej_types, outs


    def IfExp(self, operands):
        if len(operands) != 2:
            logger.warning("IfExp requires 2 arguements, currently get {}".format(len(operands)))
            raise ValueError("IfExp requires 2 arguements, currently get {}".format(len(operands)))
        outs = []
        rej_types = [[], []]
        for o in operands:
            for i in o.types:
                if not TypeObject.existSame(i, outs):
                    outs.append(i)

        return rej_types, outs

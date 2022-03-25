from hityper.typeobject import TypeObject
import hityper.tdg
from hityper import logger
from copy import copy, deepcopy

logger.name = __name__


class Rej_TypingRule(object):
    def __init__(self):
        pass

    def check_failed(self, ori, rej):
        if len(ori) == len(rej):
            logger.warning("Rejection Typing rule faild, all types are rejected.")


    def act(self, outs, operands , op, func, attr, usertypes, iterable=False):
        #if not about iterable
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
            if(left != None and (not isinstance(left, hityper.tdg.GraphBaseNode)) or (right != None and not isinstance(right,  hityper.tdg.GraphBaseNode))):
                raise ValueError("Operands must be a graph node")
        if (op in ["and", "or"]):
            return self.norej_add(outs,operands)
        elif (op == "not"):
            return self.norej_add(outs,operands)
        elif (op in ["<", "<=", ">", ">="]):
            return self.norej_add(outs,operands)
        elif (op in ["==", "!=", "is", "isnot"]):
            return self.norej_add(outs, operands)
        elif (op == "+" and right != None):
            return self.binop_add(outs,operands)
        elif (op == "*"):
            return self.binop_mul(outs,left, right)
        elif (op in ["-", "/", "//", "%", "**", "pow"] and right != None):
            return self.binop_num_op(outs, left, right, op)
        elif (op in ["+", "-", "abs"] and right == None):
            return self.NumRemainSame(outs,left, right)
        elif (op in ["|", "^", "&", "<<", ">>"]):
            return self.binop_int_op(outs, left, right)
        elif (op == "~" and right == None):
            return self.unop_int_op(outs, left, right)
        elif (op in ["in", "not in"] ):
            return self.norej_add(outs, operands)
        elif (op == "forin" and right == None):
            return self.unop_forin(outs, left, right)
        elif (op == "append"):
            return self.binop_append(outs,left, right)
        elif (op == "Subscript_Write"):
            return self.norej_add(outs, operands)
        elif (op == "Subscript_Read"):
            return self.binop_subscript(outs,operands, func, attr, usertypes)
        elif (op == "=" and right == None):
            return self.unop_assign(outs,left, right)
        elif (op == "call"):
            return self.rej_call(outs, operands, func, attr, usertypes)
        elif (op == "List_Read"):
            return self.norej_add(outs, operands)
        elif( op == "List_Write"):
            return self.List_Write(outs,operands)
        elif(op == "Tuple_Read"):
            return self.norej_add(outs, operands)
        elif(op == "Tuple_Write"):
            return  self.Add_tofirst(outs,operands)
        elif(op == "Set_Read"):
            return self.norej_add(outs, operands)
        elif(op =="Dict_Read"):
            return self.norej_add(outs, operands)
        elif(op == "JoinedStr"):
            return self.norej_add(outs, operands)
        elif(op=="."):
            return self.norej_add(outs, operands)
        elif(op=="ListComp"):
            return  self.Add_tofirst(outs, operands)
        elif(op=="SetComp"):
            return self.Add_tofirst(outs,operands)
        elif(op=="DictComp"):
            return self.norej_add(outs, operands)
        elif(op=="GeneratorExp"):
            return self.Add_tofirst(outs, operands)
        else: #for unknown_op
            return self.unknown_op(outs,operands, op)
            #raise TypeError("Unknown Operation: " + op)



    def binop_and_or(self,outs,left,right):
        # since left and right can have arbitary types, no rej_type can be inferred
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = deepcopy(left.rejtypes)
        rej_rtypes = deepcopy(right.rejtypes)
        rej_outs = outs.rejtypes
        return [rej_ltypes, rej_rtypes]

    def norej_add(self,outs,operands):
        # this function is for the arbitary input
        inputlen = len(operands)
        rej_list = []
        for node in operands:
            rej_each = node.rejtypes
            rej_list.append(rej_each)
        return rej_list

    def binop_add(self, outs, operands):
        left = operands[0]
        ltypes = left.types
        if len(operands) > 1:
            right = operands[1]
            rtypes = right.types
            rej_rtypes = deepcopy(right.rejtypes)

        rej_ltypes = deepcopy(left.rejtypes)

        rej_outs = outs.rejtypes

        for t in rej_outs:
            #  here we should divide the situation into 2: user-define or  built-in
            rej_ltypes.append(t)
            rej_rtypes.append(t)

        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)
        rej_rtypes = TypeObject.removeRedundantTypes(rej_rtypes)

        return [rej_ltypes, rej_rtypes]


    def binop_mul(self,outs,left, right):
        #add rej_out into rej_left
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = deepcopy(left.rejtypes)
        rej_rtypes = deepcopy(right.rejtypes)
        rej_outs = outs.rejtypes

        for t in rej_outs:
            rej_ltypes.append(t)

        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)

        return [rej_ltypes, rej_rtypes]

    def binop_num_op(self,outs, left, right, op):
        ltypes = left.types
        rtypes = right.types
        rej_ltypes = deepcopy(left.rejtypes)
        rej_rtypes = deepcopy(right.rejtypes)
        rej_outs = outs.rejtypes
        for t in rej_outs:
            #  here we should divide the situation into 2: numbers or others
            if t.type not in ["bool", "int", "float", "complex"]:
                rej_ltypes.append(t)
                rej_rtypes.append(t)

        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)
        rej_rtypes = TypeObject.removeRedundantTypes(rej_rtypes)

        return [rej_ltypes, rej_rtypes]

    def NumRemainSame(self, outs, left, right):
        ltypes = left.types
        rej_ltypes = deepcopy(left.rejtypes)
        rej_outs = outs.rejtypes
        for t in rej_outs:
            rej_ltypes.append(t)

        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)

        return [rej_ltypes]

    def binop_int_op(self, outs, left, right):
        rej_outs = outs.rejtypes
        ltypes = left.types
        rej_ltypes = deepcopy(left.rejtypes)
        rtypes = right.types
        rej_rtypes = deepcopy(right.rejtypes)
        for t in rej_outs:
            rej_ltypes.append(t)
            rej_rtypes.append(t)
        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)
        rej_rtypes = TypeObject.removeRedundantTypes(rej_rtypes)
        return [rej_ltypes, rej_rtypes]




    def unop_int_op(self, outs, left, right):

        # add rej_out into left
        rej_ltypes = deepcopy(left.rejtypes)
        rej_outs = outs.rejtypes
        for t in rej_outs:
            rej_ltypes.append(t)
        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)
        # if there are more than 2 operands

        return [rej_ltypes]

    def unop_forin(self,outs, left, right):
        # no right here
        rej_ltypes = deepcopy(left.rejtypes)
        rej_outs = outs.rejtypes
        for t in rej_outs:
            rej_ltypes.append(t)

        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)

        return [rej_ltypes]

    def binop_append(self,outs,left, right):
        rej_ltypes = deepcopy(left.rejtypes)
        rej_rtypes = deepcopy(right.rejtypes)
        rej_outs = outs.rejtypes
        for t in rej_outs:
            rej_ltypes.append(t)

        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)

        return [rej_ltypes,rej_rtypes]

    def binop_subscript(self, outs,operands, func, attr, usertypes):
        if len(operands)==2:
            # no infer
            rej_list = []
            for node in operands:
                rej_each = node.rejtypes
                rej_list.append(rej_each)
            return rej_list
        else:
            left = operands[0]


            rej_ltypes = deepcopy(left.rejtypes)
            rej_outs = outs.rejtypes

            for t in rej_outs:
                #  here we should divide the situation into 2: user-define or  built-in
                rej_ltypes.append(t)
            rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)

            rej_list = [rej_ltypes]
            for n in range(1,len(operands)):
                rej_each = operands[n].rejtypes
                rej_list.append(rej_each)
            return rej_list

    def unop_assign(self, outs,left, right):
        # add rejout to left
        rej_ltypes = deepcopy(left.rejtypes)
        rej_outs = outs.rejtypes
        for t in rej_outs:
            rej_ltypes.append(t)

        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)

        return [rej_ltypes]

    def List_Write(self, outs,operands):
        left = operands[0]

        rej_ltypes = deepcopy(left.rejtypes)
        rej_outs = outs.rejtypes

        for t in rej_outs:
            #  here we should divide the situation into 2: user-define or  built-in
            rej_ltypes.append(t)
        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)

        rej_list = [rej_ltypes]
        for node in range(1, len(operands)):
            rej_each = node.rejtypes
            rej_list.append(rej_each)
        return rej_list

    def Add_tofirst(self, outs, operands):
        # add rej_out into operands[0]
        left = operands[0]
        rej_ltypes = deepcopy(left.rejtypes)
        rej_outs = outs.rejtypes

        for t in rej_outs:
            rej_ltypes.append(t)
        rej_ltypes = TypeObject.removeRedundantTypes(rej_ltypes)

        rej_list = [rej_ltypes]
        for n in range(1, len(operands)):
            rej_each = operands[n].rejtypes
            rej_list.append(rej_each)
        return rej_list

    def unknown_op(self,outs,operands,op):
        print("Unknown Operation: " + op)
        rej_list = []
        for node in operands:
            rej_each = node.rejtypes
            rej_list.append(rej_each)
        return rej_list

    def rej_call(self, outs, operands, func, attr, usertypes):
        rej_outs = outs.rejtypes
        # if user-defined functions, no rej inference(because we don't know what they will do in the function)
        if func in usertypes:
            rej_list = []
            for node in operands:
                rej_each = node.rejtypes
                rej_list.append(rej_each)
            return rej_list
        # not usertype, Widely used operation funcs, e.g. list.append()
        # it means there could be overload, but we just simply don't infer here
        else:
            if attr == None:
                # no infer
                rej_list = []
                for node in operands:
                    rej_each = node.rejtypes
                    rej_list.append(rej_each)
                return rej_list
                # e.g def foo() / a = foo()
            elif func == "append" or func=="clear" or func=="copy" or func == "insert" or func == "pop" or func=="remove" or func=="discard" or func=="reverse" or func=="sort":
                #add rej_out into operands[0] ,other don't infer
                return self.Add_tofirst(outs, operands)
            elif func == "get" or func=="popitem" or func=="setdefault" or func=="update" or func=="center" or func=="zfill" or func=="expandtabs" or func == "join":
                return self.Add_tofirst(outs, operands)
            elif func == "ljust" or func=="lower" or func=="lstrip" or func=="removeprefix" or func=="removesuffix" or func =="rjust" or func=="replace":
                return self.Add_tofirst(outs, operands)
            elif func == "rstrip" or func=="strip" or func=="add" or func=="difference" or func=="difference_update" or func=="intersection" or func=="intersection_update" or func== "union":
                return self.Add_tofirst(outs, operands)
            elif func=="symmetric_difference" or func=="symmetric_difference_update" or func == "abs":
                return self.Add_tofirst(outs, operands)

            elif func=="count" or func == "index" or func == "bytes" or func =="int" or func == "float" or func == "str" or func == "tuple" or func == "list":
                return self.norej_add(outs, operands)
            elif func=="set" or func == "dict" or func == "type" or func=="fromkeys" or func=="values" or func=="encode" or func=="endswith" or func=="startswith":
                return self.norej_add(outs, operands)
            elif func=="find" or func=="rfind"or func=="partition" or func=="rpartition" or func=="rindex" or func=="rsplit" or func=="split" or func=="splitlines":
                return self.norej_add(outs, operands)
            elif func in ['isalnum', 'isalpha', 'isascii', 'isdecimal', 'isdigit', 'isidentifier', 'islower', 'isnumeric', 'isprintable', 'isspace', 'istitle', 'isupper']:
                return self.norej_add(outs, operands)
            elif func=="isdisjoint" or func=="issubset" or func=="issuperset" or func =="all" or func == "any" or func == "bin" or func=="hex" or func == "oct" or func == "divmod" or func == "enumerate":
                return self.norej_add(outs, operands)
            elif func == "getattr" or func=="globals" or func=="hash" or func == "isinstance" or func == "len" or func == "map" or func == "max" or func=="min" or func == "pow" or func == "round" or func == "sorted":
                return self.norej_add(outs, operands)
            elif func == "sum":
                return self.norej_add(outs, operands)
            elif func == "extend":
            # add rej_out into all the operands
                rej_outs = outs.rejtypes
                rej_list = []
                for node in operands:
                    rej_types = deepcopy(node.rejtypes)
                    for t in rej_outs:
                        rej_types.append(t)
                    rej_types = TypeObject.removeRedundantTypes(rej_types)
                    rej_list.append(rej_types)
                return rej_list
            else:
                return self.norej_add(outs, operands)




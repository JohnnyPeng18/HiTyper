import requests
from hityper.config import config
from hityper.typeobject import TypeObject
from hityper import logger
from hityper.tdg import *
from hityper.tdg_generator import TDGGenerator
from hityper.usertype_finder import UsertypeFinder
import os, sys
import ast
from tqdm import tqdm
import json
from gensim.models import Word2Vec
import numpy as np
from transformers import RobertaTokenizer
from multiprocessing.dummy import Pool as ThreadPool
from func_timeout import func_set_timeout, FunctionTimedOut


logger.name = __name__



class SimModel(object):
    def __init__(self, modelpath, tokenizer):
        self.model = Word2Vec.load(modelpath)
        self.tokenizer = RobertaTokenizer.from_pretrained('microsoft/graphcodebert-base', cache_dir = config["cached_dir"])
        logger.info("Loaded similarity calculation model.")
    
    def get_similarity(self, str1, str2):
        words1 = self.tokenizer.tokenize(str1)
        words2 = self.tokenizer.tokenize(str2)
        v1 = np.zeros(config["w2v_size"])
        v2 = np.zeros(config["w2v_size"])
        for i in words1:
            v1 += self.model.wv[i]
        v1 = v1 / len(words1)
        for i in words2:
            v2 += self.model.wv[i]
        v2 = v2 / len(words2)

        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))








def formatUserTypes(usertype):
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


def detectChange(prev_types, types):
    for n in prev_types:
        if n not in types:
            return True
    
    for n in types:
        if n not in prev_types:
            return True

    return False

def getRecommendations(source):
    try:
        r = requests.post(config[config["default_model"]], source, proxies = {"http": None})
        res = r.json()
    except Exception as e:
        logger.error("Error occurs when getting recommendations from Type4Py, reason: {}.".format(e))
        return None
    if not isinstance(res, dict) or res["response"] == None:
        logger.error("Type4Py cannot generate predictions for current source file.")
        return None
    rec = {}
    num = 0
    
    for c in res["response"]["classes"]:
        rec[c["q_name"]] = {}
        for func in c["funcs"]:
            rec[c["q_name"]][func["q_name"]] = {"annotations": []}
            if "params_p" in func:
                for p in func["params_p"]:
                    types = []
                    for t in func["params_p"][p]:
                        types.append(t[0])
                    rec[c["q_name"]][func["q_name"]]["annotations"].append({"category": "arg", "name": p, "type": types})
                    num += 1
            if "ret_type_p" in func:
                types = []
                for t in func["ret_type_p"]:
                    types.append(t[0])
                rec[c["q_name"]][func["q_name"]]["annotations"].append({"category": "return", "name": func["q_name"].split(".")[-1], "type": types})
                num += 1
            if "variables_p" in func:
                for p in func["variables_p"]:
                    types = []
                    for t in func["variables_p"][p]:
                        types.append(t[0])
                    rec[c["q_name"]][func["q_name"]]["annotations"].append({"category": "local", "name": p, "type": types})
                    num += 1
    rec["global"] = {"global": {"annotations": []}}
    for func in res["response"]["funcs"]:
        rec["global"][func["q_name"]] = {"annotations": []}
        if "params_p" in func:
            for p in func["params_p"]:
                types = []
                for t in func["params_p"][p]:
                    types.append(t[0])
                rec["global"][func["q_name"]]["annotations"].append({"category": "arg", "name": p, "type": types})
                num += 1
        if "ret_type_p" in func:
            types = []
            for t in func["ret_type_p"]:
                types.append(t[0])
            rec["global"][func["q_name"]]["annotations"].append({"category": "return", "name": func["q_name"].split(".")[-1], "type": types})
            num += 1
        if "variables_p" in func:
            for p in func["variables_p"]:
                types = []
                for t in func["variables_p"][p]:
                    types.append(t[0])
                rec["global"][func["q_name"]]["annotations"].append({"category": "local", "name": p, "type": types})
                num += 1
    
    for v in res["response"]["variables_p"]:
        types = []
        for t in res["response"]["variables_p"][v]:
            types.append(t[0])
        rec["global"]["global"]["annotations"].append({"category": "local", "name": v, "type": types})
        num += 1

    logger.info("Get {} recommendations from Type4Py.".format(num))
    return rec


def test_multiplefile(gtfile, detailed_gtfile, usertype_file, recfile = None, recmodel = False, topn = 1, prefix = None, eval = False):
    with open(gtfile, "r", encoding = "utf-8") as gf:
        gts = json.loads(gf.read())
    with open(detailed_gtfile, "r", encoding = "utf-8") as gf:
        detailed_gts = json.loads(gf.read())
    with open(usertype_file, "r", encoding = "utf-8") as uf:
        usertypes = json.loads(uf.read())
    if recfile:
        with open(recfile, "r", encoding = "utf-8") as rf:
            recommendations = json.loads(rf.read())
    else:
        recommendations = None

    if config["simmodel"]!= None:
        simmodel = SimModel(config[config["simmodel"]], config["tokenizer"])
    else:
        simmodel = None
    
    data = {}
    predictions = {}
    for k in detailed_gts:
        data[k] = {"total": 0, "success": {"arg": 0, "return": 0, "local": 0, "total": 0}, "nores": {"arg": 0, "return": 0, "local": 0, "total": 0}, "similar": {"arg": 0, "return": 0, "local": 0, "total": 0}, "partial": {"arg": 0, "return": 0, "local": 0, "total": 0},  "failed": {"arg": 0, "return": 0, "local": 0, "total": 0}, "acc": 0.0, "recall": 0.0, "similaracc": 0.0, "similarrecall": 0.0, "partialacc": 0.0, "partialrecall": 0.0, "file": 0}
    
    num = 0
    for f in tqdm(gts, desc = "Inferring types"):
        num +=1
        logger.info("++++++++++++++++++++++[{}/{}]Infer file {}++++++++++++++++++++++".format(num, len(gts), f))
        res, str_results = test_onefile("", f, gts = detailed_gts, usertypes = usertypes, recommendations = recommendations, recmodel = recmodel, topn = topn, simmodel = simmodel, prefix = prefix, eval = eval)
        if res == None:
            continue
        predictions[f] = str_results
        for k in res:
            for i in res[k]:
                if i == "total":
                    data[k][i] += res[k][i]
                elif i in ["success", "nores", "failed", "similar", "partial"]:
                    for j in res[k][i]:
                        data[k][i][j] += res[k][i][j]
            if (data[k]["success"]["total"] + data[k]["failed"]["total"] + data[k]["similar"]["total"] + data[k]["partial"]["total"]) != 0:
                data[k]["acc"] = data[k]["success"]["total"] / (data[k]["success"]["total"] + data[k]["failed"]["total"] + data[k]["similar"]["total"] + data[k]["partial"]["total"])
                data[k]["similaracc"] = (data[k]["success"]["total"] + data[k]["similar"]["total"]) / (data[k]["success"]["total"] + data[k]["failed"]["total"] + data[k]["similar"]["total"] + data[k]["partial"]["total"])
                data[k]["partialacc"] = (data[k]["success"]["total"] + data[k]["similar"]["total"] + data[k]["partial"]["total"]) / (data[k]["success"]["total"] + data[k]["failed"]["total"] + data[k]["similar"]["total"] + data[k]["partial"]["total"])
            else:
                data[k]["acc"] = "Not Valid"
                data[k]["similaracc"] = "Not Valid"
                data[k]["partialacc"] = "Not Valid"
            if data[k]["total"] != 0:
                data[k]["recall"] = data[k]["success"]["total"] / data[k]["total"]
                data[k]["similarrecall"] = (data[k]["success"]["total"] + data[k]["similar"]["total"]) / data[k]["total"]
                data[k]["partialrecall"] = (data[k]["success"]["total"] + data[k]["similar"]["total"] + data[k]["partial"]["total"]) / data[k]["total"]
            else:
                data[k]["recall"] = "Not Valid"
                data[k]["similarrecall"] = "Not Valid"
                data[k]["partialrecall"] = "Not Valid"
            data[k]["file"] += 1
    seconddata = {}
    seconddata["arg"] = {"success": 0, "similar": 0, "partial": 0, "failed": 0, "nores": 0, "total": 0, "acc": 0, "recall": 0, "similaracc": 0, "similarrecall": 0, "partialacc": 0, "partialrecall": 0}
    seconddata["return"] = {"success": 0, "similar": 0, "partial": 0, "failed": 0, "nores": 0, "total": 0, "acc": 0, "recall": 0, "similaracc": 0, "similarrecall": 0, "partialacc": 0, "partialrecall": 0}
    seconddata["local"] = {"success": 0, "similar": 0, "partial": 0, "failed": 0, "nores": 0, "total": 0, "acc": 0, "recall": 0, "similaracc": 0, "similarrecall": 0, "partialacc": 0, "partialrecall": 0}
    for k in data:
        for i in data[k]:
            if i in ["success", "nores", "failed", "similar", "partial"]:
                seconddata["arg"][i] += data[k][i]["arg"]
                seconddata["return"][i] += data[k][i]["return"]
                seconddata["local"][i] += data[k][i]["local"]
    for k in seconddata:
        seconddata[k]["total"] = seconddata[k]["success"] + seconddata[k]["similar"] + seconddata[k]["partial"] + seconddata[k]["failed"] + seconddata[k]["nores"]
        if seconddata[k]["success"] + seconddata[k]["similar"] + seconddata[k]["partial"] + seconddata[k]["failed"] != 0:
            seconddata[k]["acc"] = seconddata[k]["success"] / (seconddata[k]["success"] + seconddata[k]["similar"] + seconddata[k]["partial"] + seconddata[k]["failed"])
            seconddata[k]["similaracc"] = (seconddata[k]["success"] + seconddata[k]["similar"]) / (seconddata[k]["success"] + seconddata[k]["similar"] + seconddata[k]["partial"] + seconddata[k]["failed"])
            seconddata[k]["partialacc"] = (seconddata[k]["success"] + seconddata[k]["similar"] + seconddata[k]["partial"]) / (seconddata[k]["success"] + seconddata[k]["similar"] + seconddata[k]["partial"] + seconddata[k]["failed"])
        else:
            seconddata[k]["acc"] = "Not Valid"
            seconddata[k]["similaracc"] = "Not Valid"
            seconddata[k]["partialacc"] = "Not Valid"
        if seconddata[k]["total"] != 0:
            seconddata[k]["recall"] = seconddata[k]["success"]  / seconddata[k]["total"]
            seconddata[k]["similarrecall"] = (seconddata[k]["success"] + seconddata[k]["similar"]) / seconddata[k]["total"]
            seconddata[k]["partialrecall"] = (seconddata[k]["success"] + seconddata[k]["similar"] + seconddata[k]["partial"]) / seconddata[k]["total"]
        else:
            seconddata[k]["recall"] = "Not Valid"
            seconddata[k]["similarrecall"] = "Not Valid"
            seconddata[k]["partialrecall"] = "Not Valid"

    logger.info("All source files analyzed, results are shown as below:")
    for k in data:
        logger.info("Result for {}: Acc - {}, Recall - {}, Similar_Acc - {}, Similar_Recall - {}, Partial_Acc - {}, Partial_Recall - {}, Total - {}, Success Details - {}, Similar Details - {}, Partial Details - {}, Failure Details - {}, No Res Details - {}".format(k, data[k]["acc"], data[k]["recall"], data[k]["similaracc"], data[k]["similarrecall"], data[k]["partialacc"], data[k]["partialrecall"], data[k]["total"], data[k]["success"], data[k]["similar"], data[k]["partial"], data[k]["failed"], data[k]["nores"]))
    for k in seconddata:
        logger.info("Result for {}: Acc - {}, Recall - {}, Similar_Acc - {}, Similar_Recall - {}, Partial_Acc - {}, Partial_Recall - {}, Total - {}".format(k, seconddata[k]["acc"], seconddata[k]["recall"], seconddata[k]["similaracc"], seconddata[k]["similarrecall"], seconddata[k]["partialacc"], seconddata[k]["partialrecall"], seconddata[k]["total"]))
    
    return predictions
                    

    



def test_onefile(gtfile, filename, gts = None, gentg = False, usertypes = None, recommendations = None, recmodel = False, topn = 1, simmodel = None, prefix = None, eval = False):
    if gts == None:
        with open(gtfile, "r", encoding = "utf-8") as gf:
            gts = json.loads(gf.read())
    gt = {}
    locations = []
    for k in gts:
        if filename in gts[k]:
            gt[k] = {}
            for c in gts[k][filename]:
                for func in gts[k][filename][c]:
                    gt[k]["{}@{}".format(func, c)] = gts[k][filename][c][func]["annotations"]
                    if "{}@{}".format(func, c) not in locations:
                        locations.append("{}@{}".format(func, c))
    if len(gt) == 0:
        logger.error("Cannot find groundtruth types of this file.")
        return None, None
    if prefix != None:
        filepath = prefix + "/" + filename
    else:
        filepath = filename
    if not os.path.exists(filepath):
        logger.error("File {} does not exist.".format(filename))
        return None, None
    source = open(filepath, "r", encoding='UTF-8').read()
    root = ast.parse(source)
    if isinstance(usertypes, dict) and filename in usertypes:
        usertype = usertypes[filename]
    elif isinstance(usertypes, str):
        with open(usertypes, "r", encoding = "utf-8") as uf:
            usertypes = json.loads(uf.read())
            if filename in usertypes:
                usertype = usertypes[filename]
            else:
                logger.warning("Cannot get the user-defined typeset for file {}, using empty typeset.".format(filename))
                usertype = {'direct': [], 'indirect': [], 'init': [], 'num': 0, 'module': ['a']}
    else:
        logger.warning("Cannot get the user-defined typeset for file {}, using empty typeset.".format(filename))
        usertype = {'direct': [], 'indirect': [], 'init': [], 'num': 0, 'module': ['a']}
    if isinstance(recommendations,str):
        with open(recfile, "r", encoding = "utf-8") as rf:
            recommendations = json.loads(rf.read())
    elif recommendations == None and recmodel:
        recommendations = getRecommendations(source)
    elif isinstance(recommendations, dict):
        if filename in recommendations:
            recommendations = recommendations[filename]
        else:
            recommendations = None
    try:
        visitor = TDGGenerator(filename, True, None, usertype)
        global_tg = visitor.run(root)
    except Exception as e:
        logger.error("Cannot generate TDG for file {}. Reason: {}".format(filename, e))
        return None, None
    results = {}
    str_results = {}
    if recommendations != None and "global" in recommendations and "global" in recommendations["global"]:
        global_tg.passTypes(debug = False)
        global_tg.recommendType(recommendations, formatUserTypes(usertype), usertype["module"], topn, simmodel = simmodel)
        global_tg.passTypes(debug = False)
    else:
        global_tg.passTypes(debug = False)
    global_tg.simplifyTypes()
    results["global@global"] = global_tg.returntypes()
    str_results["global@global"] = global_tg.dumptypes()
    if gentg == True:
        logger.info("TDG dumped.")
        global_tg.draw(filerepo = "testtgs")
    for tg in global_tg.tgs:
        if tg.name in locations:
            try:
                if recommendations != None:
                    changed = True
                    iters = 0
                    while changed and iters < 20:
                        iters += 1
                        tg.passTypes(debug = False)
                        types = tg.findHotTypes()
                        tg.recommendType(types, recommendations, formatUserTypes(usertype), usertype["module"], topn, simmodel = simmodel, eval = eval)
                        tg.passTypes(debug = False)
                        new_types = tg.findHotTypes()
                        changed = detectChange(types, new_types)
                    tg.simplifyTypes()
                else:
                    tg.passTypes(debug = False)
                    tg.simplifyTypes()
                if gentg == True:
                    logger.info("TDG dumped.")
                    tg.draw(filerepo = "testtgs")
                results[tg.name] = tg.returntypes()
                str_results[tg.name] = tg.dumptypes()
            except Exception as e:
                logger.error("Error occurred when iterating the TDG {}, reason: {}".format(tg.name, str(e)))
                return None, None
    num = {}
    for k in gt:
        num[k] = {"total": 0, "success": {"arg": 0, "return": 0, "local": 0, "total": 0}, "nores": {"arg": 0, "return": 0, "local": 0, "total": 0}, "similar": {"arg": 0, "return": 0, "local": 0, "total": 0}, "partial": {"arg": 0, "return": 0, "local": 0, "total": 0}, "failed": {"arg": 0, "return": 0, "local": 0, "total": 0}, "acc": 0.0, "recall": 0.0, "similaracc": 0.0, "similarrecall": 0.0, "partialacc": 0.0, "partialrecall": 0.0}
        for l in gt[k]:
            for a in gt[k][l]:
                num[k]["total"] += 1
                res = None
                if l in results:
                    for r in results[l]:
                        if r["name"] == a["name"] and r["category"] == r["category"]:
                            res = r
                            break
                else:
                    logger.warning("Unable to infer location {}".format(l))
                if res == None:
                    if l in results:
                        logger.warning("Cannot infer variable {} at location {}\nGT: {}\nRES: {}".format(a["name"], l, a, results[l]))
                    num[k]["nores"]["total"] += 1
                    num[k]["nores"][a["category"]] += 1
                    continue
                gttypes = []
                if isinstance(a["type"], list):
                    for t in a["type"]:
                        gttypes += TypeObject.Str2Obj(t)
                else:
                    gttypes = TypeObject.Str2Obj(a["type"])
                if len(r["type"]) == 1 and r["type"][0].type == "bool" and len(gttypes) == 1 and gttypes[0].type == "str":
                    num[k]["success"]["total"] += 1
                    num[k]["success"][a["category"]] += 1
                elif TypeObject.isSetIncluded(r["type"], gttypes):
                    num[k]["success"]["total"] += 1
                    num[k]["success"][a["category"]] += 1
                elif TypeObject.isSetIncluded2(r["type"], gttypes):
                    num[k]["similar"]["total"] += 1
                    num[k]["similar"][a["category"]] += 1
                elif (len(r["type"]) != 0 and TypeObject.isSetIncluded(gttypes, r["type"])) or (len(r["type"]) == 1 and r["type"][0].type.lower() == "none"):
                    num[k]["partial"]["total"] += 1
                    num[k]["partial"][a["category"]] += 1
                elif len(r["type"]) == 0:
                    logger.warning("Failed to infer types for location {}\nGT: {}".format(l, a))
                    num[k]["nores"]["total"] += 1
                    num[k]["nores"][a["category"]] += 1
                else:
                    logger.warning("Incorrect result type for location {}\nGT: {} \n TGT: {} \n Result: {}".format(l, a, TypeObject.DumpOriObjects(gttypes), TypeObject.DumpOriObjects(r["type"])))
                    num[k]["failed"]["total"] += 1
                    num[k]["failed"][a["category"]] += 1
        if (num[k]["success"]["total"] + num[k]["failed"]["total"] + num[k]["similar"]["total"] + num[k]["partial"]["total"]) != 0:
            num[k]["acc"] = num[k]["success"]["total"] / (num[k]["success"]["total"] + num[k]["failed"]["total"] + num[k]["similar"]["total"] + num[k]["partial"]["total"])
            num[k]["similaracc"] = (num[k]["success"]["total"] + num[k]["similar"]["total"]) / (num[k]["success"]["total"] + num[k]["failed"]["total"] + num[k]["similar"]["total"] + num[k]["partial"]["total"])
            num[k]["partialacc"] = (num[k]["success"]["total"] + num[k]["similar"]["total"] + num[k]["partial"]["total"]) / (num[k]["success"]["total"] + num[k]["failed"]["total"] + num[k]["similar"]["total"] + num[k]["partial"]["total"])
        else:
            num[k]["acc"] = "Not Valid"
            num[k]["similaracc"] = "Not Valid"
            num[k]["partialacc"] = "Not Valid"
        if num[k]["total"] != 0:
            num[k]["recall"] = num[k]["success"]["total"] / num[k]["total"]
            num[k]["similarrecall"] = (num[k]["success"]["total"] + num[k]["similar"]["total"]) / num[k]["total"]
            num[k]["partialrecall"] = (num[k]["success"]["total"] + num[k]["similar"]["total"] + num[k]["partial"]["total"]) / num[k]["total"]
        else:
            num[k]["recall"] = "Not Valid"
            num[k]["similarrecall"] = "Not Valid"
            num[k]["partialrecall"] = "Not Valid"
    for k in num:
        logger.info("Result for {}: Acc - {}, Recall - {}, Similar_Acc - {}, Similar_Recall - {}, Partial_Acc - {}, Partial_Recall - {}, Total - {}, Success Details - {}, Similar Details - {}, Partial Details - {}, Failure Details - {}".format(k, num[k]["acc"], num[k]["recall"], num[k]["similaracc"], num[k]["similarrecall"], num[k]["partialacc"], num[k]["partialrecall"], num[k]["total"], num[k]["success"], num[k]["similar"], num[k]["partial"], num[k]["failed"]))
    logger.debug(json.dumps(gt, sort_keys=True, indent=4, separators=(',', ': ')))
    logger.debug(json.dumps(str_results, sort_keys=True, indent=4, separators=(',', ': ')))
    return num, str_results



def transformDataset(jsonrepo, outputdir = None):
    files = os.listdir(jsonrepo)
    jsonfiles = []
    for f in files:
        if f.endswith(".json"):
            jsonfiles.append(f)

    logger.info("Find {} json files.".format(len(jsonfiles)))

    gts = {}

    detailed_gts = {"user-defined": {}, "generic": {}, "simple": {}}
    
    for f in tqdm(jsonfiles, desc = "Processing JSON files"):
        data = json.loads(open(os.path.join(jsonrepo, f)).read())
        for m in data:
            for f in data[m]["src_files"]:
                if f not in gts:
                    gts[f] = {}
                for index, v in enumerate(list(data[m]["src_files"][f]["variables"].keys())):
                    name = list(data[m]["src_files"][f]["mod_var_occur"].keys())[index]
                    gttype = data[m]["src_files"][f]["variables"][v]
                    scope = "local"
                    annotation = {"category": scope, "type": gttype, "name": name}
                    if gttype not in ["", "typing.Any"]:
                        cat = TypeObject.checkType(gttype)
                        if cat != None:
                            if "global" not in gts[f]:
                                gts[f]["global"] = {}
                            if "global" not in gts[f]["global"]:
                                gts[f]["global"]["global"] = {"annotations": []}
                            if f not in detailed_gts[cat]:
                                detailed_gts[cat][f] = {}
                            if "global" not in detailed_gts[cat][f]:
                                detailed_gts[cat][f]["global"] = {}
                            if "global" not in detailed_gts[cat][f]["global"]:
                                detailed_gts[cat][f]["global"]["global"] = {"annotations": []}
                            detailed_gts[cat][f]["global"]["global"]["annotations"].append(annotation)
                            gts[f]["global"]["global"]["annotations"].append(annotation)
                for func in data[m]["src_files"][f]["funcs"]:
                    funcname = func["q_name"]
                    for index, p in enumerate(list(func["params"].keys())):
                        name = list(func["params_occur"].keys())[index]
                        gttype = func["params"][p]
                        scope = "arg"
                        annotation = {"category": scope, "type": gttype, "name": name}
                        if gttype not in ["", "typing.Any"]:
                            cat = TypeObject.checkType(gttype)
                            if cat != None:
                                if "global" not in gts[f]:
                                    gts[f]["global"] = {}
                                if funcname not in gts[f]["global"]:
                                    gts[f]["global"][funcname] = {"annotations": []}
                                if f not in detailed_gts[cat]:
                                    detailed_gts[cat][f] = {}
                                if "global" not in detailed_gts[cat][f]:
                                    detailed_gts[cat][f]["global"] = {}
                                if funcname not in detailed_gts[cat][f]["global"]:
                                    detailed_gts[cat][f]["global"][funcname] = {"annotations": []}
                                detailed_gts[cat][f]["global"][funcname]["annotations"].append(annotation)
                                gts[f]["global"][funcname]["annotations"].append(annotation)
                    for index, v in enumerate(list(func["variables"].keys())):
                        name = list(func["fn_var_occur"].keys())[index]
                        gttype = func["variables"][v]
                        scope = "local"
                        annotation = {"category": scope, "type": gttype, "name": name}
                        if gttype not in ["", "typing.Any"]:
                            cat = TypeObject.checkType(gttype)
                            if cat != None:
                                if "global" not in gts[f]:
                                    gts[f]["global"] = {}
                                if funcname not in gts[f]["global"]:
                                    gts[f]["global"][funcname] = {"annotations": []}
                                if f not in detailed_gts[cat]:
                                    detailed_gts[cat][f] = {}
                                if "global" not in detailed_gts[cat][f]:
                                    detailed_gts[cat][f]["global"] = {}
                                if funcname not in detailed_gts[cat][f]["global"]:
                                    detailed_gts[cat][f]["global"][funcname] = {"annotations": []}
                                detailed_gts[cat][f]["global"][funcname]["annotations"].append(annotation)
                                gts[f]["global"][funcname]["annotations"].append(annotation)
                    if func["ret_type"] not in ["", "typing.Any"]:
                        name = funcname
                        scope = "return"
                        gttype = func["ret_type"]
                        annotation = {"category": scope, "type": gttype, "name": name}
                        cat = TypeObject.checkType(gttype)
                        if cat != None:
                            if "global" not in gts[f]:
                                gts[f]["global"] = {}
                            if funcname not in gts[f]["global"]:
                                gts[f]["global"][funcname] = {"annotations": []}
                            if f not in detailed_gts[cat]:
                                detailed_gts[cat][f] = {}
                            if "global" not in detailed_gts[cat][f]:
                                detailed_gts[cat][f]["global"] = {}
                            if funcname not in detailed_gts[cat][f]["global"]:
                                detailed_gts[cat][f]["global"][funcname] = {"annotations": []}
                            detailed_gts[cat][f]["global"][funcname]["annotations"].append(annotation)
                            gts[f]["global"][funcname]["annotations"].append(annotation)
                for c in data[m]["src_files"][f]["classes"]:
                    classname = c["q_name"]
                    for func in c["funcs"]:
                        funcname = func["q_name"].split(".")[-1]
                        for index, p in enumerate(list(func["params"].keys())):
                            name = list(func["params_occur"].keys())[index]
                            gttype = func["params"][p]
                            scope = "arg"
                            annotation = {"category": scope, "type": gttype, "name": name}
                            if gttype not in ["", "typing.Any"]:
                                cat = TypeObject.checkType(gttype)
                                if cat != None:
                                    if classname not in gts[f]:
                                        gts[f][classname] = {}
                                    if funcname not in gts[f][classname]:
                                        gts[f][classname][funcname] = {"annotations": []}
                                    if f not in detailed_gts[cat]:
                                        detailed_gts[cat][f] = {}
                                    if classname not in detailed_gts[cat][f]:
                                        detailed_gts[cat][f][classname] = {}
                                    if funcname not in detailed_gts[cat][f][classname]:
                                        detailed_gts[cat][f][classname][funcname] = {"annotations": []}
                                    detailed_gts[cat][f][classname][funcname]["annotations"].append(annotation)
                                    gts[f][classname][funcname]["annotations"].append(annotation)
                        for index, v in enumerate(list(func["variables"].keys())):
                            name = list(func["fn_var_occur"].keys())[index]
                            gttype = func["variables"][v]
                            scope = "local"
                            annotation = {"category": scope, "type": gttype, "name": name}
                            if gttype not in ["", "typing.Any"]:
                                cat = TypeObject.checkType(gttype)
                                if cat != None:
                                    if classname not in gts[f]:
                                        gts[f][classname] = {}
                                    if funcname not in gts[f][classname]:
                                        gts[f][classname][funcname] = {"annotations": []}
                                    if f not in detailed_gts[cat]:
                                        detailed_gts[cat][f] = {}
                                    if classname not in detailed_gts[cat][f]:
                                        detailed_gts[cat][f][classname] = {}
                                    if funcname not in detailed_gts[cat][f][classname]:
                                        detailed_gts[cat][f][classname][funcname] = {"annotations": []}
                                    detailed_gts[cat][f][classname][funcname]["annotations"].append(annotation)
                                    gts[f][classname][funcname]["annotations"].append(annotation)
                        if func["ret_type"] not in ["", "typing.Any"]:
                            name = funcname
                            scope = "return"
                            gttype = func["ret_type"]
                            annotation = {"category": scope, "type": gttype, "name": name}
                            cat = TypeObject.checkType(gttype)
                            if cat != None:
                                if classname not in gts[f]:
                                    gts[f][classname] = {}
                                if funcname not in gts[f][classname]:
                                    gts[f][classname][funcname] = {"annotations": []}
                                if f not in detailed_gts[cat]:
                                    detailed_gts[cat][f] = {}
                                if classname not in detailed_gts[cat][f]:
                                    detailed_gts[cat][f][classname] = {}
                                if funcname not in detailed_gts[cat][f][classname]:
                                    detailed_gts[cat][f][classname][funcname] = {"annotations": []}
                                detailed_gts[cat][f][classname][funcname]["annotations"].append(annotation)
                                gts[f][classname][funcname]["annotations"].append(annotation)
    
    output_gtfile = os.path.join(outputdir, "GROUNDTRUTH.json") if outputdir != None else "GROUNDTRUTH.json"
    output_detailedgtfile = os.path.join(outputdir, "CLASSIFIED_GROUNDTRUTH.json") if outputdir != None else "CLASSIFIED_GROUNDTRUTH.json"

    with open(output_gtfile, "w", encoding = "utf-8") as of:
        of.write(json.dumps(gts, sort_keys=True, indent=4, separators=(',', ': ')))
    
    with open(output_detailedgtfile, "w", encoding = "utf-8") as of:
        of.write(json.dumps(detailed_gts, sort_keys=True, indent=4, separators=(',', ': ')))

    return output_gtfile, output_detailedgtfile


def collectusertype(arg):
    filerepo = arg[0]
    f = arg[1]
    filepath = os.path.join(filerepo, f) if filerepo != None else f
    projpath =  os.path.join(filerepo, "/".join(f.split("/")[0:3])) if filerepo != None else "/".join(f.split("/")[0:3])
    if not os.path.isfile(filepath):
        logger.error("Cannot find source file {}".format(filepath))
        return f, None
    try:
        source = open(filepath, "r").read()
        root = ast.parse(source)
        usertypeanalyzer = UsertypeFinder(filepath, projpath, True)
        usertypes, subtypes = usertypeanalyzer.invoke(root)
    except FunctionTimedOut as e:
        logger.warning("Timeout! Switch to NOT validate imported types!")
        try:
            source = open(filepath, "r").read()
            root = ast.parse(source)
            usertypeanalyzer = UsertypeFinder(filepath, projpath, False)
            usertypes, subtypes = usertypeanalyzer.invoke(root)
        except FunctionTimedOut as e:
            logger.warning("Timeout! Skipped...")
            return f, None
        except Exception as e:
            logger.warning("User-defined type extraction failed! Reason: {}".format(e))
            traceback.print_exc()
            return f, None
    except Exception as e:
        logger.warning("User-defined type extraction failed! Reason: {}".format(e))
        traceback.print_exc()
        return f, None
    return f, usertypes

def collectUserTypeset(datafile, filerepo = None, cores = 8, outputdir = None):
    with open(datafile, "r", encoding = "utf-8") as df:
        jsondata = json.loads(df.read())
    
    if isinstance(jsondata, dict):
        fs = list(jsondata.keys())
    else:
        fs = jsondata

    items = []
    for i, f in enumerate(fs):
        items.append((filerepo, f, i))
    
    pool = ThreadPool(cores)
    results = pool.map(collectusertype, items)
    pool.close()
    pool.join()

    data = {}


    for i in results:
        if i[1] != None:
            data[i[0]] = i[1]
    
    outputfile = os.path.join(outputdir, "USERTYPES.json") if outputdir != None else "USERTYPES.json"
    with open(outputfile, "w", encoding = "utf-8") as jf:
        jf.write(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))
    return outputfile
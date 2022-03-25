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
        logger.error("Cannot get recommendations from Type4Py.")
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
            if "return_type_p" in func:
                types = []
                for t in func["return_type_p"]:
                    types.append(t[0])
                rec[c["q_name"]][func["q_name"]]["annotations"].append({"category": "return", "name": func["q_name"], "type": types})
                num += 1
            if "variables_p" in func:
                for p in func["variables_p"]:
                    types = []
                    for t in func["variables_p"][p]:
                        types.append(t[0])
                    rec[c["q_name"]][func["q_name"]]["annotations"].append({"category": "local", "name": p, "type": types})
                    num += 1
    rec["global"] = {}
    for func in res["response"]["funcs"]:
        rec["global"][func["q_name"]] = {"annotations": []}
        if "params_p" in func:
            for p in func["params_p"]:
                types = []
                for t in func["params_p"][p]:
                    types.append(t[0])
                rec["global"][func["q_name"]]["annotations"].append({"category": "arg", "name": p, "type": types})
                num += 1
        if "return_type_p" in func:
            types = []
            for t in func["return_type_p"]:
                types.append(t[0])
            rec["global"][func["q_name"]]["annotations"].append({"category": "return", "name": func["q_name"], "type": types})
            num += 1
        if "variables_p" in func:
            for p in func["variables_p"]:
                types = []
                for t in func["variables_p"][p]:
                    types.append(t[0])
                rec["global"][func["q_name"]]["annotations"].append({"category": "local", "name": p, "type": types})
                num += 1

    logger.info("Get {} recommendations from Type4Py.".format(num))
    return rec


def test_multiplefile(gtfile, detailed_gtfile, usertype_file, recfile = None, recmodel = False, topn = 1):
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
    for k in detailed_gts:
        data[k] = {"total": 0, "success": {"arg": 0, "return": 0, "local": 0, "total": 0}, "nores": {"arg": 0, "return": 0, "local": 0, "total": 0}, "similar": {"arg": 0, "return": 0, "local": 0, "total": 0}, "partial": {"arg": 0, "return": 0, "local": 0, "total": 0},  "failed": {"arg": 0, "return": 0, "local": 0, "total": 0}, "acc": 0.0, "recall": 0.0, "similaracc": 0.0, "similarrecall": 0.0, "partialacc": 0.0, "partialrecall": 0.0, "file": 0}
    
    num = 0
    for f in gts:
        num +=1
        logger.info("++++++++++++++++++++++[{}/{}]Infer file {}++++++++++++++++++++++".format(num, len(gts), f))
        res = test_onefile("", f, gts = detailed_gts, usertypes = usertypes, recommendations = recommendations, recmodel = recmodel, topn = topn, simmodel = simmodel)
        if res == None:
            continue
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
                    

    



def test_onefile(gtfile, filename, gts = None, gentg = False, usertypes = None, recommendations = None, recmodel = False, topn = 1, simmodel = None):
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
        return None
    if not os.path.exists("/data/project/ypeng/hityper/" + filename):
        logger.error("File does not exist.")
        return None
    source = open("/data/project/ypeng/hityper/" + filename, "r", encoding='UTF-8').read()
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
        logger.error("Cannot generate TDG for this file. Reason: {}".format(e))
        return None
    results = {}
    str_results = {}
    global_tg.passTypes(debug = False)
    results["global@global"] = global_tg.returntypes()
    str_results["global@global"] = global_tg.dumptypes()
    if gentg == True:
        logger.info("TDG dumped.")
        global_tg.draw(filerepo = "testtgs")
    for tg in global_tg.tgs:
        if tg.name in locations:
            if recommendations != None:
                changed = True
                iters = 0
                while changed and iters < 20:
                    iters += 1
                    tg.passTypes(debug = False)
                    types = tg.findHotTypes()
                    tg.recommendType(types, recommendations, formatUserTypes(usertype), usertype["module"], topn, simmodel = simmodel)
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
    return num
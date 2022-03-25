import argparse
import subprocess
import ast
import os
import json
import traceback
from hityper.tdg_generator import TDGGenerator
from hityper.usertype_finder import UsertypeFinder
from hityper.utils import formatUserTypes, getRecommendations, test_multiplefile
from hityper.config import config
from hityper import logger
from hityper.utils import detectChange, SimModel
import logging
from tqdm import tqdm

logger.name = __name__


def setuplogs(repo):
    fh = logging.FileHandler(repo + '/hityper.log')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s[%(levelname)s][%(filename)s:%(lineno)d] %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    


def findusertype(args):
    if args.repo:
        outputrepo = args.output_directory if args.output_directory else "."
        setuplogs(outputrepo)
        if args.source:
            try:
                source = open(args.source, "r", encoding = "utf-8").read()
                root = ast.parse(source)
                usertypefinder = UsertypeFinder(args.source, args.repo, args.validate)
                usertypes, _ = usertypefinder.run(root)
                with open(outputrepo + "/" + args.source.replace("/", "_").replace(".py", "_USERTYPES.json"), "w", encoding = "utf-8") as of:
                    of.write(json.dumps(usertypes, sort_keys=True, indent=4, separators=(',', ': ')))
                    logger.info("Saved results to {}".format(outputrepo + "/" + args.source.replace("/", "_").replace(".py", "_USERTYPES.json")))
            except Exception as e:
                traceback.print_exc()
                logger.error("Failed to find the user-defined types in file {}, reason: {}".format(args.source, e))
        else:
            files = bytes.decode(subprocess.check_output(["find", args.repo, "-name", "*.py"])).split("\n")
            results = {}
            for f in files:
                if os.path.isfile(f):
                    try:
                        source = open(f, "r", encoding = "utf-8").read()
                        root = ast.parse(source)
                        usertypefinder = UsertypeFinder(f, args.repo, args.validate)
                        usertypes, _ = usertypefinder.run(root)
                        results[f] = usertypes
                    except Exception as e:
                        traceback.print_exc()
                        logger.error("Failed to find the user-defined types in file {}, reason: {}".format(f, e))
            with open(outputrepo + "/" + args.repo.replace("/", "_") + "_USERTYPES.json", "w", encoding = "utf-8") as of:
                of.write(json.dumps(results, sort_keys=True, indent=4, separators=(',', ': ')))
                logger.info("Saved results to {}".format(outputrepo + "/" + args.repo.replace("/", "_") + "_USERTYPES.json"))




def gentdg(args):
    if args.repo:
        if not os.path.isdir(args.repo):
            logger.error("Cannot find directory {}".format(args.repo))
            return 
        outputrepo = args.output_directory if args.output_directory else "."
        setuplogs(outputrepo)
        if args.source:
            if not os.path.isfile(args.source):
                logger.error("Cannot find source file {}".format(args.source))
            try:
                source = open(args.source, "r", encoding = "utf-8").read()
                root = ast.parse(source)
                usertypefinder = UsertypeFinder(args.source, args.repo, True)
                usertypes, _ = usertypefinder.run(root)
                generator = TDGGenerator(args.source, args.optimize, args.location, usertypes, alias = 1 if args.alias_analysis else 0, repo = args.repo if args.call_analysis else None)
                global_tg = generator.run(root)
                if args.output_format == "json":
                    with open(outputrepo + "/" + args.source.replace("/", "_").replace(".py", "_TDG.json"), "w", encoding = "utf-8") as of:
                        of.write(json.dumps(global_tg.dump(), sort_keys=True, indent=4, separators=(',', ': ')))
                        logger.info("Saved TDGs to {}".format(outputrepo + "/" + args.source.replace("/", "_").replace(".py", "_TDG.json")))
                else:
                    for tg in global_tg.tgs:
                        tg.draw(filerepo = outputrepo)
                    global_tg.draw(filerepo = outputrepo)
                    logger.info("Saved TDGs to {}".format(outputrepo))
            except Exception as e:
                traceback.print_exc()
                logger.error("Failed to generate TDG for file {}, reason: {}".format(args.source, e))
        if not args.source:
            files = bytes.decode(subprocess.check_output(["find", args.repo, "-name", "*.py"])).split("\n")
            for f in tqdm(files):
                if os.path.isfile(f):
                    try:
                        source = open(f, "r", encoding = "utf-8").read()
                        root = ast.parse(source)
                        usertypefinder = UsertypeFinder(f, args.repo, True)
                        usertypes, _ = usertypefinder.run(root)
                        generator = TDGGenerator(f, args.optimize, args.location, usertypes, alias = 1 if args.alias_analysis else 0, repo = args.repo if args.call_analysis else None)
                        global_tg = generator.run(root)
                    except Exception as e:
                        traceback.print_exc()
                        logger.error("Failed to generate TDG for file {}, reason: {}".format(f, e))
                    if args.output_format == "json":
                        with open(outputrepo + "/" + f.replace("/", "_").replace(".py", "_TDG.json"), "w", encoding = "utf-8") as of:
                            of.write(json.dumps(global_tg.dump(), sort_keys=True, indent=4, separators=(',', ': ')))
                            logger.info("Saved TDGs to {}".format(outputrepo + "/" + f.replace("/", "_").replace(".py", "_TDG.json")))
                    else:
                        for tg in global_tg.tgs:
                            tg.draw(filerepo = outputrepo)
                        global_tg.draw(filerepo = outputrepo)
                        logger.info("Saved TDGs to {}".format(outputrepo))

        

def infertypes(args):
    if args.repo:
        if not os.path.isdir(args.repo):
            logger.error("Cannot find directory {}".format(args.repo))
            return 
        outputrepo = args.output_directory if args.output_directory else "."
        setuplogs(outputrepo)
        if args.recommendations and os.path.isfile(args.recommendations):
            with open(args.recommendations, "r", encoding = "utf-8") as mf:
                recommendations = json.loads(mf.read())
        else:
            recommendations = None
        if config["simmodel"] != None:
            simmodel = SimModel(config[config["simmodel"]], config["tokenizer"])
        else:
            simmodel = None
        if args.source:
            if not os.path.isfile(args.source):
                logger.error("Cannot find source file {}".format(args.source))
            try:
                source = open(args.source, "r", encoding = "utf-8").read()
                root = ast.parse(source)
                usertypefinder = UsertypeFinder(args.source, args.repo, True)
                usertypes, _ = usertypefinder.run(root)
                generator = TDGGenerator(args.source, True, args.location, usertypes, alias = 0, repo = None)
                global_tg = generator.run(root)
                str_results = {}
                global_tg.passTypes(debug = False)
                str_results["global@global"] = global_tg.dumptypes()
                if recommendations == None and args.type4py:
                    recommendations = getRecommendations(source)
                elif isinstance(recommendations, dict) and f in recommendations:
                            recommendations = recommendations[f]
                for tg in global_tg.tgs:
                    if recommendations != None:
                        changed = True
                        iters = 0
                        while changed and iters < config["max_recommendation_iteration"]:
                            iters += 1
                            tg.passTypes(debug = False)
                            types = tg.findHotTypes()
                            tg.recommendType(types, recommendations, formatUserTypes(usertypes), usertypes["module"], args.topn, simmodel = simmodel)
                            tg.passTypes(debug = False)
                            new_types = tg.findHotTypes()
                            changed = detectChange(types, new_types)
                            tg.simplifyTypes()
                    else:
                        tg.passTypes(debug = False)
                        tg.simplifyTypes()
                    str_results[tg.name] = tg.dumptypes()
                    with open(outputrepo + "/" + args.source.replace("/", "_").replace(".py", "_INFERREDTYPES.json"), "w", encoding = "utf-8") as of:
                        of.write(json.dumps(str_results, sort_keys=True, indent=4, separators=(',', ': ')))
                    logger.info("Saved results to {}".format(outputrepo + "/" + args.source.replace("/", "_").replace(".py", "_INFERREDTYPES.json")))
            except Exception as e:
                traceback.print_exc()
                logger.error("Type inference failed for file {}, reason: {}".format(args.source, e))
        if not args.source:
            files = bytes.decode(subprocess.check_output(["find", args.repo, "-name", "*.py"])).split("\n")
            results = {}
            for f in tqdm(files):
                if os.path.isfile(f):
                    try:
                        source = open(f, "r", encoding = "utf-8").read()
                        root = ast.parse(source)
                        usertypefinder = UsertypeFinder(f, args.repo, True)
                        usertypes, _ = usertypefinder.run(root)
                        generator = TDGGenerator(f, True, args.location, usertypes, alias = 0, repo = None)
                        global_tg = generator.run(root)
                        str_results = {}
                        global_tg.passTypes(debug = False)
                        str_results["global@global"] = global_tg.dumptypes()
                        if recommendations == None and args.type4py:
                            recommendations = getRecommendations(source)
                        elif isinstance(recommendations, dict) and f in recommendations:
                            recommendations = recommendations[f]
                        for tg in global_tg.tgs:
                            if recommendations != None:
                                changed = True
                                iters = 0
                                while changed and iters < config["max_recommendation_iteration"]:
                                    iters += 1
                                    tg.passTypes(debug = False)
                                    types = tg.findHotTypes()
                                    tg.recommendType(types, recommendations, formatUserTypes(usertypes), usertypes["module"], args.topn, simmodel = simmodel)
                                    tg.passTypes(debug = False)
                                    new_types = tg.findHotTypes()
                                    changed = detectChange(types, new_types)
                                    tg.simplifyTypes()
                            else:
                                tg.passTypes(debug = False)
                                tg.simplifyTypes()
                            str_results[tg.name] = tg.dumptypes()
                        results[f] = str_results
                    except Exception as e:
                        traceback.print_exc()
                        logger.error("Type inference failed for file {}, reason: {}".format(f, e))
            with open(outputrepo + "/" + args.repo.replace("/", "_") + "_INFERREDTYPES.json", "w", encoding = "utf-8") as of:
                of.write(json.dumps(results, sort_keys=True, indent=4, separators=(',', ': ')))
            logger.info("Saved results to {}".format(outputrepo + "/" + args.repo.replace("/", "_") + "_INFERREDTYPES.json"))


def evaluate(args):
    setuplogs(".")
    test_multiplefile(args.groundtruth, args.classified_groundtruth, args.usertype, recfile = args.recommendations if args.recommendations else None, recmodel = args.type4py, topn = args.topn)




def main():
    arg_parser = argparse.ArgumentParser()
    sub_parsers = arg_parser.add_subparsers(dest='cmd')

    usertype_parser = sub_parsers.add_parser('findusertype')
    usertype_parser.add_argument('-s', '--source', required = False, type=str, help = "Path to a Python source file")
    usertype_parser.add_argument('-p', '--repo', required = True, type=str, help = "Path to a Python project")
    usertype_parser.add_argument("-v", "--validate", default = True, action="store_true", help = "Validate the imported user-defined types by finding their implementations")
    usertype_parser.add_argument('-d', "--output_directory", required = False, type=str, help = "Path to the store the usertypes")
    usertype_parser.set_defaults(func = findusertype)

    tdg_parser = sub_parsers.add_parser('gentdg')
    tdg_parser.add_argument('-s', '--source', required = False, type=str, help = "Path to a Python source file")
    tdg_parser.add_argument('-p', '--repo', required = True, type=str, help = "Path to a Python project")
    tdg_parser.add_argument('-o', '--optimize', default = False, action="store_true", help = "Remove redundant nodes in TDG")
    tdg_parser.add_argument('-l', '--location', required = False, type=str, help = "Generate TDG for a specific function")
    tdg_parser.add_argument('-a', '--alias_analysis', default = False, action="store_true",  help = "Generate alias graphs along with TDG")
    tdg_parser.add_argument('-c', '--call_analysis', default = False, action="store_true",  help = "Generate call graphs along with TDG")
    tdg_parser.add_argument('-d', "--output_directory", required = False, type=str, help = "Path to the generated TDGs")
    tdg_parser.add_argument('-f', "--output_format", default = "json", choices=["json", "pdf"], type=str, help = "Formats of output TDGs")
    tdg_parser.set_defaults(func = gentdg)


    inference_parser = sub_parsers.add_parser('infer')
    inference_parser.add_argument('-s', '--source', required = False, type=str, help = "Path to a Python source file")
    inference_parser.add_argument('-p', '--repo', required = True, type=str, help = "Path to a Python project")
    inference_parser.add_argument('-l', '--location', required = False, type=str, help = "Type inference for a specific function")
    inference_parser.add_argument('-d', "--output_directory", required = False, type=str, help = "Path to the generated TDGs")
    inference_parser.add_argument('-m', "--recommendations", required = False, type=str, help = "Path to the recommendations generated by a DL model")
    inference_parser.add_argument('-t', "--type4py", default = False, action="store_true", help = "Use Type4Py as the recommendation model")
    inference_parser.add_argument('-n', "--topn", default = 1, type = int, help = "Indicate the top n predictions from DL models used by HiTyper")
    inference_parser.set_defaults(func = infertypes)


    eval_parser = sub_parsers.add_parser('eval')
    eval_parser.add_argument('-g', '--groundtruth', required = True, type=str, help = "Path to a ground truth dataset")
    eval_parser.add_argument('-c', '--classified_groundtruth', required = True, type=str, help = "Path to a classified ground truth dataset")
    eval_parser.add_argument('-u', '--usertype', required = True, type=str, help = "Path to a previously collected user-defined type set")
    eval_parser.add_argument('-m', "--recommendations", required = False, type=str, help = "Path to the recommendations generated by a DL model")
    eval_parser.add_argument('-t', "--type4py", default = False, action="store_true", help = "Use Type4Py as the recommendation model")
    eval_parser.add_argument('-n', "--topn", default = 1, type = int, help = "Indicate the top n predictions from DL models used by HiTyper")
    eval_parser.set_defaults(func = evaluate)


    args = arg_parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()







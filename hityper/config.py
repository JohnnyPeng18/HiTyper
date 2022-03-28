

config = {

    #Indicate the web API that HiTyper should call to invoke the DL model
    "type4py": "https://type4py.com/api/predict?tc=0",

    #Indicate the default DL model used in HiTyper
    "default_model": "type4py",

    #Indicate the maximum iterations that HiTyper iterates the whole TDG to conduct static inference
    "max_tdg_iteration": 100,

    #Indicate the maximum iterations that HiTyper asks the DL model for recommendations
    "max_recommendation_iteration": 20,

    #Indicate the model used in similarity calculation of type correction, enter None if you want to simply using editing distance
    "simmodel": None,

    #Indicate the path of word2vec model
    "word2vec": "python_w2v.bin",
    "w2v_size": 100,

    #Indicate the path of tokenizer, this can be a huggingface address or a absolute path
    "tokenizer": "microsoft/graphcodebert-base",

    #Indicate the path of stored tokenizer if you use a huggingface address aabove
    "cached_dir": "./transformers"
}

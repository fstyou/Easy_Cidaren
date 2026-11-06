from functools import lru_cache

import spacy

from easy_cidaren.api.courses import use_api_get_prototype
from easy_cidaren.app_logging.config import get_logger
from easy_cidaren.paths import MODEL_DIR

model_path = str(MODEL_DIR)
module = get_logger("word_revert")


@lru_cache(maxsize = 1)
def _load_model( ):
    model = spacy.load(model_path)
    module.info("模型加载成功：%s", model_path)
    return model


def word_revert(word: str) -> str:
    """
    优先使用模型转原型
    :param word: 目标单词
    :return: 原型
    """
    try:
        nlp = _load_model( )
        module.info(f"{word}优先使用模型转原型")
        doc = nlp(word)
        for token in doc:
            if token.lemma_:
                return token.lemma_
        raise ValueError('语言模型未返回单词原型')
    except Exception as e:
        module.error("单词还原失败，使用在线接口：%s", e)
        prototype = use_api_get_prototype(word)
        if isinstance(prototype, str) and prototype:
            return prototype
        raise ValueError(f"无法获取单词原型：{word}") from e

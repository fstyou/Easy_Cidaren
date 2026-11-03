from functools import lru_cache

import spacy

from easy_cidaren.api.courses import use_api_get_prototype
from easy_cidaren.app_logging.config import Log
from easy_cidaren.paths import MODEL_DIR

model_path = str(MODEL_DIR)
module = Log("word_revert")


@lru_cache(maxsize = 1)
def _load_model( ):
    model = spacy.load(model_path)
    module.logger.info("模型加载成功：%s", model_path)
    return model


def word_revert(word: str) -> str:
    """
    优先使用模型转原型
    :param word: 目标单词
    :return: 原型
    """
    try:
        nlp = _load_model( )
        module.logger.info(f"{word}优先使用模型转原型")
        doc = nlp(word)
        for token in doc:
            # 单词已是原型，直接返回
            if token.lemma_ == word:
                return word
            # 成功
            return token.lemma_
    except Exception as e:
        module.logger.error("单词还原失败，使用在线接口：%s", e)
        prototype = use_api_get_prototype(word)
        if isinstance(prototype, str) and prototype:
            return prototype
        raise ValueError(f"无法获取单词原型：{word}") from e
    raise ValueError(f"语言模型未返回单词原型：{word}")

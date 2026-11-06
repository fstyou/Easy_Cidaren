"""Application state shared by the UI and its current task worker."""

import json
from dataclasses import replace

from easy_cidaren import __version__
from easy_cidaren.app_logging.config import get_logger
from easy_cidaren.core.settings import Settings
from easy_cidaren.paths import DATA_DIR, RUNTIME_DIR


class PublicInfo:
    def __init__(self):
        self.settings = Settings.load(RUNTIME_DIR / 'settings.json')
        self.task_list = []
        self.right_count = 0
        self.wrong_count = 0
        self.skip_count = 0
        self.topic_code = ''
        self.word_query_result = {}
        self.word_means = []
        self.exam = {}
        self.word_list = []
        self.word_dict = {}
        try:
            with open(DATA_DIR / 'word_pool.json', encoding = 'utf-8') as stream:
                self.word_dict = json.load(stream)
        except FileNotFoundError:
            pass
        if not isinstance(self.word_dict, dict) or any(
                not isinstance(key, str) or not isinstance(value, str) for key, value in self.word_dict.items( )):
            raise ValueError('词表池必须是中文释义到英文单词的映射')
        self.all_unit = {}
        self.task_id = ''
        self.now_unit = ''
        self.course_id = ''
        self.release_id = ''
        self.get_word_list_result = {}
        self.get_book_words_data = []
        self.is_self_built = False
        get_logger('public_info').info('公共组件初始化成功')
    
    @property
    def version(self) -> str:
        return __version__
    
    def save_settings(self, **changes):
        updated = replace(self.settings, **changes)
        updated.save(RUNTIME_DIR / 'settings.json')
        self.settings = updated

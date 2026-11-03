import json

from easy_cidaren import __version__
from easy_cidaren.app_logging.config import Log
from easy_cidaren.paths import DATA_DIR, RUNTIME_DIR
from easy_cidaren.utils.json_store import write_json


DEFAULT_SETTINGS = {
    'min_time': 1,
    'max_time': 2,
    'spend_min_time': 2,
    'spend_max_time': 10,
    'br_choices': True,
    'accept_encoding': 'gzip, deflate, br',
    'play_music': False,
    'music_path': '',
    'theme': 'system',
    'self_learn_lib': True,
    'self_learn_pool': True,
}


class PublicInfo:
    task_type: str
    task_type_int: int
    
    def __init__(self):
        self.get_word_list_result = {}
        RUNTIME_DIR.mkdir(parents = True, exist_ok = True)
        try:
            with open(RUNTIME_DIR / 'settings.json', 'x', encoding = 'utf-8') as f:
                json.dump(DEFAULT_SETTINGS, f, ensure_ascii = False, indent = 2)
        except FileExistsError:
            pass
        with open(RUNTIME_DIR / 'settings.json', encoding = 'utf-8') as f:
            # 用户配置文件
            user_config = json.load(f)
            self._min_time = user_config['min_time']
            self._max_time = user_config['max_time']
            self._spend_min_time = user_config['spend_min_time']
            self._spend_max_time = user_config['spend_max_time']
            self._br_choices = user_config['br_choices']
            self._headers_accept_encoding = user_config['accept_encoding']
            self._play_music = user_config['play_music']
            self._music_path = user_config['music_path']
            self._theme = user_config.get('theme', 'system')
            # 自学习开关(独立控制两个记忆库的写入; 关闭只停写入, 读取不受影响)
            self._self_learn_lib = user_config['self_learn_lib']
            self._self_learn_pool = user_config['self_learn_pool']
        
        # 任务列表
        self.task_list = ""
        # 答题对错计数(供进度条右侧统计显示)
        self.right_count = 0
        self.wrong_count = 0
        # 跳过计数(无匹配答案跳过未提交的题)
        self.skip_count = 0
        # query_answer
        self._topic_code = ''
        self.word_query_result = ''
        self.word_means = ''
        self.exam = ''
        # all word
        self.word_list = []
        # 中文释义 -> 英文短语映射(用于汉译英术语课程)
        self.word_dict = {}
        # 跨进程加载历史词表(全局词表池, mode 73 兜底跨单元前缀单词)
        try:
            with open(DATA_DIR / 'word_pool.json', encoding = 'utf-8') as f:
                self.word_dict = json.load(f)
        except FileNotFoundError:
            pass
        except (OSError, json.JSONDecodeError) as exc:
            Log("public_info").error("加载词表池失败：%s", exc)
            raise
        # all unit info
        self.all_unit = []
        self.task_id = ''
        self.now_unit = ''
        self.course_id = ''
        # class task
        self.class_task = []
        # 任务类型选择（默认1）
        self._task_choices = 1
        # unit task amount
        self.task_total_count = ''
        self.release_id = ''
        # self_built
        self.get_book_words_data = []
        self.is_self_built = False  # bool
        self.all_unit_name = []
        self.source_option = []
        pub_info = Log("public_info")
        pub_info.logger.info("公共组件初始化成功")
    
    @property
    # only read
    def topic_code(self):
        return self._topic_code
    
    @topic_code.setter
    # only write
    def topic_code(self, value):
        self._topic_code = value
    
    @property
    def task_type_choices(self):
        return self._task_choices
    
    @property
    def min_time(self) -> int:
        return self._min_time
    
    @property
    def max_time(self) -> int:
        return self._max_time
    
    @property
    def spend_min_time(self) -> int:
        return self._spend_min_time
    
    @property
    def spend_max_time(self) -> int:
        return self._spend_max_time
    
    @property
    def accept_encoding(self) -> str:
        return self._headers_accept_encoding
    
    @property
    def br_choices(self) -> bool:
        return self._br_choices
    
    @property
    def play_music(self) -> bool:
        return self._play_music
    
    @property
    def music_path(self) -> str:
        return self._music_path
    
    @property
    def theme(self) -> str:
        return self._theme

    @property
    def version(self) -> str:
        return __version__
    
    @property
    def self_learn_lib(self) -> bool:
        return self._self_learn_lib
    
    @property
    def self_learn_pool(self) -> bool:
        return self._self_learn_pool
    
    @staticmethod
    def _update_config(changes):
        with open(RUNTIME_DIR / 'settings.json', encoding = 'utf-8') as f:
            data = json.load(f)
        data.update(changes)
        write_json(RUNTIME_DIR / 'settings.json', data, indent = 2)
    
    def input_info(self, min_time, max_time, min_time_2, max_time_2, br_choices, accept_encoding, play_music,
                   music_path, theme = 'system'):
        self._update_config({
            'min_time': min_time, 'max_time': max_time,
            'spend_min_time': min_time_2, 'spend_max_time': max_time_2,
            'br_choices': br_choices, 'accept_encoding': accept_encoding,
            'play_music': play_music, 'music_path': music_path, 'theme': theme,
        })
        self._min_time = min_time
        self._max_time = max_time
        self._spend_min_time = min_time_2
        self._spend_max_time = max_time_2
        self._br_choices = br_choices
        self._headers_accept_encoding = accept_encoding
        self._play_music = play_music
        self._music_path = music_path
        self._theme = theme

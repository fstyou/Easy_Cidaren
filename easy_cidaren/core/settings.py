"""Validated application preferences, independent of task and login state."""

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from easy_cidaren.utils.json_store import write_json


@dataclass(frozen = True)
class Settings:
    min_time: int = 1
    max_time: int = 2
    spend_min_time: int = 2
    spend_max_time: int = 10
    br_choices: bool = True
    play_music: bool = True
    music_path: str = ''
    theme: str = 'system'
    self_learn_lib: bool = True
    self_learn_pool: bool = True
    
    def __post_init__(self):
        for name in ('min_time', 'max_time', 'spend_min_time', 'spend_max_time'):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 86400:
                raise ValueError(f'设置 {name} 必须是 0 至 86400 之间的整数')
        if self.min_time > self.max_time or self.spend_min_time > self.spend_max_time:
            raise ValueError('最长时间不能短于最短时间')
        for name in ('br_choices', 'play_music', 'self_learn_lib', 'self_learn_pool'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f'设置 {name} 必须是布尔值')
        if not isinstance(self.music_path, str):
            raise ValueError('提示音路径必须是字符串')
        if self.theme not in ('system', 'light', 'dark'):
            raise ValueError('外观必须是 system、light 或 dark')
    
    @property
    def accept_encoding(self) -> str:
        return 'gzip, deflate, br' if self.br_choices else 'gzip, deflate'
    
    @classmethod
    def load(cls, path: Path):
        try:
            with path.open(encoding = 'utf-8') as stream:
                data = json.load(stream)
        except FileNotFoundError:
            return cls( )
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f'无法读取设置文件：{path}') from exc
        if not isinstance(data, dict):
            raise ValueError(f'设置文件必须包含 JSON 对象：{path}')
        return cls(**{field.name: data[field.name] for field in fields(cls) if field.name in data})
    
    def save(self, path: Path):
        path.parent.mkdir(parents = True, exist_ok = True)
        write_json(path, asdict(self), indent = 2)

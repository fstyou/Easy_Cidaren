"""Rules for selecting tasks returned by the service."""

from datetime import datetime

from easy_cidaren.api.tasks import get_class_task
from easy_cidaren.app_logging.config import Log

basic_util = Log("task_selection")


def load_class_tasks(public_info):
    public_info.class_task = []
    public_info.task_list = []
    page = 1
    get_class_task(public_info, page)
    while public_info.task_total_count > page * 10:
        page += 1
        get_class_task(public_info, page)
    get_all_task(public_info)
    return public_info.task_list


def task_times(task):
    """Format start and deadline using millisecond timestamps and duration."""
    start = task.get('start_time')
    duration = task.get('over_time')
    
    def format_time(value: int | float | None) -> str:
        try:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                return '—'
            return datetime.fromtimestamp(value / 1000).strftime('%Y-%m-%d %H:%M')
        except (OverflowError, OSError, ValueError):
            return '—'
    
    deadline = (start + duration if isinstance(start, (int, float)) and not isinstance(start, bool)
                                    and isinstance(duration, (int, float)) and not isinstance(duration, bool)
                                    and start > 0 and duration > 0 else None)
    return format_time(start), format_time(deadline)


def unavailable_reason(task):
    if task.get('over_status') == 1:
        return '任务尚未开始，请在开始时间后再试'
    if task.get('progress', 0) >= 100:
        return '已完成的任务不能重新执行'
    return None


def batch_tasks(tasks):
    return [task for task in tasks if not unavailable_reason(task)]


def get_all_task(public_info):
    """
    获取全部任务（包括已完成），排除已过期
    :param public_info: 公共组件
    """
    all_task_list = []
    for tasks in public_info.class_task:
        for task in tasks['records']:
            # over_status 1 未开始 2 未过期 3 已过期
            if task['over_status'] != 3:
                # 1为班级学习任务，2为班级测试任务
                choice = public_info.task_type_choices
                if task['task_type'] == choice:
                    all_task_list.append(task)
    basic_util.logger.debug('任务数据：%s', all_task_list, extra = {'file_only': True})
    basic_util.logger.info('获取到 %s 个任务', len(all_task_list))
    public_info.task_list = all_task_list

"""Rules for selecting tasks returned by the service."""

from datetime import datetime

from easy_cidaren.api.tasks import get_class_task
from easy_cidaren.app_logging.config import get_logger

basic_util = get_logger("task_selection")


def load_class_tasks(task_type: int, *, cancelled = lambda: False):
    """Load a complete filtered list; partial pages never become visible to the UI."""
    tasks = []
    page = 1
    while not cancelled( ):
        result = get_class_task(page)
        if cancelled( ):
            return []
        tasks.extend(task for task in result['records']
                     if task['over_status'] != 3 and task['task_type'] == task_type)
        if result['total'] <= page * 10:
            break
        if not result['records']:
            raise ValueError('任务列表分页数据不完整')
        page += 1
    if cancelled( ):
        return []
    basic_util.debug('任务数据：%s', tasks, extra = {'file_only': True})
    basic_util.info('获取到 %s 个任务', len(tasks))
    return tasks


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
    if task.get('over_status') == 3:
        return '任务已过期，无法执行'
    if task.get('over_status') == 1:
        return '任务尚未开始，请在开始时间后再试'
    return None


def batch_tasks(tasks):
    return [task for task in tasks if not unavailable_reason(task) and task.get('progress', 0) < 100]

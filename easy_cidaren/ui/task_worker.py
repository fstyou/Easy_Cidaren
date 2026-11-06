"""Background execution of learning and test tasks."""
import random
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal

from easy_cidaren.api.courses import get_all_unit, get_unit_words, get_book_all_words
from easy_cidaren.api.response import SecurityVerifyError, UnsafeRequestError, WordSelectionRequiredError
from easy_cidaren.api.tasks import get_exam, select_all_word, skip_exam
from easy_cidaren.app_logging.config import get_logger
from easy_cidaren.core.answers import answer, jump_read, submit
from easy_cidaren.core.question_runner import QuestionSkipError, run_questions
from easy_cidaren.core.word_list import extract_book_word, handle_word_result, needs_word_selection, query_word_unit
from easy_cidaren.ui.task_progress import TaskProgress


class TaskWorker(QThread):
    task_finished = pyqtSignal(str)
    task_error = pyqtSignal(str)
    task_progress = pyqtSignal(object)
    task_notice = pyqtSignal(str)  # 重试/跳过等提示
    batch_finished = pyqtSignal(str)  # 批量模式全部执行结束
    
    def __init__(self, public_info, task_infos, batch_mode = False):
        super( ).__init__( )
        self.public_info = public_info
        self.logger = get_logger("task_worker")
        self.task_infos = task_infos
        self.batch_mode = batch_mode
        self._is_running = True
        self._stop_event = threading.Event( )
        self.current_task_name = ''
        self.current_index = 0
        self.current_total = 0
    
    def run(self):
        total = len(self.task_infos)
        success_count = 0
        failed_tasks = []
        for index, task_info in enumerate(self.task_infos, start = 1):
            if not self._is_running:
                break
            task_name = task_info['task_name']
            self.current_task_name = task_name
            self.current_index = index
            self.current_total = total
            self.logger.info(f"开始执行任务[{index}/{total}]：{task_name}")
            attempts = 0
            while self._is_running:
                attempts += 1
                try:
                    start_time = time.monotonic( )
                    self.complete_test(task_info)
                    if self._is_running:
                        elapsed_time = time.monotonic( ) - start_time
                        message = f"[{index}/{total}] {task_name} 已完成，用时 {elapsed_time:.2f} 秒"
                        success_count += 1
                        self.task_finished.emit(message)
                    break
                except SecurityVerifyError as e:
                    if not self._is_running:
                        return
                    # 服务端风控(11003): 重试无意义(2秒内不可能解除验证), 立即停止当前任务
                    self.logger.error(f"任务 {task_name} 需安全验证: {e}")
                    if self.batch_mode:
                        failed_tasks.append(task_name)
                        self.task_notice.emit(
                                f"[{index}/{total}] 任务 {task_name} 需安全验证已跳过：{e}，请完成验证后重试")
                    else:
                        self.task_error.emit(f"任务 {task_name} 需安全验证：{e}")
                        return
                    break
                except UnsafeRequestError as e:
                    if not self._is_running:
                        return
                    self.logger.error("任务 %s 无法继续: %s", task_name, e)
                    self.task_error.emit(f"任务 {task_name} 无法继续：{e}")
                    return
                except (QuestionSkipError, WordSelectionRequiredError) as e:
                    if not self._is_running:
                        return
                    self.logger.error("任务 %s 无法继续: %s", task_name, e)
                    if self.batch_mode:
                        failed_tasks.append(task_name)
                        self.task_notice.emit(f"[{index}/{total}] 任务 {task_name} 无法继续：{e}")
                        break
                    self.task_error.emit(f"任务 {task_name} 无法继续：{e}")
                    return
                except Exception as e:
                    if not self._is_running:
                        return
                    self.logger.error(f"任务 {task_name} 执行出错（第{attempts}次）: {e}", exc_info = True)
                    if attempts >= 3:
                        if self.batch_mode:
                            failed_tasks.append(task_name)
                            self.task_notice.emit(f"[{index}/{total}] 任务 {task_name} 连续失败3次，已跳过，继续下一个")
                        else:
                            self.task_error.emit(f"任务 {task_name} 连续失败3次：{e}")
                            return
                        break
                    if not self._is_running:
                        break
                    self.task_notice.emit(f"[{index}/{total}] 任务 {task_name} 第{attempts}次出错：{e}，2秒后自动重试")
                    self._stop_event.wait(2)
        
        if self._is_running and self.batch_mode:
            summary = f"一键刷题完成：成功 {success_count} 个，失败 {len(failed_tasks)} 个"
            if failed_tasks:
                summary += f"\n失败任务：{', '.join(failed_tasks)}"
            self.batch_finished.emit(summary)
    
    def stop(self):
        self._is_running = False
        self._stop_event.set( )
    
    def complete_test(self, task_info: dict):
        self.public_info.is_self_built = False
        self.public_info.get_book_words_data = []
        self.public_info.word_list = []
        self.public_info.now_unit = ''
        task_name = task_info['task_name']
        self.public_info.course_id = task_info['course_id']
        self.logger.info(f'开始执行任务：{task_name}')
        self.logger.debug('用课程course_id获取单元list_id')
        self.logger.debug('获取该课程的所有单元')
        get_all_unit(self.public_info)
        if not self._is_running:
            return
        self.public_info.release_id = task_info['release_id']
        matching_units = []
        for unit in self.public_info.all_unit['task_list']:
            if not self._is_running:
                return
            if unit['task_name'] == task_name:
                matching_units.append(unit)
        if len(matching_units) > 1:
            matching_ids = [unit for unit in matching_units if unit['task_id'] == task_info['task_id']]
            if len(matching_ids) != 1:
                raise QuestionSkipError('存在多个同名课程单元，无法确定目标任务')
            matching_units = matching_ids
        unit_progress = task_info['progress']
        if not matching_units:
            self.public_info.is_self_built = True
            self.public_info.task_id = task_info['task_id']
            self.logger.info(f"{task_name}为自建任务")
            if task_info['task_type'] == 1:
                self.logger.debug("完成学习任务的自建任务")
                self.logger.debug('获取该自建任务的单词')
                get_unit_words(self.public_info)
                if not self._is_running:
                    return
                self.logger.debug("获取提交单词")
                selection = query_word_unit(self.public_info)
                self.logger.debug("单词列表：%s", selection, extra = {'file_only': True})
                if needs_word_selection(unit_progress, self.public_info.get_word_list_result):
                    select_all_word(selection, self.public_info.task_id)
            else:
                self.logger.debug("开始测试任务的自建任务")
            if not self._is_running:
                return
            get_book_all_words(self.public_info)
            if not self._is_running:
                return
            extract_book_word(self.public_info)
            self.class_task_answer( )
        else:
            unit = matching_units[0]
            self.public_info.now_unit = unit['list_id']
            self.public_info.task_id = unit['task_id']
            if task_info['task_type'] == 1:
                self.logger.info(f'开始班级学习任务{self.public_info.now_unit}')
                self.complete_practice(self.public_info.now_unit, unit_progress, task_info['task_id'])
            else:
                self.logger.info(f'开始班级测试任务{self.public_info.now_unit}')
                get_unit_words(self.public_info)
                handle_word_result(self.public_info)
                self.logger.debug("单元单词：%s", self.public_info.word_list, extra = {'file_only': True})
                self.public_info.task_id = task_info['task_id']
                self.class_task_answer( )
    
    def emit_progress(self):
        """
        发送答题进度
        :return:
        """
        if isinstance(self.public_info.exam, dict):
            done = self.public_info.exam.get('topic_done_num', 0)
            total = self.public_info.exam.get('topic_total', 0)
            if total:
                self.task_progress.emit(TaskProgress(
                        done, total, self.public_info.right_count, self.public_info.wrong_count,
                        self.public_info.skip_count, self.current_index, self.current_total, self.current_task_name))
    
    def class_task_answer(self):
        if not self._is_running:
            return
        # 确保单元词表已加载(汉译英术语题依赖词表的 word_zh)
        if not self.public_info.word_list:
            get_unit_words(self.public_info)
            handle_word_result(self.public_info)
        self.start_answering( )
    
    def start_answering(self):
        if not self._is_running:
            return
        get_exam(self.public_info)
        if self.public_info.exam == 'complete':
            self.logger.info('该任务已完成，无法重复作答')
            return
        self.emit_progress( )
        self.logger.info("开始答题")
        self.answer_questions( )
    
    def answer_questions(self):
        run_questions(
                self.public_info, running = lambda: self._is_running, answer = answer,
                submit = lambda info, option: submit(info, option, running = lambda: self._is_running,
                                                     wait = self._stop_event.wait),
                read = lambda info: jump_read(info, running = lambda: self._is_running, wait = self._stop_event.wait),
                skip = skip_exam, progress = self.emit_progress,
                notice = self.task_notice.emit, logger = self.logger,
                fatal_errors = (SecurityVerifyError, UnsafeRequestError, WordSelectionRequiredError),
                delay = lambda: self._stop_event.wait(
                        random.randint(self.public_info.settings.min_time, self.public_info.settings.max_time)),
        )
    
    def complete_practice(self, unit: str, progress: int, task_id = None):
        self.logger.info(f"获取该{unit}单元的单词")
        self.public_info.now_unit = unit
        self.public_info.task_id = task_id
        get_unit_words(self.public_info)
        if not self._is_running:
            return
        self.logger.debug("处理words")
        handle_word_result(self.public_info)
        self.logger.debug("选择该单元所有单词")
        if needs_word_selection(progress, self.public_info.get_word_list_result):
            select_all_word({f"{self.public_info.course_id}:{unit}": self.public_info.word_list},
                            self.public_info.task_id)
        self.start_answering( )

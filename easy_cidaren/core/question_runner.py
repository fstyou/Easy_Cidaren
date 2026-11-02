"""Process questions independently so one malformed question need not end a task."""


class QuestionSkipError(Exception):
    """The server could not safely advance past the current question."""


def run_questions(info, *, running, answer, submit, read, skip, progress,
                  notice, logger, security_error, delay):
    while running( ) and info.exam != 'complete':
        exam = info.exam
        try:
            if not isinstance(exam, dict) or not exam.get('topic_code'):
                raise QuestionSkipError('当前题目缺少有效的题目编号，无法安全跳过')
            info.topic_code = exam['topic_code']
            mode = exam['topic_mode']
            logger.debug('处理题目：类型=%s，进度=%s/%s', mode,
                         exam.get('topic_done_num', '?'), exam.get('topic_total', '?'))
            if mode == 0:
                read(info)
            else:
                option = answer(info, mode)
                if option is None:
                    raise ValueError('未能找到可提交的答案')
                submit(info, option)
        except (security_error, QuestionSkipError):
            raise
        except Exception as exc:
            logger.exception('【题目异常】题型 %s 处理失败，尝试跳过',
                             exam.get('topic_mode', '?') if isinstance(exam, dict) else '?')
            if info.exam == 'complete' or (
                    isinstance(info.exam, dict) and info.exam.get('topic_code') != exam.get('topic_code')):
                notice('⚠ 当前题目处理异常，但服务端已进入下一题，继续执行')
                progress( )
                continue
            if not running( ):
                return
            try:
                # Keep the latest topic_code: a partial submission may have updated it.
                skip(info)
                if isinstance(info.exam, dict) and info.exam.get('topic_code') == exam.get('topic_code'):
                    raise QuestionSkipError('跳过后服务端仍返回同一道题')
            except security_error:
                raise
            except Exception as skip_exc:
                logger.exception('【跳过失败】无法继续当前任务')
                raise QuestionSkipError(f'跳过题目失败：{skip_exc}') from skip_exc
            info.skip_count += 1
            logger.warning('【题目已跳过】继续下一题')
            notice(f'⚠ 题目处理失败，已跳过并继续：{type(exc).__name__}：{exc}')
        progress( )
        if running( ) and info.exam != 'complete':
            delay( )

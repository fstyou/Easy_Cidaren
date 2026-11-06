"""Apply answer results and update the local answer library."""

from easy_cidaren.core.answer_library import add_answer, add_word_answer


def record_answer_result(public_info, result):
    if not isinstance(result, dict) or not result.get('topic_code'):
        raise ValueError('答题结果缺少有效的题目编号')
    answer_result = result.get('answer_result')
    # 对错计数(进度条右侧统计)
    if answer_result == 1:
        public_info.right_count += 1
    elif answer_result == 2:
        public_info.wrong_count += 1
    # 记录标准答案到本地答案库(word_zh -> answer_corrects, 仅短语类题型)
    exam = public_info.exam
    if isinstance(exam, dict):
        mode = exam.get('topic_mode')
        stem = exam.get('stem')
        word_zh = stem.get('remark') if isinstance(stem, dict) else None
        corrects = result.get('answer_corrects')
        if public_info.settings.self_learn_lib:
            if mode == 32 and word_zh and corrects:
                # mode 32: answer_corrects 是完整短语, 入短语库
                add_answer(word_zh, corrects)
            elif mode == 73 and word_zh and corrects:
                # mode 73: answer_corrects 是空位单词(非完整短语), 入单词库防污染短语库
                add_word_answer(word_zh, corrects)
            elif mode == 42 and word_zh and isinstance(corrects, list):
                # mode 42: answer_corrects 是选项下标数组, 通过 options 取正确答案单词入库
                options = exam.get('options') or []
                words = []
                for idx in corrects:
                    if type(idx) is int and 0 <= idx < len(options):
                        content = options[idx].get('content') if isinstance(options[idx], dict) else None
                        if content:
                            words.append(content)
                if words:
                    add_word_answer(word_zh, words)
    public_info.topic_code = result['topic_code']

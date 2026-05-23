# instr_rewrite_1.py: 使用 Qwen-2.5-VL-72B-Instruct 模型补充用户指令，基于 app-data-2.json
# 参考 Mobile-Agent-E 项目（如 api.py 中的 API 调用和 Prompt 构建）
# 原因：实现查询功能，提供可运行脚本，便于扩展

import json
import os
import requests
import re  # 新增：用于关键词提取
import logging  # 新增：用于日志
import json_repair  # 新增：假设pip install json-repair
import unicodedata  # 新增：用于语言检测
import datetime  # 新增

import time  # 新增：用于耗时测量

logging.basicConfig(level=logging.DEBUG)  # 设置日志级别

# 默认路径（参考项目布局，可自定义）
APP_DATA_PATH = "D:/Mobile-Agent/MobileAgent-main/MobileAgent-main/app-data/cn-en-app-data-action-str.json"
QWEN_MODEL = "qwen/qwen3-4b:free"  # 指定 Qwen 模型  qwen/qwen3-8b  qwen/qwen-2.5-72b-instruct
API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"  # 使用 OpenRouter 端点

def load_app_data(file_path: str = APP_DATA_PATH) -> dict:
    """读取 app-data-2.json 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"app-data-2.json 未找到于 {file_path}")
    except json.JSONDecodeError:
        raise ValueError("app-data-2.json 格式无效")

def detect_language(text: str) -> str:
    """检测输入语言：如果包含中文，返回'zh'；否则'en'"""
    for char in text:
        if unicodedata.category(char).startswith('Lo') and 'CJK' in unicodedata.name(char, ''):
            return 'zh'
    return 'en'

def build_prompt(user_instruction: str, app_data: dict, action_object_str: str = None) -> str:
    """构建 Prompt，注入 app-data-2.json 内容（核心版：意图驱动 + action_object_str匹配 + 完整操作轨迹）"""

    # 检测语言
    lang = detect_language(user_instruction)
    lang_instruction = "Output in English if the user input is in English, or in Chinese if in Chinese." if lang == 'en' else "如果用户输入是中文，则输出中文；如果是英文，则输出英文。"

    # 核心意图识别系统（基于优质生成结果分析）
    user_lower = user_instruction.lower()

    # 精确的任务意图映射（从优质结果中学习）
    core_intent_mapping = {
        # 记录/保存类意图 -> 笔记app
        'record': {
            'keywords': ['record', 'write', 'save', 'note', '笔记', '记录', '保存',],
            'target_apps': ['备忘录/笔记', '备忘录', '笔记', 'Notes', 'Memo'],
            'action_patterns': ['create note', 'save', 'record', 'write down']  # 简化，与keywords保持一致
        },

        # 搜索/查询类意图 -> 浏览器app/社交媒体app
        'search': {
            'keywords': ['search', 'find', 'look', 'browse', 'query', '查询', '推荐','查找','查看', '浏览', 'check', '咨询', '新闻', '信息','热点'],
            'target_apps': ['Google Chrome', '夸克', 'Chrome', 'X','小红书','知乎' ,'Rednotes',],
            'action_patterns': ['search', 'query', 'find', 'browse', 'check weather', 'recommend', 'view content', 'follow']  # 增加社交媒体相关操作
        },

        # 规划/组织类意图 -> 旅行/规划app
        'plan': {
            'keywords': ['plan', 'schedule', 'organize', 'travel', 'trip', 'journey', '规划', '安排', '旅行', '行程', '日程', 'calendar', '日历'],
            'target_apps': ['Tripadvisor', 'Booking', '携程旅行', '去哪儿旅行', 'Google Maps', '高德地图','大众点评'],
            'action_patterns': ['plan', 'schedule', 'organize', 'book', 'reserve', 'add event','travel']
        },

        # 社交/分享类意图 -> 社交app
        'share': {
            'keywords': ['share', 'send', 'post', 'message', '分享', '发送', '发布', '聊天', '联系', 'communicate','trend','热点','朋友圈'],
            'target_apps': ['微信', 'WeChat', '微博', 'X', 'Facebook', 'Instagram', 'LinkedIn','小红书'],
            'action_patterns': ['share', 'send', 'post', 'message', 'chat', 'search', 'like', 'comment', 'follow']  # 增加社交互动操作
        },

        # 购物/电商类意图 -> 购物app
        'shopping': {
            'keywords': ['buy', 'purchase', 'shop', 'shopping', 'cart', 'order', '挑选','购买', '购物', '电商', '淘宝', '京东', '拼多多', '性价比','亚马逊','eBay','Amazon', '书', '小说', '传记', '书籍'],
            'target_apps': ['淘宝', '京东', '拼多多', 'Amazon', 'eBay', 'Walmart'],
            'action_patterns': ['add to cart', 'purchase', 'buy', 'order', 'checkout', 'search product','view','shopping'],
            'context_rules': {
                'book_search': ['小红书', '知乎'],  # 书籍搜索使用内容社区
                'book_purchase': ['淘宝', '京东']   # 书籍购买使用电商平台
            }
        },

        # 娱乐/媒体类意图 -> 视频/音乐app
        'entertainment': {
            'keywords': ['watch', 'video', 'movie', 'music', 'song', 'play', 'listen', '观看', '视频','讲座', '电影', '音乐', '播放', '娱乐'],
            'target_apps': ['YouTube','网易云音乐', 'QQ音乐','抖音','bilibili'],
            'action_patterns': ['watch video', 'play music', 'stream', 'listen', 'view','watch','listen'],
            'context_rules': {
                'movie_info': ['猫眼', 'Fandango'],     # 电影信息查询
                'music': ['网易云音乐', 'QQ音乐'],       # 音乐播放
                'video': ['哔哩哔哩', 'YouTube'],         # 视频观看
                'live_sport': ['腾讯体育', 'PP体育'],     # 体育直播
                'entertainment': ['抖音', '快手']         # 娱乐内容
            }
        },

        # 工具/实用类意图 -> 系统工具app
        'utility': {
            'keywords': ['translate', '翻译', '计算', '转换', '工具', '设置', 'setting', 'file', '文件'],
            'target_apps': ['闹钟','相册', '天气', '备忘录', '笔记','notes','weather','Google Chorme'],
            'action_patterns': ['translate', 'change setting', 'calculate', 'convert', 'set alarm', 'view photos', 'check weather']  # 增加更多实用工具操作
        },

    }

    # 智能意图识别（支持权重和语境分析）
    def calculate_intent_score(user_text, intent_name, intent_config):
        """计算意图匹配分数"""
        score = 0
        keywords = intent_config['keywords']

        # 精确匹配权重最高
        for kw in keywords:
            if kw in user_text:
                # 长词权重更高（更具体）
                weight = len(kw) / 10  # 单词长度影响权重
                if kw in ['购物车', '购买', '电商', '电影', '视频', '讲座', '查找', '天气', '推荐', '查看', '热点', '歌曲','好友',]:
                    weight *= 1.5  # 特定领域关键词权重提升
                score += weight

        # 考虑语境：检查是否有相关动词或名词组合
        context_indicators = {
            'record': ['记录', '保存', '写', '记'],  # 简化，去除todo和任务（已在keywords中移除）
            'search': ['找', '查', '看', '搜索', '浏览', '推荐', '查找', '咨询', '热点'],  # 增加新关键词匹配
            'plan': ['计划', '安排', '预订', '行程','旅行'],
            'share': ['分享', '发', '发给', '告诉', 'post', '朋友圈','好友','发表'],  # 增加社交平台相关
            'shopping': ['买', '购', '价格', '便宜', '购物车', '电商', '性价比'],  # 增加电商平台相关
            'entertainment': ['看', '听', '播放', '娱乐', '歌曲', '视频', '电影'],  # 增加具体平台和内容类型
            'utility': ['算', '换', '转', '设置', '翻译', '计算', '转换', '工具'],  # 匹配新的keywords
            'communication': ['打', '叫', '联系', '发消息'],  # 保持原有
            'health': ['跑', '运动', '健康', '健身'],  # 保持原有
            'education': ['学', '看书', '课程', '知识']  # 保持原有
        }

        if intent_name in context_indicators:
            for indicator in context_indicators[intent_name]:
                if indicator in user_text:
                    score += 0.5  # 语境匹配加分

        return score

    # 识别用户核心意图（基于权重排序）
    intent_scores = []
    for intent_name, intent_config in core_intent_mapping.items():
        score = calculate_intent_score(user_lower, intent_name, intent_config)
        if score > 0:
            intent_scores.append((score, intent_name, intent_config))

    # 按分数排序，选择前3个最相关的意图
    # 考虑到search意图增加了大量关键词，适当调整选择数量以确保覆盖更多意图类型
    intent_scores.sort(reverse=True, key=lambda x: x[0])
    matched_intents = [(name, config) for score, name, config in intent_scores[:4]]  # 增加到4个以适应更多意图

    # 智能app选择：基于语义相似度和功能匹配
    def intelligent_app_selection(user_text, matched_intents, app_data, lang):
        """基于指令内容和app功能进行智能匹配"""
        # 提取指令中的关键实体和动作
        entities, actions = extract_entities_and_actions(user_text)

        selected_apps = []
        covered_functionality = set()

        # 特殊处理：如果是音乐分享，优先选择音乐app
        is_music_share = 'music' in entities and 'share' in actions
        if is_music_share:
            # 首先尝试从entertainment意图中选择音乐app
            for intent_name, intent_config in matched_intents:
                if intent_name == 'entertainment':
                    best_apps = find_best_apps_for_intent(intent_name, intent_config, entities, actions, app_data, lang, user_text)
                    music_apps = [app for app in best_apps if any(word in app['app_name'].lower() for word in ['音乐', 'music', '网易云', 'qq音乐', 'spotify'])]
                    if music_apps:
                        selected_apps.extend(music_apps[:1])  # 选择最好的音乐app
                        break

        # 然后处理其他意图
        for intent_name, intent_config in matched_intents:
            # 为每个意图找到最佳匹配的app
            best_apps = find_best_apps_for_intent(intent_name, intent_config, entities, actions, app_data, lang, user_text)

            for app_info in best_apps:
                if app_info['app_name'] not in [app['app_name'] for app in selected_apps]:
                    selected_apps.append(app_info)
                    covered_functionality.update(app_info.get('covered_functions', []))

            # 限制app数量，避免过度
            if len(selected_apps) >= 4:
                break

        # 如果没有找到合适的app，使用默认意图配置
        if not selected_apps:
            return matched_intents

        # 重新组织intent配置以反映实际选择的app
        optimized_intents = []
        for app in selected_apps:
            # 为每个选定的app创建对应的intent
            intent_type = app.get('primary_intent', intent_name)
            optimized_config = {
                'target_apps': [app['app_name']],
                'action_patterns': app.get('matched_patterns', []),
                'selected_app_info': app
            }
            optimized_intents.append((intent_type, optimized_config))

        return optimized_intents

    def extract_entities_and_actions(text):
        """从指令中提取关键实体和动作"""
        entities = []
        actions = []

        # 实体识别：产品、内容、服务等
        entity_keywords = {
            'book': ['书', '小说', '传记', '书籍', 'book', 'novel', 'biography', '阅读'],
            'movie': ['电影', 'movie', 'film', 'cinema', '热映', 'show', '影院', '院线', '票房'],
            'music': ['音乐', '歌曲', 'song', 'music', '播放', 'listen', '歌手', '专辑', '网易云', '虾米'],
            'video': ['视频', 'video', '直播', 'live', '赛事', '比赛', 'F1', '足球', '篮球', '比赛', '直播', 'YouTube', 'bilibili'],
            'food': ['餐厅', '美食', 'restaurant', 'food', 'eat', '吃饭', '饭店', '酒店', '菜品'],
            'travel': ['旅行', '景点', 'hotel', 'trip', 'travel', 'destination', '旅游', '度假'],
            'shopping': ['购物', '商品', 'product', 'buy', 'purchase', '商城', '电商'],
            'sport': ['运动', '健身', '跑步', '骑行', '瑜伽', '健身房', 'sport', 'exercise', 'workout']
        }

        # 动作识别：查找、购买、分享等
        action_keywords = {
            'search': ['找', '搜索', '查找', 'find', 'search', 'look'],
            'purchase': ['买', '购买', '加入购物车', 'buy', 'purchase', 'add to cart'],
            'view': ['看', '查看', 'view', 'check', 'see'],
            'share': ['分享', '发送', 'share', 'send'],
            'record': ['记录', '保存', 'record', 'save']
        }

        text_lower = text.lower()
        for entity_type, keywords in entity_keywords.items():
            if any(kw in text_lower for kw in keywords):
                entities.append(entity_type)

        for action_type, keywords in action_keywords.items():
            if any(kw in text_lower for kw in keywords):
                actions.append(action_type)

        return entities, actions

    def find_best_apps_for_intent(intent_name, intent_config, entities, actions, app_data, lang, text_lower):
        """为特定意图找到最佳匹配的app"""
        candidates = []

        # 特殊处理：如果是分享意图且包含音乐实体，额外考虑音乐app
        include_music_apps = (intent_name == 'share' or intent_name == 'entertainment') and 'music' in entities

        for app in app_data:
            if not isinstance(app, dict):
                continue

            app_name = app.get('app_name', '')
            app_functions = app.get('common_functions', [])
            app_actions = app.get('action_object_str', {})
            # 确保app_actions是字典格式，如果是字符串或空值则设为空字典
            if not isinstance(app_actions, dict):
                app_actions = {}

            # 跳过不符合意图的app，除非是音乐分享的特殊情况
            is_target_app = any(target_app.lower() in app_name.lower() for target_app in intent_config['target_apps'])
            is_music_app = include_music_apps and any(word in app_name.lower() for word in ['音乐', 'music', '网易云', 'qq音乐', 'spotify'])

            if not (is_target_app or is_music_app):
                continue

            # 计算匹配分数
            match_score = calculate_app_match_score(
                app_name, app_functions, app_actions,
                intent_name, intent_config, entities, actions, lang, text_lower
            )

            if match_score > 0:
                candidates.append({
                    'app_name': app_name,
                    'match_score': match_score,
                    'functions': app_functions,
                    'action_object_str': app_actions,
                    'primary_intent': intent_name,
                    'matched_patterns': intent_config.get('action_patterns', []),
                    'covered_functions': [intent_name]  # 标识覆盖的功能
                })

        # 按匹配分数排序
        candidates.sort(key=lambda x: x['match_score'], reverse=True)

        # 特殊处理：如果包含音乐实体且有分享动作，优先选择音乐app
        if include_music_apps and actions and 'share' in actions:
            music_apps = [app for app in candidates if any(word in app['app_name'].lower() for word in ['音乐', 'music', '网易云', 'qq音乐', 'spotify'])]
            if music_apps:
                # 将音乐app排在前面
                non_music_apps = [app for app in candidates if app not in music_apps]
                candidates = music_apps + non_music_apps

        return candidates[:2]

    def calculate_app_match_score(app_name, app_functions, app_actions, intent_name, intent_config, entities, actions, lang, text_lower):
        """计算app与指令的匹配分数"""
        score = 0
        app_name_lower = app_name.lower()

        # 1. 意图直接匹配 (40分)
        target_apps = intent_config.get('target_apps', [])
        if any(target_app.lower() in app_name_lower for target_app in target_apps):
            score += 40

        # 2. 功能匹配 (30分)
        action_patterns = intent_config.get('action_patterns', [])
        function_matches = 0
        for func in app_functions:
            func_lower = func.lower()
            for pattern in action_patterns:
                if pattern.lower() in func_lower:
                    function_matches += 1
                    break
        score += min(function_matches * 10, 30)  # 最多30分

        # 3. action_object_str匹配 (20分)
        action_matches = 0
        if isinstance(app_actions, dict):
            for action_key in app_actions.keys():
                action_key_lower = action_key.lower()
                for pattern in action_patterns:
                    if pattern.lower() in action_key_lower:
                        action_matches += 1
                        break
        elif isinstance(app_actions, str) and app_actions:
            # 如果是字符串，检查action_patterns是否在字符串中
            action_str_lower = app_actions.lower()
            for pattern in action_patterns:
                if pattern.lower() in action_str_lower:
                    action_matches += 1
                    break
        score += min(action_matches * 10, 20)  # 最多20分

        # 4. 实体匹配加分 (10分) + 上下文规则应用
        entity_bonus = 0
        context_multiplier = 1.0

        # 应用上下文规则进行精确匹配
        context_rules = intent_config.get('context_rules', {})
        for entity in entities:
            # 书籍相关实体匹配
            if entity == 'book':
                if any(word in app_name_lower for word in ['书店', '阅读', '内容', '社区', '小红书', '知乎']):
                    entity_bonus += 5
                    if 'book_search' in context_rules and any(app in app_name for app in context_rules['book_search']):
                        context_multiplier = 2.0  # 书籍搜索场景加倍权重

            # 电影相关实体匹配
            elif entity == 'movie':
                if any(word in app_name_lower for word in ['电影', '影院', 'cinema', 'movie', '猫眼', 'fandango']):
                    entity_bonus += 5
                    if 'movie_info' in context_rules and any(app in app_name for app in context_rules['movie_info']):
                        context_multiplier = 2.5  # 电影信息查询场景大幅提升权重

            # 音乐相关实体匹配
            elif entity == 'music':
                if any(word in app_name_lower for word in ['音乐', 'music', '网易云', 'qq音乐', 'spotify', 'song', '分享', 'share']):
                    entity_bonus += 5
                    if 'music' in context_rules and any(app in app_name for app in context_rules['music']):
                        context_multiplier = 2.0  # 音乐场景加倍权重
                    # 如果是分享音乐，优先选择音乐app
                    if any(word in text_lower for word in ['分享', '发送', '发给', 'share', 'send']) and entity == 'music':
                        context_multiplier = 3.0  # 音乐分享场景大幅提升权重
                        entity_bonus += 10  # 额外加分

            # 视频相关实体匹配
            elif entity == 'video':
                if any(word in app_name_lower for word in ['视频', 'video', 'youtube', 'bilibili', 'twitch', '赛事', '比赛', 'F1']):
                    entity_bonus += 5
                    if 'video' in context_rules and any(app in app_name for app in context_rules['video']):
                        context_multiplier = 1.8  # 视频观看场景提升权重
                    elif 'live_sport' in context_rules and any(word in text_lower for word in ['F1', '足球', '篮球', '比赛', '赛事']):
                        if any(app in app_name for app in context_rules['live_sport']):
                            context_multiplier = 2.2  # 体育赛事直播大幅提升权重

            # 餐厅相关实体匹配
            elif entity == 'food':
                if any(word in app_name_lower for word in ['餐厅', '美食', 'restaurant', 'food', '点评', '美团']):
                    entity_bonus += 5

            # 旅行相关实体匹配
            elif entity == 'travel':
                if any(word in app_name_lower for word in ['旅行', '地图', 'hotel', 'trip', 'travel', '高德', '百度地图']):
                    entity_bonus += 5

        # 应用上下文乘数
        score = int(score * context_multiplier)
        score += min(entity_bonus, 10)

        return score

    # 应用智能app选择
    if matched_intents:
        matched_intents = intelligent_app_selection(user_lower, matched_intents, app_data, lang)

    # 如果没有匹配到意图，使用通用搜索意图
    if not matched_intents:
        matched_intents = [('search', core_intent_mapping['search'])]

    # 核心app匹配算法（基于意图 + action_object_str优先级）
    if not isinstance(app_data, list):
        filtered_apps = []
    else:
        app_candidates = []

        for app in app_data:
            if not isinstance(app, dict):
                continue

            app_name = app.get('app_name', '')
            app_name_lower = app_name.lower()
            action_object_str = app.get('action_object_str', {})

            # 核心匹配逻辑：基于意图直接匹配目标app
            total_score = 0
            app_matched_intents = []  # 重命名以避免与全局变量冲突

            for intent_name, intent_config in matched_intents:
                # 检查是否是目标app
                target_apps = intent_config['target_apps']
                if any(target_app.lower() in app_name_lower for target_app in target_apps):
                    total_score += 100  # 直接目标app匹配，最高优先级
                    app_matched_intents.append(f"target_{intent_name}")

                # 检查action_object_str是否匹配意图模式
                elif isinstance(action_object_str, dict):
                    for action_key in action_object_str.keys():
                        action_key_lower = action_key.lower()
                        action_patterns = intent_config['action_patterns']
                        if any(pattern in action_key_lower for pattern in action_patterns):
                            total_score += 50  # action_object_str匹配，高优先级
                            app_matched_intents.append(f"action_{intent_name}")
                            break

                # 检查功能列表是否匹配
                common_functions = app.get('common_functions', [])
                for func in common_functions:
                    func_lower = func.lower()
                    action_patterns = intent_config['action_patterns']
                    if any(pattern in func_lower for pattern in action_patterns):
                        total_score += 30  # 功能匹配，中等优先级
                        app_matched_intents.append(f"function_{intent_name}")
                        break

            # 只有匹配上的app才进入候选列表
            if total_score > 0:
                app_candidates.append((total_score, {
                    'app_name': app_name,
                    'brief_introduction': app.get('brief_introduction', ''),
                    'common_functions': app.get('common_functions', []),
                    'action_object_str': action_object_str,  # 完整保留action_object_str
                    'matched_intents': app_matched_intents,
                    'match_score': total_score
                }))

        # 按匹配分数排序
        app_candidates.sort(reverse=True, key=lambda x: x[0])

        # 智能选择app组合（基于任务复杂度分析）
        selected_apps = []

        # 分析任务复杂度：简单任务倾向单app，复杂任务需要多app协作
        task_complexity = len(matched_intents)  # 匹配的意图数量
        user_instruction_length = len(user_instruction.split())  # 指令长度

        # 简单任务：单个意图，短指令 -> 倾向单app
        # 复杂任务：多个意图，长指令 -> 需要多app协作
        is_complex_task = task_complexity > 1 or user_instruction_length > 10

        if not is_complex_task:
            # 简单任务：选择最高分的单个app
            if app_candidates:
                selected_apps = [app_candidates[0][1]]  # 选择最高分app
        else:
            # 复杂任务：多app协作策略
            # 策略1: 为每个意图选择最佳匹配的app
            intent_app_map = {}
            for score, app in app_candidates:
                for matched_intent in app['matched_intents']:
                    intent_key = matched_intent.split('_')[1]  # 提取意图名称
                    if intent_key not in intent_app_map or score > intent_app_map[intent_key][0]:
                        intent_app_map[intent_key] = (score, app)

            # 从intent_app_map中选择app，确保覆盖所有意图
            covered_intents = set()
            for intent_key, (score, app) in intent_app_map.items():
                if app['app_name'] not in [s['app_name'] for s in selected_apps]:
                    selected_apps.append(app)
                    covered_intents.add(intent_key)

                # 限制app数量，避免过度
                if len(selected_apps) >= 4:
                    break

            # 策略2: 如果意图覆盖不全，补充高分app
            if len(selected_apps) < 2 and app_candidates:
                for score, app in app_candidates[:3]:
                    if app['app_name'] not in [s['app_name'] for s in selected_apps]:
                        selected_apps.append(app)
                        if len(selected_apps) >= 3:
                            break

        filtered_apps = selected_apps

    # 如果完全没有匹配，使用基于意图的默认app（支持多语言首选app）
    if not filtered_apps:
        default_app_map = {
            'record': {
                'name': {'zh': ['备忘录/笔记'], 'en': ['Notes', 'Microsoft To Do', 'Todoist']},
                'fallback': ['备忘录/笔记', 'Notes', 'Memo', 'Microsoft To Do']
            },
            'search': {
                'name': {'zh': ['夸克', '小红书', '知乎'], 'en': ['Google Chrome', 'X','Rednotes']},
                'fallback': ['夸克', 'Google Chrome', 'X', '小红书', 'Rednotes']
            },
            'plan': {
                'name': {'zh': ['携程旅行', '大众点评'], 'en': ['Tripadvisor', 'Booking']},
                'fallback': ['Booking', '携程旅行', 'Tripadvisor', 'Google Maps']
            },
            'share': {
                'name': {'zh': ['微信', '微博', '小红书'], 'en': ['X', 'Facebook', 'Instagram']},
                'fallback': ['微信', 'WeChat', '微博', 'X']
            },
            'shopping': {
                'name': {'zh': ['淘宝', '京东', '拼多多'], 'en': ['Amazon', 'eBay','walmart']},
                'fallback': ['淘宝', '京东', '拼多多', 'Amazon','walmart']
            },
            'entertainment': {
                'name': {'zh': ['抖音','哔哩哔哩','网易云音乐'], 'en': ['YouTube', 'Netflix','bilibili']},
                'fallback': ['YouTube', '网易云音乐', '抖音','哔哩哔哩']
            },
            'utility': {
                'name': {'zh': ['闹钟 ', '相册', '天气'], 'en': ['Calculator', 'Weather', 'Google Translate']},
                'fallback': ['闹钟 ', '相册', '天气', 'Calculator', 'Google Translate']
            },
            'communication': {
                'name': {'zh': ['微信'], 'en': ['facebook','WhatsApp', 'Telegram']},
                'fallback': ['微信', 'WeChat', 'facebook','WhatsApp']
            }
        }

        default_apps = []
        for intent_name, intent_config in matched_intents:
            default_config = default_app_map.get(intent_name, default_app_map['search'])

            # 根据指令语言选择首选app列表，支持用户偏好定制
            primary_apps = default_config['name'].get(lang, default_config['name'].get('zh', []))
            if not primary_apps:  # 如果该语言没有配置，使用英文默认
                primary_apps = default_config['name'].get('en', [])

            # 可扩展：根据用户历史行为调整app优先级
            # 例如：如果用户经常使用某个app，可以将其提升到列表首位

            app_found = False
            # 首先尝试匹配首选app（按语言优先级）
            for primary_app in primary_apps:
                for app in app_data:
                    if isinstance(app, dict):
                        app_name = app.get('app_name', '')
                        if app_name == primary_app:
                            default_apps.append({
                                'app_name': app_name,
                                'brief_introduction': app.get('brief_introduction', ''),
                                'common_functions': app.get('common_functions', []),
                                'action_object_str': app.get('action_object_str', {}),
                                'matched_intents': [f"default_{intent_name}"],
                                'match_score': 20
                            })
                            app_found = True
                            break
                if app_found:
                    break

            # 如果没有找到首选app，使用fallback
            if not app_found:
                for app in app_data:
                    if isinstance(app, dict):
                        app_name = app.get('app_name', '')
                        if any(fallback in app_name for fallback in default_config['fallback']):
                            default_apps.append({
                                'app_name': app_name,
                                'brief_introduction': app.get('brief_introduction', ''),
                                'common_functions': app.get('common_functions', []),
                                'action_object_str': app.get('action_object_str', {}),
                                'matched_intents': [f"default_{intent_name}"],
                                'match_score': 20
                            })
                            break

        filtered_apps = default_apps[:3]  # 最多3个默认app

    # 完整app数据注入：确保action_object_str完整保留
    formatted_apps = []
    for app in filtered_apps:
        # 完整保留action_object_str，用于生成具体操作轨迹
        formatted_app = {
            'app_name': app['app_name'],
            'description': app['brief_introduction'],
            'functions': app['common_functions'],
            'action_object_str': app['action_object_str'],  # 完整保留action_object_str
            'matched_intents': app.get('matched_intents', [])
        }
        formatted_apps.append(formatted_app)

    # 优化JSON格式：减少token但保持可读性，确保中文正确显示
    app_data_str = json.dumps(formatted_apps, ensure_ascii=False, separators=(',', ':'))

    # 核心few-shot示例：基于优质生成结果，强调具体app名称和action_object_str操作轨迹
    few_shot = """
示例1 (多app协作 - 信息获取与执行):
用户指令: 帮我找个餐厅推荐并预订座位
app数据: [{"app_name":"大众点评","description":"本地生活服务平台，提供餐厅评价和推荐","functions":["搜索餐厅","查看评价","餐厅推荐"],"action_object_str":{"open dazhongdianping app","tap search box","type restaurant type","tap search","swipe down to view results","tap restaurant detail"}},{"app_name":"美团","description":"生活服务电商平台，支持餐厅预订","functions":["餐厅预订","在线点餐"],"action_object_str":{"open meituan app","tap restaurant tab","tap search icon","type restaurant name","tap restaurant","select time and people","tap book table"}}]
输出: {"level2_instruction": "打开大众点评搜索餐厅并查看评价，再打开美团预订座位", "level3_instruction": "首先打开大众点评app，点击搜索框输入'餐厅推荐'，浏览搜索结果查看餐厅评价和评分，选择合适的餐厅并记录餐厅名称。然后打开美团app，点击餐厅标签，点击搜索图标输入记录的餐厅名称，点击餐厅进入详情页，选择用餐时间和人数，点击'立即预订'按钮完成座位预订。", "referenced_apps": ["大众点评", "美团"], "reason": "大众点评擅长餐厅信息查询和评价查看，美团专注于在线预订服务，这种app功能分工确保用户能获得准确的餐厅信息并顺利完成预订"}

示例3 (跨app协作 - 搜索记录分享):
用户指令: 搜索/查找/浏览餐厅信息并记录下来，然后分享给好友
app数据: [{"app_name":"大众点评","description":"服务类应用","functions":["搜索查询"],"action_object_str":{"open dazhongdianping app","tap the search box ","type the search content","tap the first search'result  ","swipe down to view more results","tap a result to enter the result page"}},{"app_name":"备忘录/笔记","description":"Note-taking app","functions":["创建笔记","分享笔记"],"action_object_str":{"分享笔记":["tap the share button with the arrow at the top","tap the choice 'yitupiangeshifenxiang'","tap the wechat icon","tap the search box","type the friend name","tap the search result","tap 'send' button"]}},{"app_name":"微信","description":"Social messaging app","functions":["发送消息"],"action_object_str":{"open the wechat app ","tap magnifier to search","type the friend name in the search box","tap the search friend","tap the input bar","type the chat message ","tap the  'send'button"}}
输出: {"level2_instruction": "使用大众点评搜索餐厅信息，选择一家餐厅并用备忘录/笔记记录其相关信息，再分享给微信好友", "level3_instruction": "打开大众点评app，点击搜索框输入餐厅查询内容查看结果。然后打开备忘录/笔记app，点击黄圈白色加号创建笔记，输入餐厅信息后点击黑色对勾保存。接着点击顶部的箭头分享按钮，选择'以图片格式分享'，点击微信图标，点击搜索框输入好友姓名，点击搜索结果，点击绿色'发送'按钮完成分享。", "referenced_apps": ["大众点评", "备忘录/笔记", "微信"], "reason": "大众点评用于搜索餐厅信息，备忘录/笔记用于记录和分享，微信用于社交分享"}

示例4 (多app比价 + 迭代引用app):
用户指令: 帮我将一款性价比高的香水加入购物车
app-data-2.json 数据: [{"appname": "小红书", "description": "社交媒体app", "functions": ["笔记搜索"],"action_object_str":{"open xiaohongshu app","tap the search box ","type the search content","tap the first search'result","swipe down to view more notes","tap a note link"}},{"appname": "淘宝", "description": "电商app", "functions": ["商品搜索", "加入购物车"],"action_object_str":{"open taobao app","tap the search box ","type the search content","tap the first search'result  ","swipe down to view more products","tap a product link to enter the product page","tap the 'jia ru gou wu che' button "}}, {"appname": "京东", "description": "电商app", "functions": ["商品搜索", "加入购物车"],"action_object_str":{"open jingdong app","tap the search box ","type the search content","tap the first search'result ","swipe down to view more products","tap a product link to enter ","tap the 'jia ru gou wu che' button"}}, {"appname": "拼多多", "description": "电商app", "functions": ["商品搜索", "加入购物车"],"action_object_str":{"open pinduoduo app","tap the search box","type the search content","tap the first search'result ","swipe down to view more producs","tap a product link to enter the product page","tap the 'jia ru gou wu che' button "}}]
action_object_str: {"action": "search and compare", "object": "perfume", "path": "search in each app > compare prices > add to cart in best app"}
输出: {'level2_instruction': '打开社交/搜索软件搜索'性价比高的香水/商品'，然后在淘宝/京东/拼多多等购物app进行搜索比价并加入购物车', 'level3_instruction': '打开小红书app/google Chorme,搜索'性价比高的香水/商品',找到符合要求的商品后，依次打开淘宝、京东、拼多多app, 点击顶部搜索栏输入“性价比高的香水”并点击搜索, 在结果列表中查看商品详情和价格, 记录多个app的结果信息后找到性价比最高的香水, 然后在对应app中点击加入购物车按钮', 'referenced_apps': ['淘宝', '京东', '拼多多'], 'reason': '先搜索确定性价比商品，然后进行比价，最后加入购物车'}

示例5 (多app通信 + 多action路径):
用户指令: 分享歌曲到微信好友
app-data-2.json 数据: [{"appname": "网易云音乐", "description": "在线音乐app", "functions": ["分享歌曲"], "action_object_str": {"分享歌曲": ["open netease cloud app", "tap search box", "type song name", "tap play button", "tap ellipsis", "tap share", "tap wechat icon", "tap search friend", "type friend name", "tap send"]}}, {"appname": "微信", "description": "社交app", "functions": ["发送消息"],action_object_str":{"open the wechat app ","tap magnifier to search","type friend name ","tap the search result  ","tap the input bar ","type the chat message ","tap 'send'button"}}]
输出: {'level2_instruction': '打开网易云音乐搜索歌曲并分享给微信好友', 'level3_instruction': '打开网易云音乐app, 点击搜索框输入歌曲名称, 点击播放按钮, 点击省略号图标选择分享或直接点击分享按钮, 点击微信图标切换到微信app, 搜索好友名称并发送', 'referenced_apps': ['网易云音乐', '微信'], 'reason': '网易云音乐搜索歌曲，微信用于分享'}

示例6 (信息查询与社交分享):
用户指令: 查找附近的咖啡店并分享给朋友
app数据: [{"app_name":"高德地图","description":"地图导航app，提供地点搜索和导航","functions":["搜索地点","查看详情","路线规划"],"action_object_str":{"open gaode map app","tap search box","type location","tap search","swipe down to view results","tap location detail"}},{"app_name":"微信","description":"社交通讯平台","functions":["发送消息","分享位置"],"action_object_str":{"open wechat app","tap contact","tap friend","tap input box","type message","tap send"}}]
输出: {"level2_instruction": "打开高德地图搜索附近的咖啡店，再打开微信分享给朋友", "level3_instruction": "打开高德地图app，点击搜索框输入'附近的咖啡店'，点击搜索按钮，浏览搜索结果查看咖啡店详情和评价，选择合适的咖啡店并记录店名和地址。然后打开微信app，点击联系人选择朋友，点击输入框输入'发现一家不错的咖啡店：店名，地址是...'，点击发送按钮完成分享。", "referenced_apps": ["高德地图", "微信"], "reason": "高德地图提供精准的地点搜索和详细信息，微信支持快速的社交分享，这种信息获取+社交分享的组合模式适用于各种地点发现和推荐的场景"}

示例7 (多app协作 - 天气记录和旅行规划):
用户指令: Please record the weather in Pittsburgh for the next three days and provide me with a travel plan.
app数据: [{"app_name":"Google Chrome","description":"Web browser for searching and browsing","functions":["网页搜索","信息查询"],"action_object_str":{}},{"app_name":"备忘录/笔记","description":"Note-taking app for recording information","functions":["创建笔记","搜索笔记"],"action_object_str":{"创建笔记":["open beiwanglu/biji app","tap the white plus sign in a yellow circle","type content","tap the icon of black correct symbol"]}},{"app_name":"Tripadvisor","description":"Travel planning and review platform","functions":["搜索地点","查看评价"],"action_object_str":{}}]
输出: {"level2_instruction": "Open Google Chrome to check the weather in Pittsburgh, then use the Notes app to record it, and finally use Tripadvisor to create a travel plan. (Involves browser, utility, and travel apps)", "level3_instruction": "Open the Google Chrome app, tap the search box and type 'weather in Pittsburgh for the next three days' to view the forecast. Then, open the Notes app, tap the white plus sign in a yellow circle to create a new note, and record the weather information, tap the icon of black correct symbol to save. Next, open the Tripadvisor app, tap the search icon, type 'Pittsburgh', and browse through 'Things to Do' and 'Restaurants' to create a travel plan. Finally, switch back to the Notes app to record the travel plan details.", "referenced_apps": ["Google Chrome", "备忘录/笔记", "Tripadvisor"], "reason": "Google Chrome for web search to check weather, Notes app for recording information using its note creation sequence, and Tripadvisor for travel planning based on location search functions"}

"""

    # 如果提供 action_object_str，注入到prompt中
    action_str = f"action_object_str: {action_object_str}\n" if action_object_str else ""

    prompt = (
        f"You are a mobile app instruction expert. Convert user requests into executable app operation sequences using EXACT app names,common_functions and action_object_str from the knowledge base.\n\n"
        f"DECISION PROCESS (follow step-by-step):\n"
        f"1. INTENT ANALYSIS: Identify the primary task and any secondary tasks from user input\n"
        f"2. SEMANTIC APP MATCHING:\n"
        f"   - Extract entities (books, movies, music, food, etc.) and actions (search, buy, share, etc.) from instruction\n"
        f"   - Match apps based on functionality relevance and action_object_str compatibility\n"
        f"   - Score apps by intent matching (40%), function similarity (30%), and action pattern matching (20%)\n"
        f"   - Consider language preference: Chinese apps for Chinese input, English apps for English input\n"
        f"3. WORKFLOW PLANNING: Determine logical app switching sequence based on extracted entities and actions\n"
        f"4. STEP GENERATION: Use matched apps' action_object_str and common_functions to create precise operations\n"
        f"5. VALIDATION: Ensure all referenced apps exist in knowledge base and operations are executable\n\n"
        f"MANDATORY RULES (follow precisely):\n\n"
        f"1. APP NAME RULE:\n"
        f"   - ONLY use app names EXACTLY as they appear in the app data\n"
        f"   - Example: 'Google Chrome', '备忘录/笔记', 'Tripadvisor'\n"
        f"   - NEVER use generic terms like 'browser' or 'notes app'\n"
        f"   - Apps are automatically selected based on semantic matching and functionality\n\n"
        f"2. ACTION SEQUENCE RULE:\n"
        f"   - FIND and ADAPT action_object_str steps for relevant apps\n"
        f"   - CONVERT technical steps into natural mobile UI operations\n"
        f"   - Example: 'tap the white plus sign in a yellow circle' (from action sequence)\n"
        f"   - For apps without action_object_str, use common_functions to infer operations,and use the `similar_function_action_object_str` to infer the operations.\n\n"
        f"3. WORKFLOW RULE:\n"
        f"   - SEQUENCE: Open app → Perform operations → Switch to next app\n"
        f"   - Use 'Then, open [Exact App Name]' for transitions\n"
        f"   - Complete full task workflow from start to finish\n"
        f"   - Handle multi-app collaboration when single app cannot complete task\n\n"
        f"4. DETAIL RULE:\n"
        f"   - Include SPECIFIC UI elements and gestures (tap, swipe, type, etc.),and descriptions of specific function icons and components.\n"
        f"   - Reference actual app functions from knowledge base\n"
        f"   - Make executable on real devices with precise element descriptions\n\n"
        f"5. QUALITY CHECKS:\n"
        f"   - All referenced_apps must exist in the provided knowledge base\n"
        f"   - level3_instruction must contain executable mobile operations\n"
        f"   - Operations must be logical and sequential\n"
        f"   - Avoid ambiguous descriptions like 'click the button'\n\n"
        f"6. LANGUAGE: {lang_instruction}\n\n"
        f"APP KNOWLEDGE BASE (use exact names and action_object_str):\n{app_data_str}\n\n"
        f"{action_str}"
        f"USER INSTRUCTION: {user_instruction}\n\n"
        f"REQUIRED OUTPUT FORMAT (JSON only):\n"
        f"{{\n"
        f"  \"level2_instruction\": \"Brief summary with exact app names\",\n"
        f"  \"level3_instruction\": \"Step-by-step UI operations with app switching\",\n"
        f"  \"referenced_apps\": [\"Exact names from knowledge base\"],\n"
        f"  \"reason\": \"How app functions and action sequences fulfill the task\"\n"
        f"}}\n\n"
        f"PERFECT EXAMPLES (emulate these exactly):\n{few_shot}"
    )
    return prompt

def call_qwen(prompt: str) -> tuple[str, dict]:
    """调用 Qwen API，并返回文本 + usage"""
    api_key = os.getenv("QWEN3_API_KEY") or "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"  # 从环境变量获取，或使用默认（OpenRouter key）
    if not api_key:
        raise ValueError("QWEN_API_KEY 未设置，请在环境变量中设置")

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,  # 增加到4096
        "temperature": 0.0  # 低温度，确保确定性（参考 E 项目）
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"  # 使用 Bearer Token，匹配 OpenAI 兼容端点
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        generated_text = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})  # 提取 usage
        logging.info(f"Token usage: {usage}")
        return generated_text, usage
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Qwen API 请求失败: {e}")
    except (KeyError, IndexError):
        raise ValueError("Qwen API 响应格式无效")

# 更新解析以匹配新输出结构
def rewrite_instruction(user_instruction: str, action_object_str: str = None, save_to_file: str = None,
                        app_data_override: list = None, model_override: str = None) -> dict:  # 修改返回类型为dict
    """主函数：补充用户指令（支持多级和action_object_str）

    app_data_override: 若给定，用它替代 load_app_data() 的全表（OOD 实验用：
        调用方可先从 KB 删去/隐藏目标 app，迫使改写器仅靠其余 app 知识泛化）。
    model_override: 若给定，覆盖全局 QWEN_MODEL（OOD 用 qwen3-8b）。
    """
    global QWEN_MODEL
    start_time = time.time()  # 开始计时
    if model_override:
        QWEN_MODEL = model_override
    app_data = app_data_override if app_data_override is not None else load_app_data()
    prompt = build_prompt(user_instruction, app_data, action_object_str)

    # 新增：验证action_object_str
    if action_object_str:
        try:
            json.loads(action_object_str)
        except json.JSONDecodeError:
            logging.warning("无效action_object_str，回退到None")
            action_object_str = None

    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for attempt in range(3):  # 新增：重试机制，最多3次
        response, usage = call_qwen(prompt)  # 修改为接收 usage
        # 累加 usage
        for key in total_usage:
            total_usage[key] += usage.get(key, 0)

        # 新增：清理markdown/code blocks
        response = response.strip().strip('```json').strip('```').strip()

        # 增强修复：使用json_repair
        try:
            parsed = json_repair.loads(response)
        except Exception as e:
            logging.debug(f"修复失败: {str(e)}")
            logging.debug(f"原始响应: {response}")
            parsed = None

        if parsed and 'level2_instruction' in parsed and 'level3_instruction' in parsed:
            duration = time.time() - start_time  # 计算耗时
            result = {
                "original_instruction": user_instruction,
                "level2_instruction": parsed.get('level2_instruction', ''),
                "level3_instruction": parsed.get('level3_instruction', ''),
                "referenced_apps": parsed.get('referenced_apps', []),
                "reason": parsed.get('reason', ''),
                "model": QWEN_MODEL,  # 添加调用的模型名称
                "token_usage": total_usage,  # 添加
                "duration_seconds": duration  # 添加
            }
            # 新增：日志是否使用了action_object_str
            if action_object_str:
                logging.info("Level 3使用了提供的action_object_str")
            else:
                logging.info("Level 3回退到通用JSON逻辑")
            if save_to_file:
                # 新增：读取现有文件或初始化list, 追加result, 写入
                history = []
                if os.path.exists(save_to_file):
                    with open(save_to_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                        if not isinstance(history, list):
                            history = [history]  # 如果不是list, 转换为list
                    # 新增：为历史item添加id如果缺失
                    for i, item in enumerate(history):
                        if 'id' not in item:
                            item['id'] = i + 1
                        if 'timestamp' not in item:
                            item['timestamp'] = datetime.datetime.now().isoformat()  # 添加时间戳
                # 新增：为新result添加id和timestamp
                result['id'] = len(history) + 1
                result['timestamp'] = datetime.datetime.now().isoformat()
                history.append(result)
                with open(save_to_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=4, ensure_ascii=False)
                logging.info(f"追加到历史并保存到 {save_to_file}")
            return result
        else:
            logging.warning("响应不完整或JSON格式错误: " + response)
            continue  # 重试而不是立即返回

    duration = time.time() - start_time
    return {"error": "所有重试失败", "duration_seconds": duration, "token_usage": total_usage}  # 如果循环结束仍失败

# 示例使用（优化测试）
if __name__ == "__main__":
    # 测试指令：智能app匹配
    user_input = "分享歌曲蝴蝶给zyy"
    #example_action_str = '{"action": ["search", "book"], "object": ["restaurant", "table"], "path": "search restaurant > make reservation", "app": ["review platform", "booking app"]}'
    example_action_str = None

    try:
        print("=== 测试优化后的指令改写 ===")
        print(f"用户指令: {user_input}")
        print(f"Action Object String: {example_action_str}")
        print()

        # 执行一次测试
        result = rewrite_instruction(user_input, example_action_str, save_to_file="output_rewrite_1.json")

        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            print("结果:")
            print(f"  2级指令: {result['level2_instruction']}")
            print(f"  3级指令: {result['level3_instruction']}")
            print(f"  引用app: {result['referenced_apps']}")
            print(f"  理由: {result['reason']}")
            print(f"  模型: {result['model']}")
            print(f"  Token消耗: {result['token_usage']}")
            print(f"  耗时: {result['duration_seconds']:.2f}秒")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

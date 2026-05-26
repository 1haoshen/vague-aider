import json
import jieba
import re  # 引入正则处理
from collections import defaultdict, Counter
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os
import matplotlib

# 配置非交互式后端
matplotlib.use('Agg')  
matplotlib.rcParams['font.sans-serif'] = ['Arial'] # 纯英文环境使用标准字体
matplotlib.rcParams['axes.unicode_minus'] = False

### [场景映射全局字典] ###
EN_SCENARIO_MAP = {
    '视频娱乐': 'Media & Entertainment',
    '办公协作': 'Office Collaboration',
    '出行旅游': 'Travel & Map',
    '电商购物': 'E-commerce',
    '社交媒体': 'Social Media',
    '金融与支付': 'Finance & Payment',
    'AI助手': 'AI Assistant',
    '生活方式': 'Lifestyle',
    '系统app': 'System App',
    '未知': 'Unknown'
}

def load_app_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def extract_functions_and_scenarios(data):
    functions_by_scenario = defaultdict(list)
    all_functions = []
    for app in data:
        scenario = app.get('scenario', '未知')
        common_functions = app.get('common_functions', [])
        if isinstance(common_functions, list):
            for func in common_functions:
                if func and isinstance(func, str):
                    functions_by_scenario[scenario].append(func)
                    all_functions.append((func, scenario))
    return functions_by_scenario, all_functions

def segment_and_clean_functions(functions_list):
    """强化过滤：彻底删除非英文字符及特殊符号，消除空白块"""
    trans_map = {
        '视频': 'Video', '播放': 'Play', '观看': 'Watch', '直播': 'Live', '下载': 'Download',
        '搜索': 'Search', '分享': 'Share', '收藏': 'Favorite', '评论': 'Comment', '点赞': 'Like',
        '订阅': 'Subscribe', '排行': 'Ranking', '好友': 'Friends', '消息': 'Message',
        '音乐': 'Music', '歌曲': 'Song', '编辑': 'Edit', '发送': 'Send', '接收': 'Receive',
        '会议': 'Meeting', '预约': 'Reserve', '任务': 'Task', '笔记': 'Note', '文档': 'Document',
        '支付': 'Pay', '结算': 'Billing', '订单': 'Order', '物流': 'Logistics', '查询': 'Query',
        '图片': 'Image', '照片': 'Photo', '翻译': 'Translate', '景点': 'Scenery', '发布': 'Publish',
        '内容': 'Content', '服务': 'Service', '行程': 'Itinerary', '详情': 'Details', '加入': 'Join',
        '购物车': 'Cart', '查看': 'View', '互动': 'Interaction', '文字': 'Text', '语音': 'Voice',
        '输入': 'Input', '反馈': 'Feedback', '创作': 'Create', '个人': 'Profile', '账户': 'Account',
        '关注': 'Follow', '推荐': 'Suggest', '发现': 'Discover', '扫一扫': 'Scan', '更多': 'More',
        '酒店': 'Hotel', '机票': 'Flight', '导航': 'Navigation', '位置': 'Location', '规划': 'Plan',
        '实时': 'Real-time', '地图': 'Map', '支付结算': 'Billing', '点赞视频': 'Like Video'
    }

    segmented_functions = []
    for func in functions_list:
        func = func.strip()
        if not func: continue
        
        words = jieba.cut(func)
        for word in words:
            # 1. 翻译转换
            english_word = trans_map.get(word, word)
            
            # 2. 核心修正：使用正则表达式只保留英文字母和空格
            # 这会过滤掉所有标点符号（如 ` 、 '）、中文字符和特殊控制符，从而消除空白矩形
            clean_word = re.sub(r'[^a-zA-Z\s\-]', '', english_word).strip()
            
            if len(clean_word) > 1:
                segmented_functions.append(clean_word)
                    
    return segmented_functions

def get_scenario_colors():
    return {
        '视频娱乐': '#5B9BD5', '电商购物': '#6BBE6B', '社交媒体': '#6BC6E0',
        '办公协作': '#8B7BDE', '出行旅游': '#F0AD4E', '金融与支付': '#4A7FB9',
        'AI助手': '#85C944', '生活方式': '#E84E75', '系统app': '#9E9E9E'
    }

def create_color_func(word_freq, scenario_colors, word_scenario_map):
    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        scenario = word_scenario_map.get(word, '未知')
        return scenario_colors.get(scenario, '#CCCCCC')
    return color_func

def create_ellipse_mask(width, height):
    mask = Image.new('L', (width, height), 255)
    draw = ImageDraw.Draw(mask)
    margin = 50
    draw.ellipse((margin, margin, width - margin, height - margin), fill=0)
    return np.array(mask)

def generate_wordcloud(word_freq, scenario_colors, word_scenario_map, output_base_name):
    # 使用 Windows 标准 Arial 字体（或系统默认英文字体）
    font_path = 'C:/Windows/Fonts/arial.ttf' if os.path.exists('C:/Windows/Fonts/arial.ttf') else None
    
    mask = create_ellipse_mask(1600, 1200)

    wc = WordCloud(
        width=1600, height=1200, background_color='white',
        mask=mask, max_words=130, max_font_size=160, min_font_size=15,
        random_state=42, font_path=font_path,
        color_func=create_color_func(word_freq, scenario_colors, word_scenario_map),
        font_step=2, margin=8, scale=1.5, relative_scaling=0.3, prefer_horizontal=0.7
    )

    wc.generate_from_frequencies(word_freq)

    # 保持 figsize 为 (10, 8)
    fig = plt.figure(figsize=(10, 8))

    ax_main = plt.subplot2grid((12, 1), (0, 0), rowspan=10)
    ax_main.imshow(wc, interpolation='bilinear')
    ax_main.axis('off')

    ax_main.set_title('Function Distribution in Mobile GUI Ecosystem',
                      fontsize=22, fontweight='bold', pad=-10)

    ax_legend = plt.subplot2grid((12, 1), (10, 0), rowspan=2)
    ax_legend.axis('off')

    legend_elements = []
    legend_labels = []
    for scenario, color in scenario_colors.items():
        label_en = EN_SCENARIO_MAP.get(scenario, scenario)
        legend_elements.append(plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor='white'))
        legend_labels.append(label_en)

    legend = ax_legend.legend(handles=legend_elements,
                            labels=legend_labels,
                            title='Application Scenarios (Clustered by Functions)',
                            title_fontsize=12, 
                            fontsize=10,
                            frameon=True, fancybox=True,
                            borderpad=0.5, labelspacing=0.5, columnspacing=0.8,
                            ncol=5, loc='upper center')

    legend.get_title().set_fontweight('bold')
    
    plt.subplots_adjust(top=0.95, bottom=0.05, hspace=0.02)

    # 输出 PNG 和 PDF 格式
    for fmt in ['png', 'pdf']:
        save_path = f"{output_base_name}.{fmt}"
        plt.savefig(save_path, dpi=600 if fmt=='png' else None, bbox_inches='tight', facecolor='white')
        print(f"已导出: {save_path}")

def main():
    json_path = '../AppUi.json'
    output_base_name = 'Final_WordCloud_Cleaned'

    try:
        data = load_app_data(json_path)
        _, all_functions = extract_functions_and_scenarios(data)
        
        all_segmented_words = []
        word_scenario_map = {}
        for func, scenario in all_functions:
            words = segment_and_clean_functions([func])
            all_segmented_words.extend(words)
            for word in words:
                if word not in word_scenario_map: 
                    word_scenario_map[word] = scenario

        word_freq = Counter(all_segmented_words)
        scenario_colors = get_scenario_colors()
        
        generate_wordcloud(word_freq, scenario_colors, word_scenario_map, output_base_name)
    except Exception as e:
        print(f"生成失败: {e}")

if __name__ == "__main__":
    main()
# #旧版本只调了figsize（10，8）
# import json
# import jieba
# from collections import defaultdict, Counter
# import numpy as np
# from PIL import Image, ImageDraw
# import matplotlib.pyplot as plt
# from wordcloud import WordCloud
# import os
# from matplotlib.font_manager import FontProperties
# import matplotlib

# # 配置非交互式后端，适合脚本自动化运行
# matplotlib.use('Agg')  
# matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
# matplotlib.rcParams['axes.unicode_minus'] = False

# ### [功能 D：定义中英文场景映射全局字典] ###
# EN_SCENARIO_MAP = {
#     '视频娱乐': 'Media & Entertainment',
#     '办公协作': 'Office Collaboration',
#     '出行旅游': 'Travel & Map',
#     '电商购物': 'E-commerce',
#     '社交媒体': 'Social Media',
#     '金融与支付': 'Finance & Payment',
#     'AI助手': 'AI Assistant',
#     '生活方式': 'Lifestyle',
#     '系统app': 'System App',
#     '未知': 'Unknown'
# }

# def load_app_data(json_path):
#     with open(json_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#     return data

# def extract_functions_and_scenarios(data):
#     functions_by_scenario = defaultdict(list)
#     all_functions = []
#     for app in data:
#         scenario = app.get('scenario', '未知')
#         common_functions = app.get('common_functions', [])
#         if isinstance(common_functions, list):
#             for func in common_functions:
#                 if func and isinstance(func, str):
#                     functions_by_scenario[scenario].append(func)
#                     all_functions.append((func, scenario))
#     return functions_by_scenario, all_functions

# def segment_and_clean_functions(functions_list):
#     """对功能描述进行分词和清洗，保留核心短语"""
#     custom_phrases = [
#         '高清视频', '视频播放', '观看直播', '下载视频', '搜索视频', '分享视频',
#         '收藏视频', '评论视频', '点赞视频', '发送弹幕', '订阅频道', '查看排行',
#         '离线观看', '调整清晰度', '播放列表', '好友分享', '音乐播放', '歌曲分享',
#         '图片编辑', '发送消息', '接收消息', '管理设置', '创建收藏', '删除记录',
#         '同步数据', '备份恢复', '导入导出', '登录注册', '切换账号', '绑定设备',
#         '支付结算', '充值提现', '转账汇款', '查询记录', '提醒通知', '视频通话',
#         '语音聊天', '会议预约', '任务管理', '笔记记录', '文档编辑', '表格制作',
#         '云端存储', '本地同步', '协作办公', '商品购买', '订单管理', '物流查询',
#         '优惠券', '积分兑换', '评价打分', '客服咨询', '退款申请', '发票开具',
#         '机票预订', '酒店预订', '火车票', '汽车票', '路线规划', '实时导航',
#         '打车叫车', '停车缴费', '加油充值', '违章查询', '驾驶证', '行驶证',
#         '银行卡', '信用卡', '余额查询', '交易记录', '转账汇款', '理财投资',
#         '保险购买', '贷款申请', '信用卡还款', '外汇兑换', '基金定投', '股票交易'
#     ]

#     for phrase in custom_phrases:
#         jieba.add_word(phrase)

#     synonym_map = {
#         '查找': '查询', '搜索': '查询', '检索': '查询', '浏览': '查看',
#         '观看': '播放', '收看': '播放', '收听': '播放', '欣赏': '播放',
#         '购物': '购买', '采购': '购买', '选购': '购买', '置办': '购买',
#         '付款': '支付', '结算': '支付', '结账': '支付', '付费': '支付',
#         '预订': '预订', '预约': '预订', '订购': '预订', '订票': '预订',
#         '交流': '聊天', '对话': '聊天', '沟通': '聊天', '交谈': '聊天',
#         '保存': '保存', '存储': '保存', '储存': '保存', '保留': '保存',
#         '编辑': '编辑', '更改': '编辑', '调整': '编辑', '修订': '编辑'
#     }

#     action_filters = {
#         '进行', '使用', '查看', '管理', '设置', '调整', '创建', '删除',
#         '添加', '移除', '同步', '备份', '恢复', '导入', '导出', '登录',
#         '注册', '退出', '切换', '绑定', '解绑', '发送', '接收', '记录',
#         '提醒', '通知'
#     }

#     # 扩展英文翻译映射，确保所有中文词汇都被翻译
#     trans_map = {
#         # 基础功能词
#         '视频': 'Video', '播放': 'Play', '观看': 'Watch', '直播': 'Live', '下载': 'Download',
#         '搜索': 'Search', '分享': 'Share', '收藏': 'Favorite', '评论': 'Comment', '点赞': 'Like',
#         '弹幕': 'Danmaku', '订阅': 'Subscribe', '排行': 'Ranking', '好友': 'Friends', '消息': 'Message',
#         '音乐': 'Music', '歌曲': 'Song', '编辑': 'Edit', '发送': 'Send', '接收': 'Receive',
#         '会议': 'Meeting', '预约': 'Reserve', '任务': 'Task', '笔记': 'Note', '文档': 'Document',
#         '同步': 'Sync', '协作': 'Collab', '商品': 'Product', '订单': 'Order', '物流': 'Logistics',
#         '查询': 'Query', '支付': 'Pay', '结算': 'Billing', '优惠券': 'Coupon', '评价': 'Review',
#         '机票': 'Flight', '酒店': 'Hotel', '火车票': 'Train', '规划': 'Plan', '导航': 'Navigation',
#         '位置': 'Location', '打车': 'Taxi', '停车': 'Parking', '金融': 'Finance', '理财': 'Wealth',
#         '记录': 'Record', '转换': 'Convert', '保存': 'Save', '删除': 'Delete', '设置': 'Setting',

#         # 扩展词汇
#         '高清': 'HD', '离线': 'Offline', '在线': 'Online', '本地': 'Local', '云端': 'Cloud',
#         '备份': 'Backup', '恢复': 'Restore', '导入': 'Import', '导出': 'Export', '登录': 'Login',
#         '注册': 'Register', '切换': 'Switch', '绑定': 'Bind', '解绑': 'Unbind', '提醒': 'Alert',
#         '通知': 'Notification', '通话': 'Call', '聊天': 'Chat', '语音': 'Voice', '视频通话': 'Video Call',
#         '语音聊天': 'Voice Chat', '管理': 'Manage', '创建': 'Create', '添加': 'Add', '移除': 'Remove',
#         '调整': 'Adjust', '修改': 'Modify', '更新': 'Update', '上传': 'Upload', '下载': 'Download',
#         '购买': 'Purchase', '销售': 'Sale', '交易': 'Trade', '兑换': 'Exchange', '充值': 'Top Up',
#         '提现': 'Withdraw', '转账': 'Transfer', '汇款': 'Remittance', '投资': 'Invest', '贷款': 'Loan',
#         '保险': 'Insurance', '信用卡': 'Credit Card', '银行卡': 'Bank Card', '余额': 'Balance',
#         '消费': 'Consume', '收入': 'Income', '支出': 'Expense', '预算': 'Budget', '统计': 'Statistics',

#         # 复合功能短语
#         '高清视频': 'HD Video', '视频播放': 'Video Play', '观看直播': 'Watch Live', '下载视频': 'Download Video',
#         '搜索视频': 'Search Video', '分享视频': 'Share Video', '收藏视频': 'Favorite Video',
#         '评论视频': 'Comment Video', '点赞视频': 'Like Video', '发送弹幕': 'Send Danmaku',
#         '订阅频道': 'Subscribe Channel', '查看排行': 'View Ranking', '离线观看': 'Offline Watch',
#         '调整清晰度': 'Adjust Quality', '播放列表': 'Playlist', '好友分享': 'Friend Share',
#         '音乐播放': 'Music Play', '歌曲分享': 'Song Share', '图片编辑': 'Photo Edit',
#         '发送消息': 'Send Message', '接收消息': 'Receive Message', '管理设置': 'Manage Settings',
#         '创建收藏': 'Create Favorite', '删除记录': 'Delete Record', '同步数据': 'Sync Data',
#         '备份恢复': 'Backup Restore', '导入导出': 'Import Export', '登录注册': 'Login Register',
#         '切换账号': 'Switch Account', '绑定设备': 'Bind Device', '支付结算': 'Payment Billing',
#         '充值提现': 'Top Up Withdraw', '转账汇款': 'Transfer Money', '查询记录': 'Query Record',
#         '提醒通知': 'Reminder Notification', '视频通话': 'Video Call', '语音聊天': 'Voice Chat',
#         '会议预约': 'Meeting Reserve', '任务管理': 'Task Management', '笔记记录': 'Note Record',
#         '文档编辑': 'Document Edit', '表格制作': 'Spreadsheet Create', '云端存储': 'Cloud Storage',
#         '本地同步': 'Local Sync', '协作办公': 'Collaborative Office', '商品购买': 'Product Purchase',
#         '订单管理': 'Order Management', '物流查询': 'Logistics Query', '积分兑换': 'Points Exchange',
#         '评价打分': 'Rating Review', '客服咨询': 'Customer Service', '退款申请': 'Refund Request',
#         '发票开具': 'Invoice Issue', '机票预订': 'Flight Booking', '酒店预订': 'Hotel Booking',
#         '火车票': 'Train Ticket', '汽车票': 'Bus Ticket', '路线规划': 'Route Planning',
#         '实时导航': 'Real-time Navigation', '打车叫车': 'Call Taxi', '停车缴费': 'Parking Payment',
#         '加油充值': 'Fuel Recharge', '违章查询': 'Violation Query', '驾驶证': 'Driver License',
#         '行驶证': 'Vehicle License', '余额查询': 'Balance Query', '交易记录': 'Transaction Record',
#         '理财投资': 'Investment', '保险购买': 'Insurance Purchase', '贷款申请': 'Loan Application',
#         '信用卡还款': 'Credit Card Repayment', '外汇兑换': 'Currency Exchange', '基金定投': 'Fund Fixed Investment',
#         '股票交易': 'Stock Trading'
#     }

#     segmented_functions = []
#     for func in functions_list:
#         func = func.strip()
#         if not func: continue
#         matched_phrases = []
#         for phrase in custom_phrases:
#             if phrase in func:
#                 # 翻译短语为英文，确保所有中文词汇都被翻译
#                 english_phrase = trans_map.get(phrase, f"Function_{phrase}")
#                 matched_phrases.append(english_phrase)
#                 func = func.replace(phrase, '', 1)
#         if matched_phrases: segmented_functions.extend(matched_phrases)
#         if func.strip():
#             words = jieba.cut(func)
#             filtered_words = []
#             for word in words:
#                 word = word.strip()
#                 if not word or len(word) < 2: continue
#                 if word in action_filters: continue
#                 if word in synonym_map: word = synonym_map[word]

#                 # 确保所有词汇都被翻译为英文
#                 if all('\u4e00' <= char <= '\u9fff' for char in word):
#                     # 如果是中文词汇，强制翻译
#                     english_word = trans_map.get(word, f"Func_{word}")
#                     filtered_words.append(english_word)
#                 else:
#                     # 如果已经是英文或其他语言，保留
#                     filtered_words.append(word)
#             segmented_functions.extend(filtered_words)
#     return segmented_functions

# def get_scenario_colors():
#     """为不同scenario定义明亮冷色调与浅色系综合配色方案（微调亮度）"""
#     return {
#         '视频娱乐': '#5B9BD5',  # 柔和蓝色
#         '电商购物': '#6BBE6B',  # 柔和绿色
#         '社交媒体': '#6BC6E0',  # 柔和青色
#         '办公协作': '#8B7BDE',  # 柔和紫蓝
#         '出行旅游': '#F0AD4E',  # 温暖橙色（保持原有）
#         '金融与支付': '#4A7FB9',  # 柔和深蓝
#         'AI助手': '#85C944',   # 柔和橄榄绿
#         '生活方式': '#E84E75',  # 柔和粉红
#         '系统app': '#9E9E9E'    # 中性灰色（保持原有）
#     }
# # def get_scenario_colors():
# #     """采用已优化的 Viridis 配色方案"""
# #     return {
# #         '视频娱乐': '#8E44AD', '办公协作': '#8270D1', '出行旅游': '#5A8FC8',
# #         '电商购物': '#31688E', '社交媒体': '#26828E', '金融与支付': '#1F9D8A',
# #         'AI助手': '#6ECE58', '生活方式': '#FDE725', '系统app': '#8C8C8C'
# #     }

# def create_color_func(word_freq, scenario_colors, word_scenario_map):
#     def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
#         scenario = word_scenario_map.get(word, '未知')
#         return scenario_colors.get(scenario, '#CCCCCC')
#     return color_func

# def create_ellipse_mask(width, height):
#     mask = Image.new('L', (width, height), 255)
#     draw = ImageDraw.Draw(mask)
#     margin = 50
#     draw.ellipse((margin, margin, width - margin, height - margin), fill=0)
#     return np.array(mask)

# def create_font_path_selector():
#     font_weights = {
#         'bold': ['C:/Windows/Fonts/SourceHanSansSC-Bold.otf', 'C:/Windows/Fonts/msyhbd.ttc', 'C:/Windows/Fonts/simhei.ttf'],
#         'regular': ['C:/Windows/Fonts/SourceHanSansSC-Regular.otf', 'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simsun.ttc'],
#         'light': ['C:/Windows/Fonts/SourceHanSansSC-Light.otf', 'C:/Windows/Fonts/msyh.ttc']
#     }
#     available_fonts = {}
#     for weight, paths in font_weights.items():
#         available_fonts[weight] = next((p for p in paths if os.path.exists(p)), None)
#     return available_fonts

# def create_weighted_font_func(available_fonts, word_freq):
#     max_f, min_f = max(word_freq.values() or [1]), min(word_freq.values() or [1])
#     def font_func(word, font_size, position, orientation, **kwargs):
#         freq = word_freq.get(word, min_f)
#         ratio = (freq - min_f) / (max_f - min_f) if max_f > min_f else 0.5
#         if ratio > 0.7: return available_fonts.get('bold')
#         return available_fonts.get('light') if ratio < 0.3 else available_fonts.get('regular')
#     return font_func

# def generate_wordcloud(word_freq, scenario_colors, word_scenario_map, output_base_name):
#     """生成词云图并导出多种矢量格式"""
#     fonts = create_font_path_selector()
#     mask = create_ellipse_mask(1600, 1200)

#     wc = WordCloud(
#         width=1600, height=1200, background_color='white',
#         mask=mask, max_words=150, max_font_size=130, min_font_size=12,  # 再次降低密度到150词
#         random_state=42, color_func=create_color_func(word_freq, scenario_colors, word_scenario_map),
#         font_step=2, margin=10, scale=1.3, relative_scaling=0.25, prefer_horizontal=0.6, mode='RGB'  # 增加边距降低密度
#     )

#     wc.font_path = fonts.get('regular')
#     wc.font_func = create_weighted_font_func(fonts, word_freq)
#     wc.generate_from_frequencies(word_freq)

#     fig = plt.figure(figsize=(10, 8)) # 保持画布尺寸

#     # 词云展示区 - 最大化词云区域，减少空白
#     ax_main = plt.subplot2grid((9, 16), (0, 0), rowspan=6, colspan=16)
#     ax_main.imshow(wc, interpolation='bilinear')
#     ax_main.axis('off')

#     # 紧凑标题设置
#     ax_main.set_title('Function Distribution in Mobile Application Ecosystem',
#                       fontsize=15, fontweight='bold', pad=5)

#     # 图例区 - 最小化图例区域
#     ax_legend = plt.subplot2grid((9, 16), (6, 0), rowspan=3, colspan=16)
#     ax_legend.axis('off')

#     legend_elements = []
#     legend_labels = []

#     for scenario, color in scenario_colors.items():
#         label_en = EN_SCENARIO_MAP.get(scenario, scenario)
#         legend_elements.append(plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor='white', linewidth=1))
#         legend_labels.append(label_en)

#     # 最小化图例间距设置
#     legend = ax_legend.legend(handles=legend_elements,
#                             labels=legend_labels,
#                             title='Application Scenarios (Clustered by Functions)',
#                             title_fontsize=11, # 最小化标题大小
#                             fontsize=9,        # 最小化标签大小
#                             frameon=True, fancybox=True, shadow=False,
#                             borderpad=0.3, labelspacing=0.3, columnspacing=0.8,
#                             ncol=5, loc='center')

#     legend.get_title().set_fontweight('bold')
#     legend.get_frame().set_edgecolor('lightgray')
#     legend.get_frame().set_linewidth(2.0)

#     plt.tight_layout(pad=0.2, h_pad=0.2, w_pad=0.2)

#     # [优化：多格式矢量输出]
#     formats = ['png', 'pdf', 'svg']
#     for fmt in formats:
#         save_path = f"{output_base_name}.{fmt}"
#         # PNG 使用 600 DPI 保证打印精度，矢量图（PDF/SVG）保留路径信息
#         plt.savefig(save_path, dpi=600 if fmt == 'png' else None, 
#                     bbox_inches='tight', facecolor='white')
#         print(f"已导出 {fmt.upper()} 格式: {save_path}")

# def main():
#     json_path = '../AppUi.json' # 确保路径正确
#     output_base_name = 'Academic_WordCloud_Figure'

#     try:
#         data = load_app_data(json_path)
#         _, all_functions = extract_functions_and_scenarios(data)
        
#         all_segmented_words = []
#         word_scenario_map = {}
#         for func, scenario in all_functions:
#             words = segment_and_clean_functions([func])
#             all_segmented_words.extend(words)
#             for word in words:
#                 if word not in word_scenario_map: word_scenario_map[word] = scenario

#         word_freq = Counter(all_segmented_words)
#         scenario_colors = get_scenario_colors()
        
#         generate_wordcloud(word_freq, scenario_colors, word_scenario_map, output_base_name)
#         print("\n论文级图表生成成功！建议优先使用 SVG 或 PDF 插入文档。")
#     except Exception as e:
#         print(f"生成失败: {e}")

# if __name__ == "__main__":
#     main()
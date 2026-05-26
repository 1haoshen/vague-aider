import json
import jieba
from collections import defaultdict, Counter
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os
from matplotlib.font_manager import FontProperties
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

def load_app_data(json_path):
    """加载应用数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def extract_functions_and_scenarios(data):
    """提取common_functions和对应的scenario"""
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
    """对功能描述进行分词和清洗，保留核心短语"""
    # 自定义分词词典，添加核心短语
    custom_phrases = [
        '高清视频', '视频播放', '观看直播', '下载视频', '搜索视频', '分享视频',
        '收藏视频', '评论视频', '点赞视频', '发送弹幕', '订阅频道', '查看排行',
        '离线观看', '调整清晰度', '播放列表', '好友分享', '音乐播放', '歌曲分享',
        '图片编辑', '发送消息', '接收消息', '管理设置', '创建收藏', '删除记录',
        '同步数据', '备份恢复', '导入导出', '登录注册', '切换账号', '绑定设备',
        '支付结算', '充值提现', '转账汇款', '查询记录', '提醒通知', '视频通话',
        '语音聊天', '会议预约', '任务管理', '笔记记录', '文档编辑', '表格制作',
        '云端存储', '本地同步', '协作办公', '商品购买', '订单管理', '物流查询',
        '优惠券', '积分兑换', '评价打分', '客服咨询', '退款申请', '发票开具',
        '机票预订', '酒店预订', '火车票', '汽车票', '路线规划', '实时导航',
        '打车叫车', '停车缴费', '加油充值', '违章查询', '驾驶证', '行驶证',
        '银行卡', '信用卡', '余额查询', '交易记录', '转账汇款', '理财投资',
        '保险购买', '贷款申请', '信用卡还款', '外汇兑换', '基金定投', '股票交易'
    ]

    # 添加自定义短语到jieba词典
    for phrase in custom_phrases:
        jieba.add_word(phrase)

    # 同义词映射
    synonym_map = {
        '查找': '查询', '搜索': '查询', '检索': '查询', '浏览': '查看',
        '观看': '播放', '收看': '播放', '收听': '播放', '欣赏': '播放',
        '购物': '购买', '采购': '购买', '选购': '购买', '置办': '购买',
        '付款': '支付', '结算': '支付', '结账': '支付', '付费': '支付',
        '预订': '预订', '预约': '预订', '订购': '预订', '订票': '预订',
        '交流': '聊天', '对话': '聊天', '沟通': '聊天', '交谈': '聊天',
        '保存': '保存', '存储': '保存', '储存': '保存', '保留': '保存',
        '编辑': '编辑', '更改': '编辑', '调整': '编辑', '修订': '编辑'
    }

    # 低价值动作词过滤
    action_filters = {
        '进行', '使用', '查看', '管理', '设置', '调整', '创建', '删除',
        '添加', '移除', '同步', '备份', '恢复', '导入', '导出', '登录',
        '注册', '退出', '切换', '绑定', '解绑', '发送', '接收', '记录',
        '提醒', '通知', '绑定', '解绑', '退出', '注册', '登录'
    }

    segmented_functions = []

    for func in functions_list:
        # 基本清洗：去除空格和特殊字符
        func = func.strip()
        if not func:
            continue

        # 优先匹配自定义短语
        matched_phrases = []
        for phrase in custom_phrases:
            if phrase in func:
                matched_phrases.append(phrase)
                # 从原文本中移除已匹配的短语，避免重复
                func = func.replace(phrase, '', 1)

        if matched_phrases:
            segmented_functions.extend(matched_phrases)

        # 对剩余文本进行jieba分词
        if func.strip():
            words = jieba.cut(func)

            # 过滤和处理词语
            filtered_words = []
            for word in words:
                word = word.strip()
                if not word or len(word) < 2:
                    continue

                # 过滤低价值动作词
                if word in action_filters:
                    continue

                # 同义词合并
                if word in synonym_map:
                    word = synonym_map[word]

                # 只保留中文词语
                if word.isalpha() and all('\u4e00' <= char <= '\u9fff' for char in word):
                    filtered_words.append(word)

            segmented_functions.extend(filtered_words)

    return segmented_functions

def get_scenario_colors():
    """为不同scenario定义低饱和度的浅色系颜色"""
    return {
        # '视频娱乐': '#F0DDE3',  # 低饱和浅粉红
        # '电商购物': '#E0F5E0',  # 低饱和浅绿色
        # '社交媒体': '#DDE8F2',  # 低饱和浅蓝色
        # '办公协作': '#E8D7E8',  # 低饱和浅紫色
        # '出行旅游': '#F2F0DD',  # 低饱和浅黄色
        # '金融与支付': '#F5E8DD',  # 低饱和浅橙色
        # 'AI助手': '#DDE8F0',   # 低饱和浅天蓝
        # '生活方式': '#F0E3E8',  # 低饱和浅粉色
        # '系统app': '#F2F0E8'    # 低饱和浅米色
        # """为不同scenario定义浅色系颜色"""
        '视频娱乐': '#FFB6C1',  # 浅粉红
        '电商购物': '#98FB98',  # 浅绿色
        '社交媒体': '#87CEEB',  # 浅蓝色
        '办公协作': '#DDA0DD',  # 浅紫色
        '出行旅游': '#F0E68C',  # 浅黄色
        '金融与支付': '#FFE4B5',  # 浅橙色
        'AI助手': '#B0E0E6',   # 浅天蓝
        '生活方式': '#FFC0CB',  # 浅粉色
        '系统app': '#F5DEB3'    # 浅米色
    }

def create_color_func(word_freq, scenario_colors, word_scenario_map):
    """创建颜色函数，根据词所属的scenario分配颜色"""

    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        scenario = word_scenario_map.get(word, '未知')
        color = scenario_colors.get(scenario, '#CCCCCC')  # 默认浅灰色
        return color

    return color_func

def create_ellipse_mask(width, height):
    """创建椭圆形状的遮罩，用于词云生成"""
    # 创建一个椭圆形状的遮罩图像
    mask = Image.new('L', (width, height), 255)  # L模式，255为白色
    draw = ImageDraw.Draw(mask)

    # 椭圆边距，为内容留出空间
    margin = 50  # 减小边距，更充分利用空间

    # 椭圆边界
    ellipse_bbox = (
        margin,  # 左
        margin,  # 上
        width - margin,   # 右
        height - margin   # 下
    )

    # 绘制椭圆
    draw.ellipse(ellipse_bbox, fill=0)  # 0为黑色，词云会在黑色区域绘制

    return np.array(mask)


def create_font_path_selector():
    """创建字体路径选择器，根据词频返回不同字重的字体"""
    font_weights = {
        'bold': [
            'C:/Windows/Fonts/SourceHanSansSC-Bold.otf',
            'C:/Windows/Fonts/msyhbd.ttc',
            'C:/Windows/Fonts/simhei.ttf'
        ],
        'regular': [
            'C:/Windows/Fonts/SourceHanSansSC-Regular.otf',
            'C:/Windows/Fonts/msyh.ttc',
            'C:/Windows/Fonts/simsun.ttc'
        ],
        'light': [
            'C:/Windows/Fonts/SourceHanSansSC-Light.otf',
            'C:/Windows/Fonts/SourceHanSansSC-ExtraLight.otf',
            'C:/Windows/Fonts/msyh.ttc',  # fallback
            'C:/Windows/Fonts/simsun.ttc'
        ]
    }

    # 检查每种字重可用的字体
    available_fonts = {}
    for weight, paths in font_weights.items():
        available_fonts[weight] = None
        for path in paths:
            if os.path.exists(path):
                available_fonts[weight] = path
                break

    return available_fonts

def create_weighted_font_func(available_fonts, word_freq):
    """创建基于词频的字体粗细选择函数"""
    max_freq = max(word_freq.values()) if word_freq else 1
    min_freq = min(word_freq.values()) if word_freq else 1

    def font_func(word, font_size, position, orientation, random_state=None, **kwargs):
        if word not in word_freq:
            return available_fonts.get('regular')

        freq = word_freq[word]
        freq_ratio = (freq - min_freq) / (max_freq - min_freq) if max_freq > min_freq else 0.5

        if freq_ratio > 0.7:  # 高频词使用粗体
            return available_fonts.get('bold', available_fonts.get('regular'))
        elif freq_ratio < 0.3:  # 低频词使用细体
            return available_fonts.get('light', available_fonts.get('regular'))
        else:  # 中频词使用常规体
            return available_fonts.get('regular')

    return font_func

def generate_wordcloud(word_freq, scenario_colors, word_scenario_map, output_path):
    """生成词云图"""

    # 获取可用的字体
    available_fonts = create_font_path_selector()
    print("字体检查结果:")
    for weight, path in available_fonts.items():
        status = f"[OK] {path}" if path else "[未找到]"
        print(f"  {weight}: {status}")

    # 创建椭圆形状遮罩
    mask = create_ellipse_mask(1600, 1200)

    # 创建词云对象，优化参数提高美观性和可读性
    wc = WordCloud(
        width=1600,
        height=1200,
        background_color='white',
        mask=mask,  # 使用椭圆形状遮罩
        max_words=300,  # 适中词数，避免拥挤
        max_font_size=160,  # 合适的最大字体
        min_font_size=12,   # 提高最小字体，确保可读性
        random_state=42,
        colormap=None,  # 不使用默认色图，自己控制颜色
        color_func=create_color_func(word_freq, scenario_colors, word_scenario_map),
        font_step=2,  # 更精细的字体大小步长
        margin=3,  # 增加边距，避免重叠
        scale=1.2,  # 适中的缩放比例
        relative_scaling=0.4,  # 调整相对缩放
        prefer_horizontal=0.6,  # 适当的水平排列偏好
        mode='RGB'  # RGB模式支持更多颜色
    )

    # 设置字体选择函数
    wc.font_path = available_fonts.get('regular')  # 默认字体
    wc.font_func = create_weighted_font_func(available_fonts, word_freq)

    # 生成词云
    wc.generate_from_frequencies(word_freq)

    # 创建图形和子图布局，更紧凑的设计
    fig = plt.figure(figsize=(16, 12))

    # 主词云区域（占据大部分空间）
    ax_main = plt.subplot2grid((12, 16), (0, 0), rowspan=10, colspan=16)
    ax_main.imshow(wc, interpolation='bilinear')
    ax_main.axis('off')
    ax_main.set_title('App UI Function Word Cloud', fontsize=14, fontweight='bold', pad=15)

    # 图例区域 - 紧贴词云底部，减少空白
    ax_legend = plt.subplot2grid((12, 16), (10, 0), rowspan=2, colspan=16)
    ax_legend.axis('off')

    # 创建专业的图例，3列布局
    legend_elements = []
    legend_labels = []

    for scenario, info in scenario_colors.items():
        if isinstance(info, dict):
            color = info['color']
            label = info['label']
        else:
            color = info
            label = scenario

        legend_elements.append(plt.Rectangle((0, 0), 1, 1, facecolor=color,
                                          edgecolor='white', linewidth=1,
                                          label=label))
        legend_labels.append(label)

    # 创建图例，更紧凑的布局
    legend = ax_legend.legend(handles=legend_elements,
                            labels=legend_labels,
                            title='App Scenarios',
                            title_fontsize=12,
                            fontsize=10,
                            frameon=True,
                            fancybox=True,
                            shadow=False,  # 移除阴影，更加简洁
                            borderpad=0.8,
                            labelspacing=1.2,
                            columnspacing=1.5,
                            ncol=3,  # 3列布局
                            loc='upper center')  # 移到上方中心

    # 设置图例样式
    legend.get_title().set_fontweight('bold')
    legend.get_frame().set_edgecolor('lightgray')
    legend.get_frame().set_linewidth(1.5)

    plt.tight_layout()

    # 保存为PNG和PDF两种格式
    png_path = output_path
    pdf_path = output_path.replace('.png', '.pdf')

    plt.savefig(png_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(pdf_path, dpi=300, bbox_inches='tight', facecolor='white')

    print(f"词云图已保存:")
    print(f"  PNG: {png_path}")
    print(f"  PDF: {pdf_path}")

def main():
    # 文件路径
    json_path = '../AppUi.json'
    output_dir = '.'
    output_image = 'app_ui_ellipse_wordcloud.png'

    # 检查思源黑体字体是否存在
    font_paths = [
        'C:/Windows/Fonts/SourceHanSansSC-Regular.otf',
        'C:/Windows/Fonts/SourceHanSansSC-Medium.otf',
        'C:/Windows/Fonts/SourceHanSansSC-Bold.otf',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Linux路径
        '/System/Library/Fonts/PingFang.ttc'  # macOS路径
    ]

    font_path = None
    for path in font_paths:
        if os.path.exists(path):
            font_path = path
            break

    if not font_path:
        print("警告：未找到思源黑体或类似中文字体，将使用默认字体")

    # 1. 加载数据
    print("正在加载应用数据...")
    data = load_app_data(json_path)
    print(f"共加载了 {len(data)} 个应用数据")

    # 2. 提取功能和场景
    print("正在提取功能描述...")
    functions_by_scenario, all_functions = extract_functions_and_scenarios(data)

    # 3. 统计各场景的应用数量
    print("\n各场景应用数量统计:")
    for scenario, functions in functions_by_scenario.items():
        print(f"{scenario}: {len([f for f in data if f.get('scenario') == scenario])} 个应用")

    # 4. 分词和清洗
    print("\n正在进行分词处理...")
    all_segmented_words = []
    word_scenario_map = {}

    for func, scenario in all_functions:
        words = segment_and_clean_functions([func])
        all_segmented_words.extend(words)
        for word in words:
            if word not in word_scenario_map:
                word_scenario_map[word] = scenario

    # 5. 统计词频
    word_freq = Counter(all_segmented_words)
    print(f"共提取到 {len(word_freq)} 个不同词语")
    print("高频词 TOP 20:")
    for word, freq in word_freq.most_common(20):
        print(f"  {word}: {freq} 次")

    # 6. 获取场景颜色映射
    scenario_colors = get_scenario_colors()

    print(f"\n词云配置:")
    print(f"  总词数: {len(word_freq)}")
    print(f"  最大词频: {max(word_freq.values()) if word_freq else 0}")
    print(f"  最小词频: {min(word_freq.values()) if word_freq else 0}")
    print(f"  椭圆布局: [已启用]")
    print(f"  场景分类色彩: [已启用]")
    print(f"  可变字体粗细: [已启用]")
    print(f"  PDF输出: [已启用]")

    # 7. 生成词云
    print("\n正在生成词云图...")
    output_path = os.path.join(output_dir, output_image)
    generate_wordcloud(word_freq, scenario_colors, word_scenario_map, output_path)

    print("词云图生成完成！")
    print(f"输出文件位于: {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    main()

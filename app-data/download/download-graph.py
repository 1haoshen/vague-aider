import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import MaxNLocator
import matplotlib

# 设置中文字体显示
import matplotlib.font_manager as fm

# 定义中英文标签映射
category_labels = {
    '视频娱乐': 'Video Entertainment',
    '办公协作': 'Office Collaboration',
    '出行旅游': 'Travel',
    '电商购物': 'E-commerce',
    '社交媒体': 'Social Media',
    '金融与支付': 'Finance & Payment',
    'AI助手': 'AI Assistant',
    '生活方式': 'Lifestyle'
}

# 尝试多种字体方案
font_candidates = [
    'Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei',
    'Arial Unicode MS', 'Noto Sans CJK SC', 'Source Han Sans SC'
]

# 查找可用的中文字体
available_fonts = []
for font_name in font_candidates:
    try:
        font_path = fm.findfont(font_name)
        if font_path and 'DejaVu' not in font_path:
            available_fonts.append(font_name)
            break
    except:
        continue

use_chinese = bool(available_fonts)
if use_chinese:
    plt.rcParams['font.sans-serif'] = available_fonts + ['DejaVu Sans']
    print("使用中文字体显示")
else:
    print("未找到中文字体，使用英文标签")

plt.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

# 1. 数据解析与清洗
def load_and_clean_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)

    def parse_download(val):
        if pd.isna(val) or val == "N/A" or val == "":
            return 0.0
        val = str(val).replace('+', '').upper()
        if 'B' in val:
            return float(val.replace('B', ''))
        if 'M' in val:
            return float(val.replace('M', '')) / 1000.0
        if 'K' in val:
            return float(val.replace('K', '')) / 1000000.0
        return 0.0

    # 计算总下载量 (Billions)
    df['china_val'] = df['china_android_downloads'].apply(parse_download)
    df['google_val'] = df['google_play_downloads'].apply(parse_download)
    df['total_downloads_bn'] = df['china_val'] + df['google_val']
    
    # 过滤掉下载量为0的数据以防对数计算报错
    df = df[df['total_downloads_bn'] > 0].copy()
    
    # 定义官方 8 个分类顺序
    category_order = [
        '视频娱乐', '办公协作', '出行旅游', '电商购物', 
        '社交媒体', '金融与支付', 'AI助手', '生活方式'
    ]
    df['scenario'] = pd.Categorical(df['scenario'], categories=category_order, ordered=True)
    return df

# 2. 绘制高度定制化散点图（区间合并 + Symlog轴）
def plot_custom_scatter(df, use_chinese=True):
    # 定义官方 8 个分类顺序（与数据加载函数保持一致）
    category_order = [
        '视频娱乐', '办公协作', '出行旅游', '电商购物',
        '社交媒体', '金融与支付', 'AI助手', '生活方式'
    ]

    # 根据字体支持情况选择标签
    display_labels = category_order if use_chinese else [category_labels[cat] for cat in category_order]
    plt.figure(figsize=(14, 8))
    sns.set_style("whitegrid")
    
    # 核心思路：利用 symlog 轴处理 0-1B 的压缩和 1B 以上的对数伸展
    # linthresh=1.0 表示 1.0(即1B) 以下线性处理，以上对数处理
    palette = sns.color_palette("husl", 8)
    
    # 创建散点图，但不自动生成图例
    scatter = sns.scatterplot(
        data=df,
        x='total_downloads_bn',
        y='scenario',
        hue='scenario',
        size='total_downloads_bn',
        sizes=(100, 1000),
        alpha=0.6,
        palette=palette,
        edgecolor="w",
        linewidth=1,
        legend=False  # 禁用自动图例
    )

    # 坐标轴高级定制
    plt.xscale('symlog', linthresh=1.0)
    plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.3)
    plt.text(1.05, 0.5, "1 Billion (Compression Threshold)", color='red', transform=scatter.get_xaxis_transform())

    plt.title("App Market Distribution by Category & Downloads\n(X-axis: Total Downloads | Y-axis: Category | 0-1B Region Merged)", fontsize=14)
    plt.xlabel("Total Downloads (Billions, Log-Scale after 1B)", fontsize=12)
    plt.ylabel("App Category", fontsize=12)

    # 标注下载量极值 App
    top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario').head(1)
    for _, row in top_apps.iterrows():
        plt.text(row['total_downloads_bn'], row['scenario'], f"  {row['app_name']}", fontsize=9, alpha=0.7)

    # 创建自定义图例
    handles = []
    legend_title = "应用场景" if use_chinese else "App Categories"
    for i, category in enumerate(category_order):
        handles.append(plt.scatter([], [], color=palette[i], s=100, alpha=0.6, edgecolor="w", linewidth=1))

    plt.legend(handles, display_labels, bbox_to_anchor=(1.05, 1), loc='upper left', title=legend_title, fontsize=10)
    plt.tight_layout()
    plt.savefig('scatter_custom.png', dpi=300)
    print("高度定制化散点图已生成: scatter_custom.png")

# 3. 绘制分面式对数轴直方图 / KDE (主选)
def plot_faceted_distribution(df, use_chinese=True):
    # 定义官方 8 个分类顺序
    category_order = [
        '视频娱乐', '办公协作', '出行旅游', '电商购物',
        '社交媒体', '金融与支付', 'AI助手', '生活方式'
    ]

    # 计算 log10 下载量
    df['log_downloads'] = np.log10(df['total_downloads_bn'])

    sns.set(style="whitegrid", font_scale=0.9)
    g = sns.FacetGrid(
        df, col="scenario", col_wrap=4, hue="scenario",
        sharex=True, sharey=False, height=3, aspect=1.2,
        palette="viridis"
    )

    # 绘制直方图和密度曲线
    g.map(sns.histplot, "log_downloads", kde=True, bins=10, alpha=0.4)

    g.set_axis_labels("Log10 Downloads (Billions)", "Density / Count")

    # 使用自定义标题函数确保中文正确显示
    def set_title_with_font(data, **kwargs):
        ax = plt.gca()
        scenario_name = data['scenario'].iloc[0] if len(data) > 0 else ""
        ax.set_title(scenario_name, fontsize=12, fontweight='bold')

    # 移除自动标题设置，手动设置每个子图标题
    g.set_titles("")  # 清除默认标题
    for ax, scenario in zip(g.axes.flat, category_order):
        title_text = scenario if use_chinese else category_labels[scenario]
        ax.set_title(title_text, fontsize=12, fontweight='bold')

    plt.subplots_adjust(top=0.9)
    suptitle_text = 'Faceted Distribution of App Downloads (8 Categories)' if use_chinese else '分面式应用下载量分布图 (8个分类)'
    g.fig.suptitle(suptitle_text, fontsize=15)

    plt.tight_layout()
    plt.savefig('distribution_facet.png', dpi=300)
    print("分面式分布图已生成: distribution_facet.png")

# 4. 绘制分组式小提琴图 (次选)
def plot_violin_comparison(df, use_chinese=True):
    # 定义官方 8 个分类顺序
    category_order = [
        '视频娱乐', '办公协作', '出行旅游', '电商购物',
        '社交媒体', '金融与支付', 'AI助手', '生活方式'
    ]

    df['log_downloads'] = np.log10(df['total_downloads_bn'])

    plt.figure(figsize=(12, 6))
    
    # 使用深浅渐变色反映类别差异
    sns.violinplot(
        data=df, x='scenario', y='log_downloads',
        inner="stick", palette="Purples_r", cut=0
    )

    # 设置横轴标签
    display_xticks = category_order if use_chinese else [category_labels[cat] for cat in category_order]
    plt.xticks(range(len(category_order)), display_xticks, rotation=45, ha='right')

    title_text = "Comparison of Download Distributions Across 8 App Categories" if use_chinese else "8个应用分类下载量分布对比"
    xlabel_text = "App Category" if use_chinese else "应用分类"
    plt.title(title_text, fontsize=14)
    plt.ylabel("Log10 Total Downloads (Billions)", fontsize=12)
    plt.xlabel(xlabel_text, fontsize=12)
    
    plt.tight_layout()
    plt.savefig('distribution_violin.png', dpi=300)
    print("分组式小提琴图已生成: distribution_violin.png")

# 执行逻辑
if __name__ == "__main__":
    # 请确保 AppUi.json 在当前目录下
    try:
        data_df = load_and_clean_data('AppUi.json')

        # 场景一：散点图（核心思路在于非线性轴）
        plot_custom_scatter(data_df, use_chinese)

        # 场景二：分面分布（主选，最适合对比幂律特征）
        plot_faceted_distribution(data_df, use_chinese)

        # 场景三：小提琴图（次选，展示密度分布）
        plot_violin_comparison(data_df, use_chinese)

        print("\n所有可视化方案已就绪。")
    except FileNotFoundError:
        print("错误：未找到 AppUi.json 文件，请检查路径。")
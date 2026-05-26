import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import MaxNLocator

# ================= 1. 业务逻辑设置 =================
category_labels = {
    '视频娱乐': 'Media &\nEntertainment',
    '办公协作': 'Office\nCollaboration',
    '出行旅游': 'Travel &\nMap',
    '电商购物': 'E-commerce',
    '社交媒体': 'Social\nMedia',
    '金融与支付': 'Finance &\nPayment',
    'AI助手': 'AI\nAssistant',
    '生活方式': 'Lifestyle'
}

# 解决乱码映射
app_name_map = {
    '喜马拉雅': 'Ximalaya',
    '剪映': 'Jianying (CapCut)',
    '美图秀秀/MeituXiuxiu': 'Meitu',
    '抖音/Tik Tok': 'TikTok',
    '微信': 'WeChat',
    '支付宝/Alipay': 'Alipay',
    '淘宝': 'Taobao',
    '拼多多': 'Pinduoduo',
    '京东': 'JD.com',
    '高德地图(Amap)': 'Amap',
    '百度地图': 'Baidu Map',
    '腾讯会议': 'Tencent Meeting',
    '百度网盘': 'Baidu Netdisk',
    '小红书': 'Xiaohongshu',
    '知乎': 'Zhihu',
    '微博': 'Weibo'
}

category_order = ['视频娱乐', '办公协作', '出行旅游', '电商购物', '社交媒体', '金融与支付', 'AI助手', '生活方式']
en_category_order = [category_labels[cat] for cat in category_order]

plt.rcParams['font.sans-serif'] = ['Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def load_and_clean_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)

    def parse_download(val):
        if pd.isna(val) or val == "N/A" or val == "": return 0.0
        val = str(val).replace('+', '').upper()
        if 'B' in val: return float(val.replace('B', ''))
        if 'M' in val: return float(val.replace('M', '')) / 1000.0
        if 'K' in val: return float(val.replace('K', '')) / 1000000.0
        return 0.0

    df['total_downloads_bn'] = df['china_android_downloads'].apply(parse_download) + \
                               df['google_play_downloads'].apply(parse_download)
    df = df[df['total_downloads_bn'] > 0].copy()
    
    df['app_name_en'] = df['app_name'].map(lambda x: app_name_map.get(x, x))
    
    df['scenario_en'] = df['scenario'].map(category_labels)
    df['scenario_en'] = pd.Categorical(df['scenario_en'], categories=en_category_order, ordered=True)
    return df

# 2. 高度定制化散点图
def plot_custom_scatter(df):
    plt.figure(figsize=(10, 8))
    sns.set_style("whitegrid")
    
    palette_colors = sns.color_palette("husl", 8)
    color_dict = dict(zip(en_category_order, palette_colors))
    
    scatter = sns.scatterplot(
        data=df, x='total_downloads_bn', y='scenario_en',
        hue='scenario_en', size='total_downloads_bn', sizes=(100, 1000),
        alpha=0.6, palette=color_dict, edgecolor="w", linewidth=1, legend=False
    )
    
    plt.xscale('symlog', linthresh=1.0) 
    plt.xlim(left=-0.1, right=df['total_downloads_bn'].max() * 1.3)
    
    # 阈值线处理：增加字体大小至 15
    plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.3)
    plt.text(1.05, 0.5, "1 Billion (Threshold)", 
             color='red', fontweight='bold', fontsize=14, # 已增大字体
             transform=scatter.get_xaxis_transform())

    plt.title("App Market Distribution by Category & Downloads", fontsize=22)
    plt.xlabel("Total Downloads (Billions, Log-Scale after 1B)", fontsize=18)
    plt.ylabel("App Category", fontsize=18)
    
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)

    top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario_en').head(1)
    for _, row in top_apps.iterrows():
        plt.annotate(
            row['app_name_en'], 
            xy=(row['total_downloads_bn'], row['scenario_en']),
            xytext=(0, -15),             
            textcoords="offset points",  
            ha='center',                 
            va='top',                    
            fontsize=14, 
            fontweight='bold',           
            alpha=0.8,
            color='#333333'              
        )
    
    plt.tight_layout()
    plt.savefig('scatter_custom.png', dpi=300, bbox_inches='tight')
    plt.savefig('scatter_custom.pdf', bbox_inches='tight')
    print("散点图已生成: scatter_custom.png 和 scatter_custom.pdf")

# 3. 分面式分布图
def plot_faceted_distribution(df):
    df['log_downloads'] = np.log10(df['total_downloads_bn'])
    sns.set(style="whitegrid", font_scale=0.9)
    g = sns.FacetGrid(
        df, col="scenario_en", col_wrap=4, hue="scenario_en",
        sharex=True, sharey=False, height=3, aspect=1.2,
        palette="viridis", col_order=en_category_order
    )
    g.fig.set_size_inches(10, 8)
    
    g.map(sns.histplot, "log_downloads", kde=True, bins=10, alpha=0.4)
    g.set_axis_labels("Log10 Downloads (Bn)", "Density", fontsize=15)
    g.set_titles("") 
    for ax, title_text in zip(g.axes.flat, en_category_order):
        ax.set_title(title_text, fontsize=14, fontweight='bold')
        ax.tick_params(axis='both', which='major', labelsize=10)
        
    plt.subplots_adjust(top=0.88)
    g.fig.suptitle('Faceted Distribution of App Downloads (8 Categories)', fontsize=22)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig('distribution_facet.png', dpi=300, bbox_inches='tight')
    plt.savefig('distribution_facet.pdf', bbox_inches='tight')
    print("分面分布图已生成: distribution_facet.png 和 distribution_facet.pdf")

# 4. 优化后的小提琴图
def plot_violin_comparison(df):
    df['log_downloads'] = np.log10(df['total_downloads_bn'])
    plt.figure(figsize=(10, 8))
    sns.violinplot(
        data=df, x='scenario_en', y='log_downloads',
        order=en_category_order,
        inner="stick", palette="Blues_r", cut=0
    )

    plt.xticks(rotation=0, ha='center', fontsize=12)
    plt.yticks(fontsize=15)
    
    plt.title("Comparison of Download Distributions Across 8 App Categories", fontsize=22, pad=20)
    plt.ylabel("Log10 Total Downloads (Billions)", fontsize=18)
    plt.xlabel("", fontsize=18) 
    
    plt.grid(axis='y', linestyle='--', alpha=0.4)
    
    plt.tight_layout()
    plt.savefig('distribution_violin.png', dpi=300, bbox_inches='tight')
    plt.savefig('distribution_violin.pdf', bbox_inches='tight')
    print("小提琴图已生成: distribution_violin.png 和 distribution_violin.pdf")

if __name__ == "__main__":
    try:
        data_df = load_and_clean_data('AppUi.json')
        plot_custom_scatter(data_df)
        plot_faceted_distribution(data_df)
        plot_violin_comparison(data_df)
        print("\n所有可视化方案已就绪！")
        print("生成的文件包括：")
        print("- scatter_custom.png / scatter_custom.pdf (高度定制化散点图)")
        print("- distribution_facet.png / distribution_facet.pdf (分面式分布图)")
        print("- distribution_violin.png / distribution_violin.pdf (分组式小提琴图)")
    except Exception as e:
        print(f"Error: {e}")
##version 6
# import json
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns
# from matplotlib.ticker import MaxNLocator

# # ================= 1. 业务逻辑设置 =================
# category_labels = {
#     '视频娱乐': 'Media &\nEntertainment',
#     '办公协作': 'Office\nCollaboration',
#     '出行旅游': 'Travel &\nMap',
#     '电商购物': 'E-commerce',
#     '社交媒体': 'Social\nMedia',
#     '金融与支付': 'Finance &\nPayment',
#     'AI助手': 'AI\nAssistant',
#     '生活方式': 'Lifestyle'
# }

# # 解决乱码映射：确保 Lifestyle 类别标注为英文 Ximalaya (根据JSON下载量最高者)
# app_name_map = {
#     '喜马拉雅': 'Ximalaya',
#     '剪映': 'Jianying (CapCut)',
#     '美图秀秀/MeituXiuxiu': 'Meitu',
#     '抖音/Tik Tok': 'TikTok',
#     '微信': 'WeChat',
#     '支付宝/Alipay': 'Alipay',
#     '淘宝': 'Taobao',
#     '拼多多': 'Pinduoduo',
#     '京东': 'JD.com',
#     '高德地图(Amap)': 'Amap',
#     '百度地图': 'Baidu Map',
#     '腾讯会议': 'Tencent Meeting',
#     '百度网盘': 'Baidu Netdisk',
#     '小红书': 'Xiaohongshu',
#     '知乎': 'Zhihu',
#     '微博': 'Weibo'
# }

# category_order = ['视频娱乐', '办公协作', '出行旅游', '电商购物', '社交媒体', '金融与支付', 'AI助手', '生活方式']
# en_category_order = [category_labels[cat] for cat in category_order]

# plt.rcParams['font.sans-serif'] = ['Arial', 'sans-serif']
# plt.rcParams['axes.unicode_minus'] = False

# def load_and_clean_data(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#     df = pd.DataFrame(data)

#     def parse_download(val):
#         if pd.isna(val) or val == "N/A" or val == "": return 0.0
#         val = str(val).replace('+', '').upper()
#         if 'B' in val: return float(val.replace('B', ''))
#         if 'M' in val: return float(val.replace('M', '')) / 1000.0
#         if 'K' in val: return float(val.replace('K', '')) / 1000000.0
#         return 0.0

#     df['total_downloads_bn'] = df['china_android_downloads'].apply(parse_download) + \
#                                df['google_play_downloads'].apply(parse_download)
#     df = df[df['total_downloads_bn'] > 0].copy()
    
#     # 强制转换App名称为英文
#     df['app_name_en'] = df['app_name'].map(lambda x: app_name_map.get(x, x))
    
#     df['scenario_en'] = df['scenario'].map(category_labels)
#     df['scenario_en'] = pd.Categorical(df['scenario_en'], categories=en_category_order, ordered=True)
#     return df

# # 2. 高度定制化散点图
# def plot_custom_scatter(df):
#     plt.figure(figsize=(10, 8))
#     sns.set_style("whitegrid")
    
#     palette_colors = sns.color_palette("husl", 8)
#     color_dict = dict(zip(en_category_order, palette_colors))
    
#     scatter = sns.scatterplot(
#         data=df, x='total_downloads_bn', y='scenario_en',
#         hue='scenario_en', size='total_downloads_bn', sizes=(100, 1000),
#         alpha=0.6, palette=color_dict, edgecolor="w", linewidth=1, legend=False
#     )
    
#     # --- 高度定制化坐标轴处理 ---
#     # 使用 symlog 实现：< 1B 区间线性压缩合并，> 1B 区间对数展开
#     plt.xscale('symlog', linthresh=1.0) 
#     # 强制设置左侧边界为 -0.1 (接近0)，消除原本 symlog 自动产生的负值空白区
#     plt.xlim(left=-0.1, right=df['total_downloads_bn'].max() * 1.3)
    
#     # 阈值线及描述
#     plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.3)
#     plt.text(1.05, 0.5, "1 Billion (Compression Threshold)", 
#              color='red', fontweight='bold', transform=scatter.get_xaxis_transform())

#     plt.title("App Market Distribution by Category & Downloads", fontsize=22)
#     plt.xlabel("Total Downloads (Billions, Log-Scale after 1B)", fontsize=22)
#     plt.ylabel("App Category", fontsize=22)

#     # 标注 Top Apps 在气泡正下方
#     top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario_en').head(1)
#     for _, row in top_apps.iterrows():
#         plt.annotate(
#             row['app_name_en'], 
#             xy=(row['total_downloads_bn'], row['scenario_en']),
#             xytext=(0, -15),             
#             textcoords="offset points",  
#             ha='center',                 
#             va='top',                    
#             fontsize=15, 
#             fontweight='bold',           
#             alpha=0.8,
#             color='#333333'              
#         )
    
#     # 去掉图例以突出主体
#     plt.tight_layout()
#     plt.savefig('scatter_custom.png', dpi=300)

# # 3. 分面式分布图
# def plot_faceted_distribution(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     sns.set(style="whitegrid", font_scale=0.9)
#     g = sns.FacetGrid(
#         df, col="scenario_en", col_wrap=4, hue="scenario_en",
#         sharex=True, sharey=False, height=3, aspect=1.2,
#         palette="viridis", col_order=en_category_order
#     )
#     # 固定整体 figsize 为 (10, 8)
#     g.fig.set_size_inches(10, 8)
    
#     g.map(sns.histplot, "log_downloads", kde=True, bins=10, alpha=0.4)
#     g.set_axis_labels("Log10 Downloads (Bn)", "Density")
#     g.set_titles("") 
#     for ax, title_text in zip(g.axes.flat, en_category_order):
#         ax.set_title(title_text, fontsize=15, fontweight='bold')
#     plt.subplots_adjust(top=0.9)
#     g.fig.suptitle('Faceted Distribution of App Downloads (8 Categories)', fontsize=22)
#     plt.tight_layout()
#     plt.savefig('distribution_facet.png', dpi=300)

# # 4. 优化后的小提琴图
# def plot_violin_comparison(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     plt.figure(figsize=(10, 8))
#     sns.violinplot(
#         data=df, x='scenario_en', y='log_downloads',
#         order=en_category_order,
#         inner="stick", palette="Blues_r", cut=0
#     )

#     plt.xticks(rotation=0, ha='center', fontsize=9.5) 
#     plt.yticks(fontsize=10)
    
#     plt.title("Comparison of Download Distributions Across 8 App Categories", fontsize=22, pad=15)
#     plt.ylabel("Log10 Total Downloads (Billions)", fontsize=22)
#     plt.xlabel("", fontsize=15) 
    
#     plt.grid(axis='y', linestyle='--', alpha=0.4)
    
#     plt.tight_layout()
#     plt.savefig('distribution_violin.png', dpi=300)

# if __name__ == "__main__":
#     try:
#         data_df = load_and_clean_data('AppUi.json')
#         plot_custom_scatter(data_df)
#         plot_faceted_distribution(data_df)
#         plot_violin_comparison(data_df)
#         print("Success: Scatter plot optimized with 1B compression and zero-aligned axis.")
#     except Exception as e:
#         print(f"Error: {e}")
##--version5
# import json
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns
# from matplotlib.ticker import MaxNLocator

# # ================= 1. 业务逻辑设置 =================
# category_labels = {
#     '视频娱乐': 'Media &\nEntertainment',
#     '办公协作': 'Office\nCollaboration',
#     '出行旅游': 'Travel &\nMap',
#     '电商购物': 'E-commerce',
#     '社交媒体': 'Social\nMedia',
#     '金融与支付': 'Finance &\nPayment',
#     'AI助手': 'AI\nAssistant',
#     '生活方式': 'Lifestyle'
# }

# # 解决乱码映射：重点修正生活方式类别 Top 1 为 喜马拉雅 (5B+)
# app_name_map = {
#     '喜马拉雅': 'Ximalaya',
#     '剪映': 'Jianying (CapCut)',
#     '美图秀秀/MeituXiuxiu': 'Meitu',
#     '抖音/Tik Tok': 'TikTok',
#     '微信': 'WeChat',
#     '支付宝/Alipay': 'Alipay',
#     '淘宝': 'Taobao',
#     '拼多多': 'Pinduoduo',
#     '京东': 'JD.com',
#     '高德地图(Amap)': 'Amap',
#     '百度地图': 'Baidu Map',
#     '腾讯会议': 'Tencent Meeting',
#     '百度网盘': 'Baidu Netdisk',
#     '小红书': 'Xiaohongshu',
#     '知乎': 'Zhihu',
#     '微博': 'Weibo'
# }

# category_order = ['视频娱乐', '办公协作', '出行旅游', '电商购物', '社交媒体', '金融与支付', 'AI助手', '生活方式']
# en_category_order = [category_labels[cat] for cat in category_order]

# plt.rcParams['font.sans-serif'] = ['Arial', 'sans-serif']
# plt.rcParams['axes.unicode_minus'] = False

# def load_and_clean_data(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#     df = pd.DataFrame(data)

#     def parse_download(val):
#         if pd.isna(val) or val == "N/A" or val == "": return 0.0
#         val = str(val).replace('+', '').upper()
#         if 'B' in val: return float(val.replace('B', ''))
#         if 'M' in val: return float(val.replace('M', '')) / 1000.0
#         if 'K' in val: return float(val.replace('K', '')) / 1000000.0
#         return 0.0

#     df['total_downloads_bn'] = df['china_android_downloads'].apply(parse_download) + \
#                                df['google_play_downloads'].apply(parse_download)
#     df = df[df['total_downloads_bn'] > 0].copy()
    
#     df['app_name_en'] = df['app_name'].map(lambda x: app_name_map.get(x, x))
    
#     df['scenario_en'] = df['scenario'].map(category_labels)
#     df['scenario_en'] = pd.Categorical(df['scenario_en'], categories=en_category_order, ordered=True)
#     return df

# # 2. 高度定制化散点图（修改：去掉右侧图例以突出主体）
# def plot_custom_scatter(df):
#     plt.figure(figsize=(10, 8))
#     sns.set_style("whitegrid")
    
#     palette_colors = sns.color_palette("husl", 8)
#     color_dict = dict(zip(en_category_order, palette_colors))
    
#     scatter = sns.scatterplot(
#         data=df, x='total_downloads_bn', y='scenario_en',
#         hue='scenario_en', size='total_downloads_bn', sizes=(100, 1000),
#         alpha=0.6, palette=color_dict, edgecolor="w", linewidth=1, legend=False
#     )
#     plt.xscale('symlog', linthresh=1.0)
#     plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.3)
#     plt.text(1.05, 0.5, "1 Billion (Threshold)", color='red', transform=scatter.get_xaxis_transform())

#     plt.title("App Market Distribution by Category & Downloads", fontsize=14)
#     plt.xlabel("Total Downloads (Billions, Log-Scale after 1B)", fontsize=12)
#     plt.ylabel("App Category", fontsize=12)

#     top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario_en').head(1)
#     for _, row in top_apps.iterrows():
#         plt.annotate(
#             row['app_name_en'], 
#             xy=(row['total_downloads_bn'], row['scenario_en']),
#             xytext=(0, -15),             
#             textcoords="offset points",  
#             ha='center',                 
#             va='top',                    
#             fontsize=9, 
#             fontweight='bold',           
#             alpha=0.8,
#             color='#333333'              
#         )
    
#     # 修改：已删除 plt.legend 相关代码，以使散点图主体更突出
#     plt.tight_layout()
#     plt.savefig('scatter_custom.png', dpi=300)

# # 3. 分面式分布图
# def plot_faceted_distribution(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     sns.set(style="whitegrid", font_scale=0.9)
#     g = sns.FacetGrid(
#         df, col="scenario_en", col_wrap=4, hue="scenario_en",
#         sharex=True, sharey=False, height=3, aspect=1.2,
#         palette="viridis", col_order=en_category_order
#     )
#     g.fig.set_size_inches(10, 8)
    
#     g.map(sns.histplot, "log_downloads", kde=True, bins=10, alpha=0.4)
#     g.set_axis_labels("Log10 Downloads (Bn)", "Density")
#     g.set_titles("") 
#     for ax, title_text in zip(g.axes.flat, en_category_order):
#         ax.set_title(title_text, fontsize=11, fontweight='bold')
#     plt.subplots_adjust(top=0.9)
#     g.fig.suptitle('Faceted Distribution of App Downloads (8 Categories)', fontsize=15)
#     plt.tight_layout()
#     plt.savefig('distribution_facet.png', dpi=300)

# # 4. 优化后的小提琴图
# def plot_violin_comparison(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     plt.figure(figsize=(10, 8))
#     sns.violinplot(
#         data=df, x='scenario_en', y='log_downloads',
#         order=en_category_order,
#         inner="stick", palette="Blues_r", cut=0
#     )

#     plt.xticks(rotation=0, ha='center', fontsize=9.5) 
#     plt.yticks(fontsize=10)
    
#     plt.title("Comparison of Download Distributions Across 8 App Categories", fontsize=15, pad=15)
#     plt.ylabel("Log10 Total Downloads (Billions)", fontsize=12)
#     plt.xlabel("", fontsize=10) 
    
#     plt.grid(axis='y', linestyle='--', alpha=0.4)
    
#     plt.tight_layout()
#     plt.savefig('distribution_violin.png', dpi=300)

# if __name__ == "__main__":
#     try:
#         data_df = load_and_clean_data('AppUi.json')
#         plot_custom_scatter(data_df)
#         plot_faceted_distribution(data_df)
#         plot_violin_comparison(data_df)
#         print("Success: Scatter plot highlighted by removing redundant legend.")
#     except Exception as e:
#         print(f"Error: {e}")
##--version 4
# import json
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns
# from matplotlib.ticker import MaxNLocator

# # ================= 1. 业务逻辑设置 =================
# category_labels = {
#     '视频娱乐': 'Media &\nEntertainment',
#     '办公协作': 'Office\nCollaboration',
#     '出行旅游': 'Travel &\nMap',
#     '电商购物': 'E-commerce',
#     '社交媒体': 'Social\nMedia',
#     '金融与支付': 'Finance &\nPayment',
#     'AI助手': 'AI\nAssistant',
#     '生活方式': 'Lifestyle'
# }

# # 彻底解决乱码：根据 JSON 内容，将各类别下载量最高的中文名映射为英文
# # 重点修正：生活方式类别 Top 1 为 喜马拉雅 (5B+)
# app_name_map = {
#     '喜马拉雅': 'Ximalaya',
#     '剪映': 'Jianying (CapCut)',
#     '美图秀秀/MeituXiuxiu': 'Meitu',
#     '抖音/Tik Tok': 'TikTok',
#     '微信': 'WeChat',
#     '支付宝/Alipay': 'Alipay',
#     '淘宝': 'Taobao',
#     '拼多多': 'Pinduoduo',
#     '京东': 'JD.com',
#     '高德地图(Amap)': 'Amap',
#     '百度地图': 'Baidu Map',
#     '腾讯会议': 'Tencent Meeting',
#     '百度网盘': 'Baidu Netdisk',
#     '小红书': 'Xiaohongshu',
#     '知乎': 'Zhihu',
#     '微博': 'Weibo'
# }

# category_order = ['视频娱乐', '办公协作', '出行旅游', '电商购物', '社交媒体', '金融与支付', 'AI助手', '生活方式']
# en_category_order = [category_labels[cat] for cat in category_order]

# plt.rcParams['font.sans-serif'] = ['Arial', 'sans-serif']
# plt.rcParams['axes.unicode_minus'] = False

# def load_and_clean_data(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#     df = pd.DataFrame(data)

#     def parse_download(val):
#         if pd.isna(val) or val == "N/A" or val == "": return 0.0
#         val = str(val).replace('+', '').upper()
#         if 'B' in val: return float(val.replace('B', ''))
#         if 'M' in val: return float(val.replace('M', '')) / 1000.0
#         if 'K' in val: return float(val.replace('K', '')) / 1000000.0
#         return 0.0

#     df['total_downloads_bn'] = df['china_android_downloads'].apply(parse_download) + \
#                                df['google_play_downloads'].apply(parse_download)
#     df = df[df['total_downloads_bn'] > 0].copy()
    
#     # 修正：在标注前将所有可能的中文名称转换为英文
#     df['app_name_en'] = df['app_name'].map(lambda x: app_name_map.get(x, x))
    
#     df['scenario_en'] = df['scenario'].map(category_labels)
#     df['scenario_en'] = pd.Categorical(df['scenario_en'], categories=en_category_order, ordered=True)
#     return df

# # 2. 高度定制化散点图
# def plot_custom_scatter(df):
#     plt.figure(figsize=(10, 8))
#     sns.set_style("whitegrid")
    
#     # 整合配色：确保散点颜色、纵轴 Scenario 和图例颜色完全匹配
#     palette_colors = sns.color_palette("husl", 8)
#     color_dict = dict(zip(en_category_order, palette_colors))
    
#     scatter = sns.scatterplot(
#         data=df, x='total_downloads_bn', y='scenario_en',
#         hue='scenario_en', size='total_downloads_bn', sizes=(100, 1000),
#         alpha=0.6, palette=color_dict, edgecolor="w", linewidth=1, legend=False
#     )
#     plt.xscale('symlog', linthresh=1.0)
#     plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.3)
#     plt.text(1.05, 0.5, "1 Billion (Threshold)", color='red', transform=scatter.get_xaxis_transform())

#     plt.title("App Market Distribution by Category & Downloads", fontsize=14)
#     plt.xlabel("Total Downloads (Billions, Log-Scale after 1B)", fontsize=12)
#     plt.ylabel("App Category", fontsize=12)

#     # 找到每个 Scenario 下下载量最大的应用并标注在其正下方
#     top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario_en').head(1)
#     for _, row in top_apps.iterrows():
#         plt.annotate(
#             row['app_name_en'], # 使用已经转换好的英文名
#             xy=(row['total_downloads_bn'], row['scenario_en']),
#             xytext=(0, -15),             
#             textcoords="offset points",  
#             ha='center',                 
#             va='top',                    
#             fontsize=9, 
#             fontweight='bold',           
#             alpha=0.8,
#             color='#333333'              
#         )
    
#     # 手动创建图例，以匹配整合后的配色方案
#     handles = []
#     for category in en_category_order:
#         handles.append(plt.scatter([], [], color=color_dict[category], s=100, alpha=0.6, edgecolor="w", linewidth=1))

#     plt.legend(handles, en_category_order, bbox_to_anchor=(1.02, 1), loc='upper left', title="Market Scenarios", fontsize=10)
#     plt.tight_layout()
#     plt.savefig('scatter_custom.png', dpi=300)

# # 3. 分面式分布图
# def plot_faceted_distribution(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     sns.set(style="whitegrid", font_scale=0.9)
#     g = sns.FacetGrid(
#         df, col="scenario_en", col_wrap=4, hue="scenario_en",
#         sharex=True, sharey=False, height=3, aspect=1.2,
#         palette="viridis", col_order=en_category_order
#     )
#     # 修改1：要求设置整体figsize为 (10, 8)
#     g.fig.set_size_inches(10, 8)
    
#     g.map(sns.histplot, "log_downloads", kde=True, bins=10, alpha=0.4)
#     g.set_axis_labels("Log10 Downloads (Bn)", "Density")
#     g.set_titles("") 
#     for ax, title_text in zip(g.axes.flat, en_category_order):
#         ax.set_title(title_text, fontsize=11, fontweight='bold')
#     plt.subplots_adjust(top=0.9)
#     g.fig.suptitle('Faceted Distribution of App Downloads (8 Categories)', fontsize=15)
#     plt.tight_layout()
#     plt.savefig('distribution_facet.png', dpi=300)

# # 4. 优化后的小提琴图
# def plot_violin_comparison(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     plt.figure(figsize=(10, 8))
#     sns.violinplot(
#         data=df, x='scenario_en', y='log_downloads',
#         order=en_category_order,
#         inner="stick", palette="Blues_r", cut=0
#     )

#     plt.xticks(rotation=0, ha='center', fontsize=9.5) 
#     plt.yticks(fontsize=10)
    
#     plt.title("Comparison of Download Distributions Across 8 App Categories", fontsize=15, pad=15)
#     plt.ylabel("Log10 Total Downloads (Billions)", fontsize=12)
#     plt.xlabel("", fontsize=10) 
    
#     plt.grid(axis='y', linestyle='--', alpha=0.4)
    
#     plt.tight_layout()
#     plt.savefig('distribution_violin.png', dpi=300)

# if __name__ == "__main__":
#     try:
#         data_df = load_and_clean_data('AppUi.json')
#         plot_custom_scatter(data_df)
#         plot_faceted_distribution(data_df)
#         plot_violin_comparison(data_df)
#         print("Success: App names corrected (Ximalaya for Lifestyle) and legend integrated.")
#     except Exception as e:
#         print(f"Error: {e}")
##--version3
# import json
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns
# from matplotlib.ticker import MaxNLocator

# # ================= 1. 业务逻辑设置 =================
# category_labels = {
#     '视频娱乐': 'Media &\nEntertainment',
#     '办公协作': 'Office\nCollaboration',
#     '出行旅游': 'Travel &\nMap',
#     '电商购物': 'E-commerce',
#     '社交媒体': 'Social\nMedia',
#     '金融与支付': 'Finance &\nPayment',
#     'AI助手': 'AI\nAssistant',
#     '生活方式': 'Lifestyle'
# }

# # 扩展映射字典，彻底解决 Lifestyle（小红书/美团等）及其他分类的乱码
# app_name_map = {
#     '抖音/Tik Tok': 'TikTok',
#     '抖音': 'TikTok',
#     '微信': 'WeChat',
#     '支付宝/Alipay': 'Alipay',
#     '支付宝': 'Alipay',
#     '百度地图': 'Baidu Map',
#     '高德地图': 'Amap',
#     '拼多多': 'Pinduoduo',
#     '淘宝': 'Taobao',
#     '腾讯会议': 'Tencent Meeting',
#     '小红书': 'Xiaohongshu', 
#     '大众点评': 'Dianping',
#     '快手': 'Kuaishou',
#     '微博': 'Weibo',
#     '美团': 'Meituan',
#     '钉钉': 'DingTalk',
#     'Google地图': 'Google Maps'
# }

# category_order = ['视频娱乐', '办公协作', '出行旅游', '电商购物', '社交媒体', '金融与支付', 'AI助手', '生活方式']
# en_category_order = [category_labels[cat] for cat in category_order]

# plt.rcParams['font.sans-serif'] = ['Arial', 'sans-serif']
# plt.rcParams['axes.unicode_minus'] = False

# def load_and_clean_data(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#     df = pd.DataFrame(data)

#     def parse_download(val):
#         if pd.isna(val) or val == "N/A" or val == "": return 0.0
#         val = str(val).replace('+', '').upper()
#         if 'B' in val: return float(val.replace('B', ''))
#         if 'M' in val: return float(val.replace('M', '')) / 1000.0
#         if 'K' in val: return float(val.replace('K', '')) / 1000000.0
#         return 0.0

#     df['total_downloads_bn'] = df['china_android_downloads'].apply(parse_download) + \
#                                df['google_play_downloads'].apply(parse_download)
#     df = df[df['total_downloads_bn'] > 0].copy()
    
#     # 强制转换App名称为英文
#     df['app_name'] = df['app_name'].map(lambda x: app_name_map.get(x, x))
    
#     df['scenario_en'] = df['scenario'].map(category_labels)
#     df['scenario_en'] = pd.Categorical(df['scenario_en'], categories=en_category_order, ordered=True)
#     return df

# # 2. 高度定制化散点图
# def plot_custom_scatter(df):
#     plt.figure(figsize=(10, 8))
#     sns.set_style("whitegrid")
    
#     # 核心修改：创建显式颜色映射字典，确保图例与纵轴Scenarios完美整合
#     palette_colors = sns.color_palette("husl", 8)
#     color_dict = dict(zip(en_category_order, palette_colors))
    
#     scatter = sns.scatterplot(
#         data=df, x='total_downloads_bn', y='scenario_en',
#         hue='scenario_en', size='total_downloads_bn', sizes=(100, 1000),
#         alpha=0.6, palette=color_dict, edgecolor="w", linewidth=1, legend=False
#     )
#     plt.xscale('symlog', linthresh=1.0)
#     plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.3)
#     plt.text(1.05, 0.5, "1 Billion (Threshold)", color='red', transform=scatter.get_xaxis_transform())

#     plt.title("App Market Distribution by Category & Downloads", fontsize=14)
#     plt.xlabel("Total Downloads (Billions, Log-Scale after 1B)", fontsize=12)
#     plt.ylabel("App Category", fontsize=12)

#     top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario_en').head(1)
#     for _, row in top_apps.iterrows():
#         plt.annotate(
#             row['app_name'], 
#             xy=(row['total_downloads_bn'], row['scenario_en']),
#             xytext=(0, -15),             
#             textcoords="offset points",  
#             ha='center',                 
#             va='top',                    
#             fontsize=9, 
#             fontweight='bold',           
#             alpha=0.8,
#             color='#333333'              
#         )
    
#     # 整合图例：使用显式定义的 color_dict 创建图例句柄
#     handles = []
#     for category in en_category_order:
#         handles.append(plt.scatter([], [], color=color_dict[category], s=100, alpha=0.6, edgecolor="w", linewidth=1))

#     plt.legend(handles, en_category_order, bbox_to_anchor=(1.02, 1), loc='upper left', title="Market Scenarios", fontsize=10)
#     plt.tight_layout()
#     plt.savefig('scatter_custom.png', dpi=300)

# # 3. 分面式分布图
# def plot_faceted_distribution(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     sns.set(style="whitegrid", font_scale=0.9)
#     g = sns.FacetGrid(
#         df, col="scenario_en", col_wrap=4, hue="scenario_en",
#         sharex=True, sharey=False, height=3, aspect=1.2,
#         palette="viridis", col_order=en_category_order
#     )
#     # 修改1：固定figsize为 (10, 8)
#     g.fig.set_size_inches(10, 8)
    
#     g.map(sns.histplot, "log_downloads", kde=True, bins=10, alpha=0.4)
#     g.set_axis_labels("Log10 Downloads (Bn)", "Density")
#     g.set_titles("") 
#     for ax, title_text in zip(g.axes.flat, en_category_order):
#         ax.set_title(title_text, fontsize=11, fontweight='bold')
#     plt.subplots_adjust(top=0.9)
#     g.fig.suptitle('Faceted Distribution of App Downloads (8 Categories)', fontsize=15)
#     plt.tight_layout()
#     plt.savefig('distribution_facet.png', dpi=300)

# # 4. 优化后的小提琴图
# def plot_violin_comparison(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     plt.figure(figsize=(10, 8))
#     sns.violinplot(
#         data=df, x='scenario_en', y='log_downloads',
#         order=en_category_order,
#         inner="stick", palette="Blues_r", cut=0
#     )

#     plt.xticks(rotation=0, ha='center', fontsize=9.5) 
#     plt.yticks(fontsize=10)
    
#     plt.title("Comparison of Download Distributions Across 8 App Categories", fontsize=15, pad=15)
#     plt.ylabel("Log10 Total Downloads (Billions)", fontsize=12)
#     plt.xlabel("", fontsize=10) 
    
#     plt.grid(axis='y', linestyle='--', alpha=0.4)
    
#     plt.tight_layout()
#     plt.savefig('distribution_violin.png', dpi=300)

# if __name__ == "__main__":
#     try:
#         data_df = load_and_clean_data('AppUi.json')
#         plot_custom_scatter(data_df)
#         plot_faceted_distribution(data_df)
#         plot_violin_comparison(data_df)
#         print("Success: All modifications applied and Chinese character issues resolved.")
#     except Exception as e:
#         print(f"Error: {e}")
#--version 2
# import json
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns
# from matplotlib.ticker import MaxNLocator

# # ================= 1. 业务逻辑设置 =================
# category_labels = {
#     '视频娱乐': 'Media &\nEntertainment',
#     '办公协作': 'Office\nCollaboration',
#     '出行旅游': 'Travel &\nMap',
#     '电商购物': 'E-commerce',
#     '社交媒体': 'Social\nMedia',
#     '金融与支付': 'Finance &\nPayment',
#     'AI助手': 'AI\nAssistant',
#     '生活方式': 'Lifestyle'
# }

# # 中文App名称到英文的映射字典，用于解决散点图乱码问题
# app_name_map = {
#     '抖音/Tik Tok': 'TikTok',
#     '微信': 'WeChat',
#     '支付宝/Alipay': 'Alipay',
#     '百度地图': 'Baidu Map',
#     '高德地图': 'Amap',
#     '拼多多': 'Pinduoduo',
#     '淘宝': 'Taobao',
#     '腾讯会议': 'Tencent Meeting',
#     '小红书': 'Xiaohongshu',
#     '快手': 'Kuaishou',
#     '微博': 'Weibo',
#     '美团': 'Meituan',
#     '钉钉': 'DingTalk'
# }

# category_order = ['视频娱乐', '办公协作', '出行旅游', '电商购物', '社交媒体', '金融与支付', 'AI助手', '生活方式']
# en_category_order = [category_labels[cat] for cat in category_order]

# plt.rcParams['font.sans-serif'] = ['Arial', 'sans-serif']
# plt.rcParams['axes.unicode_minus'] = False

# def load_and_clean_data(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#     df = pd.DataFrame(data)

#     def parse_download(val):
#         if pd.isna(val) or val == "N/A" or val == "": return 0.0
#         val = str(val).replace('+', '').upper()
#         if 'B' in val: return float(val.replace('B', ''))
#         if 'M' in val: return float(val.replace('M', '')) / 1000.0
#         if 'K' in val: return float(val.replace('K', '')) / 1000000.0
#         return 0.0

#     df['total_downloads_bn'] = df['china_android_downloads'].apply(parse_download) + \
#                                df['google_play_downloads'].apply(parse_download)
#     df = df[df['total_downloads_bn'] > 0].copy()
    
#     # 修改点2：将中文App名称转换为英文，避免散点图标注乱码
#     df['app_name'] = df['app_name'].map(lambda x: app_name_map.get(x, x))
    
#     df['scenario_en'] = df['scenario'].map(category_labels)
#     df['scenario_en'] = pd.Categorical(df['scenario_en'], categories=en_category_order, ordered=True)
#     return df

# # 2. 高度定制化散点图（其余部分全部保留不准动）
# def plot_custom_scatter(df):
#     plt.figure(figsize=(10, 8))
#     sns.set_style("whitegrid")
#     palette = sns.color_palette("husl", 8)
    
#     scatter = sns.scatterplot(
#         data=df, x='total_downloads_bn', y='scenario_en',
#         hue='scenario_en', size='total_downloads_bn', sizes=(100, 1000),
#         alpha=0.6, palette=palette, edgecolor="w", linewidth=1, legend=False
#     )
#     plt.xscale('symlog', linthresh=1.0)
#     plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.3)
#     plt.text(1.05, 0.5, "1 Billion (Threshold)", color='red', transform=scatter.get_xaxis_transform())

#     plt.title("App Market Distribution by Category & Downloads", fontsize=14)
#     plt.xlabel("Total Downloads (Billions, Log-Scale after 1B)", fontsize=12)
#     plt.ylabel("App Category", fontsize=12)

#     top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario_en').head(1)
#     for _, row in top_apps.iterrows():
#         plt.annotate(
#             row['app_name'], 
#             xy=(row['total_downloads_bn'], row['scenario_en']),
#             xytext=(0, -15),             
#             textcoords="offset points",  
#             ha='center',                 
#             va='top',                    
#             fontsize=9, 
#             fontweight='bold',           
#             alpha=0.8,
#             color='#333333'              
#         )
#     handles = []
#     for i, category in enumerate(en_category_order):
#         handles.append(plt.scatter([], [], color=palette[i], s=100, alpha=0.6, edgecolor="w", linewidth=1))

#     plt.legend(handles, en_category_order, bbox_to_anchor=(1.05, 1), loc='upper left', title="Categories", fontsize=10)
#     plt.tight_layout()
#     plt.savefig('scatter_custom.png', dpi=300)

# # 3. 分面式分布图（其余部分全部保留不准动）
# def plot_faceted_distribution(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     sns.set(style="whitegrid", font_scale=0.9)
#     g = sns.FacetGrid(
#         df, col="scenario_en", col_wrap=4, hue="scenario_en",
#         sharex=True, sharey=False, height=3, aspect=1.2,
#         palette="viridis", col_order=en_category_order
#     )
#     # 修改点1：调整分面式分布图的整体figsize为（10，8）
#     g.fig.set_size_inches(10, 8)
    
#     g.map(sns.histplot, "log_downloads", kde=True, bins=10, alpha=0.4)
#     g.set_axis_labels("Log10 Downloads (Bn)", "Density")
#     g.set_titles("") 
#     for ax, title_text in zip(g.axes.flat, en_category_order):
#         ax.set_title(title_text, fontsize=11, fontweight='bold')
#     plt.subplots_adjust(top=0.9)
#     g.fig.suptitle('Faceted Distribution of App Downloads (8 Categories)', fontsize=15)
#     plt.tight_layout()
#     plt.savefig('distribution_facet.png', dpi=300)

# # 4. 优化后的小提琴图（其余部分全部保留不准动）
# def plot_violin_comparison(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     plt.figure(figsize=(10, 8))
#     sns.violinplot(
#         data=df, x='scenario_en', y='log_downloads',
#         order=en_category_order,
#         inner="stick", palette="Blues_r", cut=0
#     )

#     plt.xticks(rotation=0, ha='center', fontsize=9.5) 
#     plt.yticks(fontsize=10)
    
#     plt.title("Comparison of Download Distributions Across 8 App Categories", fontsize=15, pad=15)
#     plt.ylabel("Log10 Total Downloads (Billions)", fontsize=12)
#     plt.xlabel("", fontsize=10) 
    
#     plt.grid(axis='y', linestyle='--', alpha=0.4)
    
#     plt.tight_layout()
#     plt.savefig('distribution_violin.png', dpi=300)

# if __name__ == "__main__":
#     try:
#         data_df = load_and_clean_data('AppUi.json')
#         plot_custom_scatter(data_df)
#         plot_faceted_distribution(data_df)
#         plot_violin_comparison(data_df)
#         print("Success: All modifications applied.")
#     except Exception as e:
#         print(f"Error: {e}")


# import json
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns
# from matplotlib.ticker import MaxNLocator

# # ================= 1. 业务逻辑设置 =================
# # 优化点：在长标签中加入 \n 换行符，将单行长标题转为双行，压缩横向空间
# category_labels = {
#     '视频娱乐': 'Media &\nEntertainment',
#     '办公协作': 'Office\nCollaboration',
#     '出行旅游': 'Travel &\nMap',
#     '电商购物': 'E-commerce',
#     '社交媒体': 'Social\nMedia',
#     '金融与支付': 'Finance &\nPayment',
#     'AI助手': 'AI\nAssistant',
#     '生活方式': 'Lifestyle'
# }

# category_order = ['视频娱乐', '办公协作', '出行旅游', '电商购物', '社交媒体', '金融与支付', 'AI助手', '生活方式']
# en_category_order = [category_labels[cat] for cat in category_order]

# plt.rcParams['font.sans-serif'] = ['Arial', 'sans-serif']
# plt.rcParams['axes.unicode_minus'] = False

# def load_and_clean_data(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#     df = pd.DataFrame(data)

#     def parse_download(val):
#         if pd.isna(val) or val == "N/A" or val == "": return 0.0
#         val = str(val).replace('+', '').upper()
#         if 'B' in val: return float(val.replace('B', ''))
#         if 'M' in val: return float(val.replace('M', '')) / 1000.0
#         if 'K' in val: return float(val.replace('K', '')) / 1000000.0
#         return 0.0

#     df['total_downloads_bn'] = df['china_android_downloads'].apply(parse_download) + \
#                                df['google_play_downloads'].apply(parse_download)
#     df = df[df['total_downloads_bn'] > 0].copy()
    
#     df['scenario_en'] = df['scenario'].map(category_labels)
#     df['scenario_en'] = pd.Categorical(df['scenario_en'], categories=en_category_order, ordered=True)
#     return df

# # 2. 高度定制化散点图（保持不变）
# def plot_custom_scatter(df):
#     plt.figure(figsize=(10, 8))
#     sns.set_style("whitegrid")
#     palette = sns.color_palette("husl", 8)
    
#     scatter = sns.scatterplot(
#         data=df, x='total_downloads_bn', y='scenario_en',
#         hue='scenario_en', size='total_downloads_bn', sizes=(100, 1000),
#         alpha=0.6, palette=palette, edgecolor="w", linewidth=1, legend=False
#     )
#     plt.xscale('symlog', linthresh=1.0)
#     plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.3)
#     plt.text(1.05, 0.5, "1 Billion (Threshold)", color='red', transform=scatter.get_xaxis_transform())

#     plt.title("App Market Distribution by Category & Downloads", fontsize=14)
#     plt.xlabel("Total Downloads (Billions, Log-Scale after 1B)", fontsize=12)
#     plt.ylabel("App Category", fontsize=12)

#     # top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario_en').head(1)
#     # for _, row in top_apps.iterrows():
#     #     plt.text(row['total_downloads_bn'], row['scenario_en'], f"  {row['app_name']}", fontsize=9, alpha=0.7)
#     # 标注每个类别的 Top 1 App，位置设在散点正下方
#     top_apps = df.sort_values('total_downloads_bn', ascending=False).groupby('scenario_en').head(1)
#     for _, row in top_apps.iterrows():
#         plt.annotate(
#             row['app_name'], 
#             xy=(row['total_downloads_bn'], row['scenario_en']),
#             xytext=(0, -15),             # 向下偏移 15 个像素点，确保在气泡下方
#             textcoords="offset points",  # 使用相对像素偏移，不受坐标轴缩放影响
#             ha='center',                 # 水平居中对齐
#             va='top',                    # 垂直方向顶部对齐
#             fontsize=9, 
#             fontweight='bold',           # 加粗以提高辨识度
#             alpha=0.8,
#             color='#333333'              # 深灰色，比纯黑更具高级感
#         )
#     handles = []
#     for i, category in enumerate(en_category_order):
#         handles.append(plt.scatter([], [], color=palette[i], s=100, alpha=0.6, edgecolor="w", linewidth=1))

#     plt.legend(handles, en_category_order, bbox_to_anchor=(1.05, 1), loc='upper left', title="Categories", fontsize=10)
#     plt.tight_layout()
#     plt.savefig('scatter_custom.png', dpi=300)

# # 3. 分面式分布图（保持不变）
# def plot_faceted_distribution(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     sns.set(style="whitegrid", font_scale=0.9)
#     g = sns.FacetGrid(
#         df, col="scenario_en", col_wrap=4, hue="scenario_en",
#         sharex=True, sharey=False, height=3, aspect=1.2,
#         palette="viridis", col_order=en_category_order
#     )
#     g.map(sns.histplot, "log_downloads", kde=True, bins=10, alpha=0.4)
#     g.set_axis_labels("Log10 Downloads (Bn)", "Density")
#     g.set_titles("") 
#     for ax, title_text in zip(g.axes.flat, en_category_order):
#         ax.set_title(title_text, fontsize=11, fontweight='bold')
#     plt.subplots_adjust(top=0.9)
#     g.fig.suptitle('Faceted Distribution of App Downloads (8 Categories)', fontsize=15)
#     plt.tight_layout()
#     plt.savefig('distribution_facet.png', dpi=300)

# # 4. 优化后的小提琴图
# def plot_violin_comparison(df):
#     df['log_downloads'] = np.log10(df['total_downloads_bn'])
#     # 调整画布比例，稍微增加高度，让主体更显眼
#     plt.figure(figsize=(10, 8))
#     #mako_r
#     sns.violinplot(
#         data=df, x='scenario_en', y='log_downloads',
#         order=en_category_order,
#         inner="stick", palette="Blues_r", cut=0
#     )

#     # 优化点：
#     # 1. 旋转角度设为 0（水平）或 15度，因为有了换行，水平显示也不拥挤
#     # 2. 减小横轴字体到 9.5，增加 y 轴字体
#     plt.xticks(rotation=0, ha='center', fontsize=9.5) 
#     plt.yticks(fontsize=10)
    
#     plt.title("Comparison of Download Distributions Across 8 App Categories", fontsize=15, pad=15)
#     plt.ylabel("Log10 Total Downloads (Billions)", fontsize=12)
#     plt.xlabel("", fontsize=10) # 隐藏横轴标题，因为图标本身已经很清晰
    
#     # 增加网格线透明度，减少视觉干扰
#     plt.grid(axis='y', linestyle='--', alpha=0.4)
    
#     plt.tight_layout()
#     plt.savefig('distribution_violin.png', dpi=300)

# if __name__ == "__main__":
#     try:
#         data_df = load_and_clean_data('AppUi.json')
#         plot_custom_scatter(data_df)
#         plot_faceted_distribution(data_df)
#         plot_violin_comparison(data_df)
#         print("Success: Violin plot layout optimized for better readability.")
#     except Exception as e:
#         print(f"Error: {e}")
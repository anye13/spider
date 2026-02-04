import os
import re
import time
import random
import jieba
import pandas as pd
import requests
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from snownlp import SnowNLP
from collections import Counter
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from pyecharts import options as opts
from pyecharts.charts import Pie, Line, HeatMap, Bar, WordCloud
ua = UserAgent()

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


# 3. 数据预处理
def preprocess_comments(df):
    """
    数据预处理：清洗、分词、去停用词
    :param df: 包含评论的DataFrame
    :return: 处理后的DataFrame
    """
    # 数据清洗
    df = df.drop_duplicates()
    df = df.dropna()
    # 中文分词
    stopwords = set(line.strip() for line in open('file/baidu_stopwords.txt', encoding='utf-8'))

    def process_text(text):
        words = jieba.cut(text)
        return ' '.join([word for word in words if word not in stopwords and len(word) > 1])

    df['cleaned_comment'] = df['comment'].apply(process_text)
    return df


# 4. 情感分析
def sentiment_analysis(df):
    """
    使用SnowNLP进行情感分析
    :param df: 包含评论的DataFrame
    :return: 添加情感得分的DataFrame
    """

    def get_sentiment(text):
        s = SnowNLP(text)
        return s.sentiments

    df['sentiment'] = df['comment'].apply(get_sentiment)
    return df


# 5. 可视化（使用pyecharts实现交互式图表）
def generate_visualizations(df, attraction_name="杭州西湖"):
    """
    生成五种可视化图表（使用pyecharts）
    :param df: 包含处理后的数据和情感得分的DataFrame
    :param attraction_name: 景点名称
    """
    # 确保结果目录存在
    os.makedirs('result', exist_ok=True)

    # 1. 词云图
    all_text = ' '.join(df['cleaned_comment'])
    words = jieba.lcut(all_text)
    word_counts = Counter(words)
    word_data = [(word, count) for word, count in word_counts.items() if len(word) > 1]

    wc = (
        WordCloud()
        .add("", word_data, word_size_range=[20, 100], shape="diamond")
        .set_global_opts(
            title_opts=opts.TitleOpts(title=f"{attraction_name}评论高频词云图"),
            tooltip_opts=opts.TooltipOpts(is_show=True)
        )
    )
    wc.render(f'result/{attraction_name}_wordcloud.html')

    # 2. 情感分布饼图
    df['sentiment_label'] = pd.cut(df['sentiment'],
                                   bins=[0, 0.4, 0.7, 1],
                                   labels=['消极', '中性', '积极'])
    sentiment_counts = df['sentiment_label'].value_counts()

    pie = (
        Pie()
        .add("", [list(z) for z in zip(sentiment_counts.index.tolist(), sentiment_counts.values.tolist())])
        .set_global_opts(
            title_opts=opts.TitleOpts(title=f"{attraction_name}评论情感分布"),
            legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="2%")
        )
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
    )
    pie.render(f'result/{attraction_name}_sentiment_pie.html')

    # 3. 情感趋势折线图（按月份）
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        monthly_sentiment = df.resample('M', on='date')['sentiment'].mean()

        line = (
            Line()
            .add_xaxis(monthly_sentiment.index.strftime('%Y-%m').tolist())
            .add_yaxis("情感得分", monthly_sentiment.values.round(3).tolist(),
                       is_smooth=True,
                       markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="max")]))
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f"{attraction_name}评论情感趋势"),
                xaxis_opts=opts.AxisOpts(name="月份"),
                yaxis_opts=opts.AxisOpts(name="平均情感得分"),
                datazoom_opts=[opts.DataZoomOpts()],  # 添加缩放功能
                tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross")
            )
        )
        line.render(f'result/{attraction_name}_sentiment_trend.html')

    # 4. 热力图（使用pyecharts）
    if 'date' in df.columns:
        # 提取月份和小时信息
        df['month'] = df['date'].dt.month
        df['hour'] = df['date'].dt.hour

        # 创建热力图数据
        heatmap_data = []
        for month in range(1, 13):
            for hour in range(0, 24):
                subset = df[(df['month'] == month) & (df['hour'] == hour)]
                if not subset.empty:
                    avg_sentiment = subset['sentiment'].mean()
                    heatmap_data.append([str(month), str(hour), round(avg_sentiment, 2)])

        heatmap = (
            HeatMap()
            .add_xaxis([str(i) for i in range(1, 13)])
            .add_yaxis(
                "情感得分",
                [str(i) for i in range(24)],
                heatmap_data,
                label_opts=opts.LabelOpts(is_show=True, position="inside"),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f"{attraction_name}情感得分热力图 (按月份和小时)"),
                visualmap_opts=opts.VisualMapOpts(
                    min_=0, max_=1,
                    range_color=["#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8", "#ffffbf", "#fee090", "#fdae61",
                                 "#f46d43", "#d73027", "#a50026"]
                ),
                tooltip_opts=opts.TooltipOpts(formatter="{b}月{c}时: {d}分"),
                legend_opts=opts.LegendOpts(is_show=False),
            )
        )
        heatmap.render(f'result/{attraction_name}_heatmap.html')

    # 5. 柱状图（使用pyecharts）
    # 提取所有词语
    all_words = ' '.join(df['cleaned_comment']).split()
    word_freq = Counter(all_words)
    top_words = word_freq.most_common(20)

    bar = (
        Bar()
        .add_xaxis([word[0] for word in top_words])
        .add_yaxis("出现频率", [word[1] for word in top_words])
        .set_global_opts(
            title_opts=opts.TitleOpts(title=f"{attraction_name}评论高频词TOP20"),
            xaxis_opts=opts.AxisOpts(name="词语", axislabel_opts=opts.LabelOpts(rotate=45)),
            yaxis_opts=opts.AxisOpts(name="出现频率"),
            datazoom_opts=[opts.DataZoomOpts(type_="inside")],  # 内置型数据区域缩放
            toolbox_opts=opts.ToolboxOpts(),  # 添加工具箱
        )
        .set_series_opts(
            label_opts=opts.LabelOpts(is_show=True),
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(type_="max", name="最大值"),
                    opts.MarkPointItem(type_="min", name="最小值")
                ]
            )
        )
    )
    bar.render(f'result/{attraction_name}_bar_chart.html')

class QuNaRCrawler:
    def __init__(self, attraction_name="杭州西湖",
                 attraction_url='https://travel.qunar.com/p-oi708952-xihufengjingmingsheng'):
        # 初始化景点信息
        self.attraction_name = attraction_name
        self.attraction_url = attraction_url
        # 初始化浏览器
        self.service = Service(executable_path='../chromedriver.exe')
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.options.add_argument('--disable-infobars')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--start-maximized')
        self.options.add_argument('--disable-popup-blocking')
        self.options.add_argument('--disable-notifications')
        self.options.add_argument(f'{ua.random}')
        self.driver = webdriver.Chrome(service=self.service, options=self.options)
        self.comments = []
        self.dates = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': ua.random,
            'Connection': 'keep-alive'
        })

    def scrape_qunar_comments(self, pages=20):
        """
        爬取去哪儿网景点评论
        :param pages: 需要爬取的页数
        :return: 包含评论和日期的DataFrame
        """
        print(f"开始爬取: {self.attraction_name}")
        self.driver.get(self.attraction_url)
        time.sleep(3)  # 等待页面加载

        for page in range(1, pages + 1):
            try:
                # 等待评论加载完成
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'b_comment_box'))
                )
                self.extract_data(self.driver.page_source)
                print(f'已抓取第 {page}/{pages} 页，累计评论数: {len(self.comments)}')
                time.sleep(2)  # 防止请求过快

                # 尝试翻页
                next_buttons = self.driver.find_elements(By.XPATH, '//a[@class="page next"]')
                if next_buttons:
                    next_buttons[0].click()
                    time.sleep(random.uniform(2, 4))
                else:
                    print("没有找到下一页按钮，可能已到最后一页")
                    break

            except Exception as e:
                print(f"爬取第 {page} 页时出错: {str(e)}")
                break

        # 创建DataFrame
        df = pd.DataFrame({
            'comment': self.comments,
            'date': self.dates
        })

        # 确保结果目录存在
        os.makedirs('result', exist_ok=True)

        csv_path = f'result/{self.attraction_name}_comments.csv'
        df.to_csv(csv_path, index=False, encoding='utf_8_sig')
        print(f"评论已保存到 {csv_path}")
        return df

    def extract_data(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        # 获取评论
        comments = soup.find_all("li", attrs={"class": "e_comment_item clrfix"})
        for comment in comments:
            try:
                a = comment.find("a", attrs={"class": "seeMore"})
                if a and a.get('href'):
                    response = self.session.get(a.get('href'), timeout=20)
                    if response.status_code != 200:
                        print(f"请求失败，状态码: {response.status_code}")
                        continue
                    sub_soup = BeautifulSoup(response.text, 'html.parser')
                    text_div = sub_soup.find("div", attrs={"class": "comment_content"})
                    if text_div:
                        text = text_div.text.strip()
                        self.comments.append(text)
                    else:
                        print("未找到评论内容")
                        continue
                else:
                    text_div = comment.find("div", attrs={"class": "e_comment_content"})
                    if text_div:
                        text = text_div.text.strip()
                        self.comments.append(text)
                    else:
                        print("未找到评论内容")
                        continue
            except Exception as e:
                print(f"提取评论时出错: {str(e)}")
                continue
            try:
                # 提取日期
                add_info = comment.find("div", attrs={"class": "e_comment_add_info"})
                if add_info:
                    lis = add_info.find_all("li")
                    if lis:
                        date = lis[0].text.strip()
                        pattern = r'\d{4}-\d{2}-\d{2}'  # 匹配 YYYY-MM-DD 格式
                        match = re.search(pattern, date)
                        if match:
                            date = match.group()  # 提取匹配的日期字符串
                        self.dates.append(date)
                    else:
                        self.dates.append("未知日期")
                else:
                    self.dates.append("未知日期")
            except Exception as e:
                print(f"提取日期时出错: {str(e)}")
                self.dates.append("未知日期")
            print(text[:20], date)

    def run(self):
        """主运行函数"""
        # 数据抓取
        print("开始抓取评论数据...")
        df = self.scrape_qunar_comments()
        print(f"成功抓取 {len(df)} 条评论")

        if df.empty:
            print("未获取到评论数据，程序终止")
            self.driver.quit()
            return

        # 数据预处理
        print("进行数据预处理...")
        df = preprocess_comments(df)

        # 情感分析
        print("进行情感分析...")
        df = sentiment_analysis(df)

        # 确保结果目录存在
        os.makedirs('result', exist_ok=True)

        processed_path = f'result/{self.attraction_name}_comments_processed.csv'
        df.to_csv(processed_path, index=False, encoding='utf-8-sig')
        print(f"处理后的数据已保存到 {processed_path}")

        # 可视化
        print("生成可视化图表...")
        generate_visualizations(df, self.attraction_name)
        print("可视化图表已保存为PNG文件")
        # 关闭浏览器
        self.driver.quit()


if __name__ == "__main__":
    # 运行爬虫和分析
    crawler = QuNaRCrawler()
    crawler.run()

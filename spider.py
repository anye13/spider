import requests
from bs4 import BeautifulSoup
import time
import csv
from tqdm import tqdm
import random
from fake_useragent import UserAgent
ua = UserAgent()
# 设置请求头模拟浏览器访问
headers = {
    'User-Agent': ua.random,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive'
}

# 基础URL
BASE_URL = "https://shxyj.ajcass.com"
DIRECTORY_URL = BASE_URL + "/Magazine/"


def get_article_links(page_count=3):
    """获取前三页的文章链接"""
    article_links = []

    for page in range(1, page_count + 1):
        # 构造目录页URL
        params = {
            'Year': '2024',
            'PageIndex': page,
            'Issue': '',
            'JChannelID': '',
            'Title': '',
            'Authors': '',
            'WorkUnit': ''
        }

        try:
            response = requests.get(DIRECTORY_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            # 找到所有文章项
            items = soup.select('tr')
            flag = True
            for item in items:
                if flag:  # 过滤表头
                    flag = False
                    continue
                # 提取文章详情页链接
                link = item.select_one('a[href^="/Magazine/show/?id="]')
                if link:
                    URL = BASE_URL + link['href']
                    article_links.append(URL)

            print(f"已获取第 {page} 页，共 {len(items)} 篇文章链接")
            time.sleep(random.uniform(1, 2))  # 随机延时

        except Exception as e:
            print(f"获取第 {page} 页失败: {e}")

    return article_links


def parse_article_page(url):
    """解析单篇文章页面"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取文章标题
        temp = soup.find('div', attrs={'class': 'C_right'}).find_all('div')
        title = temp[0].get_text(strip=True) if temp[0].get_text(strip=True) else ""

        # 提取作者信息
        row = soup.find_all('tr')
        temp = row[4].find_all('td')
        author = temp[1].get_text(strip=True) if temp[1] else ""
        temp = row[6].find_all('td')
        work_unit = temp[1].get_text(strip=True) if temp[1] else ""

        # 提取摘要
        temp = row[1].find_all('td')
        abstract = temp[1].find('p').get_text(strip=True) if temp[1] else ""
        # 英文摘要
        temp = row[2].find_all('td')
        abstract_en = temp[1].find('p').get_text(strip=True) if temp[1] else ""

        # 提取关键词
        temp = row[16].find_all('td')
        keywords = temp[1].get_text(strip=True) if temp[1] else ""

        # 提取期刊信息
        temp = row[8].find_all('td')
        journal_name = temp[1].get_text(strip=True) if temp[1] else ""

        # 提取年·期
        temp = row[10].find_all('td')
        year_issue = temp[1].get_text(strip=True) if temp[1] else ""
        print({
            "标题": title,
            "摘要": abstract,
            "英文摘要": abstract_en,
            "作者": author,
            "作者单位": work_unit,
            "期刊": journal_name,
            "年.期": year_issue,
            "关键词": keywords,
            "文章链接": url
        })
        return {
            "标题": title,
            "摘要": abstract,
            "英文摘要": abstract_en,
            "作者": author,
            "作者单位": work_unit,
            "期刊": journal_name,
            "年.期": year_issue,
            "关键词": keywords,
            "文章链接": url
        }

    except Exception as e:
        print(f"解析文章失败: {url} - {e}")
        return None


def main():
    # 1. 获取文章链接
    print("开始获取文章链接...")
    article_links = get_article_links(3)
    print(f"共获取到 {len(article_links)} 篇文章链接")

    # 2. 爬取文章数据
    articles_data = []
    print("\n开始爬取文章详情...")

    for link in tqdm(article_links, desc="爬取进度"):
        article_data = parse_article_page(link)
        if article_data:
            articles_data.append(article_data)
        time.sleep(random.uniform(1, 3))  # 随机延时防止被封

    # 3. 保存到CSV文件
    if articles_data:
        filename = f"result/上海研究院期刊_2024_{time.strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ["标题", "摘要", "英文摘要", "作者", "作者单位", "期刊", "年.期", "关键词", "文章链接"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(articles_data)
        print(f"\n数据已保存到: {filename}")
        print(f"共爬取 {len(articles_data)} 篇文章")
    else:
        print("未获取到有效数据")


if __name__ == "__main__":
    main()
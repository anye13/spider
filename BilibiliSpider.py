import random
import time
import csv
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from fake_useragent import UserAgent
import re

# 初始化 UserAgent，限制为常见桌面浏览器
desktop_browsers = ['chrome', 'firefox', 'safari', 'edge', 'opera']
ua = UserAgent(browsers=desktop_browsers)


def get_pc_user_agent():
    while True:
        user_agent = ua.random
        # 正则过滤移动端关键词（忽略大小写）
        if not re.search(r'Mobile|Android|iPhone|iPad|Windows Phone', user_agent, re.IGNORECASE):
            return user_agent


class BilibiliCrawler:
    def __init__(self, keyword, max_pages=10, headless=True):
        self.keyword = keyword  # 搜索关键词
        self.max_pages = max_pages  # 最大爬取页数
        self.data = []  # 存储爬取数据
        # 初始化浏览器
        self.driver = self._init_browser(headless)
        self.wait = WebDriverWait(self.driver, 15)

    def _init_browser(self, headless):
        """初始化浏览器配置"""
        # options = webdriver.EdgeOptions()
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={get_pc_user_agent()}')
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-application-cache')
        options.add_argument('--disable-cache')
        options.add_argument('--disk-cache-size=0')
        # service = Service(executable_path='../msedgedriver.exe')
        service = Service(executable_path='../chromedriver.exe')
        # driver = webdriver.Edge(service=service, options=options)
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5)
        return driver

    def __del__(self):
        """析构函数：关闭浏览器"""
        self.driver.quit()

    def login(self):

        login_button = WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@class="header-login-entry"]'))
        )
        login_button.click()
        # time.sleep(10)  # 等待页面加载
        # login_item = WebDriverWait(self.driver, 30).until(
        #     EC.presence_of_element_located((By.XPATH, '//div[@class="login-pwd-wp"]'))
        # )
        # inputs = login_item.find_elements(By.XPATH, '//div[@class="form__item"]//input')
        # inputs[0].send_keys(self.account)
        # inputs[1].send_keys(self.password)
        # login_item.find_element(By.XPATH, '//div[@class="btn_primary "]').click()
        time.sleep(20)

    def search_keyword(self):
        """访问首页并执行搜索操作"""
        print(f"正在抓取{self.keyword}关键字内容")
        # 记录当前窗口句柄
        current_handles = self.driver.window_handles
        # 定位搜索框并输入关键词（XPath）
        search_box = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@class="nav-search-input"]'))
        )
        search_box.send_keys(self.keyword)

        # 点击搜索按钮（XPath）
        search_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@class="nav-search-btn"]'))
        )
        search_button.click()
        time.sleep(random.uniform(1, 3))
        # 等待新标签页打开
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: len(d.window_handles) > len(current_handles)
            )
        except TimeoutException:
            print("错误：新标签页未打开")
            self.driver.save_screenshot("error_new_tab.png")
            return

        # 切换到新标签页
        new_handles = self.driver.window_handles
        new_tab_handle = [handle for handle in new_handles if handle not in current_handles][0]
        self.driver.switch_to.window(new_tab_handle)
        print("已切换到新标签页，URL:", self.driver.current_url)

    def extract_video_info(self):
        """提取当前页面的视频信息"""
        # print("正在加载视频列表")
        time.sleep(random.uniform(5, 10))
        # 等待视频列表加载完成（XPath）
        # WebDriverWait(self.driver, 10).until(
        #     EC.presence_of_element_located((By.XPATH, '//div[@class="video-list row"]'))
        # )
        # 定位所有视频块（XPath）
        video_items = self.driver.find_elements(By.XPATH, '//div[@class="bili-video-card"]')
        video_items_xpath = '//div[@class="video-list row"]/div[1]'
        # 提取第一个视频的信息
        try:
            # 标题（XPath）
            title = self.driver.find_element(By.XPATH,
                                             f'{video_items_xpath}//h3[@class="bili-video-card__info--tit"]').text.strip()
            # 链接（XPath）
            link = self.driver.find_element(By.XPATH,
                                            f'{video_items_xpath}//div[@class="bili-video-card__info--right"]/a').get_attribute(
                "href")
            # UP主（XPath）
            up = self.driver.find_element(By.XPATH,
                                          f'{video_items_xpath}//span[@class="bili-video-card__info--author"]').text.strip()

            # 播放量（XPath）
            play_count = self.driver.find_element(By.XPATH,
                                                  f'{video_items_xpath}//span[@class="bili-video-card__stats--item"][1]/span').text.strip()
            # 评论量
            comments_count = self.driver.find_element(By.XPATH,
                                                      f'{video_items_xpath}//span[@class="bili-video-card__stats--item"][2]/span').text.strip()
            print({
                "title": title,
                "link": link,
                "up": up,
                "play_count": play_count,
                "comments_count": comments_count
            })
            self.data.append({
                "title": title,
                "link": link,
                "up": up,
                "play_count": play_count,
                "comments_count": comments_count
            })
        except Exception as e:
            print(f"提取数据失败: {e}")

    def switch_to_next_page(self):
        """切换到下一页（XPath）"""
        try:
            next_button = self.driver.find_elements(By.XPATH,
                                                   '//button[@class="vui_button vui_pagenation--btn vui_pagenation--btn-side"]')
            if len(next_button) > 1:
                next_button[1].click()
            else:
                next_button[0].click()
            time.sleep(random.uniform(3, 5))  # 等待页面加载
            return True
        except Exception as e:
            return False

    def crawl(self):
        """执行爬取流程"""
        self.driver.get("https://www.bilibili.com/")
        time.sleep(random.uniform(1.5, 3))
        self.login()

        self.search_keyword()

        current_page = 1
        while current_page <= self.max_pages:
            print(f"正在爬取第 {current_page} 页...")
            self.extract_video_info()

            if not self.switch_to_next_page():
                print("已到达最后一页")
                break
            current_page += 1

    def save_to_csv(self, filename="bilibili_videos.csv"):
        """保存数据到 CSV 文件"""
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "link", "up", "play_count", "comments_count"])
            writer.writeheader()
            writer.writerows(self.data)
        print(f"数据已保存至 {filename}")


if __name__ == "__main__":
    # 示例：搜索“Python”并爬取前10页
    crawler = BilibiliCrawler(keyword="Python", max_pages=10, headless=False)
    crawler.crawl()
    crawler.save_to_csv()

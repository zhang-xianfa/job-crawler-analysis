# =========================================================
#  main.py - 智联招聘主入口 | 无登录/无滑块/无code37
# =========================================================
import sys
import os
import time
import random
import csv

sys.stdout.reconfigure(encoding='utf-8')

from modules.zhaopin import fetch_zhaopin_page
from modules.database import MySQLManager
from modules.analyzer import DataAnalyzer

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CRAWL_KEYWORDS = [
    'java开发', '前端开发', '后端开发', '数据分析师',
    '算法工程师', 'python开发', '软件测试', '产品经理'
]

PAGES_PER_KEYWORD = 40

def save_csv(job_list):
    if len(job_list) == 0:
        return
    keys = list(job_list[0].keys())
    ts = str(int(time.time()))[-6:]
    path = os.path.join(OUTPUT_DIR, f'智联招聘_{len(job_list)}条_{ts}.csv')
    fh = open(path, 'a', newline='', encoding='utf-8-sig')
    writer = csv.DictWriter(fh, fieldnames=keys)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        writer.writeheader()
    writer.writerows(job_list)
    fh.close()

def mysql_config():
    return {
        'mysql_host': os.getenv('MYSQL_HOST', 'localhost'),
        'mysql_port': int(os.getenv('MYSQL_PORT', '3306')),
        'mysql_user': os.getenv('MYSQL_USER', 'root'),
        'mysql_password': os.getenv('MYSQL_PASSWORD', 'root'),
        'mysql_db': os.getenv('MYSQL_DB', 'recruitment_db'),
    }

def crawl_loop():
    print('\n' + '#' * 70)
    print('# 智联招聘 - 极简稳定版')
    print('#  特点: 无需登录/无滑块验证/无code37风控')
    print('#' * 70 + '\n')
    
    config = mysql_config()
    db = MySQLManager(config)
    db_ok = False
    initial = 0
    
    if db.connect():
        db.create_database()
        db.create_table()
        try:
            db.cursor.execute('TRUNCATE TABLE jobs')
            db.conn.commit()
            print('[i] 数据库jobs表已清空重跑 ✓')
        except Exception as e:
            print(f'[i] 清空表跳过: {e}')
        initial = db.get_count()
        print(f'[i] MySQL初始记录数: {initial}')
        db_ok = True
    else:
        print('[!] MySQL暂未连接，只存CSV')
    
    ALL_JOBS = 0
    pages_ok = 0
    
    for kw_idx, keyword in enumerate(CRAWL_KEYWORDS):
        print(f'\n{"="*60}')
        print(f'关键词 {kw_idx+1}/{len(CRAWL_KEYWORDS)}: {keyword}')
        print(f'{"="*60}')
        
        for page in range(1, PAGES_PER_KEYWORD + 1):
            jobs = fetch_zhaopin_page(keyword, page)
            cnt = len(jobs)
            
            if cnt > 0:
                pages_ok += 1
                ALL_JOBS += cnt
                print(f'  第{page:2d}页 | {cnt:2d}条 | 累计: {ALL_JOBS}')
                if cnt >= 3:
                    for p in jobs[:3]:
                        print(f'    | {p["job_name"][:24]:24s} | {p["salary_range"]:12s} | {p["company_name"][:12]}')
                if jobs and db_ok:
                    db.insert_batch(jobs)
                save_csv(jobs)
            else:
                print(f'  第{page:2d}页 | 无岗位数据')
            
            if page < PAGES_PER_KEYWORD:
                sleep_sec = 3.0 + random.random() * 3.0
                time.sleep(sleep_sec)
        
        if kw_idx < len(CRAWL_KEYWORDS) - 1:
            cooldown = 10 + random.randint(0, 10)
            print(f'\n[*] 关键词切换冷却 {cooldown} 秒...')
            time.sleep(cooldown)
    
    final = 0
    if db_ok:
        final = db.get_count()
        print(f'\nMySQL本次去重后新增: {final - initial} 条')
    
    print(f'\n{"="*60}')
    print('🏁 智联招聘爬取完成')
    print(f'{"="*60}')
    print(f'  本次接口解析总岗位: {ALL_JOBS} 条')
    print(f'  成功解析有效页数: {pages_ok}')
    if db_ok:
        print(f'  MySQL最终总记录数: {final}')
    print(f'  output目录CSV已保存')
    print(f'  可视化查看: python app.py')
    print(f'{"="*60}\n')

if __name__ == '__main__':
    try:
        crawl_loop()
    except KeyboardInterrupt:
        print('\n[i] 用户中断')
    except Exception as e:
        print(f'\n[!] 异常: {e}')
        import traceback
        traceback.print_exc()

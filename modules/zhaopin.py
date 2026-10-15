# =========================================================
#  modules/zhaopin.py - 智联招聘无登录极简爬虫核心模块
# =========================================================
import sys
import os
import time
import random
import re
import requests
import urllib3
from lxml import etree

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
]

CITY_CODES = {
    '763': '全国', '538': '北京', '530': '上海', '765': '深圳', '764': '广州',
    '653': '杭州', '635': '南京', '801': '成都', '736': '武汉', '854': '西安',
}

def get_headers():
    return {
        'User-Agent': random.choice(UA_POOL),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://www.zhaopin.com/',
    }

def zhaopin_request(url, timeout=20):
    resp = requests.get(url, headers=get_headers(), verify=False, timeout=timeout)
    resp.encoding = 'utf-8'
    return resp

def build_zhaopin_search_url(keyword, page=1, city_code='763', page_size=90):
    from urllib.parse import quote
    return 'https://sou.zhaopin.com/?p=%d&pageSize=%d&kw=%s&jl=%s' % (page, page_size, quote(keyword), city_code)

def text_clean(parts):
    all_text = ''
    for p in parts:
        if isinstance(p, str):
            all_text += p.strip()
        elif hasattr(p, 'text'):
            t = (p.text or '').strip()
            if t:
                all_text += t
    return all_text.replace('\n', '').replace('\r', '').strip()

def parse_salary(salary_str):
    min_sal, max_sal, avg_sal = 0, 0, 0
    try:
        salary_str = str(salary_str).replace('K', '').replace('k', '')
        if '-' in salary_str:
            parts = salary_str.split('-')
            if len(parts) == 2:
                min_sal = float(parts[0].strip()) * 1000
                max_part = parts[1].strip()
                if '·' in max_part:
                    max_part = max_part.split('·')[0]
                max_sal = float(max_part) * 1000
                avg_sal = (min_sal + max_sal) / 2
    except:
        pass
    return int(min_sal), int(max_sal), int(avg_sal)

def parse_single_job(job_div):
    try:
        job_id = ''
        job_name = ''
        salary = ''
        company_name = ''
        location = ''
        experience = ''
        education = ''
        
        a_links = job_div.xpath('.//a')
        for a in a_links:
            href = a.get('href', '') or ''
            if 'jobdetail' in href or '/jobs/' in href:
                m = re.search(r'([A-Z0-9]{10,})', href)
                if m:
                    job_id = m.group(1)
                break
        
        name_a = job_div.xpath('.//a[contains(@class, \"jobinfo__name\")]/text()')
        if name_a:
            job_name = text_clean(name_a)
        else:
            fallback = job_div.xpath('.//div[contains(@class, \"jobinfo\")]//a/text()')
            if fallback:
                job_name = text_clean([fallback[0]])
        
        salary_p = job_div.xpath('.//p[contains(@class, \"jobinfo__salary\")]/text()')
        if salary_p:
            salary = text_clean(salary_p)
        
        info_divs = job_div.xpath('.//div[contains(@class, \"jobinfo__other-info\")]//div')
        for idx, d in enumerate(info_divs):
            txt = text_clean([d])
            if idx == 0:
                location = txt.split('·')[0] if '·' in txt else txt
            elif idx == 1:
                experience = txt
            elif idx == 2:
                education = txt
        
        comp_a = job_div.xpath('.//a[contains(@class, \"companyinfo__name\")]/text()')
        if comp_a:
            company_name = text_clean(comp_a)
        
        if len(salary) < 2 and len(job_name) < 2:
            return None
        
        salary_min, salary_max, salary_avg = parse_salary(salary)
        
        return {
            'job_name': job_name or 'N/A',
            'salary_range': salary or 'N/A',
            'salary_min': salary_min,
            'salary_max': salary_max,
            'salary_avg': salary_avg,
            'city_name': location or '城市未知',
            'area_district': '',
            'location': location or '城市未知',
            'company': company_name or '公司未知',
            'company_name': company_name or '公司未知',
            'company_industry': '智联',
            'company_scale': 'N/A',
            'industry': 'N/A',
            'scale': 'N/A',
            'job_experience': experience or 'N/A',
            'experience': experience or 'N/A',
            'job_degree': education or 'N/A',
            'education': education or 'N/A',
            'job_url': '',
            'skills': '',
            'welfare_list': '',
            'welfare': '',
            'job_id': job_id
        }
    except:
        return None

def parse_zhaopin_html(html_content):
    jobs = []
    html = etree.HTML(html_content)
    job_divs = html.xpath('//div[contains(@class, \"joblist-box__item\")]')
    if len(job_divs) < 5:
        job_divs = html.xpath('//div[contains(@class, \"job-card\")]')
    if len(job_divs) < 5:
        job_divs = html.xpath('//div[@class=\"jobinfo\"]/..')
    
    seen = set()
    for d in job_divs:
        job = parse_single_job(d)
        if job and len(job['job_name']) >= 2 and job['job_name'] != 'N/A':
            key = '%s|%s|%s' % (job['job_name'], job['company'], job['salary_range'])
            if key not in seen:
                seen.add(key)
                jobs.append(job)
    
    return jobs

def fetch_zhaopin_page(keyword, page=1, city_code='763'):
    url = build_zhaopin_search_url(keyword, page, city_code)
    resp = zhaopin_request(url)
    if resp.status_code == 200:
        jobs = parse_zhaopin_html(resp.text)
        return jobs
    print('HTTP %d' % resp.status_code)
    return []

if __name__ == '__main__':
    print('=' * 60)
    print('智联招聘模块自测试')
    print('=' * 60)
    
    jobs = fetch_zhaopin_page('java', page=1)
    print('提取岗位数: %d' % len(jobs))
    if len(jobs) > 0:
        for i in range(min(8, len(jobs))):
            j = jobs[i]
            print('%2d. %-24s | %-12s | %s' % (i+1, j['job_name'][:22], j['salary_range'][:10], j['company'][:14]))
    else:
        print('未提取到岗位')
    
    print('\n' + '=' * 60)
    print('自测完成')
    print('=' * 60)

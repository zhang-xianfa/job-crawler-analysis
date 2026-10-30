# 招聘岗位数据采集与分析平台

> Python 爬虫 + 数据清洗入库 + 可视化分析 + Flask 检索看板

采集招聘网站的岗位信息，处理反爬与限流，解析字段写入 MySQL，再做分布统计、薪资分析与
技能词云，最后用 Flask 提供一个可检索的单页看板。

---

## 一、数据采集

- **目标站点**：智联招聘（城市 + 关键词分页检索）
- **反爬对抗措施**：
  - 随机休眠采用**正态分布**（N(4, 1)）而非均匀分布，更接近真人浏览节奏
  - 分页冷却、失败熔断与重试机制
  - 补全 20 个请求头（含 `Sec-CH-UA` / `Sec-Fetch` 等浏览器指纹字段）
- **结果**：稳定采集青岛地区岗位信息 **187 条**（清洗后）

### 附：请求方案调研（结论汇总，非本仓库代码）

BOSS 直聘在第 6 页后会稳定触发 `code=37 环境异常`（风控第 1 层：TCP/TLS 握手的 JA3 指纹校验）。
项目前期在同一课程中做过三套请求方案的对比调研，结论如下：

| 方案 | 请求库 | TLS 指纹 | 拦截率（调研结论） | 成本 |
|---|---|---|---|---|
| A | `requests.Session` | Python 原生 ❌ | **100% 拦截** | 极低 |
| B | `curl_cffi` | 伪装 Chrome ✅ | **~50% 拦截** | 高 |
| C | `Playwright` | 真实 Chromium ✅ | **~20% 拦截** | 极高 |

**结论**：只改 Header 无法绕过风控，必须从 **TLS 指纹层**对抗；无头浏览器效果最好但成本最高。
本项目主干只保留 `requests`：校园网环境与部署成本约束下，用休眠/冷却/请求头组合已能稳定采集，
另两种方案仅作为选型依据，未进入主干代码。

---

## 二、清洗与入库

- 解析 **12 个字段**：岗位名称、薪资区间、公司规模、公司行业、经验要求、学历要求、技能标签等
- **非标准薪资格式处理**：把「90-100 元/时」这类写法统一拆解为 `salary_min` / `salary_max` /
  `salary_avg` 三列后再入库
- 写入 **MySQL**，以 `job_url` 唯一索引去重

---

## 三、分析与可视化

- **薪资描述性分析**：青岛地区平均 **7428 元**、中位数 **6500 元**
- **分布统计**：岗位经验、学历、公司规模三个维度的分布
- **技能需求词云**：`jieba` 分词 + `WordCloud` 生成，停用词表 767 行
- **Flask 看板**：8 个接口 + 单页前端

| 接口 | 作用 |
|---|---|
| `/api/salary-bar` | 薪资区间分布柱状图 |
| `/api/city-pie` | 城市/区域占比饼图 |
| `/api/skill-wordcloud` | 技能词云数据 |
| `/api/job-list` `/api/job-search` | 岗位列表与关键词检索 |
| `/api/cities` `/api/health` | 城市列表 / 健康检查 |

---

## 四、文件结构

```
app.py                 Flask 应用与 8 个 API
main.py                采集主流程
modules/
  zhaopin.py           招聘站点采集 + 薪资格式解析
  database.py          MySQL 读写（建表、去重、批量插入）
  analyzer.py          pandas 统计 + jieba / WordCloud 词云
templates/index.html   单页看板（ECharts）
assets/
  skill_wordcloud.png  技能需求词云（运行产物）
  city_salary_stats.csv 城市薪资统计（岗位数 / 平均 / 中位数）
.env.example           配置模板（Cookie、MySQL）
requirements.txt
```

## 五、运行

```bash
pip install -r requirements.txt
copy .env.example .env        # 填入目标站点 Cookie 与 MySQL 配置
python main.py                # 采集 + 清洗 + 入库
python app.py                 # 启动看板 → http://127.0.0.1:5000
```

---

## 说明

- 仓库**不包含任何抓取到的原始数据**（`output/` 已在 `.gitignore` 中排除），
  仅保留词云与城市薪资统计两份聚合产物。
- 本项目仅用于学习与研究，请遵守目标网站的 `robots.txt` 与服务条款。

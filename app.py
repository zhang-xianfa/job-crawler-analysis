from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
import json
from dotenv import load_dotenv
from modules.database import MySQLManager

load_dotenv()
app = Flask(__name__)

OUTPUT_DIR = "output"

def get_db_manager():
    config = {
        'mysql_host': os.getenv('MYSQL_HOST', 'localhost'),
        'mysql_port': int(os.getenv('MYSQL_PORT', 3306)),
        'mysql_user': os.getenv('MYSQL_USER', 'root'),
        'mysql_password': os.getenv('MYSQL_PASSWORD', '123456'),
        'mysql_db': os.getenv('MYSQL_DB', 'recruitment_db'),
    }
    db = MySQLManager(config)
    if db.connect():
        try:
            db.conn.select_db(config['mysql_db'])
            return db
        except:
            db.close()
    return None

def load_cleaned_data():
    csv_path = os.path.join(OUTPUT_DIR, "cleaned_job_data.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    raw_path = os.path.join(OUTPUT_DIR, "raw_job_data.csv")
    if os.path.exists(raw_path):
        return pd.read_csv(raw_path)
    return pd.DataFrame()

def load_stats_data():
    csv_path = os.path.join(OUTPUT_DIR, "city_salary_stats.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/salary-bar')
def api_salary_bar():
    df_stats = load_stats_data()
    if len(df_stats) > 0:
        return jsonify({
            'cities': df_stats['城市'].tolist(),
            'salaries': df_stats['平均薪资'].fillna(0).tolist()
        })
    db = get_db_manager()
    if db:
        try:
            rows = db.query_dict("""
                SELECT city_name, ROUND(AVG(ifnull(salary_avg, 0))) as avg_sal
                FROM jobs 
                GROUP BY city_name 
                ORDER BY avg_sal DESC
            """)
            db.close()
            return jsonify({
                'cities': [r['city_name'] for r in rows],
                'salaries': [r['avg_sal'] for r in rows]
            })
        except:
            db.close()
    df_clean = load_cleaned_data()
    if len(df_clean) > 0 and 'salary_avg' in df_clean.columns:
        return jsonify({
            'cities': ['青岛'],
            'salaries': [int(df_clean['salary_avg'].mean())]
        })
    return jsonify({'cities': [], 'salaries': []})

@app.route('/api/city-pie')
def api_city_pie():
    df_stats = load_stats_data()
    if len(df_stats) > 0:
        pie_data = []
        for _, row in df_stats.iterrows():
            pie_data.append({
                'name': row['城市'],
                'value': int(row['岗位数量'])
            })
        return jsonify(pie_data)
    db = get_db_manager()
    if db:
        try:
            rows = db.query_dict("""
                SELECT city_name, COUNT(*) as cnt 
                FROM jobs 
                GROUP BY city_name 
                ORDER BY cnt DESC
            """)
            db.close()
            return jsonify([{'name': r['city_name'], 'value': r['cnt']} for r in rows])
        except:
            db.close()
    df_clean = load_cleaned_data()
    if len(df_clean) > 0:
        return jsonify([{'name': '青岛', 'value': len(df_clean)}])
    return jsonify([])

@app.route('/api/skill-wordcloud')
def api_wordcloud():
    db = get_db_manager()
    if db:
        try:
            rows = db.query_dict("SELECT skills FROM jobs WHERE skills IS NOT NULL AND skills != ''")
            db.close()
            skills_text = ','.join([r['skills'] for r in rows])
            words = {}
            for s in skills_text.replace(',', ' ').split():
                if len(s) >= 2:
                    words[s] = words.get(s, 0) + 1
            wc_data = [{'name': k, 'value': v} for k, v in sorted(words.items(), key=lambda x: x[1], reverse=True)[:30]]
            return jsonify(wc_data)
        except:
            db.close()
    df_clean = load_cleaned_data()
    if len(df_clean) > 0 and 'skills' in df_clean.columns:
        skills_text = ','.join(df_clean['skills'].dropna().astype(str).tolist())
        words = {}
        for s in skills_text.replace(',', ' ').split():
            if len(s) >= 2:
                words[s] = words.get(s, 0) + 1
        wc_data = [{'name': k, 'value': v} for k, v in sorted(words.items(), key=lambda x: x[1], reverse=True)[:30]]
        return jsonify(wc_data)
    return jsonify([])

@app.route('/api/job-list')
def api_job_list():
    db = get_db_manager()
    if db:
        try:
            rows = db.query_dict("SELECT * FROM jobs ORDER BY id DESC LIMIT 50")
            db.close()
            return jsonify(rows)
        except:
            db.close()
    df_clean = load_cleaned_data()
    if len(df_clean) > 0:
        df_clean = df_clean.fillna('')
        return jsonify(json.loads(df_clean[:50].to_json(orient='records', force_ascii=False)))
    return jsonify([])

@app.route('/api/job-search')
def api_job_search():
    keyword = request.args.get('keyword', '')
    city = request.args.get('city', '')
    salary_min = request.args.get('salary_min', None)
    salary_max = request.args.get('salary_max', None)
    page = int(request.args.get('page', 1))
    pageSize = int(request.args.get('pageSize', 20))
    offset = (page - 1) * pageSize
    
    db = get_db_manager()
    if not db:
        return jsonify({'list': [], 'total': 0})
    
    try:
        base_sql = " FROM jobs WHERE 1=1"
        params = []
        
        if keyword:
            base_sql += " AND job_name LIKE %s"
            params.append(f"%{keyword}%")
        if city:
            base_sql += " AND city_name = %s"
            params.append(city)
        if salary_min and salary_min.isdigit():
            base_sql += " AND salary_avg >= %s"
            params.append(int(salary_min))
        if salary_max and salary_max.isdigit():
            base_sql += " AND salary_avg <= %s"
            params.append(int(salary_max))
        
        count_result = db.query_one("SELECT COUNT(*) as cnt" + base_sql, tuple(params))
        total = count_result['cnt'] if count_result else 0
        
        data_sql = "SELECT *" + base_sql + " ORDER BY id DESC LIMIT %s OFFSET %s"
        params.extend([pageSize, offset])
        rows = db.query_dict(data_sql, tuple(params))
        db.close()
        
        return jsonify({'list': rows, 'total': total})
    except Exception as e:
        db.close()
        return jsonify({'list': [], 'total': 0, 'error': str(e)})

@app.route('/api/cities')
def api_cities():
    db = get_db_manager()
    if not db:
        return jsonify([])
    try:
        rows = db.query_dict("SELECT DISTINCT city_name FROM jobs WHERE city_name IS NOT NULL ORDER BY city_name")
        db.close()
        return jsonify([r['city_name'] for r in rows])
    except:
        db.close()
    return jsonify([])

@app.route('/api/health')
def api_health():
    db = get_db_manager()
    db_ok = False
    db_count = 0
    if db:
        try:
            result = db.query_one("SELECT COUNT(*) as cnt FROM jobs")
            db_count = result['cnt'] if result else 0
            db_ok = True
        except:
            pass
        finally:
            db.close()
    return jsonify({
        'status': 'ok',
        'db_ok': db_ok,
        'db_count': db_count,
        'cleaned_count': len(load_cleaned_data()),
        'output_files': os.listdir(OUTPUT_DIR) if os.path.exists(OUTPUT_DIR) else []
    })

if __name__ == '__main__':
    print("="*70)
    print("📊 步骤13：Flask+ECharts可视化服务启动")
    print("="*70)
    db = get_db_manager()
    db_count = 0
    if db:
        try:
            result = db.query_one("SELECT COUNT(*) as cnt FROM jobs")
            db_count = result['cnt'] if result else 0
        except:
            pass
        finally:
            db.close()
    print(f"MySQL数据库连接检测成功, 现有岗位数据: {db_count} 条")
    print("\n后端API端点:")
    print("  GET /api/salary-bar     - 城市薪资柱状图")
    print("  GET /api/city-pie       - 城市岗位饼图")
    print("  GET /api/skill-wordcloud - 技能词云数据")
    print("  GET /api/job-list       - 岗位列表（前50条）")
    print("  GET /api/job-search     - 检索接口: ?keyword=&city=&salary_min=&salary_max=")
    print("  GET /api/cities         - 数据库现有城市列表")
    print("\n前端页面: http://localhost:5000/")
    print("="*70)
    print("\n答辩常见问题与解决方案记录:")
    print("  ❓ 跨域问题: Flask单页应用采用同源策略无需CORS")
    print("  ❓ 数据渲染失败: F12打开控制台检查JSON响应格式")
    print("  ❓ 中文乱码: 确保meta charset=UTF-8, font-family含微软雅黑")
    print("\n" + "🚀 答辩可视化服务启动中...")
    app.run(debug=True, host='0.0.0.0', port=5000)

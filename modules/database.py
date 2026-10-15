import pymysql
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

class MySQLManager:
    def __init__(self, config: Dict[str, Any]):
        self.host = config['mysql_host']
        self.port = config['mysql_port']
        self.user = config['mysql_user']
        self.password = config['mysql_password']
        self.db_name = config['mysql_db']
        self.conn: Optional[pymysql.Connection] = None
        self.cursor: Optional[pymysql.cursors.Cursor] = None
        self.dict_cursor: Optional[pymysql.cursors.DictCursor] = None

    def connect(self) -> bool:
        try:
            self.conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset='utf8mb4'
            )
            self.cursor = self.conn.cursor()
            self.dict_cursor = self.conn.cursor(pymysql.cursors.DictCursor)
            return True
        except Exception as e:
            print(f"❌ MySQL连接失败: {e}")
            return False

    def query_dict(self, sql: str, params: Tuple = ()) -> List[Dict]:
        try:
            self.dict_cursor.execute(sql, params)
            return self.dict_cursor.fetchall()
        except Exception as e:
            print(f"查询失败: {e}")
            return []

    def query_one(self, sql: str, params: Tuple = ()) -> Optional[Dict]:
        try:
            self.dict_cursor.execute(sql, params)
            return self.dict_cursor.fetchone()
        except:
            return None

    def create_database(self) -> bool:
        try:
            sql = f"CREATE DATABASE IF NOT EXISTS {self.db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            self.cursor.execute(sql)
            self.conn.select_db(self.db_name)
            return True
        except Exception as e:
            print(f"❌ 创建数据库失败: {e}")
            return False

    def create_table(self) -> bool:
        try:
            sql = """
            CREATE TABLE IF NOT EXISTS jobs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_name VARCHAR(255) COMMENT '岗位名称',
                salary_range VARCHAR(100) COMMENT '薪资范围',
                salary_min INT COMMENT '最低薪资(K)',
                salary_max INT COMMENT '最高薪资(K)',
                salary_avg INT COMMENT '平均薪资(K)',
                city_name VARCHAR(50) COMMENT '工作城市',
                area_district VARCHAR(100) COMMENT '工作区域',
                company_name VARCHAR(255) COMMENT '公司名称',
                company_industry VARCHAR(255) COMMENT '公司行业',
                company_scale VARCHAR(100) COMMENT '公司规模',
                job_experience VARCHAR(100) COMMENT '工作经验要求',
                job_degree VARCHAR(50) COMMENT '学历要求',
                skills TEXT COMMENT '岗位技能标签',
                welfare_list TEXT COMMENT '福利待遇',
                job_url VARCHAR(500) COMMENT '岗位链接',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_city (city_name),
                INDEX idx_salary (salary_range),
                UNIQUE INDEX idx_job_url (job_url(255))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='招聘岗位表'
            """
            self.cursor.execute(sql)
            return True
        except Exception as e:
            print(f"❌ 创建表失败: {e}")
            return False

    def insert_job(self, job: Dict[str, str]) -> int:
        try:
            sql = """
            INSERT IGNORE INTO jobs (
                job_name, salary_range, salary_min, salary_max, salary_avg,
                city_name, area_district, company_name, company_industry, company_scale,
                job_experience, job_degree, skills, welfare_list, job_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(sql, (
                job['job_name'], job['salary_range'],
                job.get('salary_min', 0), job.get('salary_max', 0), job.get('salary_avg', 0),
                job['city_name'], job['area_district'], job['company_name'], job['company_industry'],
                job['company_scale'], job['job_experience'], job['job_degree'],
                job['skills'], job['welfare_list'], job['job_url']
            ))
            self.conn.commit()
            return self.cursor.rowcount
        except Exception as e:
            print(f"❌ 插入数据失败: {e}")
            return 0

    def insert_batch(self, job_list: List[Dict[str, str]]) -> int:
        count = 0
        for job in job_list:
            count += self.insert_job(job)
        return count

    def get_count(self) -> int:
        try:
            self.cursor.execute("SELECT COUNT(*) FROM jobs")
            return self.cursor.fetchone()[0]
        except:
            return 0

    def load_to_dataframe(self) -> pd.DataFrame:
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        try:
            sql = "SELECT * FROM jobs"
            return pd.read_sql(sql, self.conn)
        except Exception as e:
            print(f"❌ 读取数据失败: {e}")
            return pd.DataFrame()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

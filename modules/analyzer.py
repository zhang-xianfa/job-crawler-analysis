import pandas as pd
import jieba
from wordcloud import WordCloud
import os
from typing import Dict, Any, List, Tuple
from modules.zhaopin import parse_salary as zhaopin_parse_salary

class DataAnalyzer:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        print("-"*50)
        print("清洗前数据行数:", len(df))

        df_cleaned = df.dropna(subset=['job_degree', 'job_experience'])
        print("dropna()后行数:", len(df_cleaned))

        df_cleaned = df_cleaned.drop_duplicates(subset=['job_name', 'company_name', 'salary_range'])
        print("drop_duplicates()后行数:", len(df_cleaned))

        if 'salary_range' in df_cleaned.columns and 'salary_avg' not in df_cleaned.columns:
            def parse_salary_wrapper(salary_str):
                min_sal, max_sal, avg_sal = zhaopin_parse_salary(salary_str)
                return pd.Series([min_sal, max_sal, avg_sal])

            df_cleaned[['salary_min', 'salary_max', 'salary_avg']] = df_cleaned['salary_range'].apply(parse_salary_wrapper)

        print("薪资字段已转换为数值型：salary_min, salary_max, salary_avg")

        if 'city_name' in df_cleaned.columns:
            df_cleaned['city_clean'] = df_cleaned['city_name'].apply(lambda x: str(x).split('-')[0] if '-' in str(x) else str(x))
            print("城市字段整洁化完成")

        print("清洗后数据行数:", len(df_cleaned))
        print("-"*50)
        return df_cleaned

    def analyze_city_salary(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'city_clean' not in df.columns:
            df['city_clean'] = df['city_name']

        stats = df.groupby('city_clean').agg({
            'id': 'count',
            'salary_avg': ['mean', 'median']
        }).round(2)

        stats.columns = ['岗位数量', '平均薪资', '薪资中位数']
        stats = stats.sort_values(by='平均薪资', ascending=False)
        stats = stats.reset_index()
        stats = stats.rename(columns={'city_clean': '城市'})

        return stats

    def generate_wordcloud(self, df: pd.DataFrame, text_column: str = 'skills') -> str:
        all_text = ','.join(df[text_column].dropna().astype(str).tolist())

        words = jieba.lcut(all_text)
        stopwords = {'的', '了', '和', '是', '在', '有', '等', '与', '或', '上', '下', '中', ')', '(', '（', '）'}
        filtered_words = [w for w in words if len(w) > 1 and w not in stopwords]
        cleaned_text = ' '.join(filtered_words)

        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simsun.ttc"
        ]
        font_path = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_path = fp
                break

        wc = WordCloud(
            width=1200,
            height=800,
            background_color='white',
            font_path=font_path,
            max_words=200,
            collocations=False
        )

        wc.generate(cleaned_text)
        output_path = os.path.join(self.output_dir, 'skill_wordcloud.png')
        wc.to_file(output_path)

        return output_path

    def get_analysis_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        city_stats = self.analyze_city_salary(df)
        return {
            'city_names': city_stats['城市'].tolist(),
            'job_counts': city_stats['岗位数量'].tolist(),
            'avg_salaries': city_stats['平均薪资'].tolist()
        }

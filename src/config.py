import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv(Path(__file__).parent.parent / '.env')

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库配置
DATABASE_PATH = os.environ.get('DATABASE_PATH', str(DATA_DIR / "family_finance.db"))
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 应用配置
# 安全：SECRET_KEY 必须通过 .env 设置，禁止使用默认值。
# 启动时由 database.create_app() 校验，缺失或为不安全默认值时拒绝启动。
INSECURE_SECRET_KEY = 'dev-secret-key-change-in-production'
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('FLASK_DEBUG', 'True') == 'True'

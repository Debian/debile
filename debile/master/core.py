from sqlalchemy import create_engine
from debile.utils.config import load_master_config

config = load_master_config()

#engine = create_engine("postgresql://localhost/debile")
#engine = create_engine("sqlite:///debile.db")

engine = create_engine(config['database'])

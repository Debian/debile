from sqlalchemy import create_engine

#engine = create_engine("postgresql://localhost/debile")  # Fix this.
engine = create_engine("sqlite:///debile.db")  # Fix this.

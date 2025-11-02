from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

password = "MKGFt3llxU"  # 
DATABASE_URL = f"mysql+pymysql://sql12805698:{password}@sql12.freesqldatabase.com:3306/sql12805698"

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

try:
    with engine.connect() as conn:
        print("✅ Connected to FreeSQLDatabase successfully!")
except Exception as e:
    print("❌ Connection failed:", e)

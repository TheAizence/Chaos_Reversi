# install_data_science_libs_latest.py
import subprocess
import sys

libraries = [
    "numpy",
    "pandas",
    "polars",
    "pyarrow",
    "matplotlib",
    "seaborn",
    "plotly",
    "bokeh",
    "altair",
    "scikit-learn",
    "xgboost",
    "lightgbm",
    "catboost",
    "statsmodels",
    "tensorflow",
    "keras",
    "torch",
    "torchvision",
    "transformers",
    "sqlalchemy",
    "pymysql",
    "psycopg2",
    "requests",
    "beautifulsoup4",
    "scrapy",
    "openpyxl",
    "xlrd",
    "textblob",
    "nltk",
    "spacy",
    "dask",
    "pyspark",
    "ray",
    "mlflow",
    "optuna",
    "hydra-core",
    "joblib",
    "tqdm",
    "pydantic",
    "python-dotenv",
    "opencv-python",
    "scipy",
    "networkx",
    "geopandas",
    "shap",
    "lime"
]

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

if __name__ == "__main__":
    for lib in libraries:
        print(f"Installing {lib}...")
        install(lib)
    print("✅ All libraries installed successfully!")

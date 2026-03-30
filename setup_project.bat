@echo off
echo Initializing CuraSource Project Structure...

:: Root Files
echo. > .env
echo. > .gitignore
echo. > README.md
echo. > requirements.txt
echo. > package.json

:: Ingestion Pipeline
mkdir ingestion\parsers
mkdir ingestion\chunkers
mkdir ingestion\extractors
mkdir ingestion\scripts
echo. > ingestion\parsers\pymupdf_parser.py
echo. > ingestion\parsers\llamaparse_parser.py
echo. > ingestion\parsers\ocr_parser.py
echo. > ingestion\chunkers\structure_chunker.py
echo. > ingestion\chunkers\deduplicator.py
echo. > ingestion\extractors\table_extractor.py
echo. > ingestion\extractors\figure_extractor.py
echo. > ingestion\embedder.py
echo. > ingestion\metadata_tagger.py
echo. > ingestion\pipeline.py

:: Backend (FastAPI)
mkdir backend\api\routes
mkdir backend\api\middleware
mkdir backend\pipeline
mkdir backend\models
mkdir backend\db
echo. > backend\main.py
echo. > backend\config.py
echo. > backend\api\dependencies.py
echo. > backend\api\routes\query.py
echo. > backend\api\routes\sources.py
echo. > backend\api\routes\feedback.py
echo. > backend\pipeline\domain_router.py
echo. > backend\pipeline\retriever.py
echo. > backend\pipeline\reranker.py
echo. > backend\pipeline\generator.py
echo. > backend\pipeline\verifier.py

:: Frontend (Next.js)
mkdir frontend\app
mkdir frontend\components\chat
mkdir frontend\components\sources
mkdir frontend\components\ui
mkdir frontend\hooks
mkdir frontend\stores
mkdir frontend\types
mkdir frontend\lib
echo. > frontend\tailwind.config.js
echo. > frontend\tsconfig.json

:: Evaluation & Docs
mkdir evaluation
mkdir docs
echo. > evaluation\run_eval.py

echo Project structure created successfully.
pause
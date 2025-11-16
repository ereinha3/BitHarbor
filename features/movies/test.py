import asyncio
import os
from pathlib import Path
from importlib import reload
from dotenv import load_dotenv

project_root = Path('/home/ethan/documents/bitharbor')
dotenv_path = project_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

if os.environ.get('TMDB_API_KEY'):
    os.environ['BITHARBOR_TMDB__API_KEY'] = os.environ['TMDB_API_KEY']
if os.environ.get('TMDB_ACCESS_TOKEN'):
    os.environ['BITHARBOR_TMDB__ACCESS_TOKEN'] = os.environ['TMDB_ACCESS_TOKEN']

os.environ.setdefault('BITHARBOR_SERVER__DATA_ROOT', '/home/ethan/tmp/bitharbor-data')
os.environ.setdefault('BITHARBOR_SERVER__POOL_ROOT', '/home/ethan/tmp/bitharbor-pool')
os.environ.setdefault('BITHARBOR_ANN__INDEX_DIRECTORY', '/mnt/vectordb/movies/diskann')
os.environ.setdefault('BITHARBOR_ANN__VECTORS_PATH', '/mnt/vectordb/movies/vectors.fp32')

for path in ['/home/ethan/tmp/bitharbor-data', '/home/ethan/tmp/bitharbor-pool', '/mnt/vectordb/movies', '/mnt/vectordb/movies/diskann']:
    Path(path).mkdir(parents=True, exist_ok=True)

from app.settings import get_settings
get_settings.cache_clear()

import features.movies.vector_index as movie_index_module
reload(movie_index_module)
from features.movies import ingest as movie_ingest_module
reload(movie_ingest_module)
from db.session import SessionLocal
from features.movies.ingest import ingest_catalog_movie
from features.movies.search import MovieCatalogSearchService, clear_registered_matches
from features.movies.download import MovieCatalogDownloadService
from features.movies import vector_index as movie_index

settings = get_settings()
clear_registered_matches()

search_service = MovieCatalogSearchService(settings)
download_service = MovieCatalogDownloadService(settings)

dest = Path('/home/ethan/tmp/catalog-downloads')
if dest.exists():
    import shutil
    shutil.rmtree(dest)
dest.mkdir(parents=True, exist_ok=True)

async def main():
    response = await search_service.search('night of the living dead', limit=1, year=1968)
    if not response.matches:
        print('No matches found')
        return
    match = response.matches[0]
    download_result = download_service.download(match.match_key, destination=dest)
    print('Download bundle:', download_result)

    poster_path = None
    if download_result.cover_art_file:
        candidate = Path(download_result.video_path).parent / download_result.cover_art_file
        if candidate.exists():
            poster_path = candidate

    metadata = {
        'title': match.tmdb_movie.title,
        'overview': match.tmdb_movie.overview,
        'genres': match.tmdb_movie.genres,
        'languages': match.tmdb_movie.languages,
        'year': match.tmdb_movie.year,
        'poster_path': str(poster_path) if poster_path else None,
        'tmdb_id': match.tmdb_id,
        'ia_identifier': match.best_candidate.identifier,
        'ia_downloads': match.best_candidate.downloads,
        'ia_score': match.best_candidate.score,
    }

    async with SessionLocal() as session:
        result = await ingest_catalog_movie(
            session=session,
            video_path=Path(download_result.video_path),
            metadata=metadata,
        )
        await session.commit()
    print('Ingest result:', result)

    vectors_path = movie_index._vectors_path
    print('Vector store path:', vectors_path, 'exists:', vectors_path.exists())
    if vectors_path.exists():
        print('Vector file size bytes:', vectors_path.stat().st_size)

asyncio.run(main())
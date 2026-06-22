import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
import re

app = Flask(__name__)

# Essential Stremio CORS rule fix
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "id": "com.torrentfreak.top10.movies",
        "version": "1.2.0",
        "name": "TorrentFreak Top 10 Movies",
        "description": "Weekly catalog of the top 10 most torrented movies from TorrentFreak via TMDB Lookup.",
        "resources": ["catalog"],
        "types": ["movie"],
        "idPrefixes": ["tt"], # Stremio still maps catalog entries by IMDb prefix "tt"
        "catalogs": [
            {
                "type": "movie",
                "id": "tf_top_10",
                "name": "TorrentFreak Top 10"
            }
        ]
    })

# Helper function to find the IMDb ID using TMDB Search API
def get_imdb_id_from_tmdb(movie_name, api_key):
    try:
        # Step 1: Search TMDB for the movie by title text
        search_url = f"https://api.themoviedb.org/3/search/movie"
        params = {"api_key": api_key, "query": movie_name}
        search_response = requests.get(search_url, params=params, timeout=5).json()
        
        if not search_response.get("results"):
            return None
            
        # Get the highest-match result (first item in array)
        tmdb_id = search_response["results"][0]["id"]
        
        # Step 2: Query external IDs endpoint to extract the true 'ttXXXXXXX' ID
        detail_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/external_ids"
        detail_params = {"api_key": api_key}
        detail_response = requests.get(detail_url, params=detail_params, timeout=5).json()
        
        return detail_response.get("imdb_id")
    except Exception as e:
        print(f"TMDB resolution error for '{movie_name}': {e}")
        return None

@app.route('/catalog/movie/tf_top_10.json')
def catalog():
    TMDB_API_KEY = "5bac60b56fcf01fd5cdca7d856416355"
    
    url = "https://torrentfreak.com/top-10-most-torrented-pirated-movies/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        metas = []

        # Targets all layout rows sequentially
        rows = soup.select('table tr')

        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) >= 3:
                # Double check that row starts with an actual list index integer (1-10)
                rank_text = cells[0].text.strip()
                if not re.match(r'^\d+$', rank_text):
                    continue
                
                # Snatch raw string directly out of column index 2
                raw_title = cells[2].text.strip()
                if not raw_title:
                    continue
                
                # Aggressive clean up to extract ONLY the clean alphanumeric title string:
                # Strips trailing elements like "6.9 / trailer", "7.6 / trailer", or standalone "/ trailer"
                clean_title = re.sub(r'\b\d+\.\d+\b', '', raw_title)
                clean_title = re.sub(r'\s*/\s*trailer.*$', '', clean_title, flags=re.IGNORECASE)
                clean_title = re.sub(r'^\d+\.\s*', '', clean_title)
                clean_title = clean_title.strip()
                
                if clean_title:
                    # Let TMDB work its magic to fetch the respective IMDb tracking identifier
                    imdb_id = get_imdb_id_from_tmdb(clean_title, TMDB_API_KEY)
                    
                    if imdb_id:
                        metas.append({
                            "id": imdb_id, # Keeps Stremio engine fully happy
                            "type": "movie",
                            "name": clean_title,
                            "poster": f"https://btttr.cc/poster/imdb/poster-default/{imdb_id}.jpg"
                        })
                        
            if len(metas) >= 10:
                break

        return jsonify({"metas": metas})
        
    except Exception as e:
        print(f"Scraper error encountered: {e}")
        return jsonify({"metas": []})

if __name__ == '__main__':
    app.run(port=7000)

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

# Standard Stremio Manifest JSON configuration
@app.route('/manifest.json')
def manifest():
    return jsonify({
        "id": "com.torrentfreak.top10.movies",
        "version": "1.0.0",
        "name": "TorrentFreak Top 10 Movies",
        "description": "Weekly catalog of the top 10 most torrented movies from TorrentFreak.",
        "resources": ["catalog"],
        "types": ["movie"],
        "idPrefixes": ["tt"],
        "catalogs": [
            {
                "type": "movie",
                "id": "tf_top_10",
                "name": "TorrentFreak Top 10"
            }
        ]
    })

# Stremio Catalog Endpoint
@app.route('/catalog/movie/tf_top_10.json')
def catalog():
    url = "https://torrentfreak.com/top-10-most-torrented-pirated-movies/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        metas = []

        # TorrentFreak puts their top 10 movie list links directly to IMDb in their tables
        links = soup.select('table tr td a[href*="imdb.com/title/"]')

        for link in links[:10]:  # Cap it at top 10
            title = link.text.strip()
            href = link.get('href', '')
            
            # Extract the 'ttXXXXXXX' ID from the IMDb link url
            imdb_match = re.search(r'tt\d+', href)
            if imdb_match and title:
                imdb_id = imdb_match.group(0)
                
                # By passing Stremio the proper IMDb ID, Stremio's internal engine (Cinemeta)
                # automatically pulls the high-res movie posters directly for you!
                metas.append({
    			"id": imdb_id,
    			"type": "movie",
    			"name": title,
    			# Updated to pull dynamic Better Posters directly from btttr.cc
    			"poster": f"https://btttr.cc/poster/imdb/poster-default/{imdb_id}.jpg"
		})

        return jsonify({"metas": metas})
        
    except Exception as e:
        print(f"Error scraping: {e}")
        return jsonify({"metas": []})

if __name__ == '__main__':
    app.run(port=7000)
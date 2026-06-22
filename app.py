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
        "version": "1.1.0",
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

@app.route('/catalog/movie/tf_top_10.json')
def catalog():
    url = "https://torrentfreak.com/top-10-most-torrented-pirated-movies/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        metas = []

        # Target all table rows on the page
        rows = soup.select('table tr')

        for row in rows:
            cells = row.find_all('td')
            
            # Ensure it is a valid data row with at least 3 columns
            if len(cells) >= 3:
                # Rule 1: Verify cell 0 contains a clean numerical rank (1-10)
                rank_text = cells[0].text.strip()
                if not re.match(r'^\d+$', rank_text):
                    continue
                
                # Rule 2: Dynamically find the IMDb ID anywhere inside this specific row
                imdb_id = None
                for link in row.find_all('a', href=True):
                    href = link['href']
                    imdb_match = re.search(r'tt\d+', href)
                    if imdb_match:
                        imdb_id = imdb_match.group(0)
                        break  # Found the ID, move to text extraction
                
                # Rule 3: Extract and clean up the title from the 3rd column (cells[2])
                raw_title = cells[2].text.strip()
                if not raw_title:
                    continue
                
                # Clean up TorrentFreak's structural text:
                # Remove ratings patterns (e.g., "7.6", "6.9") and "/ trailer" suffixes cleanly
                clean_title = re.sub(r'\b\d+\.\d+\b', '', raw_title)  # Strips decimal ratings
                clean_title = re.sub(r'\s*/\s*trailer.*$', '', clean_title, flags=re.IGNORECASE)  # Strips "/ trailer"
                clean_title = re.sub(r'^\d+\.\s*', '', clean_title)  # Strips any "1. " prefixes
                clean_title = clean_title.strip()  # Clear out remaining surrounding spaces
                
                # Rule 4: Append only if we have both a valid title and a found IMDb ID
                if imdb_id and clean_title:
                    metas.append({
                        "id": imdb_id,
                        "type": "movie",
                        "name": clean_title,
                        "poster": f"https://btttr.cc/poster/imdb/poster-default/{imdb_id}.jpg"
                    })
                        
            # Stop parsing immediately once we fill our top 10 catalog spots in order
            if len(metas) >= 10:
                break

        return jsonify({"metas": metas})
        
    except Exception as e:
        print(f"Scraper error encountered: {e}")
        return jsonify({"metas": []})

if __name__ == '__main__':
    app.run(port=7000)

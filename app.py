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

        # Find all table rows across the TorrentFreak page
        rows = soup.select('table tr')

        for row in rows:
            # Find the cell that contains the hyperlink pointing to IMDb
            imdb_link = row.find('a', href=re.compile(r'imdb\.com/title/tt\d+'))
            
            if imdb_link:
                href = imdb_link.get('href', '')
                imdb_match = re.search(r'tt\d+', href)
                
                if imdb_match:
                    imdb_id = imdb_match.group(0)
                    
                    # Target all cells within this row
                    cells = row.find_all('td')
                    
                    # TorrentFreak Columns: 
                    # cells[0] = This Week's Rank
                    # cells[1] = Last Week's Rank (e.g. "(1)", "(..)")
                    # cells[2] = True Movie Title
                    if len(cells) >= 3:
                        title = cells[2].text.strip()
                        
                        # Fallback defense: if column 2 is somehow short or empty, try column 1
                        if not title or len(title) <= 4 and ('(' in title or '.' in title):
                            title = cells[1].text.strip()
                        
                        # Clean up any lingering rank numbers just in case
                        title = re.sub(r'^\d+\.\s*', '', title) 
                        
                        metas.append({
                            "id": imdb_id,
                            "type": "movie",
                            "name": title,
                            "poster": f"https://btttr.cc/poster/imdb/poster-default/{imdb_id}.jpg"
                        })
                        
            # Prevent going over the Top 10 limit 
            if len(metas) >= 10:
                break

        return jsonify({"metas": metas})
        
    except Exception as e:
        print(f"Error scraping: {e}")
        return jsonify({"metas": []})

if __name__ == '__main__':
    app.run(port=7000)

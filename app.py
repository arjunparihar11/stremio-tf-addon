import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
import re

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "id": "com.torrentfreak.top10.movies",
        "version": "1.0.1",
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # Hardcoded fallback mappings for titles missing explicit IMDb links on TorrentFreak's table right now
    fallback_ids = {
        "mortal kombat ii": "tt19864802",
        "office romance": "tt0076706"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        metas = []

        # Target the precise rows inside TorrentFreak's actual data tables
        rows = soup.select('table tr')

        for row in rows:
            cells = row.find_all('td')
            
            # Make sure it's a valid data row containing enough columns
            if len(cells) >= 3:
                # Check if the first cell starts with a number to verify it's part of the top 10 list
                rank_text = cells[0].text.strip()
                if not re.match(r'^\d+$', rank_text):
                    continue
                
                # Column 2 is the true movie title text
                title = cells[2].text.strip()
                if not title:
                    continue

                # Clean up any lingering rank headers inside text
                title = re.sub(r'^\d+\.\s*', '', title)
                
                # Look for an IMDb hyperlink anywhere inside this specific row
                imdb_link = row.find('a', href=re.compile(r'imdb\.com/title/tt\d+'))
                imdb_id = None
                
                if imdb_link:
                    href = imdb_link.get('href', '')
                    imdb_match = re.search(r'tt\d+', href)
                    if imdb_match:
                        imdb_id = imdb_match.group(0)
                
                # If TorrentFreak didn't link it, use our static map registry fallback
                if not imdb_id:
                    imdb_id = fallback_ids.get(title.lower())
                
                # Only append if an ID was successfully resolved
                if imdb_id:
                    metas.append({
                        "id": imdb_id,
                        "type": "movie",
                        "name": title,
                        "poster": f"https://btttr.cc/poster/imdb/poster-default/{imdb_id}.jpg"
                    })
                        
            # Ensure we strictly gather up to 10 entries sequentially
            if len(metas) >= 10:
                break

        return jsonify({"metas": metas})
        
    except Exception as e:
        print(f"Error scraping: {e}")
        return jsonify({"metas": []})

if __name__ == '__main__':
    app.run(port=7000)

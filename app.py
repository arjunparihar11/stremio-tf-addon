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
        "version": "1.0.2",
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
    
    # Precise hardcoded fallback registry for rows missing clean links
    fallback_ids = {
        "mortal kombat ii": "tt19864802",
        "the devil wears prada 2": "tt20862024",
        "office romance": "tt0076706"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        metas = []

        # Find the rows inside TorrentFreak's tables
        rows = soup.select('table tr')

        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) >= 3:
                # Confirm it's a list item row by checking for a numerical rank
                rank_text = cells[0].text.strip()
                if not re.match(r'^\d+$', rank_text):
                    continue
                
                # Fetch the clean title directly from column index 2
                title = cells[2].text.strip()
                if not title:
                    continue
                
                # Strip clean any leftover list characters
                title = re.sub(r'^\d+\.\s*', '', title)
                
                # Find the IMDb ID specifically inside THIS row's link tags
                imdb_id = None
                for link in row.find_all('a', href=True):
                    href = link['href']
                    imdb_match = re.search(r'tt\d+', href)
                    if imdb_match:
                        imdb_id = imdb_match.group(0)
                        break # Grab the first valid movie link found in the row
                
                # Apply fallback mapping if TorrentFreak omitted the link
                if not imdb_id:
                    imdb_id = fallback_ids.get(title.lower())
                
                if imdb_id:
                    metas.append({
                        "id": imdb_id,
                        "type": "movie",
                        "name": title,
                        "poster": f"https://btttr.cc/poster/imdb/poster-default/{imdb_id}.jpg"
                    })
                        
            if len(metas) >= 10:
                break

        return jsonify({"metas": metas})
        
    except Exception as e:
        print(f"Error scraping data: {e}")
        return jsonify({"metas": []})

if __name__ == '__main__':
    app.run(port=7000)

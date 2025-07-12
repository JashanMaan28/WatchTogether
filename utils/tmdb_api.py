import requests
import os
from datetime import datetime

class TMDBService:
    """Service for interacting with The Movie Database (TMDB) API"""
    
    def __init__(self):
        self.api_key = os.environ.get('TMDB_API_KEY')
        self.base_url = 'https://api.themoviedb.org/3'
        self.image_base_url = 'https://image.tmdb.org/t/p'
        
        if not self.api_key:
            raise ValueError("TMDB_API_KEY environment variable is required")
    
    def search_content(self, query, content_type='multi', page=1):
        """Search for content on TMDB"""
        endpoint = f"{self.base_url}/search/{content_type}"
        params = {
            'api_key': self.api_key,
            'query': query,
            'page': page
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"TMDB API error: {e}")
            return None
    
    def get_content_details(self, tmdb_id, content_type='movie'):
        """Get detailed information about a specific content item"""
        endpoint = f"{self.base_url}/{content_type}/{tmdb_id}"
        params = {
            'api_key': self.api_key,
            'append_to_response': 'credits,videos,external_ids'
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Transform TMDB data to our format
            return self._transform_tmdb_data(data, content_type)
        except requests.RequestException as e:
            print(f"TMDB API error: {e}")
            return None
    
    def get_popular_content(self, content_type='movie', page=1):
        """Get popular content from TMDB"""
        endpoint = f"{self.base_url}/{content_type}/popular"
        params = {
            'api_key': self.api_key,
            'page': page
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"TMDB API error: {e}")
            return None
    
    def get_trending_content(self, time_window='day'):
        """Get trending content from TMDB"""
        endpoint = f"{self.base_url}/trending/all/{time_window}"
        params = {
            'api_key': self.api_key
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"TMDB API error: {e}")
            return None
    
    def _transform_tmdb_data(self, data, content_type):
        """Transform TMDB API response to our content format"""
        # Determine content type
        if content_type == 'tv':
            title = data.get('name', '')
            release_date = data.get('first_air_date', '')
            duration = data.get('episode_run_time', [0])[0] if data.get('episode_run_time') else None
        else:
            title = data.get('title', '')
            release_date = data.get('release_date', '')
            duration = data.get('runtime')
        
        # Extract year from release date
        year = None
        if release_date:
            try:
                year = datetime.strptime(release_date, '%Y-%m-%d').year
            except ValueError:
                pass
        
        # Extract genres
        genres = [genre['name'] for genre in data.get('genres', [])]
        
        # Extract cast and crew
        cast = []
        director = None
        credits = data.get('credits', {})
        
        if credits.get('cast'):
            cast = [actor['name'] for actor in credits['cast'][:10]]  # Top 10 cast members
        
        if credits.get('crew'):
            for crew_member in credits['crew']:
                if crew_member['job'] == 'Director':
                    director = crew_member['name']
                    break
        
        # Get poster and backdrop URLs
        poster_url = None
        backdrop_url = None
        if data.get('poster_path'):
            poster_url = f"{self.image_base_url}/w500{data['poster_path']}"
        if data.get('backdrop_path'):
            backdrop_url = f"{self.image_base_url}/w1280{data['backdrop_path']}"
        
        # Get trailer URL
        trailer_url = None
        videos = data.get('videos', {}).get('results', [])
        for video in videos:
            if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                trailer_url = f"https://www.youtube.com/watch?v={video['key']}"
                break
        
        # Get external IDs
        external_ids = data.get('external_ids', {})
        imdb_id = external_ids.get('imdb_id')
        
        # Determine our content type
        our_content_type = 'tv_show' if content_type == 'tv' else 'movie'
        
        return {
            'title': title,
            'description': data.get('overview', ''),
            'type': our_content_type,
            'genres': genres,
            'year': year,
            'rating': data.get('vote_average'),
            'duration': duration,
            'poster_url': poster_url,
            'backdrop_url': backdrop_url,
            'trailer_url': trailer_url,
            'director': director,
            'cast': cast,
            'country': data.get('production_countries', [{}])[0].get('name') if data.get('production_countries') else None,
            'language': data.get('original_language'),
            'imdb_id': imdb_id
        }
    
    def import_popular_content(self, content_type='movie', pages=1):
        """Import popular content from TMDB"""
        imported_content = []
        
        for page in range(1, pages + 1):
            popular_data = self.get_popular_content(content_type, page)
            if not popular_data or 'results' not in popular_data:
                continue
            
            for item in popular_data['results']:
                tmdb_id = item['id']
                details = self.get_content_details(tmdb_id, content_type)
                if details:
                    details['tmdb_id'] = tmdb_id
                    imported_content.append(details)
        
        return imported_content

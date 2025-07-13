from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, Content, Platform, ContentPlatform, UserWatchlist, ContentRating
from forms import ContentSearchForm, ContentRatingForm
from utils.tmdb_api import TMDBService
from sqlalchemy import or_, and_, desc, asc
import json
import os
import requests

content = Blueprint('content', __name__, url_prefix='/content')

@content.route('/')
def index():
    try:
        tmdb = TMDBService()
        
        search_query = request.args.get('search', '').strip()
        content_type = request.args.get('type', 'movie')
        page = request.args.get('page', 1, type=int)
        
        if search_query:
            results = tmdb.search_content(search_query, 'multi', page)
        else:
            results = tmdb.get_popular_content(content_type, page)
        
        content_items = []
        if results and 'results' in results:
            for item in results['results']:
                item_type = item.get('media_type', content_type)
                if item_type == 'tv':
                    item_type = 'tv_show'
                elif item_type == 'person':
                    continue
                
                title = item.get('title') or item.get('name', '')
                release_date = item.get('release_date') or item.get('first_air_date', '')
                year = None
                if release_date:
                    try:
                        year = int(release_date.split('-')[0])
                    except:
                        pass
                
                # Build poster URL
                poster_url = None
                if item.get('poster_path'):
                    poster_url = f"https://image.tmdb.org/t/p/w500{item['poster_path']}"
                
                content_items.append({
                    'tmdb_id': item['id'],
                    'title': title,
                    'description': item.get('overview', ''),
                    'type': item_type,
                    'year': year,
                    'rating': item.get('vote_average'),
                    'poster_url': poster_url,
                    'genre': None  # Will be populated in detail view
                })
        
        # Pagination info
        total_pages = results.get('total_pages', 1) if results else 1
        total_results = results.get('total_results', 0) if results else 0
        
        # Get current filters for template
        current_filters = {
            'search': search_query,
            'type': content_type
        }
        
        return render_template('content/browse.html',
                             content_items=content_items,
                             current_filters=current_filters,
                             page=page,
                             total_pages=min(total_pages, 500),  # TMDB limit
                             total_results=total_results,
                             per_page=20)
                             
    except Exception as e:
        current_app.logger.error(f"Error in content index: {e}")
        return render_template('content/browse.html',
                             content_items=[],
                             current_filters={'search': '', 'type': 'movie'},
                             page=1,
                             total_pages=1,
                             total_results=0,
                             per_page=20)


@content.route('/<int:tmdb_id>')
@content.route('/<int:tmdb_id>/<content_type>')
def detail(tmdb_id, content_type='movie'):
    """Content detail page using TMDB API"""
    try:
        # Initialize TMDB service
        try:
            tmdb = TMDBService()
        except Exception as tmdb_error:
            current_app.logger.error(f"TMDB Service initialization error: {tmdb_error}")
            flash('Movie database service is currently unavailable', 'error')
            return redirect(url_for('content.index'))
        
        # Get content details from TMDB
        content_details = tmdb.get_content_details(tmdb_id, content_type)
        if not content_details:
            # Try the other content type
            alt_type = 'tv' if content_type == 'movie' else 'movie'
            content_details = tmdb.get_content_details(tmdb_id, alt_type)
            if content_details:
                content_type = alt_type
        
        if not content_details:
            flash('Content not found', 'error')
            return redirect(url_for('content.index'))
        
        # Add TMDB ID to content details
        content_details['tmdb_id'] = tmdb_id
        content_details['content_type'] = content_type
        
        # Get user's watchlist status if logged in
        watchlist_status = None
        user_rating = None
        if current_user.is_authenticated:
            # Check if content exists in our database
            from models import Content as LocalContent
            local_content = LocalContent.query.filter_by(tmdb_id=tmdb_id).first()
            
            if local_content:
                watchlist_item = UserWatchlist.query.filter_by(
                    user_id=current_user.id,
                    content_id=local_content.id
                ).first()
                if watchlist_item:
                    watchlist_status = watchlist_item.status
                
                user_rating_item = ContentRating.query.filter_by(
                    user_id=current_user.id,
                    content_id=local_content.id
                ).first()
                if user_rating_item:
                    user_rating = user_rating_item.rating
        
        # Get similar content recommendations
        recommendations = []
        try:
            # Get similar movies/shows from TMDB
            endpoint = f"https://api.themoviedb.org/3/{content_type}/{tmdb_id}/similar"
            params = {'api_key': tmdb.api_key, 'page': 1}
            response = requests.get(endpoint, params=params)
            if response.status_code == 200:
                similar_data = response.json()
                for item in similar_data.get('results', [])[:6]:
                    recommendations.append({
                        'tmdb_id': item['id'],
                        'title': item.get('title') or item.get('name', ''),
                        'poster_url': f"https://image.tmdb.org/t/p/w300{item['poster_path']}" if item.get('poster_path') else None,
                        'type': content_type
                    })
        except:
            pass
        
        # Get reviews from our local database if content exists
        reviews = []
        local_content = None
        from models import Content as LocalContent
        local_content = LocalContent.query.filter_by(tmdb_id=tmdb_id).first()
        if local_content:
            reviews = ContentRating.query.filter_by(content_id=local_content.id)\
                                        .filter(ContentRating.review_text.isnot(None))\
                                        .filter(ContentRating.is_public == True)\
                                        .order_by(desc(ContentRating.created_at))\
                                        .limit(5).all()
        
        return render_template('content/detail_tmdb.html',
                             content=content_details,
                             watchlist_status=watchlist_status,
                             user_rating=user_rating,
                             recommendations=recommendations,
                             reviews=reviews,
                             local_content=local_content)
                             
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in content detail: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error loading content details', 'error')
        return redirect(url_for('content.index'))

@content.route('/search')
def search():
    """AJAX search endpoint using TMDB"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    try:
        tmdb = TMDBService()
        results = tmdb.search_content(query, 'multi', 1)
        
        search_results = []
        if results and 'results' in results:
            for item in results['results'][:10]:  # Limit to 10 results
                # Skip person results
                if item.get('media_type') == 'person':
                    continue
                
                title = item.get('title') or item.get('name', '')
                year = None
                release_date = item.get('release_date') or item.get('first_air_date', '')
                if release_date:
                    try:
                        year = int(release_date.split('-')[0])
                    except:
                        pass
                
                content_type = item.get('media_type', 'movie')
                if content_type == 'tv':
                    content_type = 'tv_show'
                
                poster_url = None
                if item.get('poster_path'):
                    poster_url = f"https://image.tmdb.org/t/p/w200{item['poster_path']}"
                
                search_results.append({
                    'tmdb_id': item['id'],
                    'title': title,
                    'year': year,
                    'type': content_type,
                    'poster_url': poster_url
                })
        
        return jsonify(search_results)
    except Exception as e:
        current_app.logger.error(f"Search error: {e}")
        return jsonify([])

@content.route('/watchlist', methods=['POST'])
@login_required
def toggle_watchlist():
    """Add/remove TMDB content from user's watchlist"""
    data = request.get_json()
    tmdb_id = data.get('tmdb_id')
    content_type = data.get('content_type', 'movie')
    status = data.get('status', 'want_to_watch')
    
    if not tmdb_id:
        return jsonify({'error': 'TMDB ID required'}), 400
    
    try:
        # Get or create local content record
        from models import Content as LocalContent
        local_content = LocalContent.query.filter_by(tmdb_id=tmdb_id).first()
        
        if not local_content:
            # Create new content record from TMDB
            tmdb = TMDBService()
            content_details = tmdb.get_content_details(tmdb_id, content_type)
            
            if not content_details:
                return jsonify({'error': 'Content not found in TMDB'}), 404
            
            # Create local content record
            local_content = LocalContent(
                title=content_details['title'],
                description=content_details['description'],
                type=content_details['type'],
                genre=', '.join(content_details.get('genres', [])),
                year=content_details.get('year'),
                rating=content_details.get('rating'),
                duration=content_details.get('duration'),
                poster_url=content_details.get('poster_url'),
                backdrop_url=content_details.get('backdrop_url'),
                trailer_url=content_details.get('trailer_url'),
                tmdb_id=tmdb_id,
                imdb_id=content_details.get('imdb_id'),
                director=content_details.get('director'),
                cast=', '.join(content_details.get('cast', [])),
                country=content_details.get('country'),
                language=content_details.get('language'),
                status='active'
            )
            db.session.add(local_content)
            db.session.flush()  # Get the ID
        
        # Check if already in watchlist
        watchlist_item = UserWatchlist.query.filter_by(
            user_id=current_user.id,
            content_id=local_content.id
        ).first()
        
        if watchlist_item:
            if status == 'remove':
                db.session.delete(watchlist_item)
                action = 'removed'
            else:
                watchlist_item.status = status
                action = 'updated'
        else:
            if status != 'remove':
                watchlist_item = UserWatchlist(
                    user_id=current_user.id,
                    content_id=local_content.id,
                    status=status
                )
                db.session.add(watchlist_item)
                action = 'added'
            else:
                action = 'none'
        
        db.session.commit()
        return jsonify({'success': True, 'action': action})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Watchlist error: {e}")
        return jsonify({'error': str(e)}), 500

@content.route('/rate', methods=['POST'])
@login_required
def rate_content():
    """Rate content"""
    data = request.get_json()
    content_id = data.get('content_id')
    rating = data.get('rating')
    review = data.get('review', '').strip()
    
    if not content_id or not rating:
        return jsonify({'error': 'Content ID and rating required'}), 400
    
    try:
        rating = float(rating)
        if rating < 1 or rating > 10:
            return jsonify({'error': 'Rating must be between 1 and 10'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid rating value'}), 400
    
    content_item = Content.query.get_or_404(content_id)
    
    # Check if user already rated this content
    existing_rating = ContentRating.query.filter_by(
        user_id=current_user.id,
        content_id=content_id
    ).first()
    
    if existing_rating:
        existing_rating.rating = rating
        existing_rating.review = review if review else None
    else:
        new_rating = ContentRating(
            user_id=current_user.id,
            content_id=content_id,
            rating=rating,
            review=review if review else None
        )
        db.session.add(new_rating)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@content.route('/debug/<int:tmdb_id>')
@content.route('/debug/<int:tmdb_id>/<content_type>')
def debug_detail(tmdb_id, content_type='movie'):
    """Debug route to test TMDB API"""
    try:
        # Initialize TMDB service
        tmdb = TMDBService()
        
        # Test basic API connection
        api_test = f"API Key exists: {bool(tmdb.api_key)}"
        
        # Get content details from TMDB
        content_details = tmdb.get_content_details(tmdb_id, content_type)
        
        debug_info = {
            'api_test': api_test,
            'tmdb_id': tmdb_id,
            'content_type': content_type,
            'content_details': content_details,
            'api_key_prefix': tmdb.api_key[:10] + '...' if tmdb.api_key else 'None'
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@content.route('/add_from_tmdb', methods=['POST'])
@login_required
def add_from_tmdb():
    """Add content from TMDB to local database for rating"""
    try:
        tmdb_id = request.form.get('tmdb_id', type=int)
        content_type = request.form.get('content_type', 'movie')
        
        # Map content type for TMDB API (handles 'tv_show' -> 'tv')
        tmdb_content_type = 'tv' if content_type == 'tv_show' else content_type
        
        if not tmdb_id:
            flash('Invalid content ID', 'error')
            return redirect(request.referrer or url_for('content.index'))
        
        # Check if content already exists
        from models import Content as LocalContent
        existing_content = LocalContent.query.filter_by(tmdb_id=tmdb_id).first()
        if existing_content:
            flash('Content already exists in database', 'info')
            return redirect(url_for('ratings.rate_content', content_id=existing_content.id))
        
        # Get content details from TMDB
        tmdb = TMDBService()
        content_details = tmdb.get_content_details(tmdb_id, tmdb_content_type)
        
        if not content_details:
            flash('Content not found on TMDB', 'error')
            return redirect(request.referrer or url_for('content.index'))
        
        # Create new content in our database
        new_content = LocalContent(
            title=content_details.get('title', ''),
            description=content_details.get('description', ''),
            type=content_details.get('type', content_type),
            genre=', '.join(content_details.get('genres', [])),
            year=content_details.get('year'),
            rating=content_details.get('rating'),
            duration=content_details.get('duration'),
            poster_url=content_details.get('poster_url'),
            backdrop_url=content_details.get('backdrop_url'),
            tmdb_id=tmdb_id,
            imdb_id=content_details.get('imdb_id'),
            director=content_details.get('director'),
            cast=', '.join(content_details.get('cast', [])) if content_details.get('cast') else None,
            country=content_details.get('country'),
            language=content_details.get('language', '').upper() if content_details.get('language') else None,
            status='active'
        )
        
        db.session.add(new_content)
        db.session.commit()
        
        flash(f'"{new_content.title}" added to database successfully!', 'success')
        return redirect(url_for('ratings.rate_content', content_id=new_content.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding content from TMDB: {e}")
        flash('Error adding content to database', 'error')
        return redirect(request.referrer or url_for('content.index'))

@content.route('/local/<int:content_id>')
@login_required
def local_detail(content_id):
    """Detail page for local content (content without TMDB ID)"""
    content_item = Content.query.get_or_404(content_id)
    
    # Get user's watchlist status
    in_watchlist = False
    if current_user.is_authenticated:
        watchlist_item = UserWatchlist.query.filter_by(
            user_id=current_user.id,
            content_id=content_item.id
        ).first()
        in_watchlist = watchlist_item is not None
    
    # Get user's rating
    user_rating = None
    if current_user.is_authenticated:
        rating = ContentRating.query.filter_by(
            user_id=current_user.id,
            content_id=content_item.id
        ).first()
        if rating:
            user_rating = rating.rating
    
    # Get average rating
    ratings = ContentRating.query.filter_by(content_id=content_item.id).all()
    avg_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else None
    
    # Get similar content
    similar_content = get_similar_content(content_item, limit=5)
    
    return render_template('content/detail.html',
                         content=content_item,
                         in_watchlist=in_watchlist,
                         user_rating=user_rating,
                         avg_rating=avg_rating,
                         total_ratings=len(ratings),
                         similar_content=similar_content)

# Helper functions
def get_unique_genres():
    """Get all unique genres from content"""
    contents = Content.query.filter(Content.genre.isnot(None)).all()
    genres = set()
    for content_item in contents:
        try:
            content_genres = json.loads(content_item.genre)
            if isinstance(content_genres, list):
                genres.update(content_genres)
        except:
            if content_item.genre:
                genres.add(content_item.genre)
    return sorted(list(genres))

def get_unique_years():
    """Get all unique years from content"""
    years = db.session.query(Content.year).filter(Content.year.isnot(None)).distinct().all()
    return sorted([year[0] for year in years], reverse=True)

def get_unique_content_types():
    """Get all unique content types"""
    types = db.session.query(Content.type).distinct().all()
    return sorted([type_[0] for type_ in types])

def get_content_recommendations(content_item, limit=6):
    """Get content recommendations based on current content"""
    recommendations = []
    
    # Simple content-based recommendations
    # 1. Same genre
    if content_item.genre:
        same_genre = Content.query.filter(
            Content.genre.ilike(f'%{content_item.get_genres()[0] if content_item.get_genres() else ""}%'),
            Content.id != content_item.id,
            Content.status == 'active'
        ).limit(3).all()
        recommendations.extend(same_genre)
    
    # 2. Same type and similar year
    if content_item.year and len(recommendations) < limit:
        similar_year = Content.query.filter(
            Content.type == content_item.type,
            Content.year.between(content_item.year - 5, content_item.year + 5),
            Content.id != content_item.id,
            Content.status == 'active'
        ).filter(~Content.id.in_([r.id for r in recommendations])).limit(limit - len(recommendations)).all()
        recommendations.extend(similar_year)
    
    # 3. Fill remaining with high-rated content
    if len(recommendations) < limit:
        high_rated = Content.query.filter(
            Content.rating >= 7.0,
            Content.id != content_item.id,
            Content.status == 'active'
        ).filter(~Content.id.in_([r.id for r in recommendations])).order_by(desc(Content.rating)).limit(limit - len(recommendations)).all()
        recommendations.extend(high_rated)
    
    return recommendations[:limit]

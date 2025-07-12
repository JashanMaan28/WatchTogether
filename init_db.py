#!/usr/bin/env python3
"""
Database initialization script for WatchTogether
Creates all tables and adds sample data
"""

import os
import sys
from datetime import datetime

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Group, GroupMember, Content, Platform, ContentPlatform, UserWatchlist, ContentRating

def init_database():
    """Initialize the database with tables and sample data"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        # Add sample platforms
        print("Adding sample platforms...")
        platforms_data = [
            {
                'name': 'Netflix',
                'logo_url': 'https://cdn.worldvectorlogo.com/logos/netflix-3.svg',
                'website_url': 'https://netflix.com'
            },
            {
                'name': 'Amazon Prime Video',
                'logo_url': 'https://cdn.worldvectorlogo.com/logos/amazon-prime-video.svg',
                'website_url': 'https://primevideo.com'
            },
            {
                'name': 'Disney+',
                'logo_url': 'https://cdn.worldvectorlogo.com/logos/disney.svg',
                'website_url': 'https://disneyplus.com'
            },
            {
                'name': 'Hulu',
                'logo_url': 'https://cdn.worldvectorlogo.com/logos/hulu-2.svg',
                'website_url': 'https://hulu.com'
            },
            {
                'name': 'HBO Max',
                'logo_url': 'https://cdn.worldvectorlogo.com/logos/hbo-max-1.svg',
                'website_url': 'https://hbomax.com'
            },
            {
                'name': 'Apple TV+',
                'logo_url': 'https://cdn.worldvectorlogo.com/logos/apple-tv.svg',
                'website_url': 'https://tv.apple.com'
            }
        ]
        
        for platform_data in platforms_data:
            platform = Platform.query.filter_by(name=platform_data['name']).first()
            if not platform:
                platform = Platform(**platform_data)
                db.session.add(platform)
        
        # Add sample content
        print("Adding sample content...")
        content_data = [
            {
                'title': 'The Shawshank Redemption',
                'description': 'Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.',
                'type': 'movie',
                'genre': '["Drama"]',
                'year': 1994,
                'rating': 9.3,
                'duration': 142,
                'director': 'Frank Darabont',
                'cast': '["Tim Robbins", "Morgan Freeman", "Bob Gunton"]',
                'country': 'USA',
                'language': 'English'
            },
            {
                'title': 'The Godfather',
                'description': 'The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.',
                'type': 'movie',
                'genre': '["Crime", "Drama"]',
                'year': 1972,
                'rating': 9.2,
                'duration': 175,
                'director': 'Francis Ford Coppola',
                'cast': '["Marlon Brando", "Al Pacino", "James Caan"]',
                'country': 'USA',
                'language': 'English'
            },
            {
                'title': 'Breaking Bad',
                'description': 'A high school chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine.',
                'type': 'tv_show',
                'genre': '["Crime", "Drama", "Thriller"]',
                'year': 2008,
                'rating': 9.5,
                'duration': 47,
                'director': 'Vince Gilligan',
                'cast': '["Bryan Cranston", "Aaron Paul", "Anna Gunn"]',
                'country': 'USA',
                'language': 'English'
            },
            {
                'title': 'Stranger Things',
                'description': 'When a young boy disappears, his mother, a police chief and his friends must confront terrifying supernatural forces.',
                'type': 'tv_show',
                'genre': '["Drama", "Fantasy", "Horror"]',
                'year': 2016,
                'rating': 8.7,
                'duration': 51,
                'cast': '["Millie Bobby Brown", "Finn Wolfhard", "Winona Ryder"]',
                'country': 'USA',
                'language': 'English'
            },
            {
                'title': 'Inception',
                'description': 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea.',
                'type': 'movie',
                'genre': '["Action", "Sci-Fi", "Thriller"]',
                'year': 2010,
                'rating': 8.8,
                'duration': 148,
                'director': 'Christopher Nolan',
                'cast': '["Leonardo DiCaprio", "Marion Cotillard", "Tom Hardy"]',
                'country': 'USA',
                'language': 'English'
            }
        ]
        
        netflix = Platform.query.filter_by(name='Netflix').first()
        prime_video = Platform.query.filter_by(name='Amazon Prime Video').first()
        
        for content_item_data in content_data:
            content_item = Content.query.filter_by(title=content_item_data['title']).first()
            if not content_item:
                content_item = Content(**content_item_data)
                db.session.add(content_item)
                db.session.flush()  # Get the ID
                
                # Add to some platforms
                if netflix:
                    content_platform = ContentPlatform(
                        content_id=content_item.id,
                        platform_id=netflix.id
                    )
                    db.session.add(content_platform)
                
                if prime_video and content_item.title in ['The Shawshank Redemption', 'Inception']:
                    content_platform = ContentPlatform(
                        content_id=content_item.id,
                        platform_id=prime_video.id
                    )
                    db.session.add(content_platform)
        
        # Create admin user if it doesn't exist
        print("Creating admin user...")
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@watchtogether.com',
                first_name='Admin',
                last_name='User'
            )
            admin_user.set_password('admin123')  # Change this in production!
            db.session.add(admin_user)
        
        try:
            db.session.commit()
            print("Database initialized successfully!")
            print("Admin user created with username: admin, password: admin123")
            print("Please change the admin password after first login!")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {e}")
            raise

if __name__ == '__main__':
    init_database()

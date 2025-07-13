from app import create_app, db
from models.recommendations import Recommendation
from collections import defaultdict
from datetime import datetime
import click


def remove_duplicate_recommendations():
    """Remove duplicate recommendations, keeping the most recent ones"""
    app = create_app()
    with app.app_context():
        print("=== CLEANING UP DUPLICATE RECOMMENDATIONS ===")
        
        # Find duplicates for each user
        user_duplicates = defaultdict(lambda: defaultdict(list))
        group_duplicates = defaultdict(lambda: defaultdict(list))
        
        # Get all active recommendations
        active_recs = Recommendation.query.filter_by(status='active').all()
        
        # Group by user/group and content_id
        for rec in active_recs:
            if rec.user_id:
                user_duplicates[rec.user_id][rec.content_id].append(rec)
            elif rec.group_id:
                group_duplicates[rec.group_id][rec.content_id].append(rec)
        
        total_removed = 0
        
        # Remove user duplicates
        for user_id, content_dict in user_duplicates.items():
            for content_id, recs in content_dict.items():
                if len(recs) > 1:
                    # Sort by creation date (newest first) and keep the newest
                    recs.sort(key=lambda x: x.created_at, reverse=True)
                    recs_to_remove = recs[1:]  # Remove all except the newest
                    
                    for rec in recs_to_remove:
                        print(f"Removing duplicate recommendation: User {user_id}, Content {content_id}")
                        db.session.delete(rec)
                        total_removed += 1
        
        # Remove group duplicates
        for group_id, content_dict in group_duplicates.items():
            for content_id, recs in content_dict.items():
                if len(recs) > 1:
                    # Sort by creation date (newest first) and keep the newest
                    recs.sort(key=lambda x: x.created_at, reverse=True)
                    recs_to_remove = recs[1:]  # Remove all except the newest
                    
                    for rec in recs_to_remove:
                        print(f"Removing duplicate group recommendation: Group {group_id}, Content {content_id}")
                        db.session.delete(rec)
                        total_removed += 1
        
        # Commit changes
        db.session.commit()
        print(f"\n=== CLEANUP COMPLETE ===")
        print(f"Total duplicate recommendations removed: {total_removed}")
        
        # Show final stats
        final_recs = Recommendation.query.filter_by(status='active').all()
        print(f"Remaining active recommendations: {len(final_recs)}")


@click.command()
def cleanup_duplicates():
    """CLI command to remove duplicate recommendations"""
    remove_duplicate_recommendations()


if __name__ == '__main__':
    remove_duplicate_recommendations()

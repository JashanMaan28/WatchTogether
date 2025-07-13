import click
from app import create_app, db
from models import User, Content, ContentRating, UserWatchlist, Group, GroupMember
from models.recommendations import (
    UserPreferenceProfile, GroupPreferenceProfile, Recommendation,
    RecommendationHistory, ABTestExperiment
)
from utils.recommendation_engine import RecommendationEngine, update_recommendation_metrics
from datetime import datetime, timedelta
import json


@click.group()
def cli():
    """WatchTogether Recommendation System CLI"""
    pass


@cli.command()
@click.option('--user-id', type=int, help='Update specific user profile')
@click.option('--all-users', is_flag=True, help='Update all user profiles')
@click.option('--force', is_flag=True, help='Force update even if recently updated')
def update_user_profiles(user_id, all_users, force):
    """Update user preference profiles based on their ratings and watchlist"""
    app = create_app()
    engine = RecommendationEngine()
    
    with app.app_context():
        if user_id:
            users = [User.query.get(user_id)]
            if not users[0]:
                click.echo(f"User with ID {user_id} not found")
                return
        elif all_users:
            users = User.query.filter_by(is_active=True).all()
        else:
            click.echo("Please specify --user-id or --all-users")
            return
        
        updated_count = 0
        for user in users:
            profile = UserPreferenceProfile.query.filter_by(user_id=user.id).first()
            
            # Check if update is needed
            if not force and profile and profile.last_updated:
                time_since_update = datetime.utcnow() - profile.last_updated
                if time_since_update < timedelta(days=1):
                    continue
            
            # Create or get profile
            if not profile:
                profile = UserPreferenceProfile(user_id=user.id)
                db.session.add(profile)
            
            # Update profile
            engine._analyze_user_preferences(profile)
            updated_count += 1
            
            click.echo(f"Updated profile for user {user.username} (confidence: {profile.confidence_score:.2f})")
        
        db.session.commit()
        click.echo(f"Updated {updated_count} user profiles")


@cli.command()
@click.option('--group-id', type=int, help='Update specific group profile')
@click.option('--all-groups', is_flag=True, help='Update all group profiles')
@click.option('--force', is_flag=True, help='Force update even if recently updated')
def update_group_profiles(group_id, all_groups, force):
    """Update group preference profiles based on member preferences"""
    app = create_app()
    engine = RecommendationEngine()
    
    with app.app_context():
        if group_id:
            groups = [Group.query.get(group_id)]
            if not groups[0]:
                click.echo(f"Group with ID {group_id} not found")
                return
        elif all_groups:
            groups = Group.query.filter_by(is_active=True).all()
        else:
            click.echo("Please specify --group-id or --all-groups")
            return
        
        updated_count = 0
        for group in groups:
            profile = GroupPreferenceProfile.query.filter_by(group_id=group.id).first()
            
            # Check if update is needed
            if not force and profile and profile.last_updated:
                time_since_update = datetime.utcnow() - profile.last_updated
                if time_since_update < timedelta(days=1):
                    continue
            
            # Create or get profile
            if not profile:
                profile = GroupPreferenceProfile(group_id=group.id)
                db.session.add(profile)
            
            # Update profile
            engine._analyze_group_preferences(profile)
            updated_count += 1
            
            click.echo(f"Updated profile for group {group.name} (members: {profile.member_count}, confidence: {profile.confidence_score:.2f})")
        
        db.session.commit()
        click.echo(f"Updated {updated_count} group profiles")


@cli.command()
@click.option('--user-id', type=int, help='Generate recommendations for specific user')
@click.option('--group-id', type=int, help='Generate recommendations for specific group')
@click.option('--algorithm', default='hybrid', help='Algorithm to use (hybrid, content_based, collaborative, trending, group_consensus)')
@click.option('--limit', default=10, help='Number of recommendations to generate')
@click.option('--batch-size', default=50, help='Batch size for bulk generation')
@click.option('--all-users', is_flag=True, help='Generate recommendations for all active users')
def generate_recommendations(user_id, group_id, algorithm, limit, batch_size, all_users):
    """Generate recommendations for users or groups"""
    app = create_app()
    engine = RecommendationEngine()
    
    with app.app_context():
        if user_id:
            try:
                recommendations = engine.generate_recommendations(
                    user_id=user_id,
                    algorithm=algorithm,
                    limit=limit
                )
                click.echo(f"Generated {len(recommendations)} recommendations for user {user_id}")
            except Exception as e:
                click.echo(f"Error generating recommendations for user {user_id}: {str(e)}")
        
        elif group_id:
            try:
                recommendations = engine.generate_recommendations(
                    group_id=group_id,
                    algorithm=algorithm,
                    limit=limit
                )
                click.echo(f"Generated {len(recommendations)} recommendations for group {group_id}")
            except Exception as e:
                click.echo(f"Error generating recommendations for group {group_id}: {str(e)}")
        
        elif all_users:
            users = User.query.filter_by(is_active=True).all()
            total_generated = 0
            
            with click.progressbar(users, label='Generating recommendations') as bar:
                for user in bar:
                    try:
                        recommendations = engine.generate_recommendations(
                            user_id=user.id,
                            algorithm=algorithm,
                            limit=limit
                        )
                        total_generated += len(recommendations)
                    except Exception as e:
                        click.echo(f"Error for user {user.username}: {str(e)}")
                        continue
                    
                    # Commit in batches
                    if total_generated % batch_size == 0:
                        db.session.commit()
            
            db.session.commit()
            click.echo(f"Generated {total_generated} total recommendations for {len(users)} users")
        
        else:
            click.echo("Please specify --user-id, --group-id, or --all-users")


@cli.command()
def update_metrics():
    """Update recommendation performance metrics"""
    app = create_app()
    
    with app.app_context():
        click.echo("Updating recommendation metrics...")
        update_recommendation_metrics()
        click.echo("Metrics updated successfully")


@cli.command()
@click.option('--days', default=30, help='Number of days to look back for cleanup')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without actually deleting')
def cleanup_old_recommendations(days, dry_run):
    """Clean up old and expired recommendations"""
    app = create_app()
    
    with app.app_context():
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find old recommendations
        old_recommendations = Recommendation.query.filter(
            Recommendation.created_at < cutoff_date
        ).all()
        
        # Find expired recommendations
        expired_recommendations = Recommendation.query.filter(
            Recommendation.expires_at < datetime.utcnow()
        ).all()
        
        total_to_delete = len(old_recommendations) + len(expired_recommendations)
        
        if dry_run:
            click.echo(f"Would delete {len(old_recommendations)} old recommendations (older than {days} days)")
            click.echo(f"Would delete {len(expired_recommendations)} expired recommendations")
            click.echo(f"Total: {total_to_delete} recommendations")
        else:
            # Delete old recommendations
            for rec in old_recommendations:
                db.session.delete(rec)
            
            # Delete expired recommendations
            for rec in expired_recommendations:
                db.session.delete(rec)
            
            db.session.commit()
            click.echo(f"Deleted {total_to_delete} old/expired recommendations")


@cli.command()
def stats():
    """Show recommendation system statistics"""
    app = create_app()
    
    with app.app_context():
        # User statistics
        total_users = User.query.filter_by(is_active=True).count()
        users_with_profiles = UserPreferenceProfile.query.count()
        
        # Group statistics
        total_groups = Group.query.filter_by(is_active=True).count()
        groups_with_profiles = GroupPreferenceProfile.query.count()
        
        # Recommendation statistics
        total_recommendations = Recommendation.query.count()
        active_recommendations = Recommendation.query.filter_by(status='active').count()
        
        # Algorithm usage
        algorithm_stats = db.session.query(
            Recommendation.algorithm,
            db.func.count(Recommendation.id)
        ).group_by(Recommendation.algorithm).all()
        
        # Feedback statistics
        feedback_stats = db.session.query(
            db.func.count(db.distinct(Recommendation.id))
        ).join(
            Recommendation.feedback
        ).scalar() or 0
        
        click.echo("=== Recommendation System Statistics ===")
        click.echo(f"Users: {total_users} total, {users_with_profiles} with profiles ({users_with_profiles/total_users*100:.1f}%)")
        click.echo(f"Groups: {total_groups} total, {groups_with_profiles} with profiles ({groups_with_profiles/total_groups*100:.1f}% if total_groups > 0 else 'N/A')")
        click.echo(f"Recommendations: {total_recommendations} total, {active_recommendations} active")
        click.echo(f"Recommendations with feedback: {feedback_stats}")
        
        click.echo("\nAlgorithm Usage:")
        for algorithm, count in algorithm_stats:
            percentage = count / total_recommendations * 100 if total_recommendations > 0 else 0
            click.echo(f"  {algorithm}: {count} ({percentage:.1f}%)")


@cli.command()
@click.argument('experiment_id')
@click.option('--status', type=click.Choice(['draft', 'running', 'paused', 'completed']), help='New status')
def manage_experiment(experiment_id, status):
    """Manage A/B testing experiments"""
    app = create_app()
    
    with app.app_context():
        experiment = ABTestExperiment.query.filter_by(experiment_id=experiment_id).first()
        
        if not experiment:
            click.echo(f"Experiment {experiment_id} not found")
            return
        
        if status:
            old_status = experiment.status
            experiment.status = status
            
            if status == 'running' and not experiment.start_date:
                experiment.start_date = datetime.utcnow()
            elif status == 'completed' and not experiment.end_date:
                experiment.end_date = datetime.utcnow()
            
            db.session.commit()
            click.echo(f"Updated experiment {experiment_id} status from {old_status} to {status}")
        else:
            # Show experiment details
            click.echo(f"Experiment: {experiment.name}")
            click.echo(f"ID: {experiment.experiment_id}")
            click.echo(f"Status: {experiment.status}")
            click.echo(f"Created: {experiment.created_at}")
            click.echo(f"Start Date: {experiment.start_date or 'Not started'}")
            click.echo(f"End Date: {experiment.end_date or 'Ongoing'}")
            click.echo(f"Primary Metric: {experiment.primary_metric}")
            
            variants = experiment.get_variants()
            traffic_split = experiment.get_traffic_split()
            
            click.echo("\nVariants:")
            for variant, config in variants.items():
                traffic = traffic_split.get(variant, 0)
                click.echo(f"  {variant}: {config.get('algorithm', 'N/A')} ({traffic}% traffic)")


@cli.command()
@click.option('--format', type=click.Choice(['json', 'csv']), default='json', help='Export format')
@click.option('--output', help='Output file path')
@click.option('--include-feedback', is_flag=True, help='Include feedback data')
def export_data(format, output, include_feedback):
    """Export recommendation data for analysis"""
    app = create_app()
    
    with app.app_context():
        # Get recommendation data
        recommendations = db.session.query(
            Recommendation,
            User.username,
            Content.title,
            Content.type,
            Content.year
        ).join(
            User, Recommendation.user_id == User.id, isouter=True
        ).join(
            Content, Recommendation.content_id == Content.id
        ).all()
        
        data = []
        for rec, username, title, content_type, year in recommendations:
            row = {
                'recommendation_id': rec.id,
                'user': username,
                'content_title': title,
                'content_type': content_type,
                'content_year': year,
                'algorithm': rec.algorithm,
                'score': rec.score,
                'status': rec.status,
                'created_at': rec.created_at.isoformat(),
                'viewed_at': rec.viewed_at.isoformat() if rec.viewed_at else None,
                'clicked_at': rec.clicked_at.isoformat() if rec.clicked_at else None
            }
            
            if include_feedback:
                feedback = rec.get_feedback_summary()
                row.update({
                    'likes': feedback['likes'],
                    'dislikes': feedback['dislikes'],
                    'total_feedback': feedback['total']
                })
            
            data.append(row)
        
        if format == 'json':
            import json
            output_data = json.dumps(data, indent=2)
        else:  # CSV
            import csv
            import io
            output_io = io.StringIO()
            if data:
                writer = csv.DictWriter(output_io, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            output_data = output_io.getvalue()
        
        if output:
            with open(output, 'w') as f:
                f.write(output_data)
            click.echo(f"Exported {len(data)} recommendations to {output}")
        else:
            click.echo(output_data)


if __name__ == '__main__':
    cli()

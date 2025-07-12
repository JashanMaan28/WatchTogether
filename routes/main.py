from flask import Blueprint, render_template

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Homepage - Hello World"""
    return render_template('index.html')

@main.route('/about')
def about():
    """About page"""
    return render_template('about.html')

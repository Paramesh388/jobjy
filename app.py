import os
from flask import Flask, render_template
from config import Config
from models.database import init_db, seed_skills_catalog_if_empty
from ml.skills_dictionary import TECH_SKILLS_TAXONOMY

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure required directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)
    
    # Initialize SQLite database and catalog
    init_db()
    seed_skills_catalog_if_empty(TECH_SKILLS_TAXONOMY)
    
    # Register blueprints
    from routes.resume_routes import resume_bp
    from routes.job_routes import job_bp
    from routes.dashboard_routes import dashboard_bp
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(job_bp)
    
    # Custom Jinja template filters
    @app.template_filter("score_badge_class")
    def score_badge_class(score):
        try:
            val = float(score)
            if val >= 75:
                return "badge-score-high"
            elif val >= 50:
                return "badge-score-mid"
            else:
                return "badge-score-low"
        except (ValueError, TypeError):
            return "badge-score-low"

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("index.html", error_message="The requested page was not found."), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("index.html", error_message="An internal server error occurred. Please try again."), 500
        
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

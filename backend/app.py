import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.database import close_db, init_db
from backend.scheduler import start_background_watcher

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.teardown_appcontext(close_db)

    # Register blueprints under /api
    from backend.routes.health import health_bp
    from backend.routes.dashboard import dashboard_bp
    from backend.routes.products import products_bp
    from backend.routes.sales import sales_bp
    from backend.routes.forecast import forecast_bp
    from backend.routes.reorder import reorder_bp
    from backend.routes.reports import reports_bp
    from backend.routes.settings import settings_bp
    from backend.routes.data import data_bp
    from backend.routes.auth import auth_bp
    from backend.routes.gst import gst_bp
    from backend.routes.market import market_bp
    from backend.routes.stock import stock_bp
    from backend.routes.alerts import alerts_bp
    from backend.routes.orders import orders_bp
    from backend.routes.pipeline import pipeline_bp
    from backend.routes.admin import admin_bp
    from backend.routes.wholesale import wholesale_bp
    from backend.routes.scanner import scanner_bp
    from backend.routes.record import record_bp

    from backend.routes.locations import locations_bp
    from backend.routes.records_api import records_bp
    from backend.routes.dealer import dealer_bp
    from backend.routes.overview import overview_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(overview_bp, url_prefix="/api")
    app.register_blueprint(products_bp, url_prefix="/api")
    app.register_blueprint(sales_bp, url_prefix="/api")
    app.register_blueprint(gst_bp, url_prefix="/api")
    app.register_blueprint(market_bp, url_prefix="/api")
    app.register_blueprint(stock_bp, url_prefix="/api")
    app.register_blueprint(forecast_bp, url_prefix="/api")
    app.register_blueprint(reorder_bp, url_prefix="/api")
    app.register_blueprint(alerts_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")
    app.register_blueprint(pipeline_bp, url_prefix="/api")
    app.register_blueprint(wholesale_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(scanner_bp, url_prefix="/api")
    app.register_blueprint(record_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api")
    app.register_blueprint(data_bp, url_prefix="/api")
    app.register_blueprint(locations_bp, url_prefix="/api")
    app.register_blueprint(records_bp, url_prefix="/api")
    app.register_blueprint(dealer_bp, url_prefix="/api")



    # Serve built SPA frontend if dist directory exists
    dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if dist_dir.exists():
        from flask import send_from_directory

        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_frontend(path):
            if path.startswith("api/"):
                return jsonify({"error": "Endpoint not found", "status_code": 404}), 404
            target_file = dist_dir / path
            if path and target_file.exists() and target_file.is_file():
                return send_from_directory(dist_dir, path)
            return send_from_directory(dist_dir, "index.html")

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        if dist_dir.exists():
            from flask import send_from_directory
            return send_from_directory(dist_dir, "index.html")
        return jsonify({"error": "Resource not found", "status_code": 404}), 404

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "status_code": 400}), 400

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal server error", "status_code": 500}), 500

    return app

if __name__ == "__main__":
    init_db()
    start_background_watcher()
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


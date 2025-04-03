def register_blueprints(app, mysql):
    from app.routes.dashboard import dashboard_bp, init_dashboard
    from app.routes.sample import sample_bp, init_sample
    from app.routes.container import container_bp, init_container
    from app.routes.test import test_bp, init_test
    
    # Initialization of blueprints with mysql
    init_dashboard(dashboard_bp, mysql)
    init_sample(sample_bp, mysql)
    init_container(container_bp, mysql)
    init_test(test_bp, mysql)
    
    # Registration of blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sample_bp)
    app.register_blueprint(container_bp)
    app.register_blueprint(test_bp)
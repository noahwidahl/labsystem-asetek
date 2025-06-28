def register_blueprints(app, mysql):
    from app.routes.dashboard import dashboard_bp, init_dashboard
    from app.routes.sample import sample_bp, init_sample
    from app.routes.container import container_bp, init_container
    from app.routes.test import test_bp, init_test
    from app.routes.scanner import scanner_bp, init_scanner
    from app.routes.printer import printer_bp, init_printer
    from app.routes.system import system_bp, init_system
    from app.routes.expiration import expiration_bp, init_expiration
    
    # Initialization of blueprints with mysql
    init_dashboard(dashboard_bp, mysql)
    init_sample(sample_bp, mysql)
    init_container(container_bp, mysql)
    init_test(test_bp, mysql)
    init_scanner(scanner_bp, mysql)
    init_printer(printer_bp, mysql)
    init_system(system_bp, mysql)
    init_expiration(expiration_bp, mysql)
    
    # Registration of blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sample_bp)
    app.register_blueprint(container_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(printer_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(expiration_bp)
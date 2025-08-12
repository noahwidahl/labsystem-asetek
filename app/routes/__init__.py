def register_blueprints(app, mysql):
    from app.routes.dashboard import dashboard_bp, init_dashboard
    from app.routes.sample import sample_bp, init_sample
    from app.routes.container import container_bp, init_container
    from app.routes.test import test_bp, init_test
    from app.routes.task import task_bp, init_task
    from app.routes.scanner import scanner_bp, init_scanner
    from app.routes.printer import printer_bp, init_printer
    from app.routes.system import system_bp, init_system
    from app.routes.expiration import expiration_bp, init_expiration
    from app.routes.barcode import barcode_bp, init_barcode
    
    # Initialization of blueprints with mysql
    init_dashboard(dashboard_bp, mysql)
    init_sample(sample_bp, mysql)
    init_container(container_bp, mysql)
    init_test(test_bp, mysql)
    init_task(task_bp, mysql)
    init_scanner(scanner_bp, mysql)
    init_printer(printer_bp, mysql)
    init_system(system_bp, mysql)
    init_expiration(expiration_bp, mysql)
    init_barcode(barcode_bp, mysql)
    
    # Registration of blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sample_bp)
    app.register_blueprint(container_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(printer_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(expiration_bp)
    app.register_blueprint(barcode_bp)

def register_blueprints_mssql(app):
    """SQL Server version - no mysql parameter needed"""
    from app.routes.dashboard_mssql import dashboard_mssql_bp
    from app.routes.sample_mssql import sample_mssql_bp
    from app.routes.container_mssql import container_mssql_bp
    from app.routes.test_mssql import test_mssql_bp
    from app.routes.task_mssql import task_mssql_bp
    from app.routes.scanner_mssql import scanner_mssql_bp
    from app.routes.system import system_bp
    from app.routes.expiration_mssql import expiration_mssql_bp
    from app.routes.barcode import barcode_bp
    
    # Registration of blueprints (SQL Server version uses mssql_db directly)
    app.register_blueprint(dashboard_mssql_bp)
    app.register_blueprint(sample_mssql_bp)  # Now includes print endpoint
    app.register_blueprint(container_mssql_bp)
    app.register_blueprint(test_mssql_bp)
    app.register_blueprint(task_mssql_bp)
    app.register_blueprint(scanner_mssql_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(expiration_mssql_bp)
    app.register_blueprint(barcode_bp)
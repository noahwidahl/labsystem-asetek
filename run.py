from app import create_app

app = create_app()

if __name__ == '__main__':
    # Kør Flask-appen på alle netværksinterfaces, så den er tilgængelig på hele netværket
    app.run(debug=True, host='0.0.0.0', port=5000)
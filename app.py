"""Entry point. `flask run` and gunicorn both import `app` from here."""

from drp import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

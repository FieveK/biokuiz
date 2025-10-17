import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'biokuiz-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///biokuiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 🔹 Konfigurasi Flask-Mail (gunakan akun Gmail)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'emailkamu@gmail.com'      # Ganti dengan email kamu
    MAIL_PASSWORD = 'password-aplikasi-gmail'  # Gunakan App Password Gmail

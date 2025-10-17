from app import db, Material, Question, User
from app import app
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    # sample material (jika belum ada)
    if Material.query.count() == 0:
        m1 = Material(
            title="Sistem Ekskresi Manusia - Ringkasan",
            text="""
Sistem ekskresi pada manusia berperan mengeluarkan zat sisa metabolisme.
Organ utama: ginjal, hati, paru-paru, dan kulit.
Ginjal berfungsi menyaring darah dan memproduksi urin.
Hati berperan detoksifikasi dan metabolisme zat.
Paru-paru mengeluarkan CO2 dan uap air.
Kulit mengeluarkan keringat yang membantu ekskresi.
""",
            image_filename="ginjal.png"
        )
        db.session.add(m1)

    # sample questions (jika belum ada)
    if Question.query.count() == 0:
        q1 = Question(
            text="Organ manakah yang bertanggung jawab menyaring darah dan menghasilkan urin?",
            qtype="mcq",
            choices="A||Ginjal;;B||Hati;;C||Paru-paru;;D||Kulit",
            correct="A"
        )
        q2 = Question(
            text="Hati berfungsi dalam detoksifikasi. Benar atau Salah?",
            qtype="tf",
            choices=None,
            correct="True"
        )
        q3 = Question(
            text="Organ yang mengeluarkan CO2 adalah paru-paru.",
            qtype="tf",
            choices=None,
            correct="True"
        )
        q4 = Question(
            text="Manakah yang termasuk fungsi kulit dalam ekskresi?",
            qtype="mcq",
            choices="A||Menyaring darah;;B||Mengeluarkan keringat;;C||Membuat urin;;D||Memproduksi enzim pencernaan",
            correct="B"
        )
        db.session.add_all([q1,q2,q3,q4])

    # sample user
    if User.query.filter_by(username='siswa1').first() is None:
        u = User(username='siswa1')
        u.set_password('password')
        db.session.add(u)

    db.session.commit()
    print("Database dibuat / diperbarui dengan data sample.")

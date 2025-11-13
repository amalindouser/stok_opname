from flask import Flask, render_template, request, jsonify, send_file
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv  # ✅ tambahkan ini
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# =========================================
# 🧩 KONFIG DATABASE NEON
# =========================================
load_dotenv()  # ✅ baca file .env
DB_URL = os.getenv("DB_URL")

def get_conn():
    return psycopg2.connect(DB_URL)


# =========================================
# 🏠 HALAMAN UTAMA
# =========================================
@app.route('/')
def index():
    return render_template('index.html')

# =========================================
# 🔍 SCAN BARANG
# =========================================
@app.route('/scan', methods=['POST'])
def scan_barang():
    kode = request.form.get('kode', '').strip()
    if not kode:
        return jsonify({'error': 'Kode barang wajib diisi.'}), 400

    try:
        conn = get_conn()
        cur = conn.cursor()
        # ✅ Bandingkan dalam bentuk teks agar 22100001 dan 22100001.0 tetap cocok
        cur.execute("""
            SELECT kode, nama, stok, satuan, departemen 
            FROM tb_barang 
            WHERE CAST(kode AS TEXT) = %s OR CAST(kode AS TEXT) = %s || '.0'
        """, (kode, kode))
        row = cur.fetchone()
        conn.close()

        if row:
            # Hilangkan ".0" di tampilan
            kode_fix = str(row[0]).replace('.0', '')
            return jsonify({
                'kode': kode_fix,
                'nama': row[1],
                'on_hand': row[2],
                'satuan': row[3],
                'departemen': row[4]
            })
        else:
            return jsonify({'error': 'Barang tidak ditemukan di database.'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================================
# 💾 SIMPAN OPNAME
# =========================================
@app.route('/save_opname', methods=['POST'])
def save_opname():
    try:
        data = request.get_json()
        items = data.get('items', [])

        if not items:
            return jsonify({"success": False, "message": "Data opname kosong."}), 400

        conn = get_conn()
        cur = conn.cursor()

        for item in items:
            kode_opname = f"OPN{datetime.now().strftime('%Y%m%d%H%M%S')}"
            kode = str(item.get('kode')).replace('.0', '')  # ✅ hilangkan .0 sebelum simpan
            nama = item.get('nama')
            stok_awal = float(item.get('on_hand', 0))
            stok_real = float(item.get('fisik', 0))
            selisih = stok_real - stok_awal
            departemen = item.get('departemen', '-')
            status = "BELUM CEK"
            jenis = "SO"
            tanggal = datetime.now().strftime("%Y-%m-%d")

            cur.execute("""
                INSERT INTO stok_opname 
                (kode_opname, kode, nama, stok_awal, stok_real, tgl, selisih, status, jenis, departemen, tanggal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (kode_opname, kode, nama, stok_awal, stok_real, tanggal, selisih, status, jenis, departemen, tanggal))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Data opname berhasil disimpan ke Neon PostgreSQL."})

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"success": False, "message": str(e)}), 500

# =========================================
# 🖨️ CETAK PDF
# =========================================
@app.route('/cetak_pdf', methods=['POST'])
def cetak_pdf():
    try:
        data = request.get_json()
        opname_items = data.get('items', [])

        if not opname_items:
            return jsonify({'error': 'Data opname kosong.'}), 400

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(BASE_DIR, f"stok_opname_{timestamp}.pdf")

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]
        title_style = styles["Title"]

        title = Paragraph(
            f"<b>LAPORAN STOK OPNAME</b><br/><font size=10>{datetime.now().strftime('%d %B %Y %H:%M:%S')}</font>",
            title_style
        )
        space = Spacer(1, 12)

        table_data = [["Barcode", "Nama Barang", "Fisik", "On Hand", "Selisih", "Departemen"]]

        for item in opname_items:
            selisih = float(item.get('fisik', 0)) - float(item.get('on_hand', 0))
            table_data.append([
                str(item.get('kode', '')).replace('.0', ''),  # ✅ tampilkan tanpa .0
                Paragraph(item.get('nama', ''), normal_style),
                str(item.get('fisik', '')),
                str(item.get('on_hand', '')),
                str(selisih),
                item.get('departemen', '')
            ])

        col_widths = [90, 200, 60, 60, 60, 100]
        table = Table(table_data, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")])
        ]))

        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        doc.build([title, space, table])

        return send_file(pdf_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# if __name__ == '__main__':
#     app.run(debug=True)

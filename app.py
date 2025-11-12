from flask import Flask, render_template, request, jsonify, send_file
import pyodbc
from datetime import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# ==============================
# 🧩 KONFIG DATABASE
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCESS_DB_PATH = os.path.join(BASE_DIR, "masterbaru.accdb")

CONN_STR = (
    r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={ACCESS_DB_PATH};"
)

def get_conn():
    return pyodbc.connect(CONN_STR)


# ==============================
# 🏠 HALAMAN UTAMA
# ==============================
@app.route('/')
def index():
    return render_template('index.html')


# ==============================
# 🔍 SCAN BARANG
# ==============================
@app.route('/scan', methods=['POST'])
def scan_barang():
    kode = request.form.get('kode', '').strip()
    if not kode:
        return jsonify({'error': 'Kode barang wajib diisi.'}), 400

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TB_BARANG WHERE KODE = ?", (kode,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                'kode': row.KODE,
                'nama': row.NAMA,
                'on_hand': row.STOK,
                'satuan': row.SATUAN,
                'departemen': row.DEPARTEMEN
            })
        else:
            return jsonify({'error': 'Barang tidak ditemukan di database.'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==============================
# 💾 SIMPAN OPNAME
# ==============================
@app.route('/save_opname', methods=['POST'])
def save_opname():
    try:
        data = request.get_json()
        items = data.get('items', [])

        conn = get_conn()
        cursor = conn.cursor()

        for item in items:
            kode_opname = f"OPN{datetime.now().strftime('%Y%m%d%H%M%S')}"
            kode = item.get('kode')
            nama = item.get('nama')
            stok_awal = float(item.get('on_hand', 0))
            stok_real = float(item.get('fisik', 0))
            selisih = stok_real - stok_awal
            departemen = item.get('departemen', '-')
            status = "BELUM CEK"
            jenis = "SO"
            tanggal = datetime.now().strftime("%m/%d/%Y")

            cursor.execute("""
                INSERT INTO stok_opname 
                (kode_opname, kode, nama, stok_awal, stok_real, TGL, selisih, status, JENIS, departemen, tanggal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (kode_opname, kode, nama, stok_awal, stok_real, tanggal, selisih, status, jenis, departemen, tanggal))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Data opname berhasil disimpan."})

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"success": False, "message": str(e)})


# ==============================
# 🖨️ CETAK PDF
# ==============================
@app.route('/cetak_pdf', methods=['POST'])
def cetak_pdf():
    try:
        data = request.get_json()
        opname_items = data.get('items', [])

        if not opname_items:
            return jsonify({'error': 'Data opname kosong.'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(BASE_DIR, f"stok_opname_{timestamp}.pdf")

        table_data = [["Barcode", "Nama Barang", "Fisik", "On Hand", "Keterangan"]]
        for item in opname_items:
            table_data.append([
                item.get('kode', ''),
                item.get('nama', ''),
                str(item.get('fisik', '')),
                str(item.get('on_hand', '')),
                item.get('keterangan', '')
            ])

        styles = getSampleStyleSheet()
        title = Paragraph(
            f"<b>LAPORAN STOK OPNAME</b><br/><font size=10>{datetime.now().strftime('%d %B %Y %H:%M:%S')}</font>",
            styles["Title"]
        )
        space = Spacer(1, 12)

        table = Table(table_data, repeatRows=1, colWidths=[90, 160, 60, 60, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
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


if __name__ == '__main__':
    app.run()

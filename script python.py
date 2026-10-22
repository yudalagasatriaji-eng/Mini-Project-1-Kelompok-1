import json
import pandas as pd
import requests


def main():
    print("1. Mengambil data dari API Satu Data Jakarta...")

    # URL API Dataset Stunting Balita
    url = "https://ws.jakarta.go.id/gateway/DataPortalSatuDataJakarta/1.0/satudata?kategori=dataset&tipe=detail&url=jumlah-balita-pendek-stunting-per-kelurahan"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            raise Exception(f"HTTP Status Error: {response.status_code}")

        text_content = response.content.decode("utf-8-sig").strip()
        if not text_content or text_content.startswith("<"):
            raise Exception("Respon API bukan format JSON valid.")

        json_data = json.loads(text_content)

        # Parsing isi data JSON
        if isinstance(json_data, dict):
            data_list = (
                json_data.get("data")
                or json_data.get("result")
                or json_data.get("values")
                or json_data
            )
        else:
            data_list = json_data

        if not isinstance(data_list, list):
            raise Exception(
                "Struktur data dari API tidak sesuai format list JSON."
            )

        df = pd.DataFrame(data_list)
        print(f"   Berhasil mengambil {len(df)} baris data murni dari API!")

    except Exception as e:
        print(f"\n[ERROR API]: {e}")
        print("Pastikan koneksi internet aktif dan coba lagi.\n")
        return

    # ---------------------------------------------------------
    # IDENTIFIKASI KOLOM SECARA OTOMATIS
    # ---------------------------------------------------------
    # 1. Kolom Wilayah / Kategori untuk Grafik
    cat_col = None
    for target in [
        "wilayah",
        "nama_wilayah",
        "kabupaten",
        "kota",
        "kecamatan",
        "kelurahan",
    ]:
        for c in df.columns:
            if target in c.lower():
                cat_col = c
                break
        if cat_col:
            break

    if not cat_col:
        string_cols = df.select_dtypes(include=["object"]).columns
        cat_col = string_cols[0] if len(string_cols) > 0 else df.columns[0]

    # 2. Kolom Jumlah / Nilai Kasus Stunting
    val_col = None
    for target in ["jumlah", "jumlah_balita", "stunting", "pendek", "total"]:
        for c in df.columns:
            if target in c.lower():
                val_col = c
                break
        if val_col:
            break

    if not val_col:
        val_col = df.columns[-1]

    # Konversi kolom jumlah kasus ke numerik murni
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce").fillna(0)

    # ---------------------------------------------------------
    # ANALISIS DATA & LOKASI STUNTING TERTINGGI
    # ---------------------------------------------------------
    print(
        f"2. Menganalisis data (Kategori: '{cat_col}', Jumlah: '{val_col}')..."
    )

    # Cari kelurahan/lokasi dengan kasus stunting tertinggi
    idx_max = df[val_col].idxmax()
    max_row = df.loc[idx_max]
    pemilik_tertinggi = max_row[cat_col]
    nilai_tertinggi = max_row[val_col]

    # Ambil detail informasi lokasi pendukung (Kecamatan / Wilayah)
    detail_ket = f"{pemilik_tertinggi}"
    for add_col in ["kecamatan", "wilayah", "kota", "tahun"]:
        for c in df.columns:
            if add_col in c.lower() and c != cat_col:
                detail_ket += f" ({max_row[c]})"
                break

    # Grouping data untuk diagram
    grouped = (
        df.groupby(cat_col)[val_col]
        .sum()
        .reset_index()
        .sort_values(by=val_col, ascending=False)
    )

    # Ambil 10 teratas jika kategori terlalu banyak agar diagram tetap rapi
    if len(grouped) > 15:
        grouped_chart = grouped.head(10)
    else:
        grouped_chart = grouped

    chart_labels = json.dumps(
        grouped_chart[cat_col].astype(str).tolist()
    )
    chart_data = json.dumps(grouped_chart[val_col].tolist())

    label_kategori = cat_col.replace("_", " ").title()
    label_nilai = val_col.replace("_", " ").title()

    # ---------------------------------------------------------
    # GENERATE FILE HTML
    # ---------------------------------------------------------
    print("3. Meng-generate file index.html...")

    html_head = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Balita Stunting DKI Jakarta</title>
    <!-- Google Fonts: Poppins -->
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- Bootstrap & Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <!-- DataTables CSS -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        body {{
            font-family: 'Poppins', sans-serif;
            background-color: #f4f7f6 !important;
        }}
        .navbar {{
            background: linear-gradient(135deg, #dc3545, #c82333);
        }}
        .card {{
            border-radius: 12px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1) !important;
        }}
        .icon-box {{
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            font-size: 24px;
        }}
        .table-responsive {{
            border-radius: 12px;
            overflow: hidden;
        }}
        table.dataTable thead th {{
            background-color: #212529;
            color: white;
            border-bottom: none;
        }}
    </style>
</head>
<body class="bg-light">

    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark shadow-sm py-3">
        <div class="container">
            <a class="navbar-brand fw-bold" href="#">
                <i class="bi bi-heart-pulse-fill me-2 text-white"></i>Satu Data Jakarta
            </a>
            <span class="navbar-text text-white-50 small">
                Portal Kesehatan Masyarakat
            </span>
        </div>
    </nav>

    <div class="container my-5">
        <!-- Header Title -->
        <div class="mb-5 text-center">
            <h2 class="fw-bold text-dark mb-2">Data Balita Pendek (Stunting) Per Kelurahan</h2>
            <p class="text-muted">Distribusi Kasus Stunting Balita Provinsi DKI Jakarta berdasarkan data terkini</p>
        </div>

        <!-- Ringkasan Statistik -->
        <div class="row g-4 mb-5">
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card border-0 shadow-sm p-4 h-100">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-muted small fw-semibold text-uppercase">Total Wilayah</span>
                            <h3 class="fw-bold text-dark mb-0 mt-2">{len(df):,}</h3>
                        </div>
                        <div class="icon-box bg-secondary bg-opacity-10 text-secondary">
                            <i class="bi bi-map-fill"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card border-0 shadow-sm p-4 h-100">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-muted small fw-semibold text-uppercase">Total Kasus</span>
                            <h4 class="fw-bold text-danger mb-0 mt-2">{df[val_col].sum():,.0f}</h4>
                        </div>
                        <div class="icon-box bg-danger bg-opacity-10 text-danger">
                            <i class="bi bi-people-fill"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card border-0 shadow-sm p-4 h-100">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-muted small fw-semibold text-uppercase">Rata-Rata</span>
                            <h4 class="fw-bold text-primary mb-0">{df[val_col].mean():,.0f} Balita</h4>
                        </div>
                        <div class="icon-box bg-primary bg-opacity-10 text-primary">
                            <i class="bi bi-bar-chart-fill"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card border-0 shadow-sm p-4 h-100">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="text-muted small fw-semibold text-uppercase">Tertinggi</span>
                            <h4 class="fw-bold text-dark mb-0 mt-2">{nilai_tertinggi:,.0f}</h4>
                        </div>
                        <div class="icon-box bg-warning bg-opacity-10 text-warning">
                            <i class="bi bi-exclamation-triangle-fill"></i>
                        </div>
                    </div>
                    <span class="badge bg-danger text-white mt-3 text-truncate w-100 py-2" title="{detail_ket}">
                        <i class="bi bi-geo-alt-fill me-1"></i>{detail_ket}
                    </span>
                </div>
            </div>
        </div>

        <!-- Section Diagram -->
        <div class="row g-4 mb-5">
            <div class="col-12 col-lg-8">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h6 class="fw-bold mb-0 text-dark"><i class="bi bi-bar-chart-line-fill me-2 text-danger"></i>Distribusi 10 Tertinggi per {label_kategori}</h6>
                    </div>
                    <div class="card-body">
                        <div style="position: relative; height:350px;">
                            <canvas id="barChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-lg-4">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h6 class="fw-bold mb-0 text-dark"><i class="bi bi-pie-chart-fill me-2 text-danger"></i>Proporsi Kasus</h6>
                    </div>
                    <div class="card-body d-flex align-items-center justify-content-center">
                        <div style="position: relative; height:300px; width:100%;">
                            <canvas id="pieChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Section Tabel -->
        <div class="card border-0 shadow-sm mb-4">
            <div class="card-header bg-white py-4 d-flex justify-content-between align-items-center border-0">
                <h6 class="fw-bold mb-0 text-dark"><i class="bi bi-table me-2 text-danger"></i>Data Detail Stunting Per Kelurahan</h6>
                <span class="badge bg-danger rounded-pill px-3 py-2">{len(df):,} Record</span>
            </div>
            <div class="card-body p-4 pt-0">
                <div class="table-responsive">
                    <table id="dataTable" class="table table-hover align-middle mb-0 w-100">
                        <thead class="table-dark">
                            <tr>
                                <th class="text-center">#</th>
"""

    # Generasi Header Tabel Tanpa Underscore (_)
    html_table = ""
    for col in df.columns:
        col_clean = col.replace("_", " ").upper()
        html_table += f"                                <th>{col_clean}</th>\n"

    html_table += """                            </tr>
                        </thead>
                        <tbody>
"""

    # Generasi Isi Baris Tabel
    for idx, row in df.iterrows():
        html_table += f"                            <tr>\n                                <td class='text-center'>{idx + 1}</td>\n"
        for col in df.columns:
            val = row[col]

            # Format angka untuk kolom jumlah kasus
            if col == val_col and isinstance(val, (int, float)):
                html_table += (
                    f"                                <td>{val:,.0f}</td>\n"
                )
            else:
                html_table += (
                    f"                                <td>{val}</td>\n"
                )

        html_table += "                            </tr>\n"

    html_table += """                        </tbody>
                    </table>
                </div>
            </div>
            <div class="card-footer bg-white text-muted text-center py-3 border-0">
                <small>Sumber Data: API Resmi <a href="https://satudata.jakarta.go.id" target="_blank" class="text-decoration-none text-danger">satudata.jakarta.go.id</a></small>
            </div>
        </div>
    </div>
"""

    # Config Chart.js & DataTables
    js_script = f"""
    <!-- jQuery dan DataTables JS -->
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

    <script>
        // Setup Global Font untuk Chart.js
        Chart.defaults.font.family = "'Poppins', sans-serif";
        Chart.defaults.color = "#6c757d";

        document.addEventListener("DOMContentLoaded", function() {{
            // Inisialisasi DataTables
            $('#dataTable').DataTable({{
                language: {{
                    url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/id.json',
                }},
                pageLength: 10,
                ordering: true
            }});

            const labels = {chart_labels};
            const dataValues = {chart_data};

            // 1. Diagram Batang
            const ctxBar = document.getElementById('barChart').getContext('2d');
            new Chart(ctxBar, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: 'Jumlah Balita Stunting',
                        data: dataValues,
                        backgroundColor: 'rgba(220, 53, 69, 0.85)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 1,
                        borderRadius: 4,
                        barPercentage: 0.6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            padding: 12,
                            callbacks: {{
                                label: function(context) {{
                                    return 'Jumlah: ' + context.raw.toLocaleString('id-ID') + ' Balita';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            grid: {{ borderDash: [4, 4] }},
                            ticks: {{
                                callback: function(value) {{ return value.toLocaleString('id-ID'); }}
                            }}
                        }},
                        x: {{
                            grid: {{ display: false }}
                        }}
                    }}
                }}
            }});

            // 2. Diagram Lingkaran
            const ctxPie = document.getElementById('pieChart').getContext('2d');
            new Chart(ctxPie, {{
                type: 'doughnut',
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: dataValues,
                        backgroundColor: [
                            '#dc3545', '#0d6efd', '#ffc107', '#0dcaf0', '#6c757d', 
                            '#d63384', '#fd7e14', '#20c997', '#6f42c1', '#198754'
                        ],
                        borderWidth: 2,
                        hoverOffset: 5
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {{
                        legend: {{ position: 'bottom', labels: {{ padding: 20 }} }},
                        tooltip: {{
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            padding: 12,
                            callbacks: {{
                                label: function(context) {{
                                    return ' ' + context.label + ': ' + context.raw.toLocaleString('id-ID') + ' Balita';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }});
    </script>
</body>
</html>
"""

    full_html = html_head + html_table + js_script

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_html)

    print(
        "4. Selesai! File 'index.html' berhasil diperbarui dengan dataset Stunting Balita (Dashboard Baru)."
    )


if __name__ == "__main__":
    main()

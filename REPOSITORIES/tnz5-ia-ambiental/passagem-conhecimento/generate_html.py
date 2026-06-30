import pandas as pd
import glob
import os
import base64
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--plots_dir', required=True)
parser.add_argument('--csv_path', required=True)
parser.add_argument('--output_html', required=True)
parser.add_argument('--description', required=True)
parser.add_argument('--os_number', required=True)
parser.add_argument('--model_name', required=True)
parser.add_argument('--model_desc', required=True)
parser.add_argument('--model_time', required=True)
parser.add_argument('--model_tax', required=True)
parser.add_argument('--conf_img', required=True)
parser.add_argument('--mm_img', required=True)
parser.add_argument('--map_img', required=True)
args = parser.parse_args()

plots_dir = args.plots_dir
csv_path = args.csv_path
output_html = args.output_html
description = args.description
os_number = args.os_number
model_name = args.model_name
model_desc = args.model_desc
model_time = args.model_time
model_tax = args.model_tax
conf_img_path = args.conf_img
mm_img_path = args.mm_img
map_img_path = args.map_img

inference_text = "As imagens a seguir apresentam a comparação da segmentação da possível ocorrência de coral sol com o quadro original do vídeo. Foram selecionados apenas os quadros onde a confiança do modelo foi superior ou igual a linha de corte."
maps_text = "Mapa com as coordenadas geográficas (Northing, Easting) da trajetória feita pelo ROV e a possível ocorrência de coral sol com confiança acima da linha de corte."
series_text = "Confiança do modelo de IA ao longo do tempo total dos vídeos da operação."
table_text = "Tabela com os eventos encontrados pelo modelo de IA onde a confiança foi superior ou igual à linha de corte."

df = pd.read_csv(csv_path)

plots_imgs = sorted(glob.glob(os.path.join(plots_dir, '*')))
plot_files = {os.path.splitext(os.path.basename(p))[0]: p for p in plots_imgs}

def img_to_base64(path):
    with open(path, "rb") as img_file:
        ext = os.path.splitext(path)[1][1:]
        b64 = base64.b64encode(img_file.read()).decode()
        return f'data:image/{ext};base64,{b64}'

def get_plot_filename(row):
    if 'Nome do vídeo' in row and 'Tempo do vídeo' in row:
        return f"{row['Nome do vídeo']}_{(row['Tempo do vídeo']).replace(':','-')}"
    return None

def plot_link(row):
    fname = get_plot_filename(row)
    if fname and fname in plot_files:
        b64img = img_to_base64(plot_files[fname])
        return f'<a href="{b64img}" class="plot-link">Abrir imagem</a>'
    return ''

if 'Nome do vídeo' in df.columns and 'Tempo do vídeo' in df.columns:
    df['Plots'] = df.apply(plot_link, axis=1)

def img_tag(path, width="600px"):
    return f'<div style="text-align:center;margin:20px 0;"><img src="{img_to_base64(path)}" class="zoomable-img" style="max-width:{width};border-radius:10px;box-shadow:0 2px 8px #888;cursor:pointer;"></div>'

plots_html = ''.join([img_tag(img) for img in plots_imgs])
conf_img = img_tag(conf_img_path)
mm_img = img_tag(mm_img_path)
map_img = img_tag(map_img_path)

table_html = df.to_html(classes='styled-table', index=False, border=0, escape=False)

css = """
<style>
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f8f9fa;
    margin: 0;
    padding: 0;
}
h1 {
    text-align: center;
    color: #222;
    margin-top: 30px;
}
h2 {
    color: #009879;
    margin: 5px 0 10px 0;
    text-align: left;
}
.section, .scroll-section, .section.table-section {
    background: #fff;
    border-radius: 10px;
    margin: 30px auto;
    padding: 25px 35px;
    max-width: 1200px;
    box-shadow: 0 2px 12px #ddd;
}
.scroll-section {
    max-height: 600px;
    overflow-y: auto;
}
.styled-table {
    border-collapse: collapse;
    margin: 25px auto;
    font-size: 1.1em;
    min-width: 600px;
    background-color: #fff;
    border-radius: 12px 12px 0 0;
    overflow: hidden;
    box-shadow: 0 2px 20px #aaa;
    width: 100%;
    text-align: center;
}
.styled-table thead tr {
    background-color: #009879;
    color: #fff;
    text-align: center;
    font-weight: bold;
}
.styled-table th, .styled-table td {
    padding: 12px 18px;
    text-align: center;
}
.styled-table tbody tr {
    border-bottom: 1px solid #dddddd;
}
.styled-table tbody tr:nth-of-type(even) {
    background-color: #f3f3f3;
}
.styled-table tbody tr:last-of-type {
    border-bottom: 2px solid #009879;
}
#img-modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0,0,0,0.85);
    align-items: center;
    justify-content: center;
}
#img-modal img {
    max-width: 90vw;
    max-height: 90vh;
    border-radius: 10px;
    box-shadow: 0 2px 12px #111;
}
#img-modal.show {
    display: flex;
}
</style>
"""

js = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    var modal = document.getElementById('img-modal');
    var modalImg = document.getElementById('img-modal-img');
    document.querySelectorAll('.zoomable-img').forEach(function(img) {
        img.onclick = function() {
            modalImg.src = this.src;
            modal.classList.add('show');
        }
    });
    modal.onclick = function(e) {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    }
    document.querySelectorAll('a.plot-link').forEach(function(link) {
        link.onclick = function(e) {
            e.preventDefault();
            modalImg.src = this.href;
            modal.classList.add('show');
        }
    });
});
</script>
<div id="img-modal"><img id="img-modal-img" src=""></div>
"""

html = f"""
<html>
<head>
<meta charset="utf-8">
<title>Relatório de análise da operação feito por IA</title>
{css}
</head>
<body>
<h1>Relatório de análise da operação feito por IA</h1>
<div class="section">
<h2>Informações cadastrais da operação</h2>
<p><b>Descrição:</b> {description}</p>
<p><b>Número da OS:</b> {os_number}</p>
</div>
<div class="section">
<h2>Informações sobre o modelo de IA utilizado</h2>
<p><b>Nome do modelo utilizado:</b> {model_name}</p>
<p><b>Recomendações e limitações do modelo:</b> {model_desc}</p>
<p><b>Taxa de quadros analisada pelo modelo:</b> {model_tax}</p>
<p><b>Tempo total de processamento:</b> {model_time}</p>
</div>
<div class="scroll-section">
<h2>Imagens onde foi identificada a probabilidade de ocorrência</h2>
<p>{inference_text}</p>
{plots_html}
</div>
<div class="section">
<h2>Mapa</h2>
<p>{maps_text}</p>
{map_img}
</div>
<div class="section">
<h2>Confiança do modelo de IA</h2>
<p>{series_text}</p>
{conf_img}
{mm_img}
</div>
<div class="section table-section">
<h2>Tabela de Eventos feita pelo modelo de IA</h2>
<p>{table_text}</p>
{table_html}
</div>
{js}
</body>
</html>
"""

with open(os_number + "/" + output_html, 'w', encoding='utf-8') as f:
    f.write(html)
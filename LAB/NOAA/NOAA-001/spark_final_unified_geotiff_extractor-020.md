# 🧭 Stable Schema v1 — Documentação de Features (GeoTIFF + Spark)

Este schema define um padrão estável para ingestão de arquivos **GeoTIFF em Spark**, garantindo:

* preservação de tipos (sem inferência incorreta)
* consistência geoespacial
* compatibilidade com GDAL / rasterio / TIFF
* segurança contra corrupção de schema no Spark

---

# 📁 1. `file` — Metadados do arquivo

| Campo          | Tipo   | Descrição                              |
| -------------- | ------ | -------------------------------------- |
| `path`         | string | Caminho completo do arquivo no sistema |
| `filename`     | string | Nome do arquivo                        |
| `extension`    | string | Extensão (ex: `.tif`)                  |
| `size_bytes`   | long   | Tamanho do arquivo em bytes            |
| `checksum_md5` | string | Hash MD5 para validação de integridade |

### 🎯 Objetivo

Garantir:

* rastreabilidade do arquivo
* deduplicação
* validação de integridade
* versionamento de dados

---

# 🛰️ 2. `raster` — Metadados principais do raster

| Campo         | Tipo               | Descrição                            |
| ------------- | ------------------ | ------------------------------------ |
| `driver`      | string             | Driver GDAL (ex: GTiff)              |
| `width`       | int                | Largura em pixels                    |
| `height`      | int                | Altura em pixels                     |
| `bands_count` | int                | Número de bandas                     |
| `dtypes`      | array<string>      | Tipo de dado por banda               |
| `crs_wkt`     | string             | Sistema de referência (WKT completo) |
| `epsg`        | int                | Código EPSG (se disponível)          |
| `transform`   | array<double>      | Matriz afim (georreferenciamento)    |
| `nodata`      | double             | Valor de NoData                      |
| `metadata`    | map<string,string> | Metadados gerais do GDAL             |

### 🎯 Objetivo

Representar a **identidade geoespacial do raster**, incluindo:

* sistema de coordenadas
* resolução espacial
* transformação geográfica

---

# 🧾 3. `tiff_ifd` — Estrutura interna do TIFF

| Campo               | Tipo          | Descrição                                |
| ------------------- | ------------- | ---------------------------------------- |
| `compression`       | string        | Tipo de compressão (NONE, LZW, etc.)     |
| `photometric`       | string        | Interpretação de cores (RGB, Gray, etc.) |
| `planar_config`     | string        | Organização dos dados (pixel/banda)      |
| `rows_per_strip`    | int           | Organização em “strips”                  |
| `tile_width`        | int           | Largura de tile (se aplicável)           |
| `tile_length`       | int           | Altura de tile                           |
| `predictor`         | int           | Otimização de compressão                 |
| `bits_per_sample`   | array<int>    | Bits por banda                           |
| `samples_per_pixel` | int           | Canais por pixel                         |
| `sample_format`     | array<string> | Tipo de dado (uint, float, etc.)         |
| `orientation`       | string        | Orientação da imagem                     |
| `byte_order`        | string        | Endianness (LSB/MSB)                     |

### 🎯 Objetivo

Descrever como o TIFF está **fisicamente armazenado**, essencial para:

* decodificação correta
* compatibilidade entre bibliotecas
* auditoria técnica

---

# 🌍 4. `geotiff` — Metadados de georreferenciamento

| Campo               | Tipo               | Descrição                      |
| ------------------- | ------------------ | ------------------------------ |
| `model_pixel_scale` | array<double>      | Tamanho do pixel no mundo real |
| `model_tiepoint`    | array<double>      | Ponto de referência geográfico |
| `geo_keys`          | map<string,string> | Todas as chaves GeoTIFF        |

### 🎯 Objetivo

Garantir o vínculo entre:

* pixels da imagem
* coordenadas reais (UTM / geográficas)

---

# 📍 5. `spatial` — Geometria derivada

| Campo    | Tipo          | Descrição                             |
| -------- | ------------- | ------------------------------------- |
| `bbox`   | array<double> | Bounding box [minX, minY, maxX, maxY] |
| `center` | array<double> | Centro geométrico da imagem           |

### 🎯 Objetivo

Permitir:

* filtros espaciais
* indexação geográfica
* integração com sistemas GIS

---

# 📊 6. `quality` — Estatísticas de qualidade por banda

Cada banda do raster gera um conjunto de métricas:

## Estrutura:

```text
quality: {
  band_1: {...},
  band_2: {...},
  band_3: {...}
}
```

## Métricas por banda

| Campo           | Tipo   | Descrição                   |
| --------------- | ------ | --------------------------- |
| `min`           | double | Valor mínimo de pixel       |
| `max`           | double | Valor máximo                |
| `mean`          | double | Média dos valores           |
| `std`           | double | Desvio padrão               |
| `valid_pixels`  | long   | Pixels válidos              |
| `nodata_pixels` | long   | Pixels NoData               |
| `valid_percent` | double | Percentual de dados válidos |

### 🎯 Objetivo

Permitir:

* controle de qualidade de imagens
* detecção de anomalias
* preparação para machine learning
* validação de sensores

---

# ⚠️ Regras de Design (Críticas)

Este schema evita problemas conhecidos de Spark:

## ❌ Anti-padrões eliminados

* mapas aninhados (`map<map<map<...>>>`)
* strings representando JSON dentro do Spark
* inferência automática de schema
* tipos inconsistentes por campo

## ✔ Padrões adotados

* `StructType` para dados estruturados
* `MapType<string,string>` apenas para metadata plana
* normalização antes da ingestão no Spark
* tipos numéricos estritos (double/int/long)

---

# 🧩 Arquitetura conceitual

```text
file      → identidade do arquivo
raster    → definição geoespacial
tiff_ifd  → estrutura interna do TIFF
geotiff   → georreferenciamento
spatial   → geometria derivada
quality   → análise estatística
```

---

# 🚀 Benefícios do Schema

Este modelo garante:

* estabilidade em pipelines Spark
* compatibilidade entre GDAL e rasterio
* eliminação de erros de inferência de tipos
* suporte a escala (multi-arquivo / batch)
* base sólida para ML geoespacial


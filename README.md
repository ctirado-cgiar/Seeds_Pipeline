# Seeds_Pipeline

**Digital phenotyping pipeline for *Phaseolus* spp. seed characterisation**  
Alliance Bioversity International and CIAT — Bean Breeding Program, Palmira, Colombia

---

## Overview

Seeds_Pipeline is a modular Python-based image processing pipeline for the morphometric, colorimetric, and shape-based characterisation of *Phaseolus* seeds from images captured with the Phenobox system. It extracts over 37 quantitative descriptors per seed, computes pairwise similarity distances, and performs unsupervised hierarchical clustering to support genotype comparison and breeding decisions.

The pipeline is operated through a graphical orchestrator (`00_orquestador_pipeline.py`) that handles all interactive steps at startup and then runs autonomously from end to end without further user intervention.

---

## Pipeline overview

```
Images (Phenobox)
       │
       ▼
01 → 02   Geometric correction (checkerboard calibration)
       │
03 → 04   Colorimetric correction (colour card)
       │
  05        Scale calibration
  06        AOI crop          ← handled by orchestrator at startup
  07        Mask exclusion    ← handled by orchestrator after step 04
       │
  08 → 09   Morphometric analysis (37 descriptors + Haralick texture)
       │
10.0 → 10.1  Colour extraction (K-means) + EMD colour distances
       │
11.0 → 11.1 → 11.2   Shape analysis (GPA + EFA)
       │
  12        Shape distances (normalised Euclidean)
  13        Export dendrograms to JSON (D3.js)
  14        Integrated PCA + Ward clustering
  15        Seed counter (Watershed)
  16        Merge with field book
```

---

## Requirements

- Python 3.11+
- Windows (tested on Windows 10/11 with Miniconda)
- Conda environment or virtualenv recommended

### Dependencies

```
opencv-python
plantcv
numpy
pandas
scipy
scikit-image
scikit-learn
matplotlib
python-dotenv
tkinter  (included in standard Python)
```

Install with:

```bash
pip install -r requirements.txt
```

---

## Setup

### 1. Create trial folder structure

Run the batch file to create the full folder structure and `.env` file for a new trial:

```bash
crear_ensayo_seedPipeline.bat
```

This creates all required subfolders and a `.env` file with the `RUTA` variable pointing to your trial folder.

### 2. Configure `.env`

The `.env` file in the `scripts/` folder must define:

```
RUTA=D:/path/to/your/trial/folder
```

All scripts read this variable to locate input and output folders.

### 3. Place input images

| Folder | Content |
|---|---|
| `all/` | Original images from the Phenobox (JPG) |
| `calibracionCamara/ajedrez/` | Checkerboard calibration images |
| `calibracionCamara/colorCard/colorCard.jpg` | Single image of the colour card |
| `libroCampo/libroCampo.csv` | Field book CSV with `In_row` column |

---

## Running the pipeline

Launch the orchestrator:

```bash
python scripts/00_orquestador_pipeline.py
```

### Startup wizard (interactive — ~2 minutes)

At launch, a setup window appears where you:

1. Select the trial folder (`RUTA`)
2. Adjust key parameters
3. Enable or disable pipeline steps
4. **Scale factor** — click two points on the reference image and enter the real distance in mm. Saved automatically to `calibracionCamara/factorEscala/factor_escala.json`
5. Check whether to activate **AOI crop** and/or **exclusion mask** (defined later on corrected images)

Press **▶ Iniciar Pipeline** — the wizard closes and the pipeline starts automatically.

### Mid-run pause (AOI and mask — ~30 seconds)

After steps 01–04 complete, the pipeline pauses and shows a dialog with the first corrected image from `colorCorrejidas/`. If AOI and/or mask were activated:

- Draw the region of interest rectangle
- Draw the exclusion mask rectangle (e.g. to cover the colour card)

Confirm → the pipeline applies the selections to the entire image batch and continues autonomously to the end.

---

## Scripts reference

### Geometric correction

| Script | Input | Output | Key parameters |
|---|---|---|---|
| `01_ObtenerParametros_Ajedrez.py` | `calibracionCamara/ajedrez/*.jpg` | `calibracionCamara/parametrosCorreccion/calibracion_params.npz` | `GUARDAR_CHESSBOARD_CORNERS` (bool) |
| `02_DistorcionCorrection_Ajedrez.py` | `all/*.jpg` | `noDistorcion/` | — |

### Colorimetric correction

| Script | Input | Output | Key parameters |
|---|---|---|---|
| `03_ObtenerMascara_ColorCard.py` | `calibracionCamara/colorCard/colorCard.jpg` | `calibracionCamara/colorCard/colorCard_mask.png` | `RADIUS` (patch detection radius, default 6); `POS` (card orientation: 1, 2 or 3, default 3) |
| `04_ColorCorrection_ByMask copy.py` | `noDistorcion/` + `colorCard_mask.png` | `colorCorrejidas/` | — |

### Scale, AOI and mask

| Script | Input | Output | Notes |
|---|---|---|---|
| `05_ConocerEscalas.py` | Reference image | `calibracionCamara/factorEscala/factor_escala.json` | Handled interactively by orchestrator |
| `06_CutImagesApp.py` | `colorCorrejidas/` | `areaInteres/` | Handled by orchestrator after step 04 |
| `07_ApplyMaskApp.py` | `areaInteres/` or `colorCorrejidas/` | same folder (in-place) | Handled by orchestrator after step 04 |

### Morphometric analysis

| Script | Input | Output | Key parameters |
|---|---|---|---|
| `08_analisisMorfometria.py` | `areaInteres/` | `Morfometria/metricasCompletas.csv`; `Binarizadas/`; `Segmentadas/`; `Resultados/` | `THRESHOLD` (Cr channel, default 127); `AREA_MIN` (200 px²); `AREA_MAX` (12000 px²); `ANCHO_MIN/MAX`; `LARGO_MIN/MAX` |
| `09_summarizeMorfometria.py` | `Morfometria/metricasCompletas.csv` | `Morfometria/metricasCompletas_summary.csv` | — |

### Colorimetric analysis

| Script | Input | Output | Key parameters |
|---|---|---|---|
| `10.0_extraerColor_Kmeans.py` | `Segmentadas/` | `Colorimetria/analisis_colores.csv` | `N_COLORS` (K dominant colours, default 2); `EROSION_ITERATIONS` (default 3); `KERNEL_SIZE` (default 7) |
| `10.1_colorDistance.py` | `Colorimetria/analisis_colores.csv` | `colorDistance/distance_matrix_emd.csv`; heatmap and dendrogram PNG | EMD computed in RGB space |

### Shape analysis

| Script | Input | Output | Key parameters |
|---|---|---|---|
| `11.0_filtrarBinarizadas.py` | `Binarizadas/` | `binarizadasFiltradas/` | `AREA_MIN_F`; `AREA_MAX_F`; `ANCHO_MIN_F/MAX_F`; `LARGO_MIN_F/MAX_F` |
| `11.1_alinearFormas.py` | `binarizadasFiltradas/` | `binarizadasAlineadas/` | `GRID_COLS` (visualisation grid columns, default 8) |
| `11.2_formaPromedio.py` | `binarizadasAlineadas/` | `formaPromedio/efa_coefficients_all_images.csv`; PNG visualisations | `N_HARMONICS` (EFA harmonics, default 20); `N_POINTS` (contour points, default 128); `MIN_SOLIDITY` (default 0.90); `MIN_CIRCULARITY` (default 0.55) |

### Distances, clustering and integration

| Script | Input | Output | Key parameters |
|---|---|---|---|
| `12_formasDistance.py` | `formaPromedio/efa_coefficients_all_images.csv` + morphometry summary | `formasDistance/shapes_distance_matrix.csv`; heatmap and dendrogram PNG | — |
| `13_linkage2json.py` | colour and shape distance matrices | `dendrogramas/dendrogram_color.json`; `dendrogram_shapes.json` | `LINKAGE_METHOD` (default `'average'`) |
| `14_clusterFormasFormayMorfometríaIntegradaIntegrada.py` | EFA coefficients + morphometry summary | `clusterIntegrado/` (PCA plots, cluster assignments) | `MAX_CLUSTERS` (default 6); `N_COMPONENTS` (max PCA components, default 10) |

### Seed counting and field book merge

| Script | Input | Output | Key parameters |
|---|---|---|---|
| `15_contadorSemillas.py` | `areaInteres/` | `conteo/reporte_YYYYMMDD_HHMMSS.csv` | `THRESHOLD_VAL` (Cr channel, default 125); `MIN_DISTANCE` (px between seeds, default 10); `PEAK_THRESHOLD` (Watershed fraction, default 0.20) |
| `16_unirDatosconLibroCampo.py` | morphometry + colour + shape + conteo CSVs + `libroCampo/libroCampo.csv` | `resultadosUnidos/metricasCompletasSemillas_*.csv` | Key normalisation: `in_row=1224.jpg` → `1224`; `_2`/`-2` suffixes treated as photo replicates |

---

## Folder structure

```
TRIAL_FOLDER/
├── all/                          ← original images
├── calibracionCamara/
│   ├── ajedrez/                  ← checkerboard images
│   ├── colorCard/                ← colour card image and mask
│   ├── factorEscala/             ← factor_escala.json
│   └── parametrosCorreccion/     ← calibracion_params.npz
├── noDistorcion/                 ← after geometric correction
├── colorCorrejidas/              ← after colorimetric correction
├── areaInteres/                  ← after AOI crop
├── Binarizadas/                  ← binary segmentation masks
├── binarizadasFiltradas/         ← filtered binary masks
├── binarizadasAlineadas/         ← GPA-aligned contours
├── Segmentadas/                  ← seed-on-white segmented images
├── Resultados/                   ← annotated result images
├── Morfometria/
│   ├── metricasCompletas.csv
│   └── metricasCompletas_summary.csv
├── Colorimetria/
│   └── analisis_colores.csv
├── colorDistance/
│   └── distance_matrix_emd.csv
├── formaPromedio/
│   └── efa_coefficients_all_images.csv
├── formasDistance/
│   └── shapes_distance_matrix.csv
├── dendrogramas/
│   ├── dendrogram_color.json
│   └── dendrogram_shapes.json
├── clusterIntegrado/
├── conteo/
├── libroCampo/
│   └── libroCampo.csv
└── resultadosUnidos/
    └── metricasCompletasSemillas_TRIAL_YYYYMMDD.csv
```

---

## Key output variables

### Morphometry (`metricasCompletas.csv`)

`Area`, `Perimeter`, `Width`, `Length`, `AR`, `Circ`, `Solid`, `Caliper`, `Theta`, `Eccentricity`, `Form_factor`, `Narrow_factor`, `Rectangularity`, `PD_ratio`, `PLW_ratio`, `Convexity`, `Elongation`, `Haralick_Circ`, `Norm_Circ`, `Radius_min/mean/max`, `Diameter_min/mean/max`, `Radius_ratio`, `Major_axis`, `Minor_axis`, `Area_CH`, `Centroid_X/Y`, `ASM`, `Contrast`, `Correlation`, `Variance` (dissimilarity), `IDM` (linear homogeneity), `Energy`, `Entropy`

### Colorimetry (`analisis_colores.csv`)

`RGB1`, `RGB2`, `Hex1`, `Hex2`, `%1`, `%2`, `L1`, `L2` (luminance), `LAB1`, `LAB2`

### Shape (`efa_coefficients_all_images.csv`)

`H1_A … H20_D` — 80 normalised EFA coefficients (4 per harmonic × 20 harmonics), invariant to orientation and starting point

---

## Notes on image naming

Scripts 10.1 and 12 expect images named as `in_row=NNNN.jpg` or `in_row=NNNN_2.jpg`. Script 16 normalises these automatically:

- `in_row=1224.jpg` → key `1224`
- `in_row=1234_2.jpg` or `in_row=1234-2.jpg` → photo replicate of `1234`, excluded from morphometry and colour but **summed** in seed counts

---

## Citation

If you use this pipeline in your research, please cite:

> Alliance Bioversity International and CIAT — Bean Breeding Program (2025). *Seeds_Pipeline: A modular Python pipeline for digital phenotyping of Phaseolus spp. seeds*. Palmira, Colombia.

Relevant methodological references:

- Zhang, Z. (2000). A flexible new technique for camera calibration. *IEEE TPAMI*, 22(11), 1330–1334.
- Berry et al. (2018). An automated, high-throughput method for standardizing image color profiles. *PeerJ*, 6:e5727.
- Kuhl & Giardina (1982). Elliptic Fourier features of a closed contour. *CGIP*, 18(3), 236–258.
- Haralick et al. (1973). Textural features for image classification. *IEEE Trans. SMC*, 3(6), 610–621.
- Rubner et al. (2000). The Earth Mover's Distance as a metric for image retrieval. *IJCV*, 40(2), 99–121.
- Ward, J. H. (1963). Hierarchical grouping to optimize an objective function. *JASA*, 58(301), 236–244.

---

## License

This project is developed for internal research use at Alliance Bioversity International and CIAT. Contact the Bean Breeding Program for collaboration inquiries.

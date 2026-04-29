import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics import silhouette_score
import os
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

class IntegratedMorphometricAnalysis:
    """Análisis integrado: Forma (EFA) + Morfometría completa"""
    
    def __init__(self, input_folder, metrics_path, output_folder):
        self.input_folder = input_folder
        self.metrics_path = metrics_path
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)
        
        self.data = None
        self.pca_model = None
        self.scaler = None
        
    def load_and_integrate_data(self):
        """Carga y combina EFA + métricas morfométricas completas"""
        # Coeficientes EFA
        efa_path = os.path.join(self.input_folder, 'efa_coefficients_all_images.csv')
        efa_df = pd.read_csv(efa_path)
        
        # Métricas morfométricas completas
        metrics_df = pd.read_csv(self.metrics_path)
        
        # Aplanar columnas multi-nivel si es necesario
        if isinstance(metrics_df.columns, pd.MultiIndex):
            metrics_df.columns = ['_'.join(col).strip() if col[1] else col[0] 
                                 for col in metrics_df.columns.values]
        
        # Renombrar columna de imagen para match
        if 'Img' in metrics_df.columns:
            metrics_df = metrics_df.rename(columns={'Img': 'image_name'})
        
        # Combinar por nombre de imagen
        self.data = pd.merge(efa_df, metrics_df, on='image_name', how='inner')
        
        if len(self.data) == 0:
            raise ValueError("No se pudo combinar EFA con métricas. Verifica nombres de imagen.")
        
        # Separar features
        self.genotypes = self.data['image_name'].values
        
        # Columnas EFA
        self.efa_cols = [col for col in self.data.columns if col.startswith('H')]
        
        # Columnas de métricas morfométricas (solo mean para reducir dimensionalidad)
        # Seleccionar las más importantes
        key_metrics = [
            'W_mean', 'L_mean', 'P_mean', 'A_mean', 'AR_mean', 'Circ_mean',
            'Solid_mean', 'Radius_mean_mean', 'Radius_ratio_mean',
            'Major_axis_mean', 'Minor_axis_mean', 'Eccentricity_mean',
            'Form_factor_mean', 'Elongation_mean', 'Convexity_mean',
            'ASM_mean', 'Contrast_mean', 'Correlation_mean', 'Entropy_mean'
        ]
        
        # Filtrar las que existen
        self.morph_cols = [col for col in key_metrics if col in self.data.columns]
        
        # Si no hay _mean, buscar sin sufijo
        if len(self.morph_cols) == 0:
            alt_metrics = ['W', 'L', 'P', 'A', 'AR', 'Circ', 'Solid', 
                          'Major_axis', 'Minor_axis', 'Eccentricity',
                          'Form_factor', 'Elongation', 'Convexity',
                          'ASM', 'Contrast', 'Entropy']
            self.morph_cols = [col for col in alt_metrics if col in self.data.columns]
        
        self.feature_names = self.efa_cols + self.morph_cols
        self.features = self.data[self.feature_names].values
        
        # Guardar info
        self.n_efa = len(self.efa_cols)
        self.n_morph = len(self.morph_cols)
        
        return self.data
    
    def perform_pca(self, n_components=None):
        """PCA sobre features integrados"""
        n_samples = self.features.shape[0]
        
        if n_components is None:
            n_components = min(10, n_samples - 1)
        else:
            n_components = min(n_components, n_samples - 1)
        
        # Estandarizar
        self.scaler = StandardScaler()
        features_scaled = self.scaler.fit_transform(self.features)
        
        # PCA
        self.pca_model = PCA(n_components=n_components)
        self.pc_scores = self.pca_model.fit_transform(features_scaled)
        
        # DataFrame de scores
        pc_cols = [f'PC{i+1}' for i in range(n_components)]
        self.pc_df = pd.DataFrame(
            self.pc_scores,
            index=self.genotypes,
            columns=pc_cols
        )
        
        return self.pc_df
    
    def plot_scree(self):
        """Gráfico de varianza explicada"""
        var_exp = self.pca_model.explained_variance_ratio_ * 100
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        axes[0].bar(range(1, len(var_exp) + 1), var_exp, 
                   color='teal', alpha=0.7, edgecolor='darkslategray', linewidth=1.5)
        axes[0].set_xlabel('PC', fontsize=11, fontweight='bold')
        axes[0].set_ylabel('Variance (%)', fontsize=11, fontweight='bold')
        axes[0].set_title('Scree Plot (Integrated)', fontsize=12, fontweight='bold')
        axes[0].grid(axis='y', alpha=0.3)
        
        cumsum = np.cumsum(var_exp)
        axes[1].plot(range(1, len(var_exp) + 1), cumsum, 'o-', 
                    color='darkgreen', linewidth=2.5, markersize=8, markeredgecolor='black')
        axes[1].axhline(80, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='80%')
        axes[1].set_xlabel('PC', fontsize=11, fontweight='bold')
        axes[1].set_ylabel('Cumulative (%)', fontsize=11, fontweight='bold')
        axes[1].set_title('Cumulative Variance', fontsize=12, fontweight='bold')
        axes[1].grid(alpha=0.3)
        axes[1].legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_folder, 'Integrated_scree_plot.png'), 
                   dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_biplot_morphometric(self, pc_x=1, pc_y=2):
        """Biplot destacando variables morfométricas"""
        fig, ax = plt.subplots(1, 1, figsize=(13, 10))
        
        pcx_idx = pc_x - 1
        pcy_idx = pc_y - 1
        
        colors = plt.cm.tab20(np.linspace(0, 1, len(self.genotypes)))
        
        # Scores
        for i, (geno, color) in enumerate(zip(self.genotypes, colors)):
            ax.scatter(self.pc_scores[i, pcx_idx], self.pc_scores[i, pcy_idx],
                      s=150, color=color, edgecolors='black', linewidth=1.5, 
                      alpha=0.7, zorder=3)
            ax.text(self.pc_scores[i, pcx_idx], self.pc_scores[i, pcy_idx], 
                   f' {geno}', fontsize=8, va='center', fontweight='bold')
        
        # Loadings
        loadings = self.pca_model.components_.T * np.sqrt(self.pca_model.explained_variance_)
        
        scale_factor = 0.7 * max(np.abs(self.pc_scores[:, [pcx_idx, pcy_idx]]).max() / 
                                  np.abs(loadings[:, [pcx_idx, pcy_idx]]).max(), 1)
        
        # Solo variables morfométricas (no EFA)
        morph_indices = [i for i, name in enumerate(self.feature_names) if name in self.morph_cols]
        
        for idx in morph_indices:
            loading_x = loadings[idx, pcx_idx] * scale_factor
            loading_y = loadings[idx, pcy_idx] * scale_factor
            
            ax.arrow(0, 0, loading_x, loading_y,
                    head_width=0.08, head_length=0.08, fc='red', ec='darkred',
                    alpha=0.7, linewidth=2.5, zorder=2)
            
            # Limpiar nombre de variable
            var_name = self.feature_names[idx].replace('_mean', '').replace('_', ' ')
            
            ax.text(loading_x * 1.15, loading_y * 1.15,
                   var_name, fontsize=8, color='darkred', 
                   fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', 
                   facecolor='yellow', alpha=0.7))
        
        var_x = self.pca_model.explained_variance_ratio_[pcx_idx] * 100
        var_y = self.pca_model.explained_variance_ratio_[pcy_idx] * 100
        
        ax.set_xlabel(f'PC{pc_x} ({var_x:.1f}%)', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'PC{pc_y} ({var_y:.1f}%)', fontsize=12, fontweight='bold')
        ax.set_title(f'Integrated Biplot: EFA ({self.n_efa}) + Morphometry ({self.n_morph})', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.grid(alpha=0.3, linestyle='--')
        ax.axhline(0, color='gray', linewidth=1, alpha=0.5)
        ax.axvline(0, color='gray', linewidth=1, alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_folder, f'Integrated_biplot_PC{pc_x}_PC{pc_y}.png'), 
                   dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_loadings_heatmap(self, n_pcs=5):
        """Heatmap de loadings de variables morfométricas"""
        # Solo primeros N PCs
        n_pcs_actual = min(n_pcs, self.pca_model.n_components_)
        
        # Extraer loadings de variables morfométricas
        morph_indices = [i for i, name in enumerate(self.feature_names) if name in self.morph_cols]
        morph_names = [self.feature_names[i].replace('_mean', '').replace('_', ' ') 
                      for i in morph_indices]
        
        loadings_morph = self.pca_model.components_[:n_pcs_actual, morph_indices].T
        
        fig, ax = plt.subplots(1, 1, figsize=(8, max(6, len(morph_names)*0.3)))
        
        sns.heatmap(
            loadings_morph,
            cmap='RdBu_r',
            center=0,
            cbar_kws={'label': 'Loading'},
            yticklabels=morph_names,
            xticklabels=[f'PC{i+1}' for i in range(n_pcs_actual)],
            annot=True,
            fmt='.2f',
            linewidths=0.5,
            ax=ax
        )
        
        ax.set_title('Morphometric Variables - PCA Loadings', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('Morphometric Variable', fontsize=11, fontweight='bold')
        ax.set_xlabel('Principal Component', fontsize=11, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_folder, 'Integrated_loadings_heatmap.png'), 
                   dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_dendrogram_with_clusters(self, method='ward', n_clusters=3):
        """Dendrograma con clusters identificados"""
        cumvar = np.cumsum(self.pca_model.explained_variance_ratio_ * 100)
        n_pcs = np.where(cumvar >= 80)[0]
        n_pcs = n_pcs[0] + 1 if len(n_pcs) > 0 else self.pc_scores.shape[1]
        n_pcs = min(n_pcs, self.pc_scores.shape[1])
        
        distances = pdist(self.pc_scores[:, :n_pcs], metric='euclidean')
        linkage_matrix = linkage(distances, method=method)
        
        fig, ax = plt.subplots(1, 1, figsize=(13, 7))
        
        dendrogram(
            linkage_matrix,
            labels=self.genotypes,
            leaf_rotation=90,
            leaf_font_size=10,
            color_threshold=linkage_matrix[-n_clusters+1, 2] if n_clusters <= len(self.genotypes) else None,
            above_threshold_color='gray',
            ax=ax
        )
        
        ax.set_xlabel('Genotype', fontsize=12, fontweight='bold')
        ax.set_ylabel('Distance', fontsize=12, fontweight='bold')
        ax.set_title(f'Hierarchical Clustering (Integrated, {method})\n{n_clusters} clusters | {n_pcs} PCs (80% var)', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        if n_clusters <= len(self.genotypes):
            ax.axhline(linkage_matrix[-n_clusters+1, 2], color='red', 
                      linestyle='--', linewidth=2, label=f'Cut (k={n_clusters})')
            ax.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_folder, f'Integrated_dendrogram_{method}_k{n_clusters}.png'), 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
        # Asignar clusters
        if n_clusters <= len(self.genotypes):
            clusters = fcluster(linkage_matrix, n_clusters, criterion='maxclust')
            
            cluster_df = pd.DataFrame({
                'Genotype': self.genotypes,
                'Cluster': clusters
            })
            
            cluster_df.to_csv(os.path.join(self.output_folder, f'cluster_assignments_k{n_clusters}.csv'), 
                             index=False)
            
            return cluster_df
        
        return None
    
    def plot_silhouette_analysis(self, max_clusters=6):
        """Análisis de silueta para determinar número óptimo de clusters"""
        cumvar = np.cumsum(self.pca_model.explained_variance_ratio_ * 100)
        n_pcs = np.where(cumvar >= 80)[0]
        n_pcs = n_pcs[0] + 1 if len(n_pcs) > 0 else self.pc_scores.shape[1]
        n_pcs = min(n_pcs, self.pc_scores.shape[1])
        
        data_for_clustering = self.pc_scores[:, :n_pcs]
        
        silhouette_scores = []
        K_range = range(2, min(max_clusters + 1, len(self.genotypes)))
        
        for k in K_range:
            distances = pdist(data_for_clustering, metric='euclidean')
            linkage_matrix = linkage(distances, method='ward')
            clusters = fcluster(linkage_matrix, k, criterion='maxclust')
            
            score = silhouette_score(data_for_clustering, clusters)
            silhouette_scores.append(score)
        
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        ax.plot(K_range, silhouette_scores, 'o-', linewidth=2.5, markersize=10,
               color='purple', markeredgecolor='black', markeredgewidth=1.5)
        
        best_k = K_range[np.argmax(silhouette_scores)]
        ax.axvline(best_k, color='red', linestyle='--', linewidth=2, 
                  label=f'Best k = {best_k}')
        
        ax.set_xlabel('Number of Clusters', fontsize=12, fontweight='bold')
        ax.set_ylabel('Silhouette Score', fontsize=12, fontweight='bold')
        ax.set_title('Silhouette Analysis - Optimal Clusters', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.grid(alpha=0.3, linestyle='--')
        ax.legend(fontsize=11)
        ax.set_xticks(K_range)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_folder, 'Integrated_silhouette_analysis.png'), 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
        return best_k
    
    def plot_morphometric_boxplots(self, cluster_df, top_n=9):
        """Boxplots de variables morfométricas por cluster"""
        if cluster_df is None:
            return
        
        # Agregar cluster al dataframe
        data_with_clusters = self.data.copy()
        data_with_clusters['Cluster'] = cluster_df['Cluster'].values
        
        # Seleccionar top N variables morfométricas más importantes
        morph_indices = [i for i, name in enumerate(self.feature_names) if name in self.morph_cols]
        
        # Importancia = suma absoluta de loadings en primeros 3 PCs
        n_pcs_importance = min(3, self.pca_model.n_components_)
        importance = np.abs(self.pca_model.components_[:n_pcs_importance, morph_indices]).sum(axis=0)
        top_indices = np.argsort(importance)[-top_n:]
        
        top_vars = [self.morph_cols[i] for i in top_indices]
        
        ncols = 3
        nrows = int(np.ceil(len(top_vars) / ncols))
        
        fig, axes = plt.subplots(nrows, ncols, figsize=(15, nrows*4))
        axes = axes.flatten() if nrows > 1 else [axes] if ncols == 1 else axes
        
        for i, var in enumerate(top_vars):
            if var in data_with_clusters.columns:
                data_with_clusters.boxplot(column=var, by='Cluster', ax=axes[i])
                var_clean = var.replace('_mean', '').replace('_', ' ')
                axes[i].set_xlabel('Cluster', fontsize=10, fontweight='bold')
                axes[i].set_ylabel(var_clean, fontsize=10, fontweight='bold')
                axes[i].set_title('')
                axes[i].get_figure().suptitle('')
        
        for i in range(len(top_vars), len(axes)):
            axes[i].axis('off')
        
        plt.suptitle(f'Top {len(top_vars)} Morphometric Variables by Cluster', 
                    fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_folder, 'Integrated_boxplots_by_cluster.png'), 
                   dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_results(self):
        """Guarda resultados numéricos"""
        # PC scores
        self.pc_df.to_csv(os.path.join(self.output_folder, 'Integrated_PCA_scores.csv'))
        
        # Loadings
        loadings_df = pd.DataFrame(
            self.pca_model.components_.T,
            index=self.feature_names,
            columns=[f'PC{i+1}' for i in range(self.pca_model.n_components_)]
        )
        loadings_df.to_csv(os.path.join(self.output_folder, 'Integrated_PCA_loadings.csv'))
        
        # Varianza
        var_df = pd.DataFrame({
            'PC': [f'PC{i+1}' for i in range(len(self.pca_model.explained_variance_ratio_))],
            'Variance_%': self.pca_model.explained_variance_ratio_ * 100,
            'Cumulative_%': np.cumsum(self.pca_model.explained_variance_ratio_ * 100)
        })
        var_df.to_csv(os.path.join(self.output_folder, 'Integrated_PCA_variance.csv'), index=False)
        
        # Datos integrados (solo features usados)
        data_to_save = self.data[['image_name'] + self.feature_names].copy()
        data_to_save.to_csv(os.path.join(self.output_folder, 'Integrated_data_used.csv'), index=False)


def main():
    print("\n" + "="*60)
    print("ANÁLISIS C: INTEGRADO (FORMA + MORFOMETRÍA)")
    print("="*60 + "\n")
    
    input_folder = os.getenv('RUTA') + '/resultadosUnidos'
    metrics_path = os.getenv('RUTA') + '/resultadosUnidos/metricasCompletasSemillas_Color-Morfologia-Forma_GGR_2025_ANALISIS_20260310.csv'
    output_folder = os.getenv('RUTA') + '/analisisFormasIntegrado'
    
    analyzer = IntegratedMorphometricAnalysis(input_folder, metrics_path, output_folder)
    
    # Cargar datos
    print("Cargando datos integrados...", end=' ')
    data = analyzer.load_and_integrate_data()
    print(f"✓ ({len(analyzer.genotypes)} genotipos, {len(analyzer.feature_names)} features)")
    print(f"  - EFA: {analyzer.n_efa} coeficientes")
    print(f"  - Morfometría: {analyzer.n_morph} variables\n")
    
    # PCA
    print("Ejecutando PCA integrado...", end=' ')
    n_components = min(10, len(analyzer.genotypes) - 1)
    analyzer.perform_pca(n_components=n_components)
    print(f"✓ ({n_components} PCs)")
    
    # Visualizaciones
    print("Generando visualizaciones...", end=' ')
    analyzer.plot_scree()
    analyzer.plot_biplot_morphometric(pc_x=1, pc_y=2)
    
    if n_components >= 3:
        analyzer.plot_biplot_morphometric(pc_x=1, pc_y=3)
    
    analyzer.plot_loadings_heatmap(n_pcs=min(5, n_components))
    
    # Silhouette
    if len(analyzer.genotypes) > 2:
        best_k = analyzer.plot_silhouette_analysis(max_clusters=min(6, len(analyzer.genotypes)-1))
        
        # Dendrogramas
        cluster_df = analyzer.plot_dendrogram_with_clusters(method='ward', n_clusters=best_k)
        analyzer.plot_dendrogram_with_clusters(method='ward', n_clusters=3)
        analyzer.plot_dendrogram_with_clusters(method='average', n_clusters=best_k)
        
        # Boxplots
        analyzer.plot_morphometric_boxplots(cluster_df, top_n=9)
    
    print("✓")
    
    # Guardar
    print("Guardando resultados...", end=' ')
    analyzer.save_results()
    print("✓")
    
    print("\n" + "="*60)
    print("✓ COMPLETADO")
    print("="*60)
    print(f"Resultados en: {output_folder}\n")


if __name__ == "__main__":
    main()
import argparse
import pandas as pd
import scanpy as sc
import os
import warnings
import time  # Added import time
from PRESENT import gene_sets_alignment, peak_sets_alignment
from PRESENT import PRESENT_function
from PRESENT.Utils import combine_BC
from PRESENT.Utils import normalize_marker_name
warnings.filterwarnings("ignore")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='PRESENT: Cross-modality representation and multi-sample integration of spatially resolved omics data')
    parser.add_argument('--outputdir', type=str, default='./PRESENT_output', help='The output dir for PRESENT')
    parser.add_argument('--spatial_key', type=str, default='spatial', help='adata_rna/adata_atac/adata_adt.obsm key under which to load the spatial matrix of spots')
    parser.add_argument('--batch_key', type=str, default=None, help='adata_rna/adata_atac/adata_adt.obsm key under which to load the batch indices of spots')
    parser.add_argument('--adata_rna_path', type=str, nargs='*', default=[], help='The path to RNA raw count matrices of spots in anndata.AnnData format')
    parser.add_argument('--adata_atac_path', type=str, nargs='*', default=[], help='The path to ATAC raw fragment count matrices of spots in anndata.AnnData format')
    parser.add_argument('--adata_adt_path', type=str, nargs='*', default=[], help='The path to ADT raw count matrices of spots in anndata.AnnData format')

    parser.add_argument('--rdata_rna_path', type=str, default=None, help='The path to RNA raw counts of reference data in anndata.AnnData format')
    parser.add_argument('--rdata_rna_anno', type=str, default=None, help='rdata_rna.obs key under which to load the annotation')
    parser.add_argument('--rdata_atac_path', type=str, default=None, help='The path to ATAC raw fragment counts of reference data in anndata.AnnData format')
    parser.add_argument('--rdata_atac_anno', type=str, default=None, help='rdata_atac.obs key under which to load the annotation')
    parser.add_argument('--rdata_adt_path', type=str, default=None, help='The path to ADT raw counts of reference data in anndata.AnnData format')
    parser.add_argument('--rdata_adt_anno', type=str, default=None, help='rdata_adt.obs key under which to load the annotation')

    parser.add_argument('--nclusters', type=int, default=10, help='Number of spatial clusters')
    parser.add_argument('--gene_min_cells', type=int, default=1, help='Minimum number of cells expressed required for a gene to pass filtering')
    parser.add_argument('--peak_min_cells_fraction', type=float, default=0.03, help='Minimum fraction of cells accessible required for a peak to pass filtering')
    parser.add_argument('--protein_min_cells', type=int, default=1, help='Minimum number of cells expressed required for a protein to pass filtering')
    parser.add_argument('--num_hvg', type=int, default=3000, help='Number of highly variable genes to select for RNA data')
    parser.add_argument('--d_lat', type=int, default=50, help='The latent dimension of final embeddings')
    parser.add_argument('--k_neighbors', type=int, default=6, help='Number of neighbors for each spot to construct graph')
    parser.add_argument('--intra_neighbors', type=int, default=6, help='Number of intra_neighbors for each spot to construct cross-sample graph')
    parser.add_argument('--inter_neighbors', type=int, default=6, help='Number of inter_neighbors for each spot to construct cross-sample graph')
    parser.add_argument('--epochs', type=float, default=100, help='Max epochs to train the model')
    parser.add_argument('--lr', type=int, default=0.001, help='Initial learning rate')
    parser.add_argument('--batch_size', type=int, default=320, help='Batch size for training')
    parser.add_argument('--device', type=str, default='cuda', help='Device used for training')
    parser.add_argument('--device_id', type=int, default=0, help='Which gpu is used for training')

    args = parser.parse_args()
    adata_rna = adata_atac = adata_adt = None

    if len(args.adata_rna_path)==1: 
        adata_rna = sc.read_h5ad(args.adata_rna_path[0])
    elif len(args.adata_rna_path)>1: 
        assert args.batch_key is not None, "Please specify the batch_key"
        adata_rna_list = []
        for path in args.adata_rna_path:
            adata_rna_list.append(sc.read_h5ad(path))
        adata_rna_list = gene_sets_alignment(adata_rna_list)
        # 调用 combine_BC 函数
        adata_rna = combine_BC(adata_rna_list)
        adata_rna.obs[args.batch_key] = adata_rna.obs["src"]

    if len(args.adata_atac_path)==1: 
        adata_atac = sc.read_h5ad(args.adata_atac_path[0])
    elif len(args.adata_atac_path)>1: 
        assert args.batch_key is not None, "Please specify the batch_key"
        adata_atac_list = []
        for path in args.adata_atac_path:
            adata_atac_list.append(sc.read_h5ad(path))
        # 检查路径中是否包含 "Mouse_Brain"
        if any("Mouse_Brain" in path for path in args.adata_atac_path):
            adata_atac_list[0].var_names = [normalize_marker_name(name) for name in adata_atac_list[0].var_names]
            adata_atac_list[1].var_names = [normalize_marker_name(name) for name in adata_atac_list[1].var_names]
            adata_atac_list[2].var_names = [normalize_marker_name(name) for name in adata_atac_list[2].var_names]
            adata_atac_list[3].var_names = [normalize_marker_name(name) for name in adata_atac_list[3].var_names]
            adata_atac_list = peak_sets_alignment(adata_atac_list, sep=("_", "_"))
        else:
            adata_atac_list = peak_sets_alignment(adata_atac_list)
        # 调用 combine_BC 函数
        adata_atac = combine_BC(adata_atac_list)
        adata_atac.obs[args.batch_key] = adata_atac.obs["src"]
    
    if len(args.adata_adt_path)==1: 
        adata_adt = sc.read_h5ad(args.adata_adt_path[0])
    elif len(args.adata_adt_path)>1: 
        assert args.batch_key is not None, "Please specify the batch_key"
        adata_adt_list = []
        for path in args.adata_adt_path:
            adata_adt_list.append(sc.read_h5ad(path))
        if any("Mouse_Thymus" in path for path in args.adata_adt_path):
            adata_adt_list[0].var_names = [normalize_marker_name(name) for name in adata_adt_list[0].var_names]
            adata_adt_list[1].var_names = [normalize_marker_name(name) for name in adata_adt_list[1].var_names]
            adata_adt_list[2].var_names = [normalize_marker_name(name) for name in adata_adt_list[2].var_names]
            adata_adt_list[3].var_names = [normalize_marker_name(name) for name in adata_adt_list[3].var_names]
        adata_adt_list = gene_sets_alignment(adata_adt_list)
        # 调用 combine_BC 函数
        adata_adt = combine_BC(adata_adt_list)
        adata_adt.obs[args.batch_key] = adata_adt.obs["src"]
    
    print("Starting PRESENT function (training process)...") # Optional: Indicate start
    start_time = time.time() # Start timer

    adata = PRESENT_function(
        args.spatial_key, 
        batch_key = args.batch_key,
        adata_rna = adata_rna,
        adata_atac = adata_atac,
        adata_adt = adata_adt,
        rdata_rna = args.rdata_rna_path,
        rdata_rna_anno = args.rdata_rna_anno,
        rdata_atac = args.rdata_atac_path,
        rdata_atac_anno = args.rdata_atac_anno,
        rdata_adt = args.rdata_adt_path,
        rdata_adt_anno = args.rdata_adt_anno,

        gene_min_cells = args.gene_min_cells,
        peak_min_cells_fraction = args.peak_min_cells_fraction,
        protein_min_cells = args.protein_min_cells,
        num_hvg = args.num_hvg,
        nclusters = args.nclusters,
        d_lat = args.d_lat,
        k_neighbors = args.k_neighbors,
        intra_neighbors = args.intra_neighbors,
        inter_neighbors = args.inter_neighbors,
        epochs = args.epochs,
        lr = args.lr,
        batch_size = args.batch_size,
        device = args.device,
        device_id = args.device_id
    )
    end_time = time.time() # End timer
    running_time = end_time - start_time
    print(f"PRESENT function (training process) finished.") # Optional: Indicate end
    print(f"Total running time for PRESENT function: {running_time:.4f} seconds") # Print duration

    if args.outputdir.endswith("/"): args.outputdir = args.outputdir[0:-1]
    os.makedirs(args.outputdir, exist_ok=True)

    adata.write_h5ad(args.outputdir + "/adata_output.h5ad")
    pd.DataFrame(adata.X, index=adata.obs_names).to_csv(args.outputdir + "/embeddings_output.csv")
    adata.obs.loc[:, ["LeidenClusters"]].to_csv(args.outputdir + "/domains_output.csv")
    print("Joint embeddings and identified domains saved")
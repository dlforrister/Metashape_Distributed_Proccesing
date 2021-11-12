#!/bin/bash

#SBATCH --job-name=u6000251_agisoft
#SBATCH --account=owner-gpu-guest
#SBATCH --partition=notchpeak-gpu-guest
#SBATCH --qos=photoscan

#SBATCH --time=72:00:00                         # wall time
#SBATCH --nodes=1                               # number of cluster nodes                             # number of requested CPU cores
#SBATCH --mem=0
#SBATCH --gres=gpu:1080ti:4
#SBATCH --exclusive
#SBATCH --mail-type FAIL,END
#SBATCH --mail-user=dale.forrister@utah.edu          # Email address for events:

#SBATCH -o slurm-%j.out-%N                      # stdout, using job ID (%j) and the first node (%N)
#SBATCH -e slurm-%j.err-%N                      # stderr, using job and first node

# Enable CPU Hyper-threading
export OMP_NUM_THREADS=$SLURM_NTASKS

# Needed for PDF export in Agisoft using QT
export QT_QPA_FONTDIR=/usr/share/fonts/open-sans

PROJECT_NAME='7_CHPC_Blue_Waters_Comparison'

module load photoscan/1.7.2
module load python/3.5.2
#photoscan.sh -platform offscreen \
#             -r $HOME/DF_GITHUB_CODE/YFDP_Drone_Mapping/JM_Code/Agisoft_metashape_workflow.py \
#			 --image-type '.JPG'\
#			 --base-path /scratch/general/lustre/u6000251/2018_Yasuni_Drone__Mapping/October/2018_Oct_2/Phantom/Photos_within_plot/$PROJECT_NAME \
#             --project-name $PROJECT_NAME \
#> /scratch/general/lustre/u6000251/2018_Yasuni_Drone__Mapping/October/2018_Oct_2/Phantom/Photos_within_plot/$PROJECT_NAME/$PROJECT_NAME.log



# Needed for PDF export in Agisoft using QT
export BASEPATH=/scratch/general/lustre/u6000251/$PROJECT_NAME
export SCRIPT_PATH=/uufs/chpc.utah.edu/common/home/u6000251/DF_GITHUB_CODE/Metashape_Distributed_Proccesing/code/agisoft_workflow_V1_2021_5_05.py

metashape.sh -platform offscreen \
             -r $SCRIPT_PATH
             --step_one_align True\
             --step_two_dense_cloud False\
             --image-type '.JPG'\
             --base-path $BASEPATH \
             --with-export True \
             --image-folder "images" \
             --project-name $PROJECT_NAME >& $BASEPATH/$PROJECT_NAME.log

#--continue-proj "3_2021_May_17_Phantom_hist_match_2021_06_01" \
# --test-area True\

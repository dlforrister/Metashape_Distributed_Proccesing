#!/bin/bash

#SBATCH -J dforr_metashape           # Job name
#SBATCH -o dforr_metashape.o%j       # Name of stdout output file
#SBATCH -e dforr_metashape.e%j       # Name of stderr error file
#SBATCH -p rtx           # Queue (partition) name
#SBATCH -N 1               # Total # of nodes (must be 1 for serial)
#SBATCH -n 1               # Total # of mpi tasks (should be 1 for OpenMP)
#SBATCH -t 48:00:00        # Run time (hh:mm:ss)
#SBATCH --mail-type=FAIL,END    # Send email at begin and end of job
#SBATCH --mail-user=dlforrister@gmail.com


# Needed for PDF export in Agisoft using QT
export QT_QPA_FONTDIR=/usr/share/fonts/open-sans

export PROJECT_NAME='test_metashape'


module load python3/3.7.0
module load tacc-singularity



# Needed for PDF export in Agisoft using QT
export BASEPATH=/home1/08531/dlforr/$PROJECT_NAME
export SCRIPT_PATH=/work2/08531/dlforr/frontera/Metashape_Distributed_Proccesing/code/agisoft_workflow_V3_2022_3_16.py
export metashape_path=/usr/metashape-pro/metashape.sh
export singularity_path=/home1/08531/dlforr/metashape_ubuntu_1604_update_v2_latest.sif


singularity exec --nv $singularity_path  $metashape_path -platform offscreen -r $SCRIPT_PATH --step-one-align True --step-two-dense-cloud False --image-type '.JPG' --base-path $BASEPATH --with-export True --image-folder "images" --project-name $PROJECT_NAME >& $BASEPATH/$PROJECT_NAME.log

#--continue-proj "3_2021_May_17_Phantom_hist_match_2021_06_01" \






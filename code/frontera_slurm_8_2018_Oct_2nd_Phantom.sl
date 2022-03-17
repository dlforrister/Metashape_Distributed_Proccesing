#!/bin/bash

#SBATCH -J dforr_metashape           # Job name
#SBATCH -o dforr_metashape.o%j       # Name of stdout output file
#SBATCH -e dforr_metashape.e%j       # Name of stderr error file
#SBATCH -p rtx           # Queue (partition) name
#SBATCH -N 1               # Total # of nodes (must be 1 for serial)
#SBATCH -t 48:00:00        # Run time (hh:mm:ss)
#SBATCH --mail-type=FAIL,END    # Send email at begin and end of job
#SBATCH --mail-user=dlforrister@gmail.com


# Needed for PDF export in Agisoft using QT
export QT_QPA_FONTDIR=/usr/share/fonts/open-sans

PROJECT_NAME='8_2018_Oct_2nd_Phantom'


module load python3/3.7.0

# Needed for PDF export in Agisoft using QT
export BASEPATH=/work2/08531/dlforr/frontera/000_metashape_projects/$PROJECT_NAME
export SCRIPT_PATH=/work2/08531/dlforr/frontera/Metashape_Distributed_Proccesing/code/agisoft_workflow_V2_2021_11_11.py

metashape.sh -platform offscreen \
             -r $SCRIPT_PATH	\
             --step-one-align True\
             --step-two-dense-cloud False\
             --image-type '.JPG'\
             --base-path $BASEPATH \
             --with-export True \
             --image-folder "images" \
             --project-name $PROJECT_NAME >& $BASEPATH/$PROJECT_NAME.log

#--continue-proj "3_2021_May_17_Phantom_hist_match_2021_06_01" \

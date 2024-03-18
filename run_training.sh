#!/bin/bash
#SBATCH --mail-user=lcdemers16@gmail.com
#SBATCH --mail-type=END,FAIL
#SBATCH --gres=gpu:a100 # Request GPU "generic resources"
#SBATCH --cpus-per-task=12 # Cores proportional to GPUs: 6 on Cedar, 16 on Graham
#SBATCH --mem=500000M      # Memory proportional to GPUs: 32000 Cedar, 64000 Graham
#SBATCH --time=0-05:00:00
#SBATCH --verbose


python /home/lidem/projects/def-pesantg/lidem/CMT_CPBP/run.py --idx 1 --gpu_index 1 --ngpu 1 --optim_name adam --restore_epoch -1 --seed 42

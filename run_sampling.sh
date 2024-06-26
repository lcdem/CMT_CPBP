#!/bin/bash
cd minicpbp
mvn package
cd ..
for ((i = 0 ; i < 10 ; i++ ))
do
    s = 42+i
    python run.py --idx 3 --gpu_index 1 --ngpu 1 --optim_name adam --restore_epoch 100 --seed s --load_rhythm --sample
done
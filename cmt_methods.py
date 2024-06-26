import torch
import torch.nn as nn
import torch.nn.functional as F
import chords_operations
import preparing_constraints

import random
import dill
import numpy as np



def set_seed(seed):
    if seed > 0:
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        random.seed(seed)

def initialization(seed, batch_size = 1):
    set_seed(seed)
    dill.detect.trace(True)
    dill.dump_session()
    # Load model (CMT class deserialize)
    with open('model.pkl', 'rb') as f:
        model = dill.load(f)
    with open('chord.pkl', 'rb') as f:
        chord = dill.load(f)
    with open('prime_rhythm.pkl', 'rb') as f:
        prime_rhythm = dill.load(f)
    
    # initialize_constraints_info(chord, sample_key)


    return initialize_model(model, chord, prime_rhythm, batch_size)

def initialize_model(model, chord, prime_rhythm, batch_size):
    chord_hidden = model.chord_forward(chord)
    pad_length = model.max_len - prime_rhythm.size(1)
    rhythm_pad = torch.zeros([batch_size, pad_length], dtype=torch.long).to(prime_rhythm.device)
    rhythm_result = torch.cat([prime_rhythm, rhythm_pad], dim=1)
    fear = 0 
    with open('debug_idx.txt', 'a') as file:
        file.write("fear 1: ")
        file.write(str(fear)+"\n")
    fear = model.scare_lockwood()
    with open('debug_idx.txt', 'a') as file:
        file.write("fear 2: ")
        file.write(str(fear)+"\n")
    return (model, rhythm_result, chord_hidden)

def initialize_constraints_info(chord, sample_key):
    chords_operations.chords_conversion(chord, sample_key)
    preparing_constraints.get_constraints_info()

def get_nb_samples(rhythm_result):
    return int(rhythm_result.shape[0])

def decoding_rhythm(model, iteration, rhythm_result, chord_hidden, seed):
    rhythm_dec_result = model.rhythm_forward(rhythm_result, chord_hidden, attention_map=False, masking=True)
    with open('debug_idx.txt', 'a') as file:
        file.write("rhythm_dec_result: ")
        file.write(str(rhythm_dec_result)+"\n")
    rhythm_out = model.rhythm_outlayer(rhythm_dec_result['output'])
    with open('debug_idx.txt', 'a') as file:
        file.write("rhythm_out: ")
        file.write(str(rhythm_out)+"\n")
    rhythm_out = model.log_softmax(rhythm_out)
    with open('debug_idx.txt', 'a') as file:
        file.write("rhythm_out (après log softmax): ")
        file.write(str(rhythm_out)+"\n")
    probs = F.softmax(rhythm_out[:,iteration-1,:], dim=-1)
    with open('debug_idx.txt', 'a') as file:
        file.write("probs: ")
        file.write(str(probs)+"\n")
    return(probs)

def get_single_CMT_prob(rhythm_out, nbSample, i):
    p = rhythm_out[nbSample].tolist()
    return p[i]

# def get_single_fixed_token(rhythm_result, nbSample, i):
#     t = rhythm_result[nbSample].tolist()
#     return int(t[i])
    
def cmt_sample(rhythm_out):
    top3_probs, top3_idxs = torch.topk(rhythm_out[:, i - 1, :], 3, dim=-1)
    idx = torch.gather(top3_idxs, 1, torch.multinomial(F.softmax(top3_probs, dim=-1), 1)).squeeze()

def sample_token(iteration, marginals, rhythm_out, rhythm_result, seed):
    with open('debug_idx.txt', 'a') as file:
        file.write("sample RHYTHM token: ")
    probs_np = np.zeros(len(marginals))
    for i in range(len(marginals)):
        probs_np[i] = marginals[i]

    probs = torch.tensor(probs_np)

    if iteration == 0:
        # Clear the contents of the file
        with open('debug_idx.txt', 'a') as file:
            pass

    idx = torch.multinomial(probs, 1).squeeze()  # sampling from marginals of cp solver
    with open('debug_idx.txt', 'a') as file:
        file.write(f'Token {iteration} \nCPBP Marginals: ')
        file.write(str(probs)+"\n")
        file.write(f'CMT rhythm_out: ')
        file.write(str(rhythm_out)+"\n")

    rhythm_result[:,iteration] = idx

    with open('debug_idx.txt', 'a') as file:
        file.write(f"rhythm_result\n")
        file.write(str(rhythm_result)+"\n")
    return(rhythm_result)

def tensor_values_by_index(tensor, index):
    try:
        nptensor = tensor.numpy()
    except AttributeError:
        nptensor = tensor
    return(float(nptensor[:,index]))

def initialization_pitch(seed, batch_size = 1):
    set_seed(seed)

    with open('model.pkl', 'rb') as f:
        model = dill.load(f)
    with open('chord.pkl', 'rb') as f:
        chord = dill.load(f)
    with open('rhythm_result.pkl', 'rb') as f:
        rhythm_result = dill.load(f)
    with open('prime_pitch.pkl', 'rb') as f:
        prime_pitch = dill.load(f)

    rhythm_emb, chord_hidden = get_rhythm_encoding(model, chord, rhythm_result) # from encoder
    pitch_result = initialize_pitch_model(model, prime_pitch, batch_size)

    return (model, pitch_result, rhythm_result, rhythm_emb, chord_hidden)


def get_rhythm_encoding(model, chord, rhythm_result):
    chord_hidden = model.chord_forward(chord)
    rhythm_dict = model.rhythm_forward(rhythm_result, chord_hidden, attention_map=False, masking=True)
    rhythm_out = model.rhythm_outlayer(rhythm_dict['output'])
    rhythm_out = model.log_softmax(rhythm_out)
    idx = torch.argmax(rhythm_out[:, -1, :], dim=1)
    rhythm_temp = torch.cat([rhythm_result[:, 1:], idx.unsqueeze(-1)], dim=1)
    rhythm_enc_dict = model.rhythm_forward(rhythm_temp, chord_hidden, attention_map=False, masking=False)
    rhythm_emb = rhythm_enc_dict['output']
    
    return rhythm_emb, chord_hidden

def initialize_pitch_model(model, prime_pitch, batch_size):
    pad_length = model.max_len - prime_pitch.size(1)
    pitch_pad = torch.ones([batch_size, pad_length], dtype=torch.long).to(prime_pitch.device)
    pitch_pad *= (model.num_pitch - 1)
    pitch_result = torch.cat([prime_pitch, pitch_pad], dim=1)
    # pitch_result.tolist()
    return pitch_result

def get_pitch_result_list(pitch_result):
    return pitch_result.tolist()

def decoding_pitch(model, iteration, pitch_result, chord_hidden, rhythm_emb, seed):
    pitch_emb = model.pitch_emb(pitch_result)
    emb = torch.cat([pitch_emb, chord_hidden[0], chord_hidden[1], rhythm_emb], -1)
    emb *= torch.sqrt(torch.tensor(model.hidden_dim, dtype=torch.float))
    pitch_dict = model.pitch_forward(emb, attention_map=False)

    if iteration == 0:
        probs = F.softmax(pitch_dict['output'][:, iteration, :], dim=-1)
    else:
        probs = F.softmax(pitch_dict['output'][:, iteration - 1, :], dim=-1)
    
    return probs

def sample_pitch_token(iteration, probs_cp, pitch_result):
    with open('debug_idx.txt', 'a') as file:
        file.write(f"jep_test sample PITCH token\n")
    probs_np = np.zeros(len(probs_cp))
    for i in range(len(probs_cp)):
        probs_np[i] = probs_cp[i]


    with open('debug_idx.txt', 'a') as file:
        file.write(f'marginals miniCPBP : ')
        file.write(str(probs_np) + "\n")

    probs = torch.tensor(probs_np)

    topk_probs, topk_idxs = torch.topk(probs, 5, dim=-1)

    with open('debug_idx.txt', 'a') as file:
        file.write(f'\n sampling pitch token at iteration {iteration} \n')
        file.write(str(topk_probs) + " ")
        file.write(str(topk_idxs) + "\n")

    idx = torch.gather(topk_idxs, 0, torch.multinomial(topk_probs, 1)).squeeze()

    with open('debug_idx.txt', 'a') as file:
        file.write(f'idx : {idx} \n')
    pitch_result[:, iteration] = idx
    return(pitch_result)

def ghost(n):
    if n == 0:
        return torch.tensor([1, 2, 3])
    else:
        return torch.tensor([4, 5, 6])
    
def crumbles_of_ghost(tableau, i):
    return tableau.tolist()[i]
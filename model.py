import torch
import torch.nn as nn
import torch.nn.functional as F
import chords_operations
import preparing_constraints

from cp import ConstraintProgramming as CP
from layers import DynamicPositionEmbedding, SelfAttentionBlock
from torch.autograd import Variable
from utils import logger
import os
import dill
import subprocess

class ChordConditionedMelodyTransformer(nn.Module):
    def __init__(self, num_pitch=89, frame_per_bar=16, num_bars=8,
                 chord_emb_size=128, pitch_emb_size=128, hidden_dim=128,
                 key_dim=128, value_dim=128, num_layers=6, num_heads=4,
                 input_dropout=0.0, layer_dropout=0.0, attention_dropout=0.0, cp=None):
        super(ChordConditionedMelodyTransformer, self).__init__()

        self.max_len = frame_per_bar * num_bars
        self.frame_per_bar = frame_per_bar
        self.num_chords = 12
        self.num_pitch = num_pitch
        self.num_rhythm = 3

        # self.rhythm_emb_size = chord_emb
        self.chord_emb_size = chord_emb_size
        self.rhythm_emb_size = pitch_emb_size // 8
        self.pitch_emb_size = pitch_emb_size
        self.chord_hidden = 7 * (pitch_emb_size // 32)  # 2 * chord_hidden + rhythm_emb = rhythm_hidden
        self.rhythm_hidden = 9 * (pitch_emb_size // 16)   # 2 * chord_hidden + rhythm_hidden = pitch_emb
        self.hidden_dim = hidden_dim

        # embedding layer
        self.chord_emb = nn.Parameter(torch.randn(self.num_chords, self.chord_emb_size,
                                                  dtype=torch.float, requires_grad=True))
        self.rhythm_emb = nn.Embedding(self.num_rhythm, self.rhythm_emb_size)
        self.pitch_emb = nn.Embedding(self.num_pitch, self.pitch_emb_size)

        lstm_input = self.chord_emb_size
        self.chord_lstm = nn.LSTM(lstm_input, self.chord_hidden, num_layers=1,
                                  batch_first=True, bidirectional=True)
        self.rhythm_pos_enc = DynamicPositionEmbedding(self.rhythm_hidden, self.max_len)
        self.pos_encoding = DynamicPositionEmbedding(self.hidden_dim, self.max_len)

        # embedding dropout
        self.emb_dropout = nn.Dropout(input_dropout)

        # Decoding layers
        rhythm_params = (
            2 * self.chord_hidden + self.rhythm_emb_size,
            self.rhythm_hidden,
            key_dim // 4,
            value_dim // 4,
            num_heads,
            self.max_len,
            False,      # include succeeding elements' positional embedding also
            layer_dropout,
            attention_dropout
        )
        self.rhythm_decoder = nn.ModuleList([
            SelfAttentionBlock(*rhythm_params) for _ in range(num_layers)
        ])
        
        pitch_params = (
            2 * self.pitch_emb_size,
            self.hidden_dim,
            key_dim,
            value_dim,
            num_heads,
            self.max_len,
            True,       # preceding only
            layer_dropout,
            attention_dropout
        )
        self.pitch_decoder = nn.ModuleList([
            SelfAttentionBlock(*pitch_params) for _ in range(num_layers)
        ])

        # output layer
        self.rhythm_outlayer = nn.Linear(self.rhythm_hidden, self.num_rhythm)
        self.pitch_outlayer = nn.Linear(self.hidden_dim, self.num_pitch)
        self.log_softmax = nn.LogSoftmax(dim=-1)

        self.cp = CP(cp, frame_per_bar=self.frame_per_bar)

    def init_lstm_hidden(self, batch_size):
        h0 = Variable(torch.zeros(2, batch_size, self.chord_hidden))
        c0 = Variable(torch.zeros(2, batch_size, self.chord_hidden))
        return (h0, c0)

    # rhythm : time_len + 1   (input & target)
    # pitch : time_len      (input only)
    # chord : time_len + 1  (input & target)
    def forward(self, rhythm, pitch, chord, attention_map=False, rhythm_only=False):
        # chord_hidden : time_len   (target timestep)
        chord_hidden = self.chord_forward(chord)

        rhythm_dec_result = self.rhythm_forward(rhythm[:, :-1], chord_hidden, attention_map, masking=True)
        rhythm_out = self.rhythm_outlayer(rhythm_dec_result['output'])
        rhythm_out = self.log_softmax(rhythm_out)
        result = {'rhythm': rhythm_out}

        if not rhythm_only:
            rhythm_enc_result = self.rhythm_forward(rhythm[:, 1:], chord_hidden, attention_map, masking=False)
            rhythm_emb = rhythm_enc_result['output']
            pitch_emb = self.pitch_emb(pitch)
            emb = torch.cat([pitch_emb, chord_hidden[0], chord_hidden[1], rhythm_emb], -1)
            emb *= torch.sqrt(torch.tensor(self.hidden_dim, dtype=torch.float))
            pitch_output = self.pitch_forward(emb, attention_map)
            result['pitch'] = pitch_output['output']

            if attention_map:
                result['weights_rdec'] = rhythm_dec_result['weights']
                result['weights_renc'] = rhythm_enc_result['weights']
                result['weights_pitch'] = pitch_output['weights']
        return result

    def chord_forward(self, chord):
        torch.set_printoptions(threshold=10_000)
        with open('debug_idx.txt', 'a') as file:
            file.write("chord: ")
            file.write(str(chord)+"\n")
        size = chord.size()
        with open('debug_idx.txt', 'a') as file:
            file.write("size: ")
            file.write(str(size)+"\n")
        chord_emb = torch.matmul(chord.float(), self.chord_emb)
        with open('debug_idx.txt', 'a') as file:
            file.write("self.chord_emb: ")
            file.write(str(self.chord_emb)+"\n")
            file.write("chord.float(): ")
            file.write(str(chord.float())+"\n")
            file.write("chord_emb: ")
            file.write(str(chord_emb)+"\n")

        h0, c0 = self.init_lstm_hidden(size[0])
        with open('debug_idx.txt', 'a') as file:
            file.write("h0: ")
            file.write(str(h0)+"\n")
            file.write("c0: ")
            file.write(str(c0)+"\n")
        self.chord_lstm.flatten_parameters()
        chord_out, _ = self.chord_lstm(chord_emb, (h0.to(chord.device), c0.to(chord.device)))
        with open('debug_idx.txt', 'a') as file:
            file.write("chord.out: ")
            file.write(str(chord_out)+"\n")
            file.write("chord.device: ")
            file.write(str(chord.device)+"\n")
        chord_for = chord_out[:, 1:, :self.chord_hidden]
        chord_back = chord_out[:, 1:, self.chord_hidden:]
        with open('debug_idx.txt', 'a') as file:
            file.write("chord_for: ")
            file.write(str(chord_for)+"\n")
            file.write("chord_back: ")
            file.write(str(chord_back)+"\n")
        return chord_for, chord_back
    
    def rhythm_forward(self, rhythm, chord_hidden, attention_map=False, masking=True):
        rhythm_emb = self.rhythm_emb(rhythm)
        rhythm_emb = torch.cat([rhythm_emb, chord_hidden[0], chord_hidden[1]], -1)
        rhythm_emb *= torch.sqrt(torch.tensor(self.rhythm_hidden, dtype=torch.float))
        rhythm_emb = self.rhythm_pos_enc(rhythm_emb)
        rhythm_emb = self.emb_dropout(rhythm_emb)
        
        weights = []
        for _, layer in enumerate(self.rhythm_decoder):
            result = layer(rhythm_emb, attention_map, masking)
            rhythm_emb = result['output']
            if attention_map:
                weights.append(result['weight']) 
        
        result = {'output': rhythm_emb}
        if attention_map:
            result['weights'] = weights
        
        return result

    def pitch_forward(self, pitch_emb, attention_map=False, masking=True):
        emb = self.pos_encoding(pitch_emb)
        emb = self.emb_dropout(emb)

        # pitch model
        pitch_weights = []
        for _, layer in enumerate(self.pitch_decoder):
            pitch_result = layer(emb, attention_map, masking)
            emb = pitch_result['output']
            if attention_map:
                pitch_weights.append(pitch_result['weight'])

        # output layer
        output = self.pitch_outlayer(emb)
        output = self.log_softmax(output)
        
        result = {'output': output}
        if attention_map:
            result['weights'] = pitch_weights
        
        return result

    def sampling(self, prime_rhythm, prime_pitch, chord, epoch, sample_key, seed, song_name, topk=None, attention_map=False):
        chord_hidden = self.chord_forward(chord)
        self.cp.config['rhythm']['activate'] = False
        self.cp.config['pitch']['activate'] = False
        # batch_size * prime_len * num_outputs
        batch_size = prime_pitch.size(0)
        pad_length = self.max_len - prime_rhythm.size(1)
        rhythm_pad = torch.zeros([batch_size, pad_length], dtype=torch.long).to(prime_rhythm.device)
        rhythm_result = torch.cat([prime_rhythm, rhythm_pad], dim=1)

        # sampling phase
        # # calculer les accords ICI
        # chords_operations.chords_conversion(chord, sample_key)
        # preparing_constraints.get_constraints_info(song_name)

        for i in range(prime_rhythm.size(1), self.max_len):
            rhythm_dec_result = self.rhythm_forward(rhythm_result, chord_hidden, attention_map, masking=True)
            rhythm_out = self.rhythm_outlayer(rhythm_dec_result['output'])
            rhythm_out = self.log_softmax(rhythm_out)
            if topk is None:
                idx = torch.argmax(rhythm_out[:, i - 1, :], dim=1)
            else:
                
                # if self.cp.config['rhythm']['activate']:
                #     # print(rhythm_out[:, i - 1, :])
                #     idx = self.cp.get_cp_rhythm_idx(rhythm_result, rhythm_out[:, i - 1, :], epoch, i, prime_pitch.device, sample_key)
                # else:
                top3_probs, top3_idxs = torch.topk(rhythm_out[:, i - 1, :], 3, dim=-1)
                idx = torch.gather(top3_idxs, 1, torch.multinomial(F.softmax(top3_probs, dim=-1), 1)).squeeze()
            rhythm_result[:, i] = idx

        #### Rhythm encoding
        rhythm_dict = self.rhythm_forward(rhythm_result, chord_hidden, attention_map, masking=True)
        rhythm_out = self.rhythm_outlayer(rhythm_dict['output'])
        rhythm_out = self.log_softmax(rhythm_out)
        idx = torch.argmax(rhythm_out[:, -1, :], dim=1)
        rhythm_temp = torch.cat([rhythm_result[:, 1:], idx.unsqueeze(-1)], dim=1)
        rhythm_enc_dict = self.rhythm_forward(rhythm_temp, chord_hidden, attention_map, masking=False)
        rhythm_emb = rhythm_enc_dict['output']
        
        ### Pitch
        if self.cp.config['pitch']['activate']:
            self.cp.save_rhythm_token(rhythm_result)

        pad_length = self.max_len - prime_pitch.size(1)
        pitch_pad = torch.ones([batch_size, pad_length], dtype=torch.long).to(prime_pitch.device)
        pitch_pad *= (self.num_pitch - 1)
        pitch_result = torch.cat([prime_pitch, pitch_pad], dim=1)
        for i in range(prime_pitch.size(1), self.max_len):
            pitch_emb = self.pitch_emb(pitch_result)
            emb = torch.cat([pitch_emb, chord_hidden[0], chord_hidden[1], rhythm_emb], -1)
            emb *= torch.sqrt(torch.tensor(self.hidden_dim, dtype=torch.float))
            pitch_dict = self.pitch_forward(emb, attention_map)
            if topk is None:
                idx = torch.argmax(pitch_dict['output'][:, i - 1, :], dim=1)
            else:
                # if self.cp.config['pitch']['activate']:
                #     probs_cp = self.cp.get_cp_pitch_probs(pitch_result, pitch_dict['output'][:, i - 1, :], epoch, i, prime_pitch.device, sample_key)
                #     topk_probs, topk_idxs = torch.topk(probs_cp, topk, dim=-1)
                #     idx = torch.gather(topk_idxs, 1, torch.multinomial(topk_probs, 1)).squeeze()
                # else:
                topk_probs, topk_idxs = torch.topk(pitch_dict['output'][:, i - 1, :], topk, dim=-1)
                idx = torch.gather(topk_idxs, 1, torch.multinomial(F.softmax(topk_probs, dim=-1), 1)).squeeze()
            pitch_result[:, i] = idx

        result = {'rhythm': rhythm_result,
                  'pitch': pitch_result}
        if attention_map:
            result['weights_rdec'] = rhythm_dict['weights']
            result['weights_renc'] = rhythm_enc_dict['weights']
            result['weights_pitch'] = pitch_dict['weights']
        return result


    def sampling_with_cp(self, prime_rhythm, prime_pitch, chord, epoch, sample_key, seed, song_name, topk=None, attention_map=False):
        if os.path.exists("debug_idx.txt"):
            os.remove("debug_idx.txt")
        
        # Rhythm
        # Save info for jep to access
        with open('model.pkl', 'w+b') as f:
            dill.dump(self, f)
        with open('chord.pkl', 'w+b') as f:
            dill.dump(chord, f)
        with open('prime_rhythm.pkl', 'w+b') as f:
            dill.dump(prime_rhythm, f)
        
        chords_operations.chords_conversion(chord, sample_key)
        preparing_constraints.get_constraints_info(song_name)

        # Execute java code
        current_dir_backup = os.getcwd()
        os.chdir(self.cp.minicpbp_working_dir)
        cp_model_name = 'rhythmPatternCorrelation'

        cmd = f'{self.cp.BASIC_JAVA_CMD}{cp_model_name} {seed}'.split()
        print(cmd)
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        batch_size = prime_pitch.size(0)
        pad_length = self.max_len - prime_rhythm.size(1)

        os.chdir(current_dir_backup)

        rhythm_pad = torch.zeros([batch_size, pad_length], dtype=torch.long).to(prime_rhythm.device)
        rhythm_result = torch.cat([prime_rhythm, rhythm_pad], dim=1)

        if process.returncode != 0:
            print(f'Java MiniCPBP rhythm failed: {process.stderr}')
        else :
            print(f'java miniCPBP rhythm succeed, process returncode :{process.returncode} - {process.stdout} - {process.stderr}')
            with open(os.path.join(self.cp.minicpbp_music_path, 'results_rhythm.txt'), 'r') as f:
                line = f.readline()
                tokens = line.split()
                print('\n Read file : ')
                print(tokens)
                for j in range(128):
                    rhythm_result[:,j] = float(tokens[j])

        ####### Pitch generration
        # Save info for jep to access
        with open('prime_pitch.pkl', 'w+b') as f:
            dill.dump(prime_pitch, f)
        with open('rhythm_result.pkl', 'w+b') as f:
            dill.dump(rhythm_result, f)
        #### Rhythm encoding
        os.chdir(self.cp.minicpbp_working_dir)
        cp_model_name = 'pitchPatternCorrelation'
        k = self.cp.config[self.cp.PITCH]['model']['k']
        
        cmd = f'{self.cp.BASIC_JAVA_CMD}{cp_model_name} {seed} {sample_key}'.split()
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        batch_size = prime_pitch.size(0)
        pad_length = self.max_len - prime_pitch.size(1)

        os.chdir(current_dir_backup)

        pitch_pad = torch.zeros([batch_size, pad_length], dtype=torch.long).to(prime_pitch.device)
        pitch_result = torch.cat([prime_pitch, pitch_pad], dim=1)

        if process.returncode != 0:
            print(f'\nJava MiniCPBP pitch failed: {process.stderr}')
        else:
            print(
                f'\njava miniCPBP pitch succeed, process returncode :{process.returncode} - {process.stdout} - {process.stderr}')
            with open(os.path.join(self.cp.minicpbp_music_path, 'results_pitch.txt'), 'r') as f:
                line = f.readline()
                tokens = line.split()
                print('\n Read file : ')
                print(tokens)
                for j in range(128):
                    pitch_result[:, j] = float(tokens[j])

        result = {'rhythm': rhythm_result,
                  'pitch': pitch_result}
        if attention_map:
            result['weights_rdec'] = rhythm_dict['weights']
            result['weights_renc'] = rhythm_enc_dict['weights']
            result['weights_pitch'] = pitch_dict['weights']
        return result



    def sampling_with_java(self, prime_rhythm, prime_pitch, chord, epoch, seed, topk=None, attention_map=False):
        if os.path.exists("debug_idx.txt"):
            os.remove("debug_idx.txt")
        
        #============================================== RHYTHM ==============================================
        # Save python variables into pkl files to access them inside JEP
        with open('model.pkl', 'w+b') as f:
            dill.dump(self, f)
        with open('chord.pkl', 'w+b') as f:
            dill.dump(chord, f)
        with open('prime_rhythm.pkl', 'w+b') as f:
            dill.dump(prime_rhythm, f)

        # Execute java code
        current_dir_backup = os.getcwd()
        os.chdir(self.cp.minicpbp_working_dir)
        cp_model_name = 'samplingRhythm'
        userConstraints = self.cp.config[self.cp.RHYTHM]['model']['userconstraints']
        print("")
        print(userConstraints)
        print("")
        cmd = f'{self.cp.BASIC_JAVA_CMD}{cp_model_name} {userConstraints} {seed}'.split()
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        batch_size = prime_pitch.size(0)
        pad_length = self.max_len - prime_rhythm.size(1)

        os.chdir(current_dir_backup)

        rhythm_pad = torch.zeros([batch_size, pad_length], dtype=torch.long).to(prime_rhythm.device)
        rhythm_result = torch.cat([prime_rhythm, rhythm_pad], dim=1)

        if process.returncode != 0:
            print(f'Java MiniCPBP rhythm failed: {process.stderr}')
        else :
            print(f'java miniCPBP rhythm succeed, process returncode :{process.returncode} - {process.stdout} - {process.stderr}')
            with open(os.path.join(self.cp.minicpbp_music_path, 'results_rhythm.txt'), 'r') as f:
                line = f.readline()
                tokens = line.split()
                print('\n Read file : ')
                print(tokens)
                for j in range(128):
                    rhythm_result[:,j] = float(tokens[j])

        #============================================== PITCH ==============================================
        # Save python variables into pkl files to access them inside JEP
        with open('prime_pitch.pkl', 'w+b') as f:
            dill.dump(prime_pitch, f)
        with open('rhythm_result.pkl', 'w+b') as f:
            dill.dump(rhythm_result, f)

        # Execute java code
        os.chdir(self.cp.minicpbp_working_dir)
        cp_model_name = 'samplingPitch'
        userConstraints = self.cp.config[self.cp.PITCH]['model']['userconstraints']
        k = self.cp.config[self.cp.PITCH]['model']['k']
        java_debug = "jdb"
        JAVA_CMD = f'jdb -cp ../../../target/minicpbp-1.0.jar minicpbp.examples.'
        cmd = f'{self.cp.BASIC_JAVA_CMD}{cp_model_name} {userConstraints} {seed} {k}'.split()
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        batch_size = prime_pitch.size(0)
        pad_length = self.max_len - prime_pitch.size(1)

        os.chdir(current_dir_backup)

        pitch_pad = torch.zeros([batch_size, pad_length], dtype=torch.long).to(prime_pitch.device)
        pitch_result = torch.cat([prime_pitch, pitch_pad], dim=1)

        if process.returncode != 0:
            print(f'\nJava MiniCPBP pitch failed: {process.stderr}')
        else:
            print(
                f'\njava miniCPBP pitch succeed, process returncode :{process.returncode} - {process.stdout} - {process.stderr}')
            with open(os.path.join(self.cp.minicpbp_music_path, 'results_pitch.txt'), 'r') as f:
                line = f.readline()
                tokens = line.split()
                print('\n Read file : ')
                print(tokens)
                for j in range(128):
                    pitch_result[:, j] = float(tokens[j])

        result = {'rhythm': rhythm_result,
                  'pitch': pitch_result}
        if attention_map:
            result['weights_rdec'] = rhythm_dict['weights']
            result['weights_renc'] = rhythm_enc_dict['weights']
            result['weights_pitch'] = pitch_dict['weights']
        return result
    
    def scare_lockwood(self):
        return "Where is Lucy? Where did she go?"

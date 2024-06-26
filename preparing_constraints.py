import json
import random
import os
import numpy as np
import time

N_SECTIONS = 16

def get_constraints_info(song_name):

    seed = int(np.random.rand() * (2**32 - 1))
    np.random.seed(1887642256)

    corr_notes, corr_rhythms, corr_intervals, trends_notes, trends_rhythms, trends_intervals = readJsonFile()

    trends_notes = np.transpose(trends_notes).tolist()
    trends_rhythms = np.transpose(trends_rhythms).tolist()
    trends_intervals = np.transpose(trends_intervals).tolist()

    note_sections = choose_sections(corr_notes, trends_notes)
    rhythms_sections = choose_sections(corr_rhythms, trends_rhythms)
    intervals_sections = choose_sections(corr_intervals, trends_intervals)

    # note_sections = [[0.625, 0.75, 0.875, 1.0], [0.5, 0.5625, 0.75, 0.8125]]
    # intervals_sections = [[0.5, 0.625, 0.875, 1.0], [0.5, 0.5625, 0.9375, 1.0]]
    # rhythms_sections = [[0.0, 0.1875, 0.25, 0.4375]]
    # note_sections = [[0.0625, 0.125, 0.25, 0.3125], [0.5, 0.625, 0.75, 0.875]]
    # rhythms_sections = [[0.5, 0.5625, 0.5625, 0.625], [0.5, 0.625, 0.75, 0.875], [0.625, 0.6875, 0.875, 0.9375]]
    # intervals_sections = [[0.0625, 0.125, 0.25, 0.3125], [0.0625, 0.125, 0.3125, 0.375], [0.5, 0.5625, 0.5625, 0.625], [0.5625, 0.625, 0.75, 0.8125]]
    # note_sections = [[0.125, 0.1875, 0.25, 0.3125], [0.1875, 0.25, 0.4375, 0.5], [0.625, 0.6875, 0.875, 0.9375]]
    # rhythms_sections = [[0.125, 0.1875, 0.375, 0.4375], [0.5625, 0.625, 0.625, 0.6875], [0.625, 0.6875, 0.8125, 0.875], [0.625, 0.6875, 0.875, 0.9375]]
    # intervals_sections = [[0.0, 0.0625, 0.3125, 0.375], [0.5625, 0.6875, 0.8125, 0.9375]]


    # note_sections, rhythms_sections, intervals_sections = all_overlaps(note_sections, rhythms_sections, intervals_sections)
    print("note_sections, rhythms_sections, intervals_sections")
    print(get_bar_nb(note_sections))
    print(get_bar_nb(rhythms_sections))
    print(get_bar_nb(intervals_sections))

    log_results(note_sections, rhythms_sections, intervals_sections, song_name, seed)

    notes_result = {'sections': note_sections}
    rhythms_results = {'sections': rhythms_sections}
    intervals_results = {'sections': intervals_sections}

    writeJsonFile(notes_result, "notes")
    writeJsonFile(rhythms_results, "rhythms")
    writeJsonFile(intervals_results, "intervals") 

def get_bar_nb(sections):
    bou = []
    for sec in sections:
        coucou = [(((e/0.0625)/2)+1) for e in sec]
        bou.append(coucou)
    return bou

def all_overlaps(notes, rhythms, intervals):
    # notes avec lui-même
    # intervalles avec lui-même
    # rythmes avec lui-même
    # notes et intervalles
    
    # notes avec notes
    previous_length_notes = 0
    previous_length_intervals = 0
    previous_length_ryhthms = 0

    while previous_length_notes < len(notes) or previous_length_intervals < len(intervals) or previous_length_ryhthms < len(rhythms):
        previous_length_notes = len(notes)
        previous_length_intervals = len(intervals)
        previous_length_ryhthms = len(rhythms)
        
        overlapping_notes = overlaps_whithin_same(notes)
        notes = add_to_existing(notes, overlapping_notes)

        overlapping_rhythms = overlaps_whithin_same(rhythms)
        rhythms = add_to_existing(rhythms, overlapping_rhythms)

        overlapping_intervals = overlaps_whithin_same(intervals)
        intervals = add_to_existing(intervals, overlapping_intervals)
        # print("Notes-intervalles")
        overlapping_intervals = overlaps_between_types(notes, intervals)
        intervals = add_to_existing(intervals, overlapping_intervals)        

        # overlapping_rhythms = overlaps_between_types(notes, rhythms)
        # rhythms = add_to_existing(rhythms, overlapping_rhythms)

        # overlapping_rhythms = overlaps_between_types(intervals, rhythms)
        # rhythms = add_to_existing(rhythms, overlapping_rhythms)

    return notes, rhythms, intervals

def add_to_existing(sections, overlapping_sections):
    sections.extend(overlapping_sections)
    sections = np.unique(np.array([np.sort(sub) for sub in sections]), axis=0).tolist()
    return sections


def overlaps_whithin_same(sections): 
    overlapping_sections =[]
    # print("whithin same")
    # print(sections)
    for i in range(len(sections)):
        for j in range(len(sections)):
            if i!=j:
                # if (notes[i][2] <= notes[j][2] and notes[j][2] <= notes[i][3]) or (notes[i][2] <= notes[j][3] and notes[j][3] <= notes[i][3]) or (notes[j][2] <= notes[i][2] and notes[j][3] >= notes[i][3]):
                # print(sections[j][2],sections[i][3],sections[j][3],sections[i][2])
                # print(sections[j][2] < sections[i][3] and sections[j][3] > sections[i][2])

                if sections[j][2] < sections[i][3] and sections[j][3] > sections[i][2]:
                    overlap_section = compute_overlap_index(sections[i], sections[j])
                    # print("overlap_section")
                    # print(sections[i], sections[j])
                    # print(overlap_section)
                    #     if notes[j][2] <= notes[i][3] and notes[j][3] >= notes[i][2];
                    if overlap_section[0] != overlap_section[2] and overlap_section[1] != overlap_section[3]:
                        overlapping_sections.append(overlap_section)
    # sections.extend(overlapping_sections)
    # sections = np.unique(np.array([np.sort(sub) for sub in sections]), axis=0).tolist()

    return overlapping_sections

def compute_overlap_index(section_i, section_j):
    start_overlap = max(section_i[2], section_j[2]) 
    end_overlap = min(section_i[3], section_j[3])
    
    proportion_start_overlap_i = (start_overlap - section_i[2]) / (section_i[3] - section_i[2])
    section_start_i = proportion_start_overlap_i * (section_i[1]- section_i[0]) + section_i[0]
    
    proportion_start_overlap_j = (start_overlap - section_j[2]) / (section_j[3] - section_j[2])
    section_start_j = proportion_start_overlap_j * (section_j[1]- section_j[0]) + section_j[0]
    
    proportion_end_overlap_i = (end_overlap - section_i[2]) / (section_i[3] - section_i[2])
    section_end_i = proportion_end_overlap_i * (section_i[1]- section_i[0]) + section_i[0]
    
    proportion_end_overlap_j = (end_overlap - section_j[2]) / (section_j[3] - section_j[2])
    section_end_j = proportion_end_overlap_j * (section_j[1]- section_j[0]) + section_j[0]

    return [min(section_start_i, section_start_j), min(section_end_i, section_end_j), max(section_start_i, section_start_j), max(section_end_i, section_end_j)]

def overlaps_between_types(type1, type2):
    # print("between types")
    overlapping_sections =[]
    for i in range(len(type1)):
        for j in range(len(type2)):
            # print(type2[j][2],type1[i][3],type2[j][3],type1[i][2])
            # print(type2[j][2] < type1[i][3] and type2[j][3] > type1[i][2])

            # if (notes[i][2] <= notes[j][2] and notes[j][2] <= notes[i][3]) or (notes[i][2] <= notes[j][3] and notes[j][3] <= notes[i][3]) or (notes[j][2] <= notes[i][2] and notes[j][3] >= notes[i][3]):
            if type2[j][2] < type1[i][3] and type2[j][3] > type1[i][2] and (type1[i] != type2[j]):
                overlap_section = compute_overlap_index(type1[i], type2[j])
                #     if notes[j][2] <= notes[i][3] and notes[j][3] >= notes[i][2];
                # print("overlap_section")
                # print(type1[i], type2[j])
                # print(overlap_section)
                # print(overlap_section[0] != overlap_section[2] and overlap_section[1] != overlap_section[3])
                # print(overlap_section[0] != overlap_section[2] and overlap_section[1] != overlap_section[3])
                if overlap_section[0] != overlap_section[2] and overlap_section[1] != overlap_section[3]:
                    overlapping_sections.append(overlap_section)
    # type2.extend(overlapping_sections)
    # type2 = np.unique(np.array([np.sort(sub) for sub in type2]), axis=0).tolist()

    return overlapping_sections

def log_results(note_sections, rhythms_sections, intervals_sections, song_name, seed):
    now = time.time()
    now_tuple = time.localtime(now)
    now_millisecond = int(1e3 * (now % 1.0))

    s = '[%02d-%02d %02d:%02d:%02d.%03d] ' % (
        now_tuple[2],  # day
        now_tuple[1],  # month
        now_tuple[3],  # hour
        now_tuple[4],  # min
        now_tuple[5],  # sec
        now_millisecond)
    
    with open("debug_section_selection.txt", "a") as f:
        f.write("START : "+s+ "   Song name : " + song_name +"\n")
        f.write("Numpy seed : " + str(seed)+ "\n")
        f.write("NOTES: "+ str(len(note_sections)) + "\n")
        write_sections_and_bars(f, note_sections)
        f.write("RYTHMES: "+ str(len(rhythms_sections)) + "\n")
        write_sections_and_bars(f, rhythms_sections)
        f.write("INTERVALLES: "+ str(len(intervals_sections)) + "\n")
        write_sections_and_bars(f, intervals_sections)
        f.write("\n")

def write_sections_and_bars(f, sections):
    f.write("Sections: [")
    for s in range(len(sections)):
        f.write("[")
        for i in range(len(sections[s])):
            f.write(str(sections[s][i])) 
            if i < len(sections[s])-1:
                f.write(", ")
            else:
                f.write("]")
        if s < len(sections)-1:
            f.write(", ")
    f.write("]\n")

    f.write("Mesures: [")
    for s in range(len(sections)):
        f.write("[")
        for i in range(len(sections[s])):
            f.write(str(((sections[s][i]/0.0625)/2)+1)) 
            if i < len(sections[s])-1:
                f.write(", ")
            else:
                f.write("]")
        if s < len(sections)-1:
            f.write(", ")
    f.write("]\n")

def readJsonFile():

    with open('matrices_info.json', 'r') as file:
        data = json.load(file)
    
    return data['dep_notes'], data['dep_rhythms'], data['dep_intervals'], data['trends_notes'], data['trends_rhythms'], data['trends_intervals']

def writeJsonFile(content, type):
    filepath = os.path.join(os.path.dirname(__file__)+"/minicpbp/src/main/java/minicpbp/examples/data/MusicCP", type+"_sections.json")
    # filepath = os.path.join(type+"_sections.json")
    with open(filepath, "w") as json_file:
        json.dump(content, json_file)

def choose_sections(correlations, trends):
    sections = sections_selection(correlations, trends)
    np.random.shuffle(sections)
    kept_sections = []
    # if (sections[0][1] - sections[0][0]) < 0.25 or (sections[1][1] - sections[1][0]) < 0.25:
    #     for i in range(2,len(sections)):
    #         if (sections[0][1] - sections[0][0]) < 0.25:
    #             kept_sections.append(sections[i])
    #             break
    #         break
    # kept_sections.append(sections[0])
    # kept_sections.append(sections[1])

    # print(sections, len(sections))
    counter = 0
    max_counter = N_SECTIONS
    for section in sections:
        if max_counter > (counter + (section[1] - section[0])*N_SECTIONS*2) :
            print(counter)
            counter += (section[1] - section[0])*N_SECTIONS*2
            kept_sections.append(section)


    print("BOUCLE FINIE,  ", counter)
    # compter le nombre de paires par longueur et supprimer??????????

    return kept_sections

def sections_selection(correlation_matrix, trends):
    # print(len(trends))
    threshold = np.percentile(correlation_matrix, 95)

    selected_sections = []
    max_selected = 0

    for i in range(len(correlation_matrix)):
        for j in range(len(correlation_matrix[i])):
            if correlation_matrix[i][j] > threshold:
                if i != j:
                    if (len(correlation_matrix) == len(correlation_matrix[0])):
                        max_length = 0
                        while i+max_length < len(correlation_matrix) and j+max_length < len(correlation_matrix[i]) and correlation_matrix[i+max_length][j+max_length] > threshold:
                            max_length += 1
                        length = get_length(trends, i, j, max_length)

                        #il faut que la longueur ne dépasse pas 1
                        selected_sections.append([i*(1/N_SECTIONS),i*(1/N_SECTIONS)+length*(1/N_SECTIONS), j*(1/N_SECTIONS), j*(1/N_SECTIONS)+length*(1/N_SECTIONS)])            
                        for k in range(length):
                            if i+k < len(correlation_matrix) and j+k < len(correlation_matrix[i]):
                                correlation_matrix[i+k][j+k] = 0

    # print("DECILE : ", len(selected_sections))
    # print(selected_sections)
    selected_sections =  np.unique(np.array([np.sort(sub) for sub in selected_sections]), axis=0).tolist()
    # print("FIN", len(selected_sections))
    # print(selected_sections)
    return selected_sections

def get_length(trends, section_i, section_j, max_length):
    end_1 = 100
    end_2 = 100
    # print("max_length", max_length)
    # value = np.random.rand()*100
    # for i in range(len(trends[section_i])):
    #     if value < sum(trends[section_i][0:i+1]/sum(trends[section_i][0:max_length+1])):
    #         return i+1
    
    isNotCorrectLength = True
    while True:
        value = np.random.rand()*100
        # print(value)
        for i in range(len(trends[section_i])):
            if value < sum(trends[section_i][0:i+1]):

                length = i+1
                
                # end_1 = section_i*(1/N_SECTIONS)+length*(1/N_SECTIONS)
                # end_2 = section_j*(1/N_SECTIONS)+length*(1/N_SECTIONS)
                if length <= max_length:
                    return length
                else:
                    break # from the for loop


get_constraints_info("bou")
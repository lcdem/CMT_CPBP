import json
import random
import os
import numpy as np


N_SECTIONS = 16

def get_constraints_info():

    corr_notes, corr_rhythms, corr_intervals, trends_notes, trends_rhythms, trends_intervals = readJsonFile()

    trends_notes = np.transpose(trends_notes).tolist()
    trends_rhythms = np.transpose(trends_rhythms).tolist()
    trends_intervals = np.transpose(trends_intervals).tolist()

    note_sections = choose_sections(corr_notes, trends_notes)
    rhythms_sections = choose_sections(corr_rhythms, trends_rhythms)
    intervals_sections = choose_sections(corr_intervals, trends_intervals)

    notes_result = {'sections': note_sections}
    rhythms_results = {'sections': rhythms_sections}
    intervals_results = {'sections': intervals_sections}
    print("CHOISIS", len(note_sections))
    print(note_sections)
    print("CHOISIS", len(rhythms_sections))
    print(rhythms_sections)
    print("CHOISIS", len(intervals_sections))
    print(intervals_sections)
    # print(rhythms_sections)
    # print(intervals_sections)

    writeJsonFile(notes_result, "notes")
    writeJsonFile(rhythms_results, "rhythms")
    writeJsonFile(intervals_results, "intervals")


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
    max_counter = 8
    for section in sections:
        if max_counter > (counter + (section[1] - section[0])*N_SECTIONS*2) :
            counter += (section[1] - section[0])*N_SECTIONS*2
            kept_sections.append(section)

    # compter le nombre de paires par longueur et supprimer??????????

    return kept_sections

def sections_selection(correlation_matrix, trends):
    print(len(trends))
    threshold = np.percentile(correlation_matrix, 90)

    selected_sections = []

    for i in range(len(correlation_matrix)):
        for j in range(len(correlation_matrix[i])):
            if correlation_matrix[i][j] > threshold:
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
                        
                    
    print("DECILE : ", len(selected_sections))
    # print(selected_sections)
    selected_sections =  np.unique(np.array([np.sort(sub) for sub in selected_sections]), axis=0).tolist()
    print("FIN", len(selected_sections))
    print(selected_sections)
    return selected_sections

def get_length(trends, section_i, section_j, max_length):
    end_1 = 100
    end_2 = 100
    # value = np.random.rand()*100
    # for i in range(len(trends[section_i])):
    #     if value < sum(trends[section_i][0:i+1]/sum(trends[section_i][0:max_length+1])):
    #         return i+1
    
    isNotCorrectLength = True
    while isNotCorrectLength:
        value = np.random.rand()*100
        # print(value)
        for i in range(len(trends[section_i])):
            if value < sum(trends[section_i][0:i+1]):

                length = i+1
                start_1 = section_i*(1/N_SECTIONS)
                start_2 = section_j*(1/N_SECTIONS)
                end_1 = section_i*(1/N_SECTIONS)+length*(1/N_SECTIONS)
                end_2 = section_j*(1/N_SECTIONS)+length*(1/N_SECTIONS)
                if end_1 <= max_length and end_2 <= max_length:
                    isNotCorrectLength = False
                    return length
                else:
                    break # from the for loop


# get_constraints_info()
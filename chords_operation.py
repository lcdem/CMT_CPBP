import numpy as np 
from utils import logger


def chords_management(chords):
    chords = replace_with_first_non_zero_subarray(chords)

    return convert_chords(chords)



def replace_with_first_non_zero_subarray(arr):
    # Find the first subarray containing a non-zero value
    first_non_zero_subarray = None
    for subarray in arr:
        if 1 in subarray:  # Assuming "non-zero" means containing a '1'
            first_non_zero_subarray = subarray
            break
    
    # If no such subarray is found, return the array as is
    if first_non_zero_subarray is None:
        return arr
    
    # Replace preceding subarrays that do not contain a '1' with the first non-zero subarray
    for i in range(len(arr)):
        if 1 not in arr[i]: 
            arr[i] = first_non_zero_subarray.copy()  
    
    return arr

def chord_qualification_converter(chords):
    maj_third = 4
    min_third = 3
    if len(chords_intervals) == 2:
        if chords_intervals[0] == maj_third and chords_intervals[1] == min_third: # accord Maj
            return ""
        if chords_intervals[0] == min_third and chords_intervals[1] == maj_third: # accord min
            return "m"
    if len(chords_intervals) == 3: # accord 7e
        if chords_intervals[0] == maj_third and chords_intervals[1] == min_third and chords_intervals[2] == min_third:
            return "7"
        if chords_intervals[0] == min_third and chords_intervals[1] == min_third and chords_intervals[2] == min_third:
            return "m7"
    return "Aucun type d'accord détécté, pas normal!"



def convert_chords(chords, key=1, key_mode='major'):
    key = (int(key) * 7) % 12
    converted_chords = []
    maj_third = 4
    min_third = 3
    aug_fifth = 8
    dim_fifth = 6

    major_degrees = [1, 3, 5, 6, 8, 10, 12]
    minor_degrees = [1, 3, 4, 6, 8, 9, 12] # min harmonique
    # print(key)
    # print(chord)
    for notes in chords:
        chord = []
        for i in range(len(notes)):
            if notes[i] == 1 :
                # print(i)
                note_in_mode = (i - (key)) % 12 + 1 # donne l'index dans la gamme
                # print(note_in_mode)
                chord.append(note_in_mode)

        chord.sort()
        print(chord)
        count = 0
        while ((chord[1]-chord[0]) % 12 != 5 and (chord[1]-chord[0]) % 12 != 2) :
            if chord[1]-chord[0] != min_third or chord[1]-chord[0] != maj_third:
                logger.info("Erreur dans les accords")
            if count == 5: # 7e diminuée ou 5e augmentée
                break
            count += 1
            
            chord.append(chord.pop(0))
        chord.append(chord.pop(0))
        
            
        
        print(chord)
        root_note = chord[0]
        # if key_mode == "major" and len(chord) >= 3 and (chord[2] - chord[0]) == aug_fifth:
        #     print("Erreur: Accord de quinte augmentée détecté dans une partition de tonalité Majeure")
        #     return "Error"
        
        note_scale_degree = ""
        # try:
        if key_mode == "major":
            if root_note == 11 and (chord[1] - chord[0]) % 12 == maj_third: # c'est un 5 mixte ex: si bémol en Do Maj 4/4
                note_scale_degree = "4/4"
                converted_chords.append(str(note_scale_degree))
                continue
            if root_note == 9 and (chord[1] - chord[0]) % 12 == maj_third: # c'est un 6 mixte ex: la bémol en Do Maj (6e degré de do mineur, tonalité directe)
                note_scale_degree = "4/3mixte"
                converted_chords.append(str(note_scale_degree))
                continue
            if root_note == 7:
                if (chord[1] - chord[0]) == min_third: # ex: do# en Sol Maj
                    note_scale_degree = "3/2"
                    converted_chords.append(str(note_scale_degree))
                    continue
                if (chord[1] - chord[0]) == maj_third and (chord[2] - chord[1]) == min_third: # ex: sol# - do béc - ré# - fa# en Ré Maj, ça donne V7/VII
                    note_scale_degree = "5/7"
                    converted_chords.append(str(note_scale_degree))
                    continue
            if root_note == 4:
                note_scale_degree = "3mixte"
                converted_chords.append(str(note_scale_degree))
                continue
            if root_note == 2 and (chord[2] - chord[0]) == dim_fifth: # ex: ré#-fa#-la en ré Majeur
                note_scale_degree = "7/2"
                converted_chords.append(str(note_scale_degree))
                continue
            if root_note == 1 and (len(chord) == 4) and (chord[3] - chord[2]) == min_third: # ex: reela-c11 accord de ré Maj 7 de dom alors que la tonalité est ré Majeur (V7/IV)
                note_scale_degree = "5/4"
                converted_chords.append(str(note_scale_degree))
                continue
            else:
                if root_note in major_degrees:
                    note_scale_degree += str(major_degrees.index(root_note) + 1) # le +1 est pour convertir dans les degrés connus ex: 1, 2, 3, 4, 5, 6 ,7
                else:
                    note_scale_degree += str(major_degrees.index(root_note-1) + 1)

        else:
            note_scale_degree += str(minor_degrees.index(root_note) + 1)

        note_scale_degree += "/1"
        if note_scale_degree == "2/1":
            if (chord[1] - chord[0]) == maj_third:
                note_scale_degree = "5/5"
        if note_scale_degree == "6/1":
            if (chord[1] - chord[0]) == maj_third:
                note_scale_degree = "5/2"
        if note_scale_degree == "6/1":
            if (chord[1] - chord[0]) == maj_third:
                note_scale_degree = "5/2"

        converted_chords.append(str(note_scale_degree))
    # except ValueError:
    #     print(note_in_mode, " is not in list. Root note was " + str(root_note) + " key was " + str(true_key) + " " + str(key_mode) )
        
    return converted_chords

# Example 2D array
a = np.array([[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.],[0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 1.],[1., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0.], [1., 0., 1., 0., 0., 0., 1., 0., 0., 1., 0., 0.]])

# Apply the replacement
modified_a = chords_management(a)
print(modified_a)
#!/usr/bin/python

from struct import unpack, pack, calcsize
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import glob
import os
from collections import defaultdict
from datetime import datetime, timedelta
import traceback
import time
import cPickle as pickle
from memory_profiler import profile

def read_HR_file(HR_file):
    full_data = []
    with open(HR_file, 'rb') as f:
        full = f.read()
        fmt = "16s8s8s4siiiiid"
        data_len = (len(full) - calcsize(fmt))/8

        fmt = fmt + str(data_len) + "d"
        full_data = unpack(fmt,full)
        measure_name, uom, ICU_unit, bed, year, month, day, hour, minute, second, data = full_data[0], \
                                                                        full_data[1], \
                                                                        full_data[2],\
                                                                        full_data[3],\
                                                                        full_data[4],\
                                                                        full_data[5],\
                                                                        full_data[6],\
                                                                        full_data[7],\
                                                                        full_data[8],\
                                                                        full_data[9],\
                                                                        full_data[10:]
    f.close()
    
    data = np.reshape(list(data), (4, len(data)/4), order = 'F')
    data_df = pd.DataFrame(data).transpose()
    
    #Create date
    date_str = str(month).zfill(2) + str(day).zfill(2) \
            + str(year).zfill(2) + " " + str(hour).zfill(2) \
            + str(minute).zfill(2) + str(int(second)).zfill(2)
    date_format = '%m%d%Y %H%M%S'
    try:
        date = datetime.strptime(date_str, date_format)
    except:
        date = None

    #delete full data after it has been unpacked
    del full_data   

    #Removes any values outside HR bounds of 10 and 300 
    data_df = data_df[(data_df.iloc[:,0] > 10) & (data_df.iloc[:,0] < 300)]
    
    return date, ICU_unit, data_df 

def combine_HR_files(HR_files, using_files = True, old = {}, new_df = {}, new_date = 0):
    if using_files:
        HR_files = sorted(HR_files, key = lambda x: int(x.split('_')[-2]))
        date = 0
        ICU_unit = ''
        final_df = pd.DataFrame()
        for f in HR_files: 
            if final_df.empty:
                date, ICU_unit, final_df = read_HR_file(f)
                if not final_df.empty:
                    time_last_entry = final_df.iloc[-1,1]
            else:
                date_temp, ICU_unit, cur_df = read_HR_file(f)
                try:
                    diff_between_entries = date_temp - (date + timedelta(seconds = int(time_last_entry)))
                    new_offset = time_last_entry + diff_between_entries.total_seconds()
                    cur_df.iloc[:,1] = cur_df.iloc[:,1] + new_offset
                    final_df = pd.concat([final_df, cur_df], ignore_index=True)
                    time_last_entry = cur_df.iloc[-1,1]
                except: 
                    pass
#                     print "Failed to add by df. File failed is: ", f
#                     print "Shape of df: ", cur_df.shape
#                     traceback.print_exc()
#                     print 
        return date, ICU_unit, final_df

    #using dictionaries
    else:
        try:
            time_last_entry = old['time_offset'].iloc[-1]
            diff_between_entries  = new_date - (old['date'] + timedelta(seconds = int(time_last_entry)))
            new_offset = time_last_entry + diff_between_entries.total_seconds()
            new_df.iloc[:,1] = new_df.iloc[:,1] + new_offset
            old['val'].append(new_df.iloc[:,0])
            old['time_offset'].append(new_df.iloc[:,1])
        except:
            print "Failed to add by dict."
            traceback.print_exc()
            print
        return old
    
def procure_HR_data(data_path):
    counter = 0
    HR_cycles = defaultdict(list)
    directories = next(os.walk(data_path))[1]
    total_pts = len(directories)
    for pt in directories:
        print '\r{0} %done'.format(float(counter+1)/total_pts*100),
        sub_folder_list = []
        counter += 1
        
        #Creates all subfolder names from MRN mapping
        pt_map = pd.read_csv(data_path + pt + '/MRN-Mapping.csv')
        pt_map['subFolder'] = np.where(~pt_map.MRN_WaveCycleTable.isnull(), 
                                       pt_map.UnitBed + "-" 
                                           + pt_map.MRN_WaveCycleTable,
                                       pt_map.UnitBed + "-" + "NONMRN-WaveID-"
                                           + pt_map.WaveCycleUID.astype(str))
                
        #Ensures that folder has at least 15 minutes of data (15*60 / 2 - since data point every 2 seconds)
        pt_map = pt_map[(pt_map.WaveCycleStop - pt_map.WaveCycleStart) > 450]
        sub_folders = pt_map['subFolder'].unique()
        
        #For each sub folder for a pt
        for i, folder in enumerate(sub_folders):
            
            #Get HR file and read/parse binary
            HR_path = data_path + pt + "/" + folder + '/*HR.vital'
            HR_files = glob.glob(HR_path)
            
            #Reads HR file
            date, ICU_unit, data_df = combine_HR_files(HR_files)
            
            #NOTE: Key = patient MRN + _ + ICU_unit (NO BED NUMBER)
            #Again ensures > than 15 minutes of data
            if len(data_df) > 450:  
                key = pt + ICU_unit
                key = key.replace('\x00', '')
#                 
                #Adds ICU stay if doesn't exist OR in different ICU
                # Note: start time + last offset = stop time of last entry
                if key not in HR_cycles.keys() or \
                     (HR_cycles[key][-1]['ICU_unit'] != ICU_unit):
#                       
                    ICU_stay = defaultdict(list)
                    ICU_stay['SA_ID'] = pt.replace('\x00', '')
                    ICU_stay['ICU_unit'] = ICU_unit.replace('\x00', '')
                    ICU_stay['val'] = list(data_df.iloc[:,0])
                    ICU_stay['time_offset'] = list(data_df.iloc[:,1])
                    ICU_stay['date'] = date
                    HR_cycles[key].append(ICU_stay)

                #Adds values to previous entry if in same ICU and difference between entries is less than one hour
                ##FIX!!!!!!!!!!!!
                else:
                    print "ICU COMBINED"       
                    print len(HR_cycles[key])
                    print
                    #Add difference between times and total time so far to CHANGE time offset of addition
                    HR_cycles[key][-1] = combine_HR_files(None, using_files = False, 
                                      old = HR_cycles[key][-1], 
                                      new_df = data_df, new_date = date)
        
    
    print "# of Patients: ", counter
    return HR_cycles


def segment_HR_blocks(HR_cycles, seg_len = 6, keep_percent = 0.67):
    num_blocks = 0
    
    final_HR_cycles = [cycle for sublist in HR_cycles.values() for cycle in sublist]
    final_blocks = []
    
    print "Number of stays: ", len(final_HR_cycles)
    print
    for index, cycle in enumerate(final_HR_cycles):
        print '{0:.2f} %done'.format(float(index+1)/len(final_HR_cycles)*100)
        
        i = 0
        j = 1
        start_offset = cycle['time_offset'][i]
        end_offset = cycle['time_offset'][-1]
        cur_offset = cycle['time_offset'][j]
        print "END: ", end_offset
        if end_offset < 0:
            print "--------------------------NEGATIVE------------------------"
        
        while cur_offset < end_offset:
            #print '\r{0:.2f} %done with particular stay'.format(float(j+1)/len(cycle['time_offset'])*100),
   
            #Still under 6 hr block
            if (cur_offset - start_offset) <= seg_len*60*60:
                j += 1 
                cur_offset = cycle['time_offset'][j]
            
            #Completed 6 hr block
            else: 
                
                #Keep only if >4 hrs of data is present
                if (j-i)/(seg_len*30.0*60.0) > keep_percent:
                    new_block = defaultdict(list)
                    new_block = cycle.copy()
                    new_block['hours_recorded'] = (j - i)/(30.0*60.0) 
                    new_block['time_offset'] = new_block['time_offset'][i:j]
                    new_block['val'] = new_block['val'][i:j]
                    final_blocks.append(new_block)
                    i = j
                    start_offset = cycle['time_offset'][i]
                    j += 1 
                    cur_offset = cycle['time_offset'][j]
                
                    num_blocks += 1
                else:
                    j += 1 
                    cur_offset = cycle['time_offset'][j]
        print "Num blocks:", num_blocks
        print "Patient: ", cycle['SA_ID']
        print "ICU_unit: ", cycle['ICU_unit']
        print
        
    return final_blocks

if __name__ == '__main__':

    import time
    t0 = time.time()
    data_path = 'DATA/March2013Data/'
    final_HR_cycles = procure_HR_data(data_path)
    t1 = time.time()
    total = t1-t0
    print "TOTAL TIME READING: ", total

    t0 = time.time()
    final_blocks = segment_HR_blocks(final_HR_cycles)
    final_blocks_df = pd.DataFrame(final_blocks)
    t1 = time.time()
    total = t1-t0
    print "TOTAL TIME SEGMENTING: ", total
    
    final_blocks_df['start_time'] = final_blocks_df.apply(lambda x: x['date'] + timedelta(seconds = x['time_offset'][0]), axis = 1) 
    final_blocks_df['end_time'] = final_blocks_df.apply(lambda x: x['date'] + timedelta(seconds = x['time_offset'][-1]), axis = 1) 
    final_blocks_df = final_blocks_df[~final_blocks_df.date.isnull()]
    #final_blocks_df['length_of_block'] = final_blocks_df.apply(lambda x: (x['end_time'] - x['start_time']).seconds/(60.0*60), axis = 1)
    print "Finished adding columns to df."
    
    high = datetime(2013, 5, 1)
    low = datetime(2013, 2, 1)
    final_blocks_df = final_blocks_df[(final_blocks_df.start_time > low) & (final_blocks_df.start_time < high)]
    
    print "Limited to dates between 2-22-13 and 4-30-13."
    
    # Output final segemnts to json
    final_blocks_df.to_json('JSONs/HR_segments.json')
    print "Finished creating segments JSON."
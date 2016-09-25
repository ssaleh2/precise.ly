#!/usr/bin/python


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
import sys
from joblib import Parallel, delayed
import multiprocessing


final = pd.read_json('JSONs/final_NO_SERIES_6_hrs.json')

print "Done with loading FINAL NO SERIES with Demographics!"

def add_pharm_class(pharm_class, given_meds, seg_hours = 6):
    global final
    final[pharm_class] = 0
    count = 0
    success = 0
    success_next = 0
    total = len(given_meds[given_meds.PharmaceuticalClass == pharm_class])
    for admin in given_meds[given_meds.PharmaceuticalClass == pharm_class].itertuples(index = False, name = None):
        print "\r{}% done".format(float(count+1)/total*100),
        count += 1
        SA_ID = -4
        TAKEN_TIME = -2
        pt_blocks = final[final['SA_ID'] == admin[SA_ID]]
        i = 0
        found = False
        
        while found == False and i < len(pt_blocks):
            time_diff = admin[TAKEN_TIME] - pt_blocks.iloc[i].start_time
            
            #less than 1 day, so that you can check seconds
            #THEN, ensure that number of seconds is less than length of block (i.e. ~ 6 hours)
            if (0 <= time_diff.days < 1) and \
                (0 <= time_diff.seconds < pt_blocks.iloc[i].hours_recorded*60.0*30):
                
                time_to_add = pt_blocks.iloc[i].end_time - admin[TAKEN_TIME]
                
                #Gives weight to medications
                #Add to current block if new_val > than cur_val (i.e. if med of same class given at 1 hr in rather than 4 hours in)
                new_val = time_to_add.seconds/(pt_blocks.iloc[i].hours_recorded*60.0*60)
                if new_val > final[pharm_class].iloc[pt_blocks.iloc[i].name]:
                    final[pharm_class].iloc[pt_blocks.iloc[i].name] = new_val
                    success += 1
                found = True
            
            #Can be applied to second block
            if i < (len(pt_blocks) - 1):
                time_diff_next = admin[TAKEN_TIME] +  timedelta(seconds = seg_hours*60.0*60.0) - pt_blocks.iloc[i+1].start_time
                    
                if (0 <= time_diff_next.days < 1) and \
                    (0 <= time_diff_next.seconds < pt_blocks.iloc[i+1].hours_recorded*60.0*30):
                    new_val = time_diff_next.seconds/(pt_blocks.iloc[i+1].hours_recorded*60.0*60)
                    
                    if new_val > final[pharm_class].iloc[pt_blocks.iloc[i+1].name]:
              
                        final[pharm_class].iloc[pt_blocks.iloc[i+1].name] = new_val 
                        success_next += 1

           
            i+=1
    #
    if (success + success_next) < 50: 
            final.drop(pharm_class, axis = 1, inplace = True)
    #print final.head()      
    print "Success for %s." %(pharm_class)
    print "Of %d entries, completed CURRENT %d for %0.4f %%" %(count, success, success*100/float(count))
    print "Of %d entries, completed NEXT %d for %0.4f %%" %(count, success_next, success_next*100/float(count))
    
    #return final

if __name__ == '__main__':

	given_meds = pd.read_json('JSONs/given_meds_ALL_25_min.json')

	print "Done with loading given meds!"

	#num_cores = multiprocessing.cpu_count()
	#Parallel(n_jobs = num_cores)(delayed(add_pharm_class)(pharm_class, given_meds) for pharm_class in given_meds.PharmaceuticalClass.unique())
	for pharm_class in given_meds.PharmaceuticalClass.unique():
		add_pharm_class(pharm_class, given_meds)
	print final.head()
	final.to_json("JSONs/final_HR_segments_with_meds_FULL_6_hrs.json")
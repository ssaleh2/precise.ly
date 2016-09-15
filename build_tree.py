import numpy as np
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.neighbors.kde import KernelDensity
from scipy import stats
import time

class decisionnode:
    def __init__(self,col=-1,value=None,num=-1,results=None,tb=None,fb=None, samples = [], gain = -1):
        self.col=col # column index of criteria being tested
        self.value=value # vlaue necessary to get a true result
        self.results=results # dict of results for a branch, None for everything except endpoints
        self.num=num # number of samples in node
        self.tb=tb # true decision nodes 
        self.fb=fb # false decision nodes
        self.samples=samples # all sample ids of node
        self.gain = gain
    def __str__(self):
        return "COL: %s | VALUE: %s | RESULTS: %s | \n NUM: %s | TB: %s | FB: %s \n\n" %(str(self.col), 
                                                    str(self.value),
                                                    str(self.results),
                                                    str(self.num),
                                                    str(self.tb),
                                                    str(self.fb))

def divideset(rows,column,value):
    
    # Function that places a row in the first group 
    # (true) or the second group (false)
    split_function=None
    
    # for numerical values
    if isinstance(value,int) or isinstance(value,float):
        split_function=lambda row:row[column]>value
        
    # for nominal values
    else:
        split_function=lambda row:row[column]==value
   
   # Divide the rows into two lists and return them
    list1=[row for row in rows if split_function(row)]
    list2=[row for row in rows if not split_function(row)]
    return (list1,list2)

# Measures KL divergence SUM of each distribution vs. averge of distributions
def KL_div(PDF_dists):
    
    #KL divergence between each distribution and avg
    divs = []
    
    pdf_avg = np.divide(map(sum, zip(*PDF_dists)), len(PDF_dists))
    for pdf in PDF_dists:
        divs.append(stats.entropy(pdf, pdf_avg))

    KL_div = sum(divs)
    return KL_div

def buildKLtree(rows, scorefun=KL_div, min_leaf_size = 100):
    print "MIN_LEAF_SIZE: ", min_leaf_size

    if len(rows) == 0: 
        print "EMPTY."
        return decisionnode()
    
    best_gain = 0.0
    best_criteria = None
    best_lists = None

    # Assumes last item in each row is pdf dist
    pdf_dists = [item[-1] for item in rows]
#     print pdf_dists[0]
    current_score = scorefun(pdf_dists)
#     print "SCORE", current_score
#     print
    
    len_features = len(rows[0]) - 1 # to get number of features
    count = 0
    
    #all columns of features
    for col in range(1, len_features):
        
        count+=1
        print "\r {0:0.2f}% done".format(float(count)/len_features*100),

        # find different values in this column
        column_values = list(set([row[col] for row in rows]))
        print "Num of Unique Values: ", len(column_values) 
        
        if type(column_values[0]) == float and min(column_values) == 0 and max(column_values) < 1.1:
            column_values = [0]
            print "Decreased column %d to binary." %(col)
            print column_values
        
        if len(column_values) > 25:
        #    #Consider doing unequal bins???
            #_, column_values = np.histogram(column_values, bins = 25)
            bins = [20, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56, 59, 62, 65, 68, 71, 74, 77, 80, 84, 87, 90, 93, 96]
            column_values = [age for age in bins if age <= max(column_values) and age >= min(column_values)]
            
            print "Downsizd to %d bins." %(len(column_values))   
            print column_values
           
        
        # for each possible value, try to divide on that value
        for i, value in enumerate(column_values):
            print "Index: %d | Value: " %i,
            print value
            list1, list2 = divideset(rows, col, value)

            # Information gain
#             p = float(len(list1)) / len(rows)
            pdfs_left = [item[-1] for item in list1]
            pdfs_right = [item[-1] for item in list2]
            gain = current_score - (scorefun(pdfs_left) + scorefun(pdfs_right))
            
            #change numbers for min leaf size
            if gain > best_gain and len(list1) >= min_leaf_size and len(list2) >= min_leaf_size:
                best_gain = gain
                best_criteria = (col, value)
                best_lists = (list1, list2)
    
    print "BEST CRITERIA:", best_criteria
    if best_gain > 0:
        print "Split."
        print
        
        sample_id1 = [item[0] for item in best_lists[0]]
        sample_id2 = [item[0] for item in best_lists[1]]
     
        trueBranch = buildKLtree(best_lists[0])
        falseBranch = buildKLtree(best_lists[1])
        return decisionnode(col=best_criteria[0], value=best_criteria[1],
                tb=trueBranch, fb=falseBranch, samples=sample_id1+sample_id2, gain = best_gain)
    
    else:
        print "Leaf."
        print
        sample_ids = [item[0] for item in rows]
        pdf_dists = [item[-1] for item in rows]
        return decisionnode(num = len(rows), results=scorefun(pdf_dists), samples = sample_ids)

def printtree(tree, columns, indent=''):
    # Is this a leaf node?
    if tree.results!=None:
        
        print "KL: {0:0.2f} | Samples: {1}".format(tree.results, tree.num)
    else:
        # Print the criteria
        print 'Column ' + str(columns[tree.col])+' : '+str(tree.value)+'? '

        # Print the branches
        print indent+'True or > ->',
        printtree(tree.tb,columns, indent+'  ')
        print indent+'False or </= ->',
        printtree(tree.fb,columns, indent+'  ')

if __name__ == '__main__':
	
	import pickle

	# final_NO_SERIES = pd.read_json('JSONs/final_NO_SERIES.json')
	# final_with_meds = pd.read_json('JSONs/final_with_meds_FINAL.json')
	final_with_meds = pd.read_json('JSONs/final_HR_segments_with_meds.json')

	final_with_meds = final_with_meds.drop([u'hist', 'DOB', 'DeathDate', 'SA_ID', 'PAT_ID','date','end_time','start_time', 'length_of_block'], axis = 1)

	#Move sample ID to beginning
	final_with_meds = final_with_meds[[final_with_meds.columns[-1]] + list(final_with_meds.columns[0:-1])]
    
	# full_final = final_with_meds.join(final_NO_SERIES, how='inner', lsuffix = 'med')

	
	#full_final['Gender'] = full_final['Gender'].replace(['Male', 'Female'], [0, 1])
	#full_final.drop(['SA_ID', 'hist'], axis = 1, inplace = True)
	#full_final.drop(['SA_ID'], axis = 1, inplace = True)
	#full_final_subset = full_final[['Age', 'EthnicGroup', 'Gender', 'ICU_unit', 'Race', 'pdf']]

	print "Finished loading in data."

	print "Buliding tree."
	#print "HR Bins - every 5 from 20 to 220."
	print
    
	t0 = time.time()
	min_sample_leaf = 100    
	FINAL_TREE = buildKLtree(final_with_meds.values, scorefun = KL_div, min_leaf_size = min_sample_leaf)
	t1 = time.time()
	total_build = t1 - t0
	#FINAL_TREE = pickle.load(open('Pickles/final_min_leaf_' +str(min_sample_leaf)+ '.tree', 'rb'))
	print "TOTAL TIME BUILDING TREE: ", total_build
	print "FINISHED building tree. Now saving tree..."
	pickle.dump(FINAL_TREE, open('Pickles/final_min_leaf_' +str(min_sample_leaf)+ '.tree', 'wb'))
    
	print "Done saving. Now printing tree..."
	printtree(FINAL_TREE, final_with_meds.columns)
	

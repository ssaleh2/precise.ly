import numpy as np
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.neighbors.kde import KernelDensity
from scipy import stats

class decisionnode:
    def __init__(self,col=-1,value=None,results=None,tb=None,fb=None):
        self.col=col # column index of criteria being tested
        self.value=value # vlaue necessary to get a true result
        self.results=results # dict of results for a branch, None for everything except endpoints
        self.tb=tb # true decision nodes 
        self.fb=fb # false decision nodes
    def __str__(self):
        return "COL: %s | VALUE: %s | RESULTS: %s | TB: %s | FB: %s \n\n" %(str(self.col), 
                                                                       str(self.value),
                                                                       str(self.results),
                                                                       str(self.tb),
                                                                       str(self.fb))

def divideset(rows,column,value):
    # Make a function that tells us if a row is in the first group 
    # (true) or the second group (false)
    split_function=None
    # for numerical values
    if isinstance(value,int) or isinstance(value,float):
        split_function=lambda row:row[column]>=value
    # for nominal values
    else:
        split_function=lambda row:row[column]==value
   
   # Divide the rows into two lists and return them
    list1=[row for row in rows if split_function(row)] # if split_function(row) 
    list2=[row for row in rows if not split_function(row)]
    return (list1,list2)

# Entropy is the sum of p(x)log(p(x)) across all the different possible results
#targets should be array of arrays of pdfs
def KL_div(PDF_dists):
    #KL divergence between each distribution and avg
    divs = []
    #print "SUM 10 PDFS: ", map(sum, zip(*PDF_dists[0:10]))
    
    pdf_avg = np.divide(map(sum, zip(*PDF_dists)), len(PDF_dists))
    for pdf in PDF_dists:
        divs.append(scipy.stats.entropy(pdf, pdf_avg))

    KL_div = sum(divs)
    return KL_div

def buildKLtree(rows, scorefun=KL_div):
    
    if len(rows) == 0: 
        print "EMPTY."
        return decisionnode()
    
    best_gain = 0.0
    best_criteria = None
    best_lists = None

#     print "ROWS: "
#     print rows
    
    ####REMEMBER TO CHANGE DATA SO PDF IS LAST COLUMN
    # Assumes last item in each row is pdf dist
    pdf_dists = [item[-1] for item in rows]
#     print pdf_dists[0]
    current_score = scorefun(pdf_dists)
#     print "SCORE", current_score
#     print
    
    len_features = len(rows[0]) - 1 # to get number of features
    
    #all columns of features
    for col in range(0, len_features):
        
        # find different values in this column
        column_values = set([row[col] for row in rows])

        # for each possible value, try to divide on that value
        for value in column_values:
            list1, list2 = divideset(rows, col, value)

            # Information gain
#             p = float(len(list1)) / len(rows)
            pdfs_left = [item[-1] for item in list1]
            pdfs_right = [item[-1] for item in list2]
            gain = current_score - (scorefun(pdfs_left) + scorefun(pdfs_right))
            
        #IS THIS WHERE min leaf size?
            if gain > best_gain and len(list1) > 0 and len(list2) > 0:
                best_gain = gain
                best_criteria = (col, value)
                best_lists = (list2, list2)
    
    #print "BEST CRITERIA: "
    #print best_criteria
    if best_gain > 0:
        print "Split."
        trueBranch = buildtree(best_lists[0])
        falseBranch = buildtree(best_lists[1])
        return decisionnode(col=best_criteria[0], value=best_criteria[1],
                tb=trueBranch, fb=falseBranch)
    else:
        print "Leaf."
        return decisionnode(results=uniquecounts(rows))

def printtree(tree,indent=''):
    # Is this a leaf node?
    if tree.results!=None:
        print str(tree.results)
    else:
        # Print the criteria
        print 'Column ' + str(tree.col)+' : '+str(tree.value)+'? '
​
        # Print the branches
        print indent+'True->',
        printtree(tree.tb,indent+'  ')
        print indent+'False->',
        printtree(tree.fb,indent+'  ')

if __name__ == '__main__':
	

	# final_NO_SERIES = pd.read_json('JSONs/final_NO_SERIES.json')
	# final_with_meds = pd.read_json('JSONs/final_with_meds_FINAL.json')
	# final_NO_SERIES = final_NO_SERIES.drop(['DOB', 'DeathDate', 'PAT_ID','index','date','end_time','start_time', 'length_of_block', 'index'], axis =1)
	# final_with_meds = final_with_meds.drop([u'Age', u'EthnicGroup', u'Gender', u'ICU_unit', u'Race',
 #       u'hist', 'DOB', 'DeathDate', 'PAT_ID','index','date','end_time','start_time', 'pdf', 'length_of_block', 'index', 'date', 'end_time', 'index', 'length_of_block', 'pdf', 'hist', 'start_time'], axis = 1)
	# full_final = final_with_meds.join(final_NO_SERIES, how='inner', lsuffix = 'med')

	full_final = pd.read_json('JSONs/full_final.json')
	
	full_final['Gender'] = full_final['Gender'].replace(['Male', 'Female'], [0, 1])
	full_final.drop(['SA_ID', 'hist'], axis = 1, inplace = True)
	full_final.drop(['SA_IDmed'], axis = 1, inplace = True)

	print "Finished loading in data."


	print "Buliding tree."
	FINAL_TREE = buildKLtree(full_final.values)
	print "FINISHED building tree. Now building tree..."
	
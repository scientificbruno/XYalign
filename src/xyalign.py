from __future__ import division
import argparse
import os
import subprocess
import sys
from matplotlib import pyplot as plt
import pysam

def main():
	""" Main program"""
	args = parse_args()
	## First round of Platypus calling
	
	
def parse_args():
	"""Parse command-line arguments"""
	parser = argparse.ArgumentParser(description="XYalign.  A tool to estimate sex chromosome ploidy and use this information to correct mapping and variant calling on the sex chromosomes.")
	parser.add_argument("--bam", required=True,
						help="Input bam file.")
	parser.add_argument("--ref", required=True,
						help="Path to reference sequence (including file name).")
	parser.add_argument("--chromosomes", "-c", default=["chrX","chrY","chr19"],
						help="Chromosomes to analyze.")
	
						
def platypus_calling(bam, ref, chroms, cpus, output_file):
	""" Uses platypus to make variant calls on provided bam file
	
	bam is input bam file
	ref is path to reference sequence
	chroms is a list of chromosomes to call on, e.g., ["chrX", "chrY", "chr19"]
	cpus is the number of threads/cores to use
	output_file is the name of the output vcf
	"""
	regions = ','.join(map(str,chroms))
	command_line = "platypus callVariants --bamFiles {} -o {} --refFile {} --nCPU {} --regions {} --assemble 1".format(bam, output_file, ref, cpus, regions)
	return_code = subprocess.call(command_line, shell=True)
	if return_code == 0:
		return True
	else:
		return None
		
def parse_platypus_VCF(filename,qualCutoff):
    infile = open("{}".format(filename),'r')
    positions = []
    quality = []
    readBalance = []
    for line in infile:
        if line[0]=='#':
            continue
        cols=line.strip('\n').split('\t')
        pos = int(cols[1])
        qual = float(cols[5])
        if qual < qualCutoff:
            continue
        TR = cols[7].split(';')[17].split('=')[1]
        TC = cols[7].split(';')[14].split('=')[1]
        if ',' in TR or ',' in TC:
            continue
        if (float(TR)==0) or (float(TC) == 0):
            continue    
        ReadRatio = float(TR)/float(TC)
        
        # Add to arrays
        readBalance.append(ReadRatio)
        positions.append(pos)
        quality.append(qual)
        
    
	return (positions,quality,readBalance)
	
def plot_read_balance(positions,readBalance,sampleID,MarkerSize,MarkerAlpha,Xlim):
    if "X" in sampleID:
        Color="green"
    elif "Y" in sampleID:
        Color = "blue"
    else:
    	Color = "red"
    fig = plt.figure(figsize=(15,5))
    axes = fig.add_subplot(111)
    axes.scatter(positions,readBalance,c=Color,alpha=MarkerAlpha,s=MarkerSize,lw=0)
    axes.set_xlim(0,Xlim)
    axes.set_title(sampleID)
    axes.set_xlabel("Chromosomal Coordinate")
    axes.set_ylabel("Read Balance")
    #print(len(positions))
    plt.savefig("%s_ReadBalance_GenomicScatter.svg"%sampleID)
    plt.savefig("%s_ReadBalance_GenomicScatter.png"%sampleID)
	#plt.show()
	
def hist_read_balance(readBalance,sampleID):
    if "X" in sampleID:
        Color="green"
    elif "Y" in sampleID:
        Color = "blue"
    else:
    	Color = "red"
    fig = plt.figure(figsize=(8,8))
    axes = fig.add_subplot(111)
    axes.set_title(sampleID)
    axes.set_xlabel("Read Balance")
    axes.set_ylabel("Frequency")
    axes.hist(readBalance,bins=50,color=Color)
    plt.savefig("%s_ReadBalance_Hist.svg"%sampleID)
    plt.savefig("%s_ReadBalance_Hist.png"%sampleID)
	#plt.show()
	